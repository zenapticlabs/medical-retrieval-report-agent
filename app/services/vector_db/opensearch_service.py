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


    ## TEST BLOCK START
    def debug_vector_search(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        """Debug semantic search functionality"""
        try:
            logger.info(f"=== DEBUGGING SEMANTIC SEARCH FOR: '{query_text}' ===")
            
            # Step 1: Check if we can generate embeddings for the query
            from app.services.document_processor import DocumentProcessor
            processor = DocumentProcessor()
            
            logger.info("Step 1: Generating query embedding...")
            query_vector = processor.get_embedding(query_text)
            
            if hasattr(query_vector, 'tolist'):
                query_vector = query_vector.tolist()
            elif not isinstance(query_vector, list):
                query_vector = list(query_vector)
                
            logger.info(f"Query vector dimension: {len(query_vector)}")
            logger.info(f"Query vector sample (first 5 values): {query_vector[:5]}")
            
            # Step 2: Check if documents have embeddings
            logger.info("Step 2: Checking if documents have embeddings...")
            sample_query = {
                "size": 3,
                "query": {"match_all": {}},
                "_source": ["document_name", "embedding", "content"]
            }
            
            response = self.client.search(index=self.index_name, body=sample_query)
            
            docs_with_embeddings = 0
            docs_without_embeddings = 0
            
            for hit in response.get('hits', {}).get('hits', []):
                source = hit['_source']
                if 'embedding' in source and source['embedding']:
                    docs_with_embeddings += 1
                    embedding_dim = len(source['embedding']) if isinstance(source['embedding'], list) else 0
                    logger.info(f"Document '{source.get('document_name', 'Unknown')}' has embedding with dimension: {embedding_dim}")
                else:
                    docs_without_embeddings += 1
                    logger.warning(f"Document '{source.get('document_name', 'Unknown')}' has NO embedding!")
            
            logger.info(f"Documents WITH embeddings: {docs_with_embeddings}")
            logger.info(f"Documents WITHOUT embeddings: {docs_without_embeddings}")
            
            # Step 3: Test the k-NN search directly
            logger.info("Step 3: Testing k-NN search...")
            
            # First try with a very broad search to see if k-NN works at all
            knn_query = {
                "size": top_k,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_vector,
                            "k": top_k * 2  # Get more results to see variety
                        }
                    }
                },
                "_source": ["document_name", "content", "keywords", "medical_terms"]
            }
            
            logger.info(f"k-NN query: {knn_query}")
            
            knn_response = self.client.search(index=self.index_name, body=knn_query)
            
            knn_results = []
            for hit in knn_response.get('hits', {}).get('hits', []):
                source = hit['_source']
                score = hit['_score']
                content = source.get('content', '')
                
                # Check if this is actually semantic (no exact keyword matches)
                content_lower = content.lower()
                query_words = query_text.lower().split()
                has_exact_match = any(word in content_lower for word in query_words if len(word) > 2)
                
                result = {
                    "document_name": source.get('document_name', ''),
                    "score": score,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "has_exact_keyword_match": has_exact_match,
                    "is_semantic_match": not has_exact_match
                }
                knn_results.append(result)
                
                logger.info(f"Result: {result['document_name']}, Score: {score:.4f}, Semantic: {result['is_semantic_match']}")
            
            # Step 4: Try a completely different semantic query
            logger.info("Step 4: Testing with a semantic-only query...")
            
            # Use synonyms or related medical terms that won't have exact matches
            semantic_test_queries = [
                "cardiac arrest",  # if original was "heart attack"
                "hypertension",    # if original was "high blood pressure" 
                "myocardial infarction",  # if original was "heart attack"
                "cerebrovascular accident"  # if original was "stroke"
            ]
            
            semantic_results = {}
            for test_query in semantic_test_queries:
                if test_query.lower() != query_text.lower():
                    logger.info(f"Testing semantic query: '{test_query}'")
                    test_vector = processor.get_embedding(test_query)
                    if hasattr(test_vector, 'tolist'):
                        test_vector = test_vector.tolist()
                    
                    test_response = self.client.search(
                        index=self.index_name,
                        body={
                            "size": 3,
                            "query": {
                                "knn": {
                                    "embedding": {
                                        "vector": test_vector,
                                        "k": 3
                                    }
                                }
                            },
                            "_source": ["document_name", "content"]
                        }
                    )
                    
                    semantic_results[test_query] = len(test_response.get('hits', {}).get('hits', []))
                    logger.info(f"'{test_query}' returned {semantic_results[test_query]} results")
            
            return {
                "query": query_text,
                "query_vector_dimension": len(query_vector),
                "index_stats": {
                    "docs_with_embeddings": docs_with_embeddings,
                    "docs_without_embeddings": docs_without_embeddings
                },
                "knn_results": knn_results,
                "semantic_test_results": semantic_results,
                "total_knn_hits": len(knn_results),
                "purely_semantic_hits": len([r for r in knn_results if r["is_semantic_match"]])
            }
            
        except Exception as e:
            logger.error(f"Error in debug_vector_search: {str(e)}")
            return {"error": str(e)}

    def test_embedding_similarity(self, text1: str, text2: str) -> Dict[str, Any]:
        """Test if embedding model can detect semantic similarity between two texts"""
        try:
            from app.services.document_processor import DocumentProcessor
            import numpy as np
            
            processor = DocumentProcessor()
            
            # Generate embeddings for both texts
            emb1 = processor.get_embedding(text1)
            emb2 = processor.get_embedding(text2)
            
            if hasattr(emb1, 'tolist'):
                emb1 = emb1.tolist()
            if hasattr(emb2, 'tolist'):
                emb2 = emb2.tolist()
            
            # Calculate cosine similarity
            emb1_np = np.array(emb1)
            emb2_np = np.array(emb2)
            
            dot_product = np.dot(emb1_np, emb2_np)
            norm1 = np.linalg.norm(emb1_np)
            norm2 = np.linalg.norm(emb2_np)
            
            cosine_similarity = dot_product / (norm1 * norm2)
            
            return {
                "text1": text1,
                "text2": text2,
                "cosine_similarity": float(cosine_similarity),
                "embedding_dimension": len(emb1),
                "similarity_interpretation": {
                    "very_similar": cosine_similarity > 0.8,
                    "similar": cosine_similarity > 0.6,
                    "somewhat_similar": cosine_similarity > 0.4,
                    "different": cosine_similarity <= 0.4
                }
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    ### TEST BLOCK ENDS


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
                        "includes": ["title", "file_name", "content", "chunk_text", "chunk_index", "file_type", "keywords", "medical_terms"]
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
                    document_name = source.get("file_name", "Unknown Document")
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