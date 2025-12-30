# Blockchain/simple_blockchain.py
import hashlib
import json
from datetime import datetime
from typing import List, Dict

class SimpleBlockchain:
    """A simple blockchain that runs in memory - no wallet needed!"""
    
    def __init__(self):
        self.chain: List[Dict] = []
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block"""
        genesis = {
            "index": 0,
            "timestamp": str(datetime.now()),
            "data": "Genesis Block - DISHA Disaster Management",
            "previous_hash": "0",
            "hash": self.calculate_hash(0, str(datetime.now()), "Genesis", "0")
        }
        self.chain.append(genesis)
    
    def calculate_hash(self, index: int, timestamp: str, data: str, previous_hash: str) -> str:
        """Calculate SHA256 hash"""
        value = str(index) + timestamp + str(data) + previous_hash
        return hashlib.sha256(value.encode()).hexdigest()
    
    def get_latest_block(self) -> Dict:
        """Get the last block in chain"""
        return self.chain[-1]
    
    def add_disaster_block(self, disaster_type: str, latitude: float, 
                          longitude: float, radius_meters: int, severity: int) -> Dict:
        """Add a disaster to the blockchain"""
        
        previous_block = self.get_latest_block()
        index = previous_block["index"] + 1
        timestamp = str(datetime.now())
        
        data = {
            "disaster_type": disaster_type,
            "latitude": latitude,
            "longitude": longitude,
            "radius_meters": radius_meters,
            "severity": severity,
            "timestamp": timestamp,
            "verified": False
        }
        
        block = {
            "index": index,
            "timestamp": timestamp,
            "data": data,
            "previous_hash": previous_block["hash"],
            "hash": self.calculate_hash(index, timestamp, json.dumps(data), previous_block["hash"])
        }
        
        self.chain.append(block)
        
        return {
            "success": True,
            "block_index": index,
            "block_hash": block["hash"],
            "message": "Disaster recorded on blockchain"
        }
    
    def get_disaster(self, block_index: int) -> Dict:
        """Get disaster by block index"""
        if 0 <= block_index < len(self.chain):
            return self.chain[block_index]
        return {"error": "Block not found"}
    
    def get_all_disasters(self) -> List[Dict]:
        """Get all disaster blocks (skip genesis)"""
        return self.chain[1:]  # Skip genesis block
    
    def verify_disaster(self, block_index: int) -> Dict:
        """Mark disaster as verified"""
        if 1 <= block_index < len(self.chain):
            self.chain[block_index]["data"]["verified"] = True
            return {"success": True, "message": f"Block {block_index} verified"}
        return {"error": "Block not found"}
    
    def validate_chain(self) -> bool:
        """Check if blockchain is valid"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Check if previous hash matches
            if current["previous_hash"] != previous["hash"]:
                return False
            
            # Recalculate hash and verify
            calculated_hash = self.calculate_hash(
                current["index"],
                current["timestamp"],
                json.dumps(current["data"]) if isinstance(current["data"], dict) else current["data"],
                current["previous_hash"]
            )
            
            if current["hash"] != calculated_hash:
                return False
        
        return True
    
    def get_stats(self) -> Dict:
        """Get blockchain statistics"""
        return {
            "total_blocks": len(self.chain),
            "total_disasters": len(self.chain) - 1,  # Exclude genesis
            "is_valid": self.validate_chain(),
            "latest_block_hash": self.get_latest_block()["hash"]
        }