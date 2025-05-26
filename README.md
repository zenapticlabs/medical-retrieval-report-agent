# Medical Document Search System

A powerful medical document search system that uses advanced AI to process, index, and search through medical documents with high accuracy and context awareness.

## Features

- **Intelligent Document Processing**

  - Processes DOCX and PDF medical documents
  - Maintains page numbers and document structure
  - Preserves section context and metadata
  - Handles long documents without truncation
- **Advanced Search Capabilities**

  - Semantic search using BioLORD-2023 medical model
  - Keyword-based matching with context
  - Page-aware results with section information
  - Date extraction near keywords
  - 10-word contextual summaries
- **User-Friendly Interface**

  - Clean, modern web interface
  - Real-time search results
  - Highlighted keyword matches
  - Document metadata display
  - Page number and section information

## Technical Stack

- **Backend**

  - Python 3.x
  - Flask web framework
  - BioLORD-2023 for medical text embeddings
  - Elasticsearch for vector storage
  - LangChain for text processing
- **Frontend**

  - HTML/CSS
  - JavaScript
  - Bootstrap for styling
- **Infrastructure**

  - Docker containerization
  - Elasticsearch for data storage
  - NLTK for text processing

## Prerequisites

- Docker and Docker Compose
- Python 3.x (for local development)
- Git

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd medical-document-search
   ```
2. Build and start the containers:

   ```bash
   docker-compose up --build
   ```
3. Access the web interface at `http://localhost:5000`

## Usage

1. **Process Documents**

   - Place medical documents in the `Redacted/` directory
   - Documents should be in DOCX or PDF format
   - The system will automatically process and index them
2. **Search Documents**

   - Enter medical terms or keywords in the search box
   - Results will show:
     - 10-word contextual summaries
     - Page numbers
     - Section information
     - Dates near keywords
     - Document metadata
3. **View Results**

   - Results are grouped by document
   - Each match shows:
     - Keyword summary
     - Page number
     - Section context
     - Relevant dates
     - Document name

## Project Structure

```
medical-document-search/
├── app.py                 # Flask application
├── document_processor.py  # Document processing logic
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker services
├── templates/            # Web interface templates
│   └── index.html       # Main search interface
└── Redacted/            # Medical documents directory
    ├── Redacted_Kidney/
    ├── Redacted_Kidney2/
    └── Redacted_Bladder/
```

## Configuration

The system can be configured through environment variables:

- `ELASTICSEARCH_HOST`: Elasticsearch host (default: elasticsearch)
- `ELASTICSEARCH_PORT`: Elasticsearch port (default: 9200)
- `MAX_RETRIES`: Connection retry attempts (default: 10)
- `RETRY_INTERVAL`: Seconds between retries (default: 10)

## Development

1. **Local Development**

   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python app.py
   ```
2. **Running Tests**

   ```bash
   # Add test commands here when implemented
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license information here]

## Acknowledgments

- BioLORD-2023 model by FremyCompany
- Elasticsearch for vector storage
- LangChain for text processing
- Flask web framework
