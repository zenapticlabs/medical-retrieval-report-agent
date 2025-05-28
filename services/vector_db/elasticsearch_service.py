import os
import logging
from typing import Dict, List, Optional, Any
from elasticsearch import Elasticsearch
from .base import VectorDBService

logger = logging.getLogger(__name__)

class ElasticsearchService(VectorDBService):
    def __init__(self, host: str = None, port: int = None):
        self.host = host or os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
        self.port = port or int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.es = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Elasticsearch"""
        try:
            self.es = Elasticsearch([{'host': self.host, 'port': self.port}])
            if not self.es.ping():
                raise ConnectionError("Failed to connect to Elasticsearch")
            logger.info("Successfully connected to Elasticsearch")
        except Exception as e:
            logger.error(f"Error connecting to Elasticsearch: {str(e)}")
            raise

    def create_index(self, index_name: str, dimensions: int) -> bool:
        """Create a new index in Elasticsearch"""
        try:
            if self.es.indices.exists(index=index_name):
                logger.info(f"Index {index_name} already exists")
                return True

            self.es.indices.create(
                index=index_name,
                body={
                    "mappings": {
                        "properties": {
                            "content": {"type": "text", "analyzer": "standard"},
                            "embedding": {"type": "dense_vector", "dims": dimensions},
                            "document_name": {"type": "keyword"},
                            "chunk_index": {"type": "integer"},
                            "page_number": {"type": "integer"},
                            "section": {"type": "keyword"},
                            "keywords": {"type": "keyword"},
                            "context": {"type": "text"},
                            "metadata": {"type": "object"},
                            "extracted_date": {"type": "keyword"}
                        }
                    }
                }
            )
            logger.info(f"Successfully created index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {str(e)}")
            return False

    def delete_index(self, index_name: str) -> bool:
        """Delete an existing index"""
        try:
            if self.es.indices.exists(index=index_name):
                self.es.indices.delete(index=index_name)
                logger.info(f"Successfully deleted index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {str(e)}")
            return False

    def index_document(self, index_name: str, document: Dict[str, Any]) -> bool:
        """Index a document with its vector embedding"""
        try:
            self.es.index(index=index_name, body=document)
            return True
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            return False

    def search(self, index_name: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            response = self.es.search(
                index=index_name,
                body={
                    "query": {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": query_vector}
                            }
                        }
                    },
                    "size": top_k
                }
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'source': hit['_source']
                })
            return results
        except Exception as e:
            logger.error(f"Error performing search: {str(e)}")
            return []

    def list_documents(self, index_name: str) -> List[Dict[str, Any]]:
        """List all documents in the index"""
        try:
            response = self.es.search(
                index=index_name,
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
            for bucket in response['aggregations']['unique_documents']['buckets']:
                documents.append({
                    'name': bucket['key'],
                    'chunks': bucket['doc_count'],
                    'max_page': int(bucket['max_page']['value']) if bucket['max_page']['value'] else 1
                })
            
            return documents
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []

    def get_document(self, index_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        try:
            response = self.es.get(index=index_name, id=document_id)
            return response['_source']
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None 