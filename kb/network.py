import socket
import threading
import pickle

class Network:
    def __init__(self, peer):
        self.peer = peer
    
    def run_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', self.peer.port))
        server.listen(5)
        print(f"Peer {self.peer.id} listening on port {self.peer.port}")
        while True:
            client_socket, addr = server.accept()
            print(f"Connection accepted from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()
    
    def handle_client(self, client_socket):
        try:
            data = client_socket.recv(4096)
            if data:
                message = pickle.loads(data)
                self.peer.handle_message(message, client_socket)
        except EOFError as e:
            print(f"EOFError: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            client_socket.close()
    
    def send_message(self, peer_port, message):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', peer_port))
            sock.send(pickle.dumps(message))
            sock.close()
        except Exception as e:
            print(f"Failed to send message to port {peer_port}: {e}")

    def broadcast_message(self, message):
        for peer_id, peer_port in self.peer.peers.items():
            self.send_message(peer_port, message)
