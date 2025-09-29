# peer.py
import socket
import threading
import sys
import queue

class Peer:
    def __init__(self, host, port, name, msg_queue):
        self.host = host
        self.port = port
        self.name = name
        self.me = f"{self.name} ({self.host}:{self.port})"
        self.peers = {}            # socket -> addr
        self.lock = threading.Lock()
        self.msg_queue = msg_queue
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

    def handle_client(self, client_socket, addr):
        print(f"[CONEXÃO] Conectado a {addr}")
        with self.lock:
            self.peers[client_socket] = addr

        try:
            while True:
                message_bytes = client_socket.recv(1024)
                if not message_bytes:
                    break

                try:
                    message = message_bytes.decode('utf-8')
                    remetente, conteudo = message.split('|', 1)
                except Exception:
                    # mensagem malformada; ignora
                    continue

                display_message = f"[{remetente} disse]: {conteudo}"
                # limpa linha atual e escreve mensagem
                sys.stdout.write('\r' + ' ' * 80 + '\r')
                sys.stdout.write(display_message + '\n')
                sys.stdout.write("Você: ")
                sys.stdout.flush()

                # retransmite (flooding)
                self.broadcast(message_bytes, client_socket)
        finally:
            with self.lock:
                if client_socket in self.peers:
                    del self.peers[client_socket]
            client_socket.close()
            print(f"[DESCONECTADO] {addr}")

    def broadcast(self, message_bytes, sender_socket):
        with self.lock:
            for peer_socket in list(self.peers.keys()):
                if peer_socket is sender_socket:
                    continue
                try:
                    peer_socket.send(message_bytes)
                except Exception:
                    addr = self.peers.pop(peer_socket, None)
                    try:
                        peer_socket.close()
                    except:
                        pass
                    print(f"[PEER REMOVIDO] Conexão com {addr} perdida.")

    def listen_for_connections(self):
        print(f"[ESCUTANDO] Peer em {self.host}:{self.port}")
        while True:
            client_socket, addr = self.server_socket.accept()
            t = threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True)
            t.start()

    def connect_to_peer(self, peer_host, peer_port):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((peer_host, peer_port))
            # Reaproveita handle_client para gerenciar essa conexão também
            t = threading.Thread(target=self.handle_client, args=(client_socket, (peer_host, peer_port)), daemon=True)
            t.start()
            print(f"[CONECTADO] {peer_host}:{peer_port}")
        except Exception as e:
            print(f"[ERRO] Não foi possível conectar a {peer_host}:{peer_port} -> {e}")

    def process_messages(self):
        """Consome a fila interna e faz broadcast das mensagens locais."""
        while True:
            msg_content = self.msg_queue.get()  # bloqueia até ter mensagem
            if msg_content is None:
                # protocolo para encerrar (opcional)
                break
            formatted_message = f"{self.me}|{msg_content}"
            self.broadcast(formatted_message.encode('utf-8'), None)

    def start(self):
        # Thread servidor
        server_thread = threading.Thread(target=self.listen_for_connections, daemon=True)
        server_thread.start()

        # Thread consumidora da fila
        consumer_thread = threading.Thread(target=self.process_messages, daemon=True)
        consumer_thread.start()

        # Thread de input do usuário (SEM multiprocessing)
        input_thread = threading.Thread(target=self.user_input_thread, daemon=True)
        input_thread.start()

        # Mantém o main vivo; captura Ctrl+C para encerrar graciosamente
        try:
            while True:
                server_thread.join(1)
                consumer_thread.join(1)
                input_thread.join(1)
        except KeyboardInterrupt:
            print("\n[SAINDO] Encerrando...")
            # opcional: fechar sockets
            try:
                self.server_socket.close()
            except:
                pass
            # sinaliza fim ao consumer (se desejar)
            try:
                self.msg_queue.put(None)
            except:
                pass
            sys.exit(0)

    def user_input_thread(self):
        """Thread que lê do stdin e coloca na fila."""
        while True:
            try:
                msg = input("Você: ")
            except EOFError:
                # stdin fechado; termina a thread
                break
            if msg is None:
                continue
            if msg.strip() == "":
                continue
            self.msg_queue.put(msg)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python peer.py <SEU_HOST> <SUA_PORTA> <SEU_NOME> [HOST_DO_PEER_EXISTENTE] [PORTA_DO_PEER_EXISTENTE]")
        sys.exit(1)

    my_host = sys.argv[1]
    my_port = int(sys.argv[2])
    my_name = sys.argv[3]

    msg_queue = queue.Queue()

    peer = Peer(my_host, my_port, my_name, msg_queue)

    if len(sys.argv) == 6:
        peer_host = sys.argv[4]
        peer_port = int(sys.argv[5])
        t = threading.Thread(target=peer.connect_to_peer, args=(peer_host, peer_port), daemon=True)
        t.start()

    peer.start()
