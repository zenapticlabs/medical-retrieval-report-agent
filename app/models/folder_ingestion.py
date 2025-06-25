from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class IngestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class FolderIngestion(Base):
    __tablename__ = "folder_ingestions"

    id = Column(Integer, primary_key=True, index=True)
    folder_path = Column(String(1000), nullable=False)
    ingestion_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(IngestionStatus), nullable=False, default=IngestionStatus.PENDING)
    user_id = Column(Integer, ForeignKey("users.id"))
    lambda_job_id = Column(String(255), nullable=True)
    error_message = Column(String(1000), nullable=True)
    download_url = Column(String(1000), nullable=True)
    processed_files_count = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="folder_ingestions") 