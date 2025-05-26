from flask import Flask, render_template, request, jsonify
from document_processor import DocumentProcessor
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
processor = DocumentProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        query = request.json.get('query', '')
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        logger.info(f"Processing search query: {query}")
        results = processor.search(query)
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_documents():
    try:
        documents_dir = os.path.join(os.path.dirname(__file__), 'Redacted')
        logger.info(f"Processing documents in directory: {documents_dir}")
        
        if not os.path.exists(documents_dir):
            return jsonify({
                'error': f'Documents directory not found: {documents_dir}',
                'status': 'error',
                'files': []
            }), 404
        
        processed_files = processor.process_all_documents(documents_dir)
        
        # Ensure processed_files is a list
        if not isinstance(processed_files, list):
            processed_files = []
        
        # Get the count of processed files
        file_count = len(processed_files) if processed_files else 0
        
        response = {
            'message': f'Successfully processed {file_count} documents',
            'status': 'success' if file_count > 0 else 'warning',
            'files': processed_files,
            'processed_files': processed_files  # Add this for backward compatibility
        }
        
        if file_count == 0:
            response['message'] = 'No documents were processed'
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'files': [],
            'processed_files': []  # Add this for backward compatibility
        }), 500

@app.route('/documents', methods=['GET'])
def list_documents():
    """List all processed documents"""
    try:
        results = processor.list_documents()
        return jsonify({
            'status': 'success',
            'documents': results
        })
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'documents': []
        }), 500

@app.route('/documents/<document_name>', methods=['GET'])
def get_document(document_name):
    """Get content of a specific document"""
    try:
        content = processor.get_document_content(document_name)
        if content is None:
            return jsonify({
                'error': f'Document not found: {document_name}',
                'status': 'error'
            }), 404
            
        return jsonify({
            'status': 'success',
            'document_name': document_name,
            'content': content
        })
    except Exception as e:
        logger.error(f"Error getting document content: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 