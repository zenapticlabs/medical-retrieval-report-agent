from typing import Dict, Type
from .base import VectorDBService
from .elasticsearch_service import ElasticsearchService

class VectorDBFactory:
    """Factory class for creating vector database service instances"""
    
    _services: Dict[str, Type[VectorDBService]] = {
        'elasticsearch': ElasticsearchService,
        # Add more vector database implementations here
        # 'pinecone': PineconeService,
        # 'weaviate': WeaviateService,
        # etc.
    }
    
    @classmethod
    def create_service(cls, service_type: str, **kwargs) -> VectorDBService:
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