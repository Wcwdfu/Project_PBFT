import hashlib
import time
import socket
import threading
import pickle

class Block:
    def __init__(self, index, timestamp, data, prev_hash='0'):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.prev_hash = prev_hash
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
    def __init__(self, genesis_block=None):
        self.chain = []
        if genesis_block:
            self.chain.append(genesis_block)
        else:
            self.createGenesis()
    
    def createGenesis(self):
        genesis_block = Block(0, time.time(), 'Genesis')
        self.chain.append(genesis_block)
    
    def addBlock(self, nBlock):
        nBlock.prev_hash = self.chain[-1].hash
        nBlock.hash = nBlock.calHash()
        self.chain.append(nBlock)
    
    def isValid(self):
        for i in range(1, len(self.chain)):
            if self.chain[i].hash != self.chain[i].calHash():
                return False
            if self.chain[i].prev_hash != self.chain[i-1].hash:
                return False
        return True
    
    def __str__(self):
        return '\n'.join([str(block) for block in self.chain])

class Peer:
    def __init__(self, id, port):
        self.id = id
        self.port = port
        self.peers = {}
        self.blockchain = None
        self.prepare_msgs = {}
        self.commit_msgs = {}
        self.view = 0
        self.total_peers = 1 
        self.primary_id = self.view % self.total_peers
        self.server_running = True  # 서버 실행 플래그

        if self.id == self.primary_id:
            self.blockchain = BlockChain()

        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
    
    def update_primary(self):
        self.primary_id = self.view % self.total_peers
    
    def connect_peer(self, peer_id, peer_port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', peer_port))
            self.peers[peer_id] = peer_port
            self.total_peers += 1
            self.update_primary()
            self.synchronize_genesis_block(peer_id, peer_port)
            print(f"피어 {peer_id}에 포트 {peer_port}로 연결되었습니다.")

            # Send a message to the peer to connect back
            message = {'type': 'connect_back', 'peer_id': self.id, 'peer_port': self.port}
            sock.send(pickle.dumps(message))
            sock.close()
        except Exception as e:
            print(f"피어 {peer_id}에 포트 {peer_port}로 연결하는 데 실패했습니다: {e}")

    def synchronize_genesis_block(self, peer_id, peer_port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', peer_port))
            if self.blockchain is None:
                message = {'type': 'request_genesis'}
                sock.send(pickle.dumps(message))
                data = sock.recv(4096)
                if data:
                    genesis_block_data = pickle.loads(data)
                    genesis_block = Block(genesis_block_data['index'],
                                          genesis_block_data['timestamp'],
                                          genesis_block_data['data'],
                                          genesis_block_data['prev_hash'])
                    self.blockchain = BlockChain(genesis_block)
                    print(f"피어 {peer_id}로부터 제네시스 블록이 동기화되었습니다.")
            else:
                genesis_block = self.blockchain.chain[0]
                genesis_block_data = {
                    'index': genesis_block.index,
                    'timestamp': genesis_block.timestamp,
                    'data': genesis_block.data,
                    'prev_hash': genesis_block.prev_hash
                }
                message = {'type': 'send_genesis', 'genesis_block': genesis_block_data}
                sock.send(pickle.dumps(message))
            sock.close()
        except Exception as e:
            print(f"피어 {peer_id}에 포트 {peer_port}로 제네시스 블록을 동기화하는 데 실패했습니다: {e}")

    def run_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', self.port))
        server.listen(5)
        print(f"피어 {self.id}이(가) 포트 {self.port}에서 대기 중입니다.")
        try:
            while self.server_running:
                server.settimeout(1.0)
                try:
                    client_socket, addr = server.accept()
                    print(f"{addr}에서 연결이 수락되었습니다.")
                    threading.Thread(target=self.handle_client, args=(client_socket,)).start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print(f"피어 {self.id} 서버가 종료됩니다.")
        finally:
            server.close()
    
    def stop_server(self):
        self.server_running = False
        self.server_thread.join()
    
    def handle_client(self, client_socket):
        try:
            data = client_socket.recv(4096)
            if data:
                message = pickle.loads(data)
                if message['type'] == 'request_genesis':
                    self.send_genesis_block(client_socket)
                elif message['type'] == 'send_genesis':
                    self.receive_genesis_block(message['genesis_block'])
                elif message['type'] == 'block':
                    self.handle_propose(message['block'])
                elif message['type'] == 'prepare':
                    self.handle_prepare(message['block'], message['peer_id'])
                elif message['type'] == 'commit':
                    self.handle_commit(message['block'], message['peer_id'])
                elif message['type'] == 'view_change':
                    self.handle_view_change(message['new_view'], message['peer_id'])
                elif message['type'] == 'connect_back':
                    self.handle_connect_back(message['peer_id'], message['peer_port'])
        except EOFError as e:
            print(f"EOFError: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            client_socket.close()
    
    def handle_connect_back(self, peer_id, peer_port):
        if peer_id not in self.peers:
            self.peers[peer_id] = peer_port
            self.total_peers+=1
            self.update_primary()
            print(f"양방향 연결 성공 아이디:{peer_id}의 포트:{peer_port} ")

    def send_genesis_block(self, client_socket):
        try:
            if self.blockchain:
                genesis_block = self.blockchain.chain[0]
                genesis_block_data = {
                    'index': genesis_block.index,
                    'timestamp': genesis_block.timestamp,
                    'data': genesis_block.data,
                    'prev_hash': genesis_block.prev_hash
                }
                message = {'type': 'send_genesis', 'genesis_block': genesis_block_data}
                client_socket.send(pickle.dumps(message))
                print("제네시스 블록이 요청한 피어로 전송되었습니다.")
        except Exception as e:
            print(f"제네시스 블록을 전송하는 데 실패했습니다: {e}")

    def receive_genesis_block(self, genesis_block_data):
        if self.blockchain is None:
            genesis_block = Block(genesis_block_data['index'],
                                  genesis_block_data['timestamp'],
                                  genesis_block_data['data'],
                                  genesis_block_data['prev_hash'])
            self.blockchain = BlockChain(genesis_block)
            print("제네시스 블록을 수신하여 블록체인이 초기화되었습니다.")
    
    def handle_propose(self, block):
        if self.id == self.primary_id:
            print(f"블록 {block.index}에 대한 propose 단계가 시작되었습니다.")
            self.prepare_msgs[block.hash] = set()
            self.commit_msgs[block.hash] = set()
            self.broadcast_prepare(block)
        else:
            print(f"피어 {self.primary_id}로부터 블록 propose를 받았습니다.")
    
    def handle_prepare(self, block, peer_id):
        print(f"prepare 단계: 피어 {peer_id}로부터 블록 {block.index}에 대한 prepare MSG를 받았습니다.")
        if block.hash not in self.prepare_msgs:
            self.prepare_msgs[block.hash] = set()
        self.prepare_msgs[block.hash].add(peer_id)
        if len(self.prepare_msgs[block.hash]) >= (len(self.peers) // 3) * 2 + 1:
            self.broadcast_commit(block)
    
    def handle_commit(self, block, peer_id):
        print(f"commit 단계: 피어 {peer_id}로부터 블록 {block.index}에 대한 commit MSG를 받았습니다.")
        if block.hash not in self.commit_msgs:
            self.commit_msgs[block.hash] = set()
        self.commit_msgs[block.hash].add(peer_id)
        if len(self.commit_msgs[block.hash]) >= (len(self.peers) // 3) * 2 + 1:
            if not any(b.hash == block.hash for b in self.blockchain.chain):
                self.blockchain.addBlock(block)
                print(f"블록 {block.index}이(가) 블록체인에 추가되었습니다.")
    
    def handle_view_change(self, new_view, peer_id):
        print(f"피어 {peer_id}가 새로운 뷰 {new_view}로 변경을 요청했습니다.")
        self.view_change_votes += 1
        if self.view_change_votes > (len(self.peers) // 3) * 2:
            self.view = new_view
            self.update_primary()
            self.view_change_votes = 0
            print(f"뷰가 {self.view}(으)로 변경되었으며, 새로운 주 노드는 {self.primary_id}입니다.")
    
    def broadcast_prepare(self, block):
        for peer_id, peer_port in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', peer_port))
                message = {'type': 'prepare', 'block': block, 'peer_id': self.id}
                sock.send(pickle.dumps(message))
                sock.close()
                print(f"피어 {peer_id}에 블록 {block.index}에 대한 prepare MSG를 전송했습니다.")
            except Exception as e:
                print(f"피어 {peer_id}에 포트 {peer_port}로 prepare MSG를 보내는 데 실패했습니다: {e}")
    
    def broadcast_commit(self, block):
        for peer_id, peer_port in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', peer_port))
                message = {'type': 'commit', 'block': block, 'peer_id': self.id}
                sock.send(pickle.dumps(message))
                sock.close()
                print(f"피어 {peer_id}에 블록 {block.index}에 대한 commit MSG를 전송했습니다.")
            except Exception as e:
                print(f"피어 {peer_id}에 포트 {peer_port}로 commit MSG를 보내는 데 실패했습니다: {e}")
    
    def propose_block(self, block):
        if self.id == self.primary_id:
            print(f"블록 {block.index}을(를) 제안 중입니다.")
            self.broadcast_propose(block)
            self.handle_propose(block)
        else:
            print(f"노드 {self.id}은(는) 주 노드가 아닙니다.")
    
    def broadcast_propose(self, block):
        for peer_id, peer_port in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', peer_port))
                message = {'type': 'block', 'block': block}
                sock.send(pickle.dumps(message))
                sock.close()
                print(f"피어 {peer_id}에 블록 {block.index}에 대한 블록 propose MSG를 전송했습니다.")
            except Exception as e:
                print(f"피어 {peer_id}에 포트 {peer_port}로 블록 propose MSG를 보내는 데 실패했습니다: {e}")

def main():
    id = int(input("피어 ID를 입력하세요: "))
    port = int(input("포트 번호를 입력하세요: "))
    peer = Peer(id, port)

    while True:
        print("1. 피어 추가")
        print("2. 블록 추가")
        print("3. 블록체인 출력")
        print("4. 종료")
        choice = input("옵션을 선택하세요: ")

        if choice == "1":
            peer_id = int(input("연결할 피어 ID를 입력하세요: "))
            peer_port = int(input("연결할 피어의 포트 번호를 입력하세요: "))
            peer.connect_peer(peer_id, peer_port)
        elif choice == "2":
            data = input("블록 데이터를 입력하세요: ")
            if peer.blockchain is None:
                print("블록체인이 초기화되지 않았습니다.")
            else:
                print(" -----! PBFT 시작 !-----\n")
                block = Block(len(peer.blockchain.chain), time.time(), data)
                peer.propose_block(block)
        elif choice == "3":
            print("현재 블록체인:")
            if peer.blockchain:
                print(peer.blockchain)
            else:
                print("없음")
        elif choice == "4":
            peer.stop_server()
            break
        else:
            print("잘못된 옵션입니다. 다시 시도하세요.")

if __name__ == "__main__":
    main()
