import os
import logging
import boto3
import time
from typing import Dict, List, Optional, Any
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from .base import VectorDBService

logger = logging.getLogger(__name__)

class OpenSearchService(VectorDBService):
    def __init__(self):
        self.endpoint = os.getenv('OPENSEARCH_ENDPOINT')
        self.region = os.getenv('AWS_REGION', 'us-east-2')
        self.index_name = os.getenv('OPENSEARCH_INDEX_NAME', 'medical-documents')
        self.vector_dimension = int(os.getenv('VECTOR_DIMENSION', '384'))
        
        # Set AWS credentials from environment variables
        os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
        os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')
        os.environ['AWS_DEFAULT_REGION'] = self.region
        
        self.client = None
        self._connect()
        self._ensure_index()

    def _connect(self) -> None:
        """Establish connection to OpenSearch"""
        try:
            # Create AWS session with credentials
            session = boto3.Session(
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=self.region
            )
            credentials = session.get_credentials()
            aws_auth = AWSV4SignerAuth(credentials, self.region, 'es')

            # Remove https:// from endpoint if present
            host = self.endpoint.replace("https://", "")
            
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=aws_auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                pool_maxsize=20,
                timeout=30
            )
            logger.info(f"Successfully connected to OpenSearch at {self.endpoint}")
        except Exception as e:
            logger.error(f"Error connecting to OpenSearch: {str(e)}")
            raise

    def _ensure_index(self, max_retries: int = 3) -> None:
        """Ensure the index exists, with retry logic"""
        for attempt in range(max_retries):
            try:
                if not self.client.indices.exists(index=self.index_name):
                    logger.info(f"Index {self.index_name} does not exist. Creating...")
                    self.create_index(self.index_name, self.vector_dimension)
                else:
                    logger.info(f"Index {self.index_name} already exists")
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to ensure index exists after {max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed to ensure index exists: {str(e)}")
                time.sleep(1)  # Wait before retrying

    def create_index(self, index_name: str, dimensions: int) -> bool:
        """Create a new index in OpenSearch"""
        try:
            if self.client.indices.exists(index=index_name):
                logger.info(f"Index {index_name} already exists")
                return True

            # Define the index mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "content": {"type": "text", "analyzer": "standard"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": dimensions,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 200,
                                    "m": 16
                                }
                            }
                        },
                        "document_name": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "page_number": {"type": "integer"},
                        "section": {"type": "keyword"},
                        "keywords": {"type": "keyword"},
                        "context": {"type": "text"},
                        "metadata": {"type": "object"},
                        "extracted_date": {"type": "keyword"}
                    }
                },
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100,
                        "number_of_shards": 1,
                        "number_of_replicas": 1
                    }
                }
            }

            # Create the index
            response = self.client.indices.create(
                index=index_name,
                body=mapping
            )
            
            # Verify the index was created
            if not self.client.indices.exists(index=index_name):
                raise Exception("Index creation response was successful but index does not exist")
                
            logger.info(f"Successfully created index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {str(e)}")
            return False

    def delete_index(self, index_name: str) -> bool:
        """Delete an existing index"""
        try:
            if self.client.indices.exists(index=index_name):
                self.client.indices.delete(index=index_name)
                logger.info(f"Successfully deleted index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {str(e)}")
            return False

    def index_document(self, index_name: str, document: Dict[str, Any]) -> bool:
        """Index a document with its vector embedding"""
        try:
            # Ensure index exists before indexing
            self._ensure_index()
            
            # Index the document without refresh parameter
            response = self.client.index(
                index=index_name,
                body=document
            )
            
            if not response.get('result') in ['created', 'updated']:
                raise Exception(f"Unexpected response from OpenSearch: {response}")
                
            return True
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            return False

    def search(self, index_name: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            # Ensure index exists before searching
            self._ensure_index()
            
            response = self.client.search(
                index=index_name,
                body={
                    "size": top_k,
                    "query": {
                        "knn": {
                            "embedding": {
                                "vector": query_vector,
                                "k": top_k
                            }
                        }
                    }
                }
            )
            
            # Format response to match Elasticsearch format
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
            # Ensure index exists before listing
            self._ensure_index()
            
            response = self.client.search(
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
            
            # Format response to match Elasticsearch format
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
            # Ensure index exists before getting document
            self._ensure_index()
            
            response = self.client.get(index=index_name, id=document_id)
            return response['_source']
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None 