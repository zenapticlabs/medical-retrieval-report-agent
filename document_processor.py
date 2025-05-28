import os
import re
import torch
import numpy as np
from docx import Document
from transformers import AutoTokenizer, AutoModel
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import nltk
import time
import logging
import warnings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from datetime import datetime
from services.vector_db import VectorDBFactory

# Suppress specific warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download NLTK data
nltk.download('punkt')
nltk.download('stopwords')

class DocumentProcessor:
    def __init__(self, vector_db_type: str = 'elasticsearch', **vector_db_kwargs):
        logger.info("Initializing DocumentProcessor...")
        
        # Initialize vector database service
        self.vector_db = VectorDBFactory.create_service(vector_db_type, **vector_db_kwargs)
        self.index_name = "medical_documents"
        
        self.stop_words = set(stopwords.words('english'))
        
        # Initialize LangChain components with larger chunk size
        logger.info("Initializing LangChain components...")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,  # Increased chunk size
            chunk_overlap=200,  # Increased overlap for better context
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            keep_separator=True  # Keep separators for better context
        )
        
        # Initialize BioLORD model for embeddings
        logger.info("Loading BioLORD-2023 model...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                "FremyCompany/BioLORD-2023",
                local_files_only=False,
                force_download=True
            )
            self.model = AutoModel.from_pretrained(
                "FremyCompany/BioLORD-2023",
                local_files_only=False,
                force_download=True
            )
            self.model.eval()
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    def get_embedding(self, text):
        """Generate embeddings using BioLORD model with no truncation"""
        try:
            # Calculate max length based on model's maximum context
            max_length = self.tokenizer.model_max_length
            
            # If text is longer than max_length, process in chunks
            if len(text) > max_length:
                logger.warning(f"Text length ({len(text)}) exceeds model max length ({max_length}). Processing in chunks...")
                
                # Split text into smaller chunks with overlap
                words = text.split()
                chunks = []
                current_chunk = []
                current_length = 0
                
                for word in words:
                    word_length = len(word) + 1  # +1 for space
                    if current_length + word_length > max_length * 0.8:  # Use 80% of max length
                        chunks.append(' '.join(current_chunk))
                        # Keep last 20% of words for overlap
                        overlap_words = current_chunk[-int(len(current_chunk) * 0.2):]
                        current_chunk = overlap_words
                        current_length = sum(len(w) + 1 for w in overlap_words)
                    current_chunk.append(word)
                    current_length += word_length
                
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                
                embeddings = []
                for chunk in chunks:
                    tokens = self.tokenizer(chunk, return_tensors="pt", truncation=True, max_length=max_length)
                    with torch.no_grad():
                        outputs = self.model(**tokens)
                    chunk_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                    embeddings.append(chunk_embedding)
                
                # Average the embeddings
                return np.mean(embeddings, axis=0)
            else:
                # Process normally if within limits
                tokens = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
                with torch.no_grad():
                    outputs = self.model(**tokens)
                return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def is_template_text(self, text):
        template_patterns = [
            r"Please index all documents you have reviewed",
            r"This should include medical records",
            r"VA benefit records",
            r"transcripts",
            r"MEDICAL RECORD REVIEW",
            r"Record Index",
            r"\[.*?\]",  # Text in square brackets
            r"^\s*$",    # Empty lines
            r"^\s*\d+\s*$"  # Just numbers
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in template_patterns)

    def extract_keywords(self, text):
        # Extract medical terms and important words
        words = word_tokenize(text.lower())
        # Remove stop words and short words
        keywords = [word for word in words if word not in self.stop_words and len(word) > 3]
        return list(set(keywords))  # Remove duplicates

    def extract_page_from_text(self, text):
        """Extract page number from text content using various patterns"""
        page_patterns = [
            r'Page\s+(\d+)',
            r'page\s+(\d+)',
            r'PAGE\s+(\d+)',
            r'P\.\s*(\d+)',
            r'p\.\s*(\d+)',
            r'^(\d+)$',  # Just a number on its own line
            r'^\s*(\d+)\s*$'  # Number with whitespace
        ]
        
        for pattern in page_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

    def create_keyword_summary(self, text, keyword, max_words=10):
        """Create a 10-word summary including the keyword"""
        try:
            # Find keyword position (case insensitive)
            text_lower = text.lower()
            keyword_lower = keyword.lower()
            
            keyword_pos = text_lower.find(keyword_lower)
            if keyword_pos == -1:
                return f"Summary for {keyword}"
            
            # Get words around the keyword
            words = text.split()
            keyword_word_index = -1
            
            # Find the word index of the keyword
            for i, word in enumerate(words):
                if keyword_lower in word.lower():
                    keyword_word_index = i
                    break
            
            if keyword_word_index == -1:
                return f"Summary for {keyword}"
            
            # Calculate how many words to take before and after the keyword
            # to get exactly 10 words total
            remaining_words = max_words - 1  # -1 for the keyword itself
            before_words = remaining_words // 2
            after_words = remaining_words - before_words
            
            # Extract words around the keyword
            start_idx = max(0, keyword_word_index - before_words)
            end_idx = min(len(words), keyword_word_index + after_words + 1)
            
            # Adjust if we're at the start or end of the text
            if start_idx == 0:
                end_idx = min(len(words), max_words)
            elif end_idx == len(words):
                start_idx = max(0, len(words) - max_words)
            
            summary_words = words[start_idx:end_idx]
            
            # Ensure we have exactly 10 words
            if len(summary_words) > max_words:
                # If we have too many words, prioritize keeping the keyword
                keyword_idx = summary_words.index(words[keyword_word_index])
                start = max(0, keyword_idx - before_words)
                end = min(len(summary_words), start + max_words)
                summary_words = summary_words[start:end]
            
            return " ".join(summary_words).strip()
        except Exception as e:
            logger.error(f"Error creating keyword summary: {str(e)}")
            return f"Summary for {keyword}"

    def get_chunks_with_pages(self, text, document_name):
        """Split text into chunks and associate with page numbers"""
        logger.info("Starting document chunking process with page detection...")
        
        # First, try to split text by page breaks or page indicators
        page_chunks = []
        current_page = 1
        
        # Split by common page break patterns
        page_break_patterns = [
            r'\n\s*Page\s+\d+\s*\n',
            r'\n\s*page\s+\d+\s*\n',
            r'\n\s*PAGE\s+\d+\s*\n',
            r'\f',  # Form feed character
            r'\n\s*\d+\s*\n(?=\S)',  # Number on its own line followed by content
        ]
        
        # Try to split by page breaks
        text_parts = [text]
        for pattern in page_break_patterns:
            new_parts = []
            for part in text_parts:
                new_parts.extend(re.split(pattern, part))
            text_parts = new_parts
        
        # If we found page breaks, assign page numbers
        if len(text_parts) > 1:
            for i, part in enumerate(text_parts):
                if part.strip():  # Skip empty parts
                    page_chunks.append({
                        'text': part.strip(),
                        'page': i + 1
                    })
        else:
            # No clear page breaks found, estimate pages by content length
            # Assume ~500 words per page (rough estimate)
            words_per_page = 500
            words = text.split()
            
            for i in range(0, len(words), words_per_page):
                page_text = ' '.join(words[i:i + words_per_page])
                page_chunks.append({
                    'text': page_text,
                    'page': (i // words_per_page) + 1
                })
        
        # Now split each page chunk into smaller chunks using LangChain
        processed_chunks = []
        current_section = "main"
        section_context = []
        
        for page_chunk in page_chunks:
            page_text = page_chunk['text']
            page_number = page_chunk['page']
            
            # Split page text into smaller chunks
            chunks = self.text_splitter.split_text(page_text)
            
            for i, chunk in enumerate(chunks):
                # Skip empty chunks
                if not chunk.strip():
                    continue
                    
                # Skip template text
                if self.is_template_text(chunk):
                    continue
                
                # Check if this is a section header
                if chunk.isupper() or re.match(r'^[A-Z][a-z]+:', chunk):
                    current_section = chunk
                    section_context = [chunk]
                    continue
                
                # Add chunk to section context
                section_context.append(chunk)
                
                # Process chunk if it has substantial content
                if len(chunk.strip()) >= 50:
                    # Include section context in the chunk
                    context_text = " ".join(section_context[-3:])
                    keywords = self.extract_keywords(context_text)
                    
                    # Try to extract more specific page number from chunk content
                    chunk_page = self.extract_page_from_text(chunk) or page_number
                    
                    logger.info(f"Processing chunk for page {chunk_page}:")
                    logger.info(f"- Section: {current_section}")
                    logger.info(f"- Length: {len(chunk)} characters")
                    logger.info(f"- Keywords: {', '.join(keywords[:5])}...")
                    
                    processed_chunks.append({
                        'text': chunk,
                        'page_number': chunk_page,
                        'section': current_section,
                        'context': context_text,
                        'keywords': keywords
                    })
        
        # If no chunks were processed, create at least one chunk with the full text
        if not processed_chunks and text.strip():
            logger.info("No chunks met criteria, creating single chunk with full text")
            keywords = self.extract_keywords(text)
            processed_chunks.append({
                'text': text,
                'page_number': 1,
                'section': 'main',
                'context': text,
                'keywords': keywords
            })
        
        logger.info(f"Chunking complete. Total processed chunks: {len(processed_chunks)}")
        return processed_chunks

    def create_index(self):
        """Create or recreate the vector database index"""
        self.vector_db.delete_index(self.index_name)
        return self.vector_db.create_index(self.index_name, dimensions=768)

    def extract_date(self, text):
        """Extract date from text using regex."""
        date_pattern = r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'
        match = re.search(date_pattern, text)
        if match:
            return match.group(0)
        return None

    def process_document(self, docx_path):
        try:
            logger.info(f"Processing document: {docx_path}")
            
            # Use LangChain's Docx2txtLoader to load the document
            loader = Docx2txtLoader(docx_path)
            documents = loader.load()
            
            if not documents:
                logger.warning(f"No content found in document: {docx_path}")
                return
            
            # Get the full text from the document
            text = documents[0].page_content
            metadata = documents[0].metadata
            
            logger.info(f"Document loaded. Total length: {len(text)} characters")
            logger.info(f"Document metadata: {metadata}")
            
            document_name = os.path.basename(docx_path)
            
            # Get chunks with page information
            chunks = self.get_chunks_with_pages(text, document_name)
            
            logger.info(f"Processing {len(chunks)} chunks for document: {document_name}")
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} on page {chunk['page_number']}")
                
                # Generate embedding for the chunk with its context
                embedding = self.get_embedding(chunk['context'])
                
                # Extract date from chunk
                extracted_date = self.extract_date(chunk['text'])
                
                # Store in vector database
                document = {
                    "content": chunk['text'],
                    "context": chunk['context'],
                    "embedding": embedding.tolist(),
                    "document_name": document_name,
                    "chunk_index": i,
                    "page_number": chunk['page_number'],
                    "section": chunk['section'],
                    "keywords": chunk['keywords'],
                    "metadata": metadata,
                    "extracted_date": extracted_date
                }
                
                self.vector_db.index_document(self.index_name, document)
                logger.info(f"Chunk {i+1} processed and stored successfully on page {chunk['page_number']}")
            
            logger.info(f"Successfully processed document: {docx_path}")
        except Exception as e:
            logger.error(f"Error processing document {docx_path}: {str(e)}")
            raise

    def search(self, query, top_k=5):
        try:
            # Remove stop words from query
            query_words = word_tokenize(query.lower())
            query_words = [word for word in query_words if word not in self.stop_words]
            query = " ".join(query_words)
            
            # Get query embedding
            query_embedding = self.get_embedding(query)
            
            # Search in vector database
            results = self.vector_db.search(self.index_name, query_embedding.tolist(), top_k)
            
            # Process and format results
            document_results = {}
            
            for result in results:
                source = result['source']
                doc_name = source['document_name']
                content = source['content']
                page_number = source.get('page_number', 1)
                extracted_date = source.get('extracted_date', '')
                
                if doc_name not in document_results:
                    document_results[doc_name] = {
                        'document_name': doc_name,
                        'keyword_matches': {}
                    }
                
                # For each keyword in the query, find matches in the content
                for keyword in query_words:
                    if keyword.lower() in content.lower():
                        # Extract date near the keyword
                        date_near_keyword = self.extract_date_near_keyword(content, keyword)
                        # Use extracted date from chunk if no date found near keyword
                        final_date = date_near_keyword or extracted_date or 'Not specified'
                        
                        # Create keyword summary
                        keyword_summary = self.create_keyword_summary(content, keyword)
                        
                        if keyword not in document_results[doc_name]['keyword_matches']:
                            document_results[doc_name]['keyword_matches'][keyword] = []
                        
                        # Add the match with its context, page number, and summary
                        document_results[doc_name]['keyword_matches'][keyword].append({
                            'date': final_date,
                            'content': content,
                            'page_number': page_number,
                            'summary': keyword_summary,
                            'section': source.get('section', 'main')
                        })
            
            # Remove documents with no matches
            document_results = {
                doc_name: doc_data 
                for doc_name, doc_data in document_results.items() 
                if any(len(matches) > 0 for matches in doc_data['keyword_matches'].values())
            }
            
            # Sort matches by score within each keyword group
            for doc_name in document_results:
                for keyword in document_results[doc_name]['keyword_matches']:
                    # Limit to top matches per keyword
                    document_results[doc_name]['keyword_matches'][keyword] = \
                        document_results[doc_name]['keyword_matches'][keyword][:3]
            
            return document_results
        except Exception as e:
            logger.error(f"Error performing search: {str(e)}")
            return {}

    def list_documents(self):
        """List all documents in the index"""
        return self.vector_db.list_documents(self.index_name)

    def get_document_content(self, document_name):
        """Get all chunks of a specific document organized by page"""
        try:
            # Search for all chunks of the document
            results = self.vector_db.search(
                self.index_name,
                query_vector=[0] * 768,  # Dummy vector for getting all documents
                top_k=1000
            )
            
            # Filter results for the specific document
            document_chunks = [
                result['source'] for result in results
                if result['source']['document_name'] == document_name
            ]
            
            if not document_chunks:
                return None
            
            # Organize chunks by page
            pages = {}
            metadata = None
            
            for chunk in document_chunks:
                page_num = chunk.get('page_number', 1)
                
                if page_num not in pages:
                    pages[page_num] = []
                
                pages[page_num].append({
                    'chunk_index': chunk.get('chunk_index', 0),
                    'content': chunk.get('content', ''),
                    'section': chunk.get('section', 'main'),
                    'keywords': chunk.get('keywords', []),
                    'extracted_date': chunk.get('extracted_date', '')
                })
                
                # Get metadata from the first chunk
                if metadata is None:
                    metadata = chunk.get('metadata', {})
            
            return {
                'document_name': document_name,
                'total_pages': len(pages),
                'total_chunks': sum(len(chunks) for chunks in pages.values()),
                'pages': pages,
                'metadata': metadata
            }
        except Exception as e:
            logger.error(f"Error getting document content: {str(e)}")
            return None

    def process_all_documents(self, documents_dir):
        """Process all documents in the directory, dropping old data first"""
        processed_files = []
        
        try:
            if not os.path.exists(documents_dir):
                logger.error(f"Documents directory not found: {documents_dir}")
                return processed_files
            
            # Create fresh index
            self.create_index()
            
            # First, collect all .docx files
            docx_files = []
            for root, dirs, files in os.walk(documents_dir):
                for file in files:
                    if file.endswith('.docx'):
                        docx_files.append(os.path.join(root, file))
            
            if not docx_files:
                logger.warning(f"No .docx files found in directory: {documents_dir}")
                return processed_files
            
            logger.info(f"Found {len(docx_files)} .docx files to process")
            
            # Then process each file
            for file_path in docx_files:
                try:
                    logger.info(f"Processing document: {file_path}")
                    self.process_document(file_path)
                    processed_files.append(file_path)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    continue  # Continue with next file even if one fails
            
            logger.info(f"Successfully processed {len(processed_files)} out of {len(docx_files)} files")
            return processed_files
            
        except Exception as e:
            logger.error(f"Error in process_all_documents: {str(e)}")
            return processed_files  # Return empty list instead of raising

    def extract_date_near_keyword(self, text, keyword, window_size=100):
        """Extract date that appears before a keyword within a window of text."""
        try:
            # Find the position of the keyword
            keyword_pos = text.lower().find(keyword.lower())
            if keyword_pos == -1:
                return None
            
            # Look for date before and after the keyword within window_size characters
            text_before = text[max(0, keyword_pos - window_size):keyword_pos + len(keyword)]
            text_after = text[keyword_pos:min(len(text), keyword_pos + len(keyword) + window_size)]
            
            # Combine both before and after text for date search
            search_text = text_before + " " + text_after
            
            # Try different date patterns
            date_patterns = [
                r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
                r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YYYY
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
                r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',  # DD Month YYYY
                r'\b\d{4}-\d{1,2}-\d{1,2}\b',  # YYYY-MM-DD
                r'\b\d{1,2}\.\d{1,2}\.\d{2,4}\b'  # DD.MM.YYYY
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, search_text, re.IGNORECASE)
                if matches:
                    return matches[-1]  # Return the most recent date
                
            return None
        except Exception as e:
            logger.error(f"Error extracting date near keyword: {str(e)}")
            return None 