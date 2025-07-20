from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.services.document_processor import DocumentProcessor
from app.core.logging import setup_logging
from typing import Dict, List, Optional, Any

# Setup logging
logger = setup_logging()

# Create router
router = APIRouter()

# Initialize document processor
processor = DocumentProcessor()

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 20



def transform_search_results_for_ui(self, raw_results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Transform OpenSearch raw results into UI-compatible format"""
    from collections import defaultdict
    import re
    
    def extract_keywords_from_text(text: str, query: str) -> List[str]:
        """Extract keywords from query that appear in the text"""
        query_words = [word.lower().strip() for word in re.split(r'[,\s]+', query) if len(word.strip()) > 2]
        text_lower = text.lower()
        
        found_keywords = []
        for word in query_words:
            if word in text_lower:
                found_keywords.append(word)
        
        return found_keywords
    
    # Group results by document name
    documents_dict = defaultdict(lambda: {
        "document_name": "",
        "chunks": []
    })
    
    for result in raw_results:
        # Extract document name - try multiple possible field names
        doc_name = result.get("document_name")
        if not doc_name:
            doc_name = result.get("file_type", "Unknown Document")
        if not doc_name or doc_name == "Unknown Document":
            # If still no name, create one from document_id
            doc_id = result.get("document_id", "")
            if doc_id:
                # Extract document name from ID if it follows pattern like "docname_page"
                doc_name = doc_id.split('_')[0] if '_' in doc_id else doc_id
            else:
                doc_name = "Unknown Document"
        
        content = result.get("content", "")
        page_number = result.get("page_number", 1)
        score = result.get("score", 0.0)
        document_id = result.get("document_id", "")
        
        # Extract additional fields
        file_type = result.get("file_type", "")
        keywords = result.get("keywords", [])
        medical_terms = result.get("medical_terms", [])
        
        # Extract keywords that match the query
        found_keywords = extract_keywords_from_text(content, query)
        
        # Add keywords from document metadata if available
        if keywords:
            query_words = [word.lower().strip() for word in re.split(r'[,\s]+', query) if len(word.strip()) > 2]
            for keyword in keywords:
                if keyword.lower() in query_words:
                    found_keywords.append(keyword)
        
        # Remove duplicates
        found_keywords = list(set(found_keywords))
        
        # Determine if this is an exact keyword match or semantic match
        is_keyword_match = len(found_keywords) > 0
        
        chunk_data = {
            "content": content,
            "page_number": page_number,
            "document_id": document_id,
            "score": score,
            "found_keywords": found_keywords if is_keyword_match else [],
            "semantic_score": score if not is_keyword_match else None,
            "file_type": file_type,
            "keywords": keywords,
            "medical_terms": medical_terms
        }
        
        # Set document name if not already set
        if not documents_dict[doc_name]["document_name"]:
            documents_dict[doc_name]["document_name"] = doc_name
        
        documents_dict[doc_name]["chunks"].append(chunk_data)
    
    # Sort chunks within each document by score (highest first)
    for doc_data in documents_dict.values():
        doc_data["chunks"].sort(key=lambda x: x["score"], reverse=True)
    
    return dict(documents_dict)



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

        raw_results = processor.search(query_vector, top_k=query.top_k)

        return transform_search_results_for_ui(raw_results, query.query)
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 