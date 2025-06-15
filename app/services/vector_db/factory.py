from typing import Dict, Type
import os
from .base import VectorDBService
from .elasticsearch_service import ElasticsearchService
from .opensearch_service import OpenSearchService

class VectorDBFactory:
    """Factory class for creating vector database service instances"""
    
    _services: Dict[str, Type[VectorDBService]] = {
        'elasticsearch': ElasticsearchService,
        'opensearch': OpenSearchService
    }
    
    @classmethod
    def create_service(cls, service_type: str = None, **kwargs) -> VectorDBService:
        """
        Create a vector database service instance
        
        Args:
            service_type: Type of vector database service to create
            **kwargs: Additional arguments to pass to the service constructor
            
        Returns:
            VectorDBService: Instance of the requested vector database service
            
        Raises:
            ValueError: If the requested service type is not supported
        """
        # If service_type is not provided, determine from environment variable
        if service_type is None:
            use_opensearch = os.getenv('USE_OPENSEARCH', 'false').lower() == 'true'
            service_type = 'opensearch' if use_opensearch else 'elasticsearch'
        
        if service_type not in cls._services:
            supported_services = ', '.join(cls._services.keys())
            raise ValueError(f"Unsupported vector database service type: {service_type}. "
                           f"Supported types are: {supported_services}")
        
        service_class = cls._services[service_type]
        return service_class(**kwargs)
    
    @classmethod
    def register_service(cls, service_type: str, service_class: Type[VectorDBService]) -> None:
        """
        Register a new vector database service type
        
        Args:
            service_type: Name of the service type
            service_class: Class implementing the VectorDBService interface
        """
        if not issubclass(service_class, VectorDBService):
            raise ValueError(f"Service class must implement VectorDBService interface")
        cls._services[service_type] = service_class 