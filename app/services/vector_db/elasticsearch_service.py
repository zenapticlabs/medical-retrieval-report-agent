import os
import logging
from typing import Dict, List, Optional, Any
from elasticsearch import Elasticsearch
from .base import VectorDBService
import time
from app.core.config import settings

logger = logging.getLogger(__name__)

class ElasticsearchService(VectorDBService):
    def __init__(self):
        self.host = settings.ELASTICSEARCH_HOST
        self.port = settings.ELASTICSEARCH_PORT
        self.index_name = settings.OPENSEARCH_INDEX_NAME
        self.vector_dimension = settings.VECTOR_DIMENSION
        self.max_retries = settings.MAX_RETRIES
        self.retry_interval = settings.RETRY_INTERVAL
        self.es = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Elasticsearch with retry logic"""
        retries = 0
        while retries < self.max_retries:
            try:
                self.es = Elasticsearch([f"http://{self.host}:{self.port}"])
                if self.es.ping():
                    logger.info("Successfully connected to Elasticsearch")
                    return
                else:
                    logger.warning("Elasticsearch ping failed")
            except Exception as e:
                logger.warning(f"Attempt {retries + 1}/{self.max_retries} failed to connect to Elasticsearch: {str(e)}")
            
            retries += 1
            if retries < self.max_retries:
                logger.info(f"Retrying in {self.retry_interval} seconds...")
                time.sleep(self.retry_interval)
        
        raise ConnectionError("Failed to connect to Elasticsearch after maximum retries")

    def create_index(self) -> bool:
        """Create the index with vector field mapping"""
        try:
            if not self.es.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "document_name": {"type": "keyword"},
                            "page_number": {"type": "integer"},
                            "content": {"type": "text"},
                            "vector": {
                                "type": "dense_vector",
                                "dims": self.vector_dimension
                            }
                        }
                    }
                }
                self.es.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created index {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            return False

    def delete_index(self) -> bool:
        """Delete the index"""
        try:
            if self.es.indices.exists(index=self.index_name):
                self.es.indices.delete(index=self.index_name)
                logger.info(f"Deleted index {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting index: {str(e)}")
            return False

    def index_document(self, document_id: str, document_name: str, page_number: int, content: str, vector: list) -> bool:
        """Index a document with its vector embedding"""
        try:
            logger.info(f"Indexing document {document_name} page {page_number}")
            
            # Validate input
            if not document_id or not document_name or not content or not vector:
                logger.error("Missing required fields for document indexing")
                return False
                
            if not isinstance(vector, list) or len(vector) != self.vector_dimension:
                logger.error(f"Invalid vector dimension. Expected {self.vector_dimension}, got {len(vector) if isinstance(vector, list) else 'not a list'}")
                return False
            
            doc = {
                "document_name": document_name,
                "page_number": page_number,
                "content": content,
                "vector": vector
            }
            
            # Index the document
            response = self.es.index(
                index=self.index_name,
                id=document_id,
                body=doc,
                refresh=True  # Ensure the document is searchable immediately
            )
            
            if response.get('result') == 'created' or response.get('result') == 'updated':
                logger.info(f"Successfully indexed document {document_name} page {page_number}")
                return True
            else:
                logger.error(f"Failed to index document {document_name} page {page_number}. Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexing document {document_name} page {page_number}: {str(e)}")
            return False

    def search(self, query_vector: list, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            script_query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                        "params": {"query_vector": query_vector}
                    }
                }
            }
            
            response = self.es.search(
                index=self.index_name,
                body={
                    "size": top_k,
                    "query": script_query,
                    "_source": ["document_name", "page_number", "content"]
                }
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "document_id": hit["_id"],
                    "document_name": hit["_source"]["document_name"],
                    "page_number": hit["_source"]["page_number"],
                    "content": hit["_source"]["content"],
                    "score": hit["_score"]
                })
            return results
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the index"""
        try:
            response = self.es.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "unique_documents": {
                            "terms": {
                                "field": "document_name",
                                "size": 1000
                            },
                            "aggs": {
                                "max_page": {
                                    "max": {
                                        "field": "page_number"
                                    }
                                }
                            }
                        }
                    }
                }
            )
            
            documents = []
            for bucket in response["aggregations"]["unique_documents"]["buckets"]:
                documents.append({
                    "document_name": bucket["key"],
                    "total_pages": int(bucket["max_page"]["value"])
                })
            return documents
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        try:
            response = self.es.get(index=self.index_name, id=document_id)
            return {
                "document_id": response["_id"],
                "document_name": response["_source"]["document_name"],
                "page_number": response["_source"]["page_number"],
                "content": response["_source"]["content"]
            }
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            return None 