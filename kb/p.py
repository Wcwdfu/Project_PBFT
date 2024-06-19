from kb.peer import Peer
from kb.block import Block
import time

def main():
    id = int(input("Enter your peer ID: "))
    port = int(input("Enter your port number: "))
    peer = Peer(id, port)

    while True:
        print("1. Add peer")
        print("2. Add block")
        print("3. Print blockchain")
        print("4. Exit")
        print("5. Toggle Byzantine mode")
        choice = input("Choose an option: ")

        if choice == "1":
            peer_id = int(input("Enter peer ID to connect: "))
            peer_port = int(input("Enter peer port number: "))
            peer.connect_peer(peer_id, peer_port)
        elif choice == "2":
            data = input("Enter block data: ")
            if peer.blockchain is None:
                print("Blockchain is not initialized.")
            else:
                block = Block(len(peer.blockchain.chain), time.time(), data)
                peer.propose_block(block)
                print("--- PBFT start !! ---\n")
        elif choice == "3":
            print("Current Blockchain:")
            if peer.blockchain:
                print(peer.blockchain)
            else:
                print("None")
        elif choice == "4":
            break
        elif choice == "5":
            peer.set_byzantine(not peer.byzantine)
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
