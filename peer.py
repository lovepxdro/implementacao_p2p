# peer.py
"""Aplicação de chat peer-to-peer com suporte a concorrência e paralelismo.

Este módulo implementa um nó (``Peer``) que pode aceitar conexões de outros
peers e encaminhar mensagens para todos os participantes conectados. Ele
utiliza *threads* para operações de rede e entrada do usuário, além de um
processo separado responsável por persistir o histórico de mensagens em disco.
"""

from __future__ import annotations

import multiprocessing as mp
import queue
import socket
import sys
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple

BUFFER_SIZE = 1024


def log_worker(log_queue: "mp.Queue[Optional[Tuple[str, str]]]", log_path: str) -> None:
    """Processo que persiste eventos do chat em um arquivo de log."""

    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("\n=== Nova sessão iniciada ===\n")
        log_file.flush()

        while True:
            entry = log_queue.get()
            if entry is None:
                log_file.write("=== Sessão encerrada ===\n")
                log_file.flush()
                break

            timestamp, text = entry
            log_file.write(f"[{timestamp}] {text}\n")
            log_file.flush()


class Peer:
    """Representa um nó da rede P2P."""

    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        msg_queue: "queue.Queue[Optional[str]]",
        log_queue: Optional["mp.Queue[Optional[Tuple[str, str]]]"] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.me = f"{self.name} ({self.host}:{self.port})"

        self.peers: Dict[socket.socket, Tuple[str, int]] = {}
        self.lock = threading.Lock()
        self.console_lock = threading.Lock()
        self.msg_queue = msg_queue
        self.log_queue = log_queue
        self.shutdown_event = threading.Event()
        self.msg_sentinel_sent = False
        self.log_sentinel_sent = False
        self.prompt = f"{self.name}> "

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.server_socket.settimeout(1.0)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def log_event(self, text: str) -> None:
        if not self.log_queue:
            return
        try:
            self.log_queue.put((datetime.now().isoformat(timespec="seconds"), text))
        except Exception:
            pass

    def print_cli(self, text: str) -> None:
        """Imprime mensagens sincronizadas com o prompt atual."""

        with self.console_lock:
            sys.stdout.write("\r" + " " * 120 + "\r")
            sys.stdout.write(f"{text}\n")
            if not self.shutdown_event.is_set():
                sys.stdout.write(self.prompt)
            sys.stdout.flush()

    # ------------------------------------------------------------------
    # Loop principal de atendimento de clientes
    # ------------------------------------------------------------------
    def handle_client(self, client_socket: socket.socket, addr: Tuple[str, int]) -> None:
        self.print_cli(f"[CONEXÃO] Conectado a {addr}")
        self.log_event(f"Conexão estabelecida com {addr}")

        with self.lock:
            self.peers[client_socket] = addr

        try:
            while not self.shutdown_event.is_set():
                try:
                    message_bytes = client_socket.recv(BUFFER_SIZE)
                except ConnectionResetError:
                    break
                except OSError:
                    break

                if not message_bytes:
                    break

                try:
                    message = message_bytes.decode("utf-8")
                    remetente, conteudo = message.split("|", 1)
                except Exception:
                    # mensagem malformada; ignora
                    continue

                display_message = f"[{remetente} disse]: {conteudo}"
                self.log_event(f"Mensagem recebida de {remetente}: {conteudo}")

                self.print_cli(display_message)

                # retransmite (flooding)
                self.broadcast(message_bytes, client_socket)
        finally:
            with self.lock:
                if client_socket in self.peers:
                    del self.peers[client_socket]

            try:
                client_socket.close()
            except Exception:
                pass

            self.print_cli(f"[DESCONECTADO] {addr}")
            self.log_event(f"Conexão encerrada com {addr}")

    # ------------------------------------------------------------------
    def broadcast(self, message_bytes: bytes, sender_socket: Optional[socket.socket]) -> None:
        with self.lock:
            sockets = list(self.peers.keys())

        for peer_socket in sockets:
            if sender_socket is not None and peer_socket is sender_socket:
                continue

            try:
                peer_socket.send(message_bytes)
            except Exception:
                addr = None
                with self.lock:
                    addr = self.peers.pop(peer_socket, None)
                try:
                    peer_socket.close()
                except Exception:
                    pass
                self.print_cli(f"[PEER REMOVIDO] Conexão com {addr} perdida.")
                self.log_event(f"Peer removido: {addr}")

    # ------------------------------------------------------------------
    def listen_for_connections(self) -> None:
        self.print_cli(f"[ESCUTANDO] Peer em {self.host}:{self.port}")
        while not self.shutdown_event.is_set():
            try:
                client_socket, addr = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                if self.shutdown_event.is_set():
                    break
                continue

            thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, addr),
                daemon=True,
            )
            thread.start()

        self.print_cli("[ESCUTA ENCERRADA]")

    # ------------------------------------------------------------------
    def connect_to_peer(self, peer_host: str, peer_port: int) -> None:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((peer_host, peer_port))
            thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, (peer_host, peer_port)),
                daemon=True,
            )
            thread.start()
            self.print_cli(f"[CONECTADO] {peer_host}:{peer_port}")
            self.log_event(f"Conectado manualmente a {peer_host}:{peer_port}")
        except Exception as exc:
            self.print_cli(
                f"[ERRO] Não foi possível conectar a {peer_host}:{peer_port} -> {exc}"
            )
            self.log_event(f"Falha ao conectar em {peer_host}:{peer_port}: {exc}")

    # ------------------------------------------------------------------
    def process_messages(self) -> None:
        """Consome a fila interna e faz broadcast das mensagens locais."""
        while True:
            msg_content = self.msg_queue.get()
            if msg_content is None:
                break

            if msg_content.strip() == "":
                continue

            self.log_event(f"Mensagem local enviada: {msg_content}")
            formatted_message = f"{self.me}|{msg_content}"
            self.broadcast(formatted_message.encode("utf-8"), None)

    def show_peers(self) -> None:
        with self.lock:
            if not self.peers:
                peers_snapshot: list[str] = []
            else:
                peers_snapshot = [f"- {addr[0]}:{addr[1]}" for addr in self.peers.values()]

        if not peers_snapshot:
            self.print_cli("Nenhum peer conectado no momento.")
        else:
            message = "Peers conectados:\n" + "\n".join(peers_snapshot)
            self.print_cli(message)

    def show_help(self) -> None:
        help_lines = [
            "Comandos disponíveis:",
            "/help                -> mostra esta ajuda",
            "/connect HOST PORT   -> conecta a um peer ativo",
            "/peers               -> lista peers conectados",
            "/quit                -> encerra o programa",
            "Qualquer outro texto será enviado como mensagem ao chat.",
        ]
        self.print_cli("\n".join(help_lines))

    def handle_command(self, command: str) -> bool:
        """Processa comandos digitados na linha de comando.

        Retorna ``True`` se o comando solicitar o encerramento da thread de
        entrada; caso contrário, ``False``.
        """

        tokens = command[1:].strip().split()
        if not tokens:
            self.print_cli("Comando vazio. Digite /help para ajuda.")
            return False

        cmd = tokens[0].lower()
        args = tokens[1:]

        if cmd in {"quit", "exit"}:
            self.print_cli("Encerrando a partir do comando /quit...")
            self.shutdown_event.set()
            return True

        if cmd == "help":
            self.show_help()
            return False

        if cmd == "peers":
            self.show_peers()
            return False

        if cmd == "connect":
            if len(args) < 2:
                self.print_cli("Uso: /connect HOST PORT")
                return False
            host, port_str = args[0], args[1]
            try:
                port_value = int(port_str)
            except ValueError:
                self.print_cli("Porta inválida. Use um número inteiro.")
                return False
            self.print_cli(f"Conectando a {host}:{port_value}...")
            self.connect_to_peer(host, port_value)
            return False

        self.print_cli(f"Comando desconhecido: /{cmd}. Digite /help para ajuda.")
        return False

    # ------------------------------------------------------------------
    def start(self) -> None:
        server_thread = threading.Thread(target=self.listen_for_connections, daemon=True)
        consumer_thread = threading.Thread(target=self.process_messages, daemon=True)
        input_thread = threading.Thread(target=self.user_input_thread, daemon=True)

        server_thread.start()
        consumer_thread.start()
        input_thread.start()

        self.print_cli("Interface pronta. Digite /help para ver os comandos disponíveis.")
        self.log_event("Peer inicializado e pronto para mensagens.")

        threads = (server_thread, consumer_thread, input_thread)
        try:
            while any(t.is_alive() for t in threads):
                for t in threads:
                    t.join(timeout=0.5)
        except KeyboardInterrupt:
            self.print_cli("[SAINDO] Encerrando...")
        finally:
            self.shutdown()
            for t in threads:
                t.join(timeout=1.0)

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        just_set = not self.shutdown_event.is_set()
        self.shutdown_event.set()
        if just_set:
            self.log_event("Iniciando desligamento do peer.")

        try:
            self.server_socket.close()
        except Exception:
            pass

        with self.lock:
            for peer_socket in list(self.peers.keys()):
                try:
                    peer_socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    peer_socket.close()
                except Exception:
                    pass
            self.peers.clear()

        if not self.msg_sentinel_sent:
            try:
                self.msg_queue.put(None)
                self.msg_sentinel_sent = True
            except Exception:
                pass

        if self.log_queue and not self.log_sentinel_sent:
            try:
                self.log_event("Peer desligado.")
                self.log_queue.put(None)
                self.log_sentinel_sent = True
            except Exception:
                pass

    # ------------------------------------------------------------------
    def user_input_thread(self) -> None:
        """Thread que lê do stdin e coloca na fila."""
        while not self.shutdown_event.is_set():
            try:
                msg = input(self.prompt)
            except EOFError:
                break
            except KeyboardInterrupt:
                break

            if msg is None:
                continue

            trimmed = msg.strip()
            if trimmed == "":
                continue

            if trimmed.startswith("/"):
                should_exit = self.handle_command(trimmed)
                if should_exit:
                    break
                continue

            self.msg_queue.put(msg)

        if not self.msg_sentinel_sent:
            try:
                self.msg_queue.put(None)
                self.msg_sentinel_sent = True
            except Exception:
                pass


def parse_args(argv: list[str]) -> Tuple[str, int, str, Optional[str], Optional[int]]:
    if len(argv) < 4:
        print(
            "Uso: python peer.py <SEU_HOST> <SUA_PORTA> <SEU_NOME> "
            "[HOST_DO_PEER_EXISTENTE] [PORTA_DO_PEER_EXISTENTE]"
        )
        sys.exit(1)

    host = argv[1]
    port = int(argv[2])
    name = argv[3]

    peer_host: Optional[str] = None
    peer_port: Optional[int] = None
    if len(argv) == 6:
        peer_host = argv[4]
        peer_port = int(argv[5])

    return host, port, name, peer_host, peer_port


if __name__ == "__main__":
    mp.freeze_support()

    my_host, my_port, my_name, bootstrap_host, bootstrap_port = parse_args(sys.argv)

    msg_queue: "queue.Queue[Optional[str]]" = queue.Queue()
    log_queue: "mp.Queue[Optional[Tuple[str, str]]]" = mp.Queue()
    log_path = f"chat_history_{my_port}.log"

    logger_process = mp.Process(target=log_worker, args=(log_queue, log_path))
    logger_process.start()

    peer = Peer(my_host, my_port, my_name, msg_queue, log_queue=log_queue)

    connect_thread: Optional[threading.Thread] = None
    if bootstrap_host and bootstrap_port:
        connect_thread = threading.Thread(
            target=peer.connect_to_peer,
            args=(bootstrap_host, bootstrap_port),
            daemon=True,
        )
        connect_thread.start()

    try:
        peer.start()
    finally:
        peer.shutdown()
        if not peer.log_sentinel_sent:
            try:
                log_queue.put(None)
            except Exception:
                pass
        logger_process.join(timeout=5.0)
        if connect_thread:
            connect_thread.join(timeout=1.0)
