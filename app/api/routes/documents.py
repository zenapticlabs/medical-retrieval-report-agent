from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import os
from app.services.document_processor import DocumentProcessor
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
logger = setup_logging()

# Create router
router = APIRouter()

# Initialize document processor
processor = DocumentProcessor()

@router.get("/process")
async def process_documents() -> Dict[str, Any]:
    """
    Process all documents in the configured directory
    """
    try:
        documents_dir = os.path.join("/app", settings.DOCUMENTS_DIR)
        logger.info(f"Processing documents in directory: {documents_dir}")
        
        if not os.path.exists(documents_dir):
            raise HTTPException(
                status_code=404,
                detail=f"Documents directory not found: {documents_dir}"
            )
        
        processed_files = processor.process_all_documents(documents_dir)
        
        if not isinstance(processed_files, list):
            processed_files = []
        
        file_count = len(processed_files)
        
        return {
            "message": f"Successfully processed {file_count} documents" if file_count > 0 else "No documents were processed",
            "status": "success" if file_count > 0 else "warning",
            "files": processed_files
        }
        
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def list_documents() -> Dict[str, Any]:
    """
    List all processed documents
    """
    try:
        results = processor.list_documents()
        return {
            "status": "success",
            "documents": results
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_name}")
async def get_document(document_name: str) -> Dict[str, Any]:
    """
    Get content of a specific document
    """
    try:
        # Get the document's embedding first
        query_text = f"Document: {document_name}"
        query_embedding = processor.get_embedding(query_text)
        
        # Search for the document using the embedding
        results = processor.search(query_embedding.tolist(), top_k=1)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {document_name}"
            )
            
        return {
            "status": "success",
            "document_name": document_name,
            "content": results[0]["content"]
        }
    except Exception as e:
        logger.error(f"Error getting document content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 