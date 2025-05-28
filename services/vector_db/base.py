from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class VectorDBService(ABC):
    """Base interface for vector database operations"""
    
    @abstractmethod
    def create_index(self, index_name: str, dimensions: int) -> bool:
        """Create a new index in the vector database"""
        pass
    
    @abstractmethod
    def delete_index(self, index_name: str) -> bool:
        """Delete an existing index"""
        pass
    
    @abstractmethod
    def index_document(self, index_name: str, document: Dict[str, Any]) -> bool:
        """Index a document with its vector embedding"""
        pass
    
    @abstractmethod
    def search(self, index_name: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        pass
    
    @abstractmethod
    def list_documents(self, index_name: str) -> List[Dict[str, Any]]:
        """List all documents in the index"""
        pass
    
    @abstractmethod
    def get_document(self, index_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        pass 