import hashlib
import time
import json
import socket
import threading
import pickle

class Block:
    def __init__(self, index, timestamp, data):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.prev_hash = 0
        self.hash = self.calHash()
    
    def calHash(self):
        return hashlib.sha256(str(self.index).encode() 
                              + str(self.data).encode()
                              + str(self.timestamp).encode()
                              + str(self.prev_hash).encode()
                              ).hexdigest()
    
    def __str__(self):
        return f"Block(index: {self.index}, timestamp: {self.timestamp}, data: {self.data}, prev_hash: {self.prev_hash}, hash: {self.hash})"

class BlockChain:
    def __init__(self):
        self.chain = []
        self.createGenesis()
    
    def createGenesis(self):
        self.chain.append(Block(0, time.time(), 'Genesis'))
    
    def addBlock(self, nBlock):
        nBlock.prev_hash = self.chain[len(self.chain)-1].hash
        nBlock.hash = nBlock.calHash()
        self.chain.append(nBlock)
    
    def isValid(self):
        i = 1
        while i < len(self.chain):
            if self.chain[i].hash != self.chain[i].calHash():
                return False
            if self.chain[i].prev_hash != self.chain[i-1].hash:
                return False
            i += 1
        return True
    
    def __str__(self):
        return '\n'.join([str(block) for block in self.chain])

class Peer:
    def __init__(self, id, port):
        self.id = id
        self.port = port
        self.peers = {}
        self.blockchain = BlockChain()
        self.prepare_msgs = {}
        self.commit_msgs = {}
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.start()
    
    def connect_peer(self, peer_id, peer_port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', peer_port))
            self.peers[peer_id] = peer_port
            print(f"Connected to peer {peer_id} on port {peer_port}")
            sock.close()
        except Exception as e:
            print(f"Failed to connect to peer {peer_id} on port {peer_port}: {e}")
    
    def run_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', self.port))
        server.listen(5)
        while True:
            client_socket, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()
    
    def handle_client(self, client_socket):
        try:
            data = client_socket.recv(4096)
            if data:
                message = pickle.loads(data)
                if message['type'] == 'block':
                    self.handle_propose(message['block'])
                elif message['type'] == 'prepare':
                    self.handle_prepare(message['block'], message['peer_id'])
                elif message['type'] == 'commit':
                    self.handle_commit(message['block'], message['peer_id'])
        except EOFError as e:
            print(f"EOFError: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            client_socket.close()
    
    def handle_propose(self, block):
        print(f"Propose phase started for block {block.index}")
        self.prepare_msgs[block.hash] = set()
        self.commit_msgs[block.hash] = set()
        self.broadcast_prepare(block)
    
    def handle_prepare(self, block, peer_id):
        print(f"Prepare phase: received prepare from peer {peer_id} for block {block.index}")
        self.prepare_msgs[block.hash].add(peer_id)
        if len(self.prepare_msgs[block.hash]) > (len(self.peers) // 3) * 2: # Simple majority rule
            self.broadcast_commit(block)
    
    def handle_commit(self, block, peer_id):
        print(f"Commit phase: received commit from peer {peer_id} for block {block.index}")
        self.commit_msgs[block.hash].add(peer_id)
        if len(self.commit_msgs[block.hash]) > (len(self.peers) // 3) * 2: # Simple majority rule
            self.blockchain.addBlock(block)
            print(f"Block {block.index} added to the blockchain.")
    
    def broadcast_prepare(self, block):
        for peer_id, peer_port in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', peer_port))
                message = {'type': 'prepare', 'block': block, 'peer_id': self.id}
                sock.send(pickle.dumps(message))
                sock.close()
                print(f"Broadcasted prepare to peer {peer_id} for block {block.index}")
            except Exception as e:
                print(f"Failed to send prepare to peer {peer_id} on port {peer_port}: {e}")
    
    def broadcast_commit(self, block):
        for peer_id, peer_port in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', peer_port))
                message = {'type': 'commit', 'block': block, 'peer_id': self.id}
                sock.send(pickle.dumps(message))
                sock.close()
                print(f"Broadcasted commit to peer {peer_id} for block {block.index}")
            except Exception as e:
                print(f"Failed to send commit to peer {peer_id} on port {peer_port}: {e}")
    
    def propose_block(self, block):
        print(f"Proposing block {block.index}")
        self.broadcast_propose(block)
        self.handle_propose(block)
    
    def broadcast_propose(self, block):
        for peer_id, peer_port in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', peer_port))
                message = {'type': 'block', 'block': block}
                sock.send(pickle.dumps(message))
                sock.close()
                print(f"Broadcasted block proposal to peer {peer_id} for block {block.index}")
            except Exception as e:
                print(f"Failed to send block to peer {peer_id} on port {peer_port}: {e}")
    
def main():
    id = input("Enter your peer ID: ")
    port = int(input("Enter your port number: "))
    peer = Peer(id, port)

    while True:
        print("1. Add peer")
        print("2. Add block")
        print("3. Print blockchain")
        print("4. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            peer_id = input("Enter peer ID to connect: ")
            peer_port = int(input("Enter peer port number: "))
            peer.connect_peer(peer_id, peer_port)
        elif choice == "2":
            data = input("Enter block data: ")
            block = Block(len(peer.blockchain.chain), time.time(), data)
            peer.propose_block(block)
        elif choice == "3":
            print("Current Blockchain:")
            print(peer.blockchain)
        elif choice == "4":
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
