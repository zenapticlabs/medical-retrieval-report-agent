from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.folder_ingestion import IngestionStatus

class FolderIngestionBase(BaseModel):
    folder_path: str

class FolderIngestionCreate(FolderIngestionBase):
    pass

class FolderIngestionUpdate(BaseModel):
    status: Optional[IngestionStatus] = None
    lambda_job_id: Optional[str] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    processed_files_count: Optional[int] = None

class FolderIngestionResponse(FolderIngestionBase):
    id: int
    ingestion_date: datetime
    status: IngestionStatus
    user_id: int
    lambda_job_id: Optional[str] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    processed_files_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedIngestionResponse(BaseModel):
    items: List[FolderIngestionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int 