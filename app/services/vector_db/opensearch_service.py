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
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            # Ensure index exists before searching
            self._ensure_index()
            
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": top_k,
                    "query": {
                        "knn": {
                            "embedding": {
                                "vector": query_vector,
                                "k": top_k
                            }
                        }
                    },
                    "_source": {
                        "includes": ["document_type", "content", "chunk_text", "chunk_index", "file_type", "keywords", "medical_terms"]
                    }
                }
            )


            logger.debug(f"OpenSearch response status: {response.get('timed_out', False)}")

            # Check if we got valid results
            if 'hits' not in response or 'hits' not in response['hits']:
                logger.warning("No hits found in OpenSearch response")
                return []
            
            # Format response to match expected structure
            results = []
            hits = response['hits']['hits']
            total_hits = response['hits'].get('total', {})
            
            if isinstance(total_hits, dict):
                total_count = total_hits.get('value', 0)
            else:
                total_count = total_hits
                
            logger.info(f"OpenSearch found {total_count} total matches, returning top {len(hits)} results")
            
            for hit in hits:
                try:
                    source = hit.get('_source', {})
                    
                    # Extract data from your actual index structure
                    content = source.get("content") or source.get("chunk_text", "")
                    document_name = source.get("document_type", "Unknown Document")
                    chunk_index = source.get("chunk_index", 0)
                    file_type = source.get("file_type", "")
                    keywords = source.get("keywords", [])
                    medical_terms = source.get("medical_terms", [])
                    
                    result = {
                        "document_id": hit.get('_id', ''),
                        "document_name": document_name,
                        "page_number": chunk_index,  # Using chunk_index as page_number
                        "content": content,
                        "score": hit.get('_score', 0.0),
                        "file_type": file_type,
                        "keywords": keywords,
                        "medical_terms": medical_terms
                    }
                    results.append(result)
                    logger.debug(f"Processed hit: doc_id={result['document_id']}, score={result['score']}")
                except Exception as hit_error:
                    logger.error(f"Error processing search hit: {str(hit_error)}")
                    continue
            
            logger.info(f"Search completed successfully. Returning {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error performing OpenSearch k-NN search: {str(e)}")
            logger.error(f"Query vector length: {len(query_vector) if isinstance(query_vector, list) else 'not a list'}")
            logger.error(f"Expected vector dimension: {self.vector_dimension}")
            logger.error(f"Index name: {self.index_name}")
            
            # Try to provide more debugging info
            try:
                if self.client and self.client.indices.exists(index=self.index_name):
                    mapping = self.client.indices.get_mapping(index=self.index_name)
                    logger.error(f"Index mapping: {mapping}")
                else:
                    logger.error("Index does not exist or client is not initialized")
            except Exception as debug_error:
                logger.error(f"Could not get debug info: {str(debug_error)}")
                
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