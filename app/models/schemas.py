from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query string")
    top_k: Optional[int] = Field(20, description="Number of results to return")

class SearchResponse(BaseModel):
    results: Dict[str, Any] = Field(..., description="Search results")

class DocumentProcessResponse(BaseModel):
    message: str = Field(..., description="Processing status message")
    status: str = Field(..., description="Processing status")
    files: List[str] = Field(default_factory=list, description="List of processed files")

class DocumentListResponse(BaseModel):
    status: str = Field(..., description="Response status")
    documents: List[Dict[str, Any]] = Field(..., description="List of documents")

class DocumentResponse(BaseModel):
    status: str = Field(..., description="Response status")
    document_name: str = Field(..., description="Name of the document")
    content: Dict[str, Any] = Field(..., description="Document content")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    status: str = Field("error", description="Error status") 