import pytest
from app.services.document_processor import DocumentProcessor
from app.services.vector_db import VectorDBFactory
import os

@pytest.fixture
def document_processor():
    return DocumentProcessor()

def test_document_processor_initialization(document_processor):
    assert document_processor is not None
    assert document_processor.vector_db is not None
    assert document_processor.tokenizer is not None
    assert document_processor.model is not None

def test_vector_db_connection(document_processor):
    # Test that we can connect to the vector database
    assert document_processor.vector_db._connect() is not None

def test_index_operations(document_processor):
    # Test index creation and deletion
    test_index = "test_index"
    try:
        # Create index
        document_processor.vector_db.create_index(test_index)
        
        # Delete index
        document_processor.vector_db.delete_index(test_index)
        
        assert True
    except Exception as e:
        pytest.fail(f"Index operations failed: {str(e)}")

def test_document_processing(document_processor):
    # Test document processing with a sample document
    test_doc_path = "test_document.docx"
    try:
        # Create a test document
        from docx import Document
        doc = Document()
        doc.add_paragraph("This is a test document for medical document processing.")
        doc.save(test_doc_path)
        
        # Process the document
        result = document_processor.process_document(test_doc_path)
        
        assert result is not None
        assert "document_id" in result
        assert "status" in result
        assert result["status"] == "success"
        
    except Exception as e:
        pytest.fail(f"Document processing failed: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(test_doc_path):
            os.remove(test_doc_path) 