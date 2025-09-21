import socket
import threading
import sys

class Peer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.me = f"{self.host}:{self.port}" # Identificador único para este peer
        self.peers = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

    def handle_client(self, client_socket, addr):
        print(f"[CONEXÃO ENTRANTE] Conectado a {addr}")
        self.peers[client_socket] = addr
        
        while True:
            try:
                message_bytes = client_socket.recv(1024)
                if not message_bytes:
                    break
                
                # ### MUDANÇA 1: EXIBIR A MENSAGEM RECEBIDA ###
                # A lógica de exibir a mensagem na tela foi adicionada aqui.
                message = message_bytes.decode('utf-8')
                remetente, conteudo = message.split('|', 1)

                # Prepara a string para exibição
                display_message = f"[{remetente} disse]: {conteudo}"

                # Limpa a linha atual e exibe a mensagem (mesma lógica do cliente_multithread.py)
                sys.stdout.write('\r' + ' ' * 80 + '\r')
                sys.stdout.write(display_message + '\n')
                sys.stdout.write("Você: ")
                sys.stdout.flush()

                # ### MUDANÇA 2: RETRANSMITIR A MENSAGEM ORIGINAL ###
                # Garante que a mensagem original (com remetente) seja retransmitida.
                self.broadcast(message_bytes, client_socket)
                
            except:
                break
        
        print(f"[DESCONECTADO] Peer {addr} desconectou.")
        del self.peers[client_socket]
        client_socket.close()

    def broadcast(self, message_bytes, sender_socket):
        for peer_socket in list(self.peers.keys()):
            if peer_socket != sender_socket:
                try:
                    peer_socket.send(message_bytes)
                except:
                    addr = self.peers.pop(peer_socket, None)
                    peer_socket.close()
                    print(f"[PEER REMOVIDO] Conexão com {addr} perdida.")

    def listen_for_connections(self):
        print(f"[ESCUTANDO] Peer escutando em {self.host}:{self.port}")
        while True:
            client_socket, addr = self.server_socket.accept()
            thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
            thread.daemon = True
            thread.start()

    def connect_to_peer(self, peer_host, peer_port):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((peer_host, peer_port))
            
            thread = threading.Thread(target=self.handle_client, args=(client_socket, (peer_host, peer_port)))
            thread.daemon = True
            thread.start()
            print(f"[CONEXÃO SAINDO] Conectado com sucesso ao peer {peer_host}:{peer_port}")

        except Exception as e:
            print(f"[ERRO] Não foi possível conectar ao peer {peer_host}:{peer_port}. Erro: {e}")

    def start(self):
        server_thread = threading.Thread(target=self.listen_for_connections)
        server_thread.daemon = True
        server_thread.start()
        
        # Imprime o primeiro prompt para o usuário
        sys.stdout.write("Você: ")
        sys.stdout.flush()
        
        while True:
            msg_content = input("") # Input sem prompt
            if msg_content:
                # ### MUDANÇA 3: FORMATAR A MENSAGEM ANTES DE ENVIAR ###
                # Adiciona o identificador do remetente à mensagem.
                formatted_message = f"{self.me}|{msg_content}"
                self.broadcast(formatted_message.encode('utf-8'), None)

            # Re-imprime o prompt para a próxima mensagem
            sys.stdout.write("Você: ")
            sys.stdout.flush()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python peer_final.py <SEU_HOST> <SUA_PORTA> [HOST_DO_PEER_EXISTENTE] [PORTA_DO_PEER_EXISTENTE]")
        sys.exit(1)

    my_host = sys.argv[1]
    my_port = int(sys.argv[2])
    
    peer = Peer(my_host, my_port)

    if len(sys.argv) == 5:
        peer_host = sys.argv[3]
        peer_port = int(sys.argv[4])
        connect_thread = threading.Thread(target=peer.connect_to_peer, args=(peer_host, peer_port))
        connect_thread.daemon = True
        connect_thread.start()

    peer.start()