from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.services.document_processor import DocumentProcessor
from app.core.logging import setup_logging

# Setup logging
logger = setup_logging()

# Create router
router = APIRouter()

# Initialize document processor
processor = DocumentProcessor()

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 20

@router.post("/search")
async def search(query: SearchQuery) -> Dict[str, Any]:
    """
    Search for documents using the provided query
    """
    try:
        logger.info(f"Processing search query: {query.query}")
        results = processor.search(query.query, top_k=query.top_k)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 