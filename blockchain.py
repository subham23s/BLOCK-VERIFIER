import hashlib
import json
import time


class Block:
    def __init__(self, index, file_name, file_hash, file_type, previous_hash, difficulty=4):
        self.index = index
        self.timestamp = time.time()
        self.file_name = file_name
        self.file_hash = file_hash
        self.file_type = file_type  # 'image', 'document', 'model', etc.
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = 0
        self.current_hash = self.mine_block()

    def compute_hash(self):
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "file_name": self.file_name,
            "file_hash": self.file_hash,
            "file_type": self.file_type,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self):
        """Proof-of-Work: find nonce such that hash starts with 'difficulty' zeros."""
        target = "0" * self.difficulty
        while True:
            hash_attempt = self.compute_hash()
            if hash_attempt.startswith(target):
                return hash_attempt
            self.nonce += 1


class Blockchain:
    def __init__(self, difficulty=4):
        self.chain = []
        self.difficulty = difficulty
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(0, "GENESIS", "GENESIS", "genesis", "0", self.difficulty)
        self.chain.append(genesis)

    def add_block(self, file_name, file_hash, file_type="file"):
        previous_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            file_name=file_name,
            file_hash=file_hash,
            file_type=file_type,
            previous_hash=previous_block.current_hash,
            difficulty=self.difficulty
        )
        self.chain.append(new_block)
        return new_block

    def find_block_by_hash(self, file_hash):
        """Search chain for a block with matching file hash."""
        for block in self.chain[1:]:
            if block.file_hash == file_hash:
                return block
        return None

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.current_hash != current.compute_hash():
                return False
            if current.previous_hash != previous.current_hash:
                return False
            if not current.current_hash.startswith("0" * current.difficulty):
                return False
        return True

    def to_list(self):
        return [
            {
                "index": b.index,
                "timestamp": b.timestamp,
                "file_name": b.file_name,
                "file_hash": b.file_hash,
                "file_type": b.file_type,
                "previous_hash": b.previous_hash,
                "nonce": b.nonce,
                "difficulty": b.difficulty,
                "current_hash": b.current_hash
            }
            for b in self.chain
        ]

    @classmethod
    def from_list(cls, chain_data, difficulty=4):
        bc = cls.__new__(cls)
        bc.chain = []
        bc.difficulty = difficulty
        for d in chain_data:
            b = Block.__new__(Block)
            b.index = d["index"]
            b.timestamp = d["timestamp"]
            b.file_name = d["file_name"]
            b.file_hash = d["file_hash"]
            b.file_type = d.get("file_type", "file")
            b.previous_hash = d["previous_hash"]
            b.nonce = d["nonce"]
            b.difficulty = d.get("difficulty", difficulty)
            b.current_hash = d["current_hash"]
            bc.chain.append(b)
        return bc
 