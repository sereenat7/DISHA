# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from Disaster.trigger import trigger_disaster
from News.info import get_current_natural_disasters
from Blockchain.simple_blockchain import SimpleBlockchain

app = FastAPI(
    title="DISHA - Disaster Management with Blockchain",
    description="Trigger disasters & record on blockchain (No wallet needed!)",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize simple blockchain (no setup needed!)
blockchain = SimpleBlockchain()

class DisasterTriggerRequest(BaseModel):
    type: str = Field(..., description="Type of disaster")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: int = Field(default=1000, ge=100)
    severity: int = Field(default=5, ge=1, le=10)

@app.post("/disaster/trigger")
async def api_trigger_disaster(request: DisasterTriggerRequest):
    """Trigger disaster and save to blockchain"""
    try:
        # Trigger disaster in your system
        result = trigger_disaster(
            disaster_type=request.type,
            latitude=request.latitude,
            longitude=request.longitude,
            radius_meters=request.radius_meters
        )
        
        # Save to blockchain
        blockchain_result = blockchain.add_disaster_block(
            disaster_type=request.type,
            latitude=request.latitude,
            longitude=request.longitude,
            radius_meters=request.radius_meters,
            severity=request.severity
        )
        
        return {
            "disaster": result,
            "blockchain": blockchain_result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/blockchain/disaster/{block_index}")
async def get_disaster_from_blockchain(block_index: int):
    """Get specific disaster from blockchain"""
    result = blockchain.get_disaster(block_index)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/blockchain/disasters")
async def get_all_blockchain_disasters():
    """Get all disasters from blockchain"""
    return {
        "disasters": blockchain.get_all_disasters(),
        "count": len(blockchain.get_all_disasters())
    }

@app.get("/blockchain/stats")
async def get_blockchain_statistics():
    """Get blockchain statistics"""
    return blockchain.get_stats()

@app.post("/blockchain/verify/{block_index}")
async def verify_disaster(block_index: int):
    """Verify a disaster (mark as authentic)"""
    result = blockchain.verify_disaster(block_index)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/blockchain/validate")
async def validate_blockchain():
    """Check if blockchain is tamper-proof"""
    is_valid = blockchain.validate_chain()
    return {
        "is_valid": is_valid,
        "message": "Blockchain is intact ✅" if is_valid else "Blockchain has been tampered! ⚠️"
    }

@app.get("/news/disasters")
async def api_get_disasters():
    return get_current_natural_disasters()

@app.get("/")
async def root():
    return {
        "message": "DISHA Disaster Management with Simple Blockchain!",
        "blockchain_status": "✅ Active (No wallet needed!)",
        "docs": "/docs"
    }