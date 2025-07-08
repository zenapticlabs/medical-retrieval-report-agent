import logging
import sys
from app.core.config import settings

def setup_logging():
    """Configure logging for the application"""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels for third-party libraries
    logging.getLogger("elasticsearch").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("opensearch").setLevel(logging.WARNING)
    
    # Create logger for this application
    logger = logging.getLogger("medical_document_search")
    logger.setLevel(log_level)
    
    return logger 