import hashlib
import time
import json

class Block():
    # 블록 생성 시 초기화
    def __init__(self, index, timestamp, data):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.prev_hash = 0
        self.hash = self.calHash()
    # 해시 계산함수, 16진수로 반환
    def calHash(self):
        return hashlib.sha256(str(self.index).encode() 
                              + str(self.data).encode()
                              + str(self.timestamp).encode()
                              + str(self.prev_hash).encode()
                              ).hexdigest()
    
class BlockChain:
    # 초기화
    def __init__(self):
        self.chain = []
        self.createGenesis()
    # 최초의 블록 생성
    def createGenesis(self):
        self.chain.append(Block(0, time.time(), 'Genesis'))
    # 블록 추가
    # 이전의 해쉬값과 현 블록의 해쉬값 계산해서 chain에 추가
    def addBlock(self, nBlock):
        nBlock.prev_hash = self.chain[len(self.chain)-1].hash
        nBlock.hash = nBlock.calHash()
        self.chain.append(nBlock)
    # 체인 유효성 검사
    def isValid(self):
        i = 1
        while(i<len(self.chain)):
            # 현재 블록에 저장된 현재 블록 해쉬값 != 현재 블록을 계산한 해쉬값
            if(self.chain[i].hash != self.chain[i].calHash()):
                return False
            # 현재 블록에 저장된 이전 블록 해쉬값 != 이전 블록의 해쉬값
            if(self.chain[i].prev_hash != self.chain[i-1].hash):
                return False
            i += 1
        return True

# 테스트

# 블록체인 bc 생성    
bc = BlockChain()

# bc 체인에 블록 추가
bc.addBlock(Block(len(bc.chain), time.time(), {"amount":10}))
# 체인에 블록 추가
bc.addBlock(Block(len(bc.chain), time.time(), {"amount":100}))
# 체인에 블록 추가
bc.addBlock(Block(len(bc.chain), time.time(), {"amount":10000}))

# 체인의 모든 블록 정보 출력
# vars() -> 객체의 모든 속성과 값을 딕셔너리로 반환
# json.dumps() -> 딕셔너리를 JSON 문자열로 변환, indent = 들여쓰기 줄수
for block in bc.chain:
    print(json.dumps(vars(block), indent=4))

# 수정 없이 체인 유효성 검사 -> True 반환
print('Chian is OK? ', bc.isValid())

# 중간 블록 데이터 변경 후 체인 유효성 검사 -> False 반환
bc.chain[2].data = "fake"
print('Chian is OK? ', bc.isValid())
bc.chain[2].hash = bc.chain[2].calHash()
print('Chian is OK? ', bc.isValid())