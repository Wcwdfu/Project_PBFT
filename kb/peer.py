import threading
from kb.block import Block, BlockChain
from kb.network import Network

class Peer:
    def __init__(self, id, port):
        self.id = id
        self.port = port
        self.byzantine = False
        self.peers = {}
        self.blockchain = None
        self.prepare_msgs = {}
        self.commit_msgs = {}
        self.reply_msgs = {}
        self.view = 0
        self.total_peers = 1  # Start with 1 as this peer is already part of the network
        self.primary_id = self.view % self.total_peers

        if self.id == self.primary_id:
            self.blockchain = BlockChain()  # 프라이머리노드만 제네시스블록을 생성

        self.network = Network(self)
        self.server_thread = threading.Thread(target=self.network.run_server)
        self.server_thread.start()
    
    def update_primary(self):
        self.primary_id = self.view % self.total_peers
    
    def connect_peer(self, peer_id, peer_port):
        if peer_id in self.peers:
            print(f"Peer {peer_id} is already connected.")
            return

        try:
            self.network.send_message(peer_port, {'type': 'connect', 'peer_id': self.id, 'peer_port': self.port})
            self.peers[peer_id] = peer_port
            self.total_peers += 1  # 총 피어수 계산
            self.update_primary() 
            self.synchronize_genesis_block(peer_id, peer_port)
            print(f"Connected to peer {peer_id} on port {peer_port}")
        except Exception as e:
            print(f"Failed to connect to peer {peer_id} on port {peer_port}: {e}")

    def synchronize_genesis_block(self, peer_id, peer_port):
        if self.blockchain is None:
            self.network.send_message(peer_port, {'type': 'request_genesis'})
        else:
            genesis_block = self.blockchain.chain[0]
            genesis_block_data = {
                'index': genesis_block.index,
                'timestamp': genesis_block.timestamp,
                'data': genesis_block.data,
                'prev_hash': genesis_block.prev_hash
            }
            self.network.send_message(peer_port, {'type': 'send_genesis', 'genesis_block': genesis_block_data})
    
    def handle_message(self, message, client_socket):
        if message['type'] == 'request_genesis':
            self.send_genesis_block(client_socket)
        elif message['type'] == 'send_genesis':
            self.receive_genesis_block(message['genesis_block'])
        elif message['type'] == 'connect':
            self.handle_connect(message['peer_id'], message['peer_port'])
        elif message['type'] == 'block':
            self.handle_propose(message['block'])
        elif message['type'] == 'prepare':
            self.handle_prepare(message['block'], message['peer_id'])
        elif message['type'] == 'commit':
            self.handle_commit(message['block'], message['peer_id'])
        elif message['type'] == 'reply':
            self.handle_reply(message['block'], message['peer_id'])
        elif message['type'] == 'view_change':
            self.handle_view_change(message['new_view'], message['peer_id'])

    def handle_connect(self, peer_id, peer_port):
        self.peers[peer_id] = peer_port
        self.total_peers += 1  # 총 피어수 계산
        self.update_primary()
        print(f"Peer {peer_id} connected from port {peer_port}")
        # 연결된 피어가 요청을 보낸 피어에게도 연결 요청을 보냄
        if peer_id not in self.peers:
            self.connect_peer(peer_id, peer_port)
    
    def send_genesis_block(self, client_socket):
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
            print("Sent genesis block to requesting peer")

    def receive_genesis_block(self, genesis_block_data):
        if self.blockchain is None:
            genesis_block = Block(genesis_block_data['index'],
                                  genesis_block_data['timestamp'],
                                  genesis_block_data['data'],
                                  genesis_block_data['prev_hash'])
            self.blockchain = BlockChain(genesis_block)
            print("Genesis block received and blockchain initialized")

    def handle_propose(self, block):
        if self.id == self.primary_id:
            print(f"Propose phase started for block {block.index}")
            self.prepare_msgs[block.hash] = set()
            self.commit_msgs[block.hash] = set()
            self.reply_msgs[block.hash] = set()
            self.broadcast_prepare(block)
        else:
            print(f"Received block proposal from peer {self.primary_id}")

    def handle_prepare(self, block, peer_id):
        print(f"Prepare phase: received prepare from peer {peer_id} for block {block.index}")
        if self.byzantine:
            print(f"Byzantine node {self.id} is sending incorrect prepare message")
            block.hash = 'fake_hash'  # 악의적으로 잘못된 해시 값 사용
        if block.hash not in self.prepare_msgs:
            self.prepare_msgs[block.hash] = set()
        self.prepare_msgs[block.hash].add(peer_id)
        if len(self.prepare_msgs[block.hash]) > (len(self.peers) // 3) * 2:
            self.broadcast_commit(block)

    def handle_commit(self, block, peer_id):
        print(f"Commit phase: received commit from peer {peer_id} for block {block.index}")
        if self.byzantine:
            print(f"Byzantine node {self.id} is sending incorrect commit message")
            block.hash = 'fake_hash'  # 악의적으로 잘못된 해시 값 사용
        if block.hash not in self.commit_msgs:
            self.commit_msgs[block.hash] = set()
        self.commit_msgs[block.hash].add(peer_id)
        if len(self.commit_msgs[block.hash]) > (len(self.peers) // 3) * 2:
            self.broadcast_reply(block)

    def handle_reply(self, block, peer_id):
        print(f"Reply phase: received reply from peer {peer_id} for block {block.index}")
        if block.hash not in self.reply_msgs:
            self.reply_msgs[block.hash] = set()
        self.reply_msgs[block.hash].add(peer_id)
        if len(self.reply_msgs[block.hash]) >= (len(self.peers) // 3) * 2 + 1:
            if not any(b.hash == block.hash for b in self.blockchain.chain):
                self.blockchain.addBlock(block)
                print(f"Block {block.index} added to the blockchain.")

    def handle_view_change(self, new_view, peer_id):
        print(f"View change requested by peer {peer_id} to view {new_view}")
        self.view_change_votes += 1
        if self.view_change_votes > (len(self.peers) // 3) * 2:
            self.view = new_view
            self.update_primary()  # 프라이머리노드 다시 계산
            self.view_change_votes = 0
            print(f"View changed to {self.view}, new primary is {self.primary_id}")
    
    def broadcast_prepare(self, block):
        message = {'type': 'prepare', 'block': block, 'peer_id': self.id}
        self.network.broadcast_message(message)
        print(f"Broadcasted prepare to all peers for block {block.index}")
    
    def broadcast_commit(self, block):
        message = {'type': 'commit', 'block': block, 'peer_id': self.id}
        self.network.broadcast_message(message)
        print(f"Broadcasted commit to all peers for block {block.index}")
    
    def broadcast_reply(self, block):
        message = {'type': 'reply', 'block': block, 'peer_id': self.id}
        self.network.broadcast_message(message)
        print(f"Broadcasted reply to all peers for block {block.index}")

    def propose_block(self, block):
        if self.id == self.primary_id:
            print(f"Proposing block {block.index}")
            self.broadcast_propose(block)
            self.handle_propose(block)
        else:
            print(f"Node {self.id} is not the primary node.")
    
    def broadcast_propose(self, block):
        message = {'type': 'block', 'block': block}
        self.network.broadcast_message(message)
        print(f"Broadcasted block proposal to all peers for block {block.index}")

    def set_byzantine(self, byzantine):
        self.byzantine = byzantine
        if byzantine:
            print(f"Node {self.id} is now a Byzantine node.")
        else:
            print(f"Node {self.id} is now a normal node.")
