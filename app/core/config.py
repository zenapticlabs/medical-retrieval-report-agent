from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Elasticsearch settings
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    
    # OpenSearch settings
    USE_OPENSEARCH: bool = os.getenv("USE_OPENSEARCH", "false").lower() == "true"
    OPENSEARCH_ENDPOINT: Optional[str] = os.getenv("OPENSEARCH_ENDPOINT")
    OPENSEARCH_INDEX_NAME: str = os.getenv("OPENSEARCH_INDEX_NAME", "medical_documents")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-2")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # Lambda function settings
    LAMBDA_FUNCTION_NAME: str = os.getenv("LAMBDA_FUNCTION_NAME", "chronology-summaries-SharePointChronologyFunction-j91ttACGYNQq")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    # SharePoint settings
    SHAREPOINT_TENANT_ID: str = os.getenv("SHAREPOINT_TENANT_ID")
    SHAREPOINT_CLIENT_ID: str = os.getenv("SHAREPOINT_CLIENT_ID")
    SHAREPOINT_CLIENT_SECRET: str = os.getenv("SHAREPOINT_CLIENT_SECRET")
    SHAREPOINT_SITE_ID: str = os.getenv("SHAREPOINT_SITE_ID")
    
    # Vector dimensions
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "768"))
    
    # Document processing settings
    DOCUMENTS_DIR: str = os.getenv("DOCUMENTS_DIR", "Redacted")
    
    # Retry settings
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "10"))
    RETRY_INTERVAL: int = int(os.getenv("RETRY_INTERVAL", "10"))
    
    # Model settings
    TRANSFORMERS_CACHE: str = "/root/.cache"
    
    # MySQL settings
    MYSQL_ROOT_PASSWORD: str
    MYSQL_DATABASE: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    
    # JWT settings - Extended for better user experience
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours default
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings object
settings = Settings() 