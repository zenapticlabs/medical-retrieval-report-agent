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

        #FIXED: Convert text query to vector embedding first
        query_vector = processor.get_embedding(query.query)

        logger.info(f"Embeddings of user query, {query_vector}")

        if hasattr(query_vector, 'tolist'):
            query_vector = query_vector.tolist()
        elif not isinstance(query_vector, list):
            query_vector = list(query_vector)
        
        logger.info(f"Generated query vector with dimension: {len(query_vector)}")

        results = processor.search(query_vector, top_k=query.top_k)

        return {"results": results}
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 