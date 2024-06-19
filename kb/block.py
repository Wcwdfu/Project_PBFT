import hashlib
import time

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
