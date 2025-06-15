from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.user import User
from app.models.folder_ingestion import FolderIngestion, IngestionStatus
from app.schemas.folder_ingestion import (
    FolderIngestionCreate,
    FolderIngestionResponse,
    FolderIngestionUpdate,
    PaginatedIngestionResponse
)
from app.core.auth import get_current_user
from app.services.sharepoint_service import SharePointService
from app.core.logging import setup_logging
from datetime import datetime, date
from sqlalchemy import func

router = APIRouter()
logger = setup_logging()
sharepoint_service = SharePointService()

@router.get("/folders/list")
async def list_folders(
    path: Optional[str] = Query("", description="Path to list folders from"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List folders from SharePoint"""
    try:
        logger.info(f"Listing folders from path: {path}")
        
        # Get folder contents from SharePoint
        items = sharepoint_service.list_folder_contents(path)
        
        # Filter folders based on path
        if not path:  # If we're at root level
            # Only show Document Summary Project folder
            folders = [
                {"name": item["name"]}
                for item in items
                if "folder" in item and item["name"] == "Document Summary Project"
            ]
        else:
            # Show all folders for subdirectories
            folders = [
                {"name": item["name"]}
                for item in items
                if "folder" in item
            ]
        
        # Sort folders alphabetically
        folders.sort(key=lambda x: x["name"])
        
        logger.info(f"Found {len(folders)} folders in path: {path}")
        return folders
    except Exception as e:
        logger.error(f"Error listing folders: {str(e)}")
        if "Authentication failed" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SharePoint authentication failed. Please check your credentials."
            )
        elif "Folder not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

@router.post("/folders/ingest", response_model=FolderIngestionResponse)
async def create_folder_ingestion(
    folder: FolderIngestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new folder ingestion record and trigger the ingestion process"""
    try:
        logger.info(f"Starting ingestion for folder: {folder.folder_path}")
        
        # Check if the folder is at the 3rd level
        path_parts = folder.folder_path.split('/')
        if len(path_parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ingestion is only allowed at the 3rd level of the folder structure"
            )
        
        # Verify folder exists in SharePoint
        try:
            folder_metadata = sharepoint_service.get_folder_metadata(folder.folder_path)
            if not folder_metadata.get("folder"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected path is not a folder"
                )
        except Exception as e:
            logger.error(f"Folder not found in SharePoint: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder not found in SharePoint: {str(e)}"
            )

        # Check if there's already an active ingestion for this folder today
        today = date.today()
        existing_ingestion = db.query(FolderIngestion).filter(
            FolderIngestion.folder_path == folder.folder_path,
            FolderIngestion.status.in_([IngestionStatus.PENDING, IngestionStatus.PROCESSING]),
            func.date(FolderIngestion.created_at) == today
        ).first()

        if existing_ingestion:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An ingestion process is already running for this folder today"
            )

        # Create ingestion record with correct enum value
        db_ingestion = FolderIngestion(
            folder_path=folder.folder_path,
            user_id=current_user.id,
            status=IngestionStatus.PENDING  # Using the enum value directly
        )
        db.add(db_ingestion)
        db.commit()
        db.refresh(db_ingestion)

        try:
            # TODO: Trigger AWS Lambda function here
            # This would be implemented based on your AWS Lambda setup
            # For now, we'll just update the status to PROCESSING
            db_ingestion.status = IngestionStatus.PROCESSING
            db.commit()
            db.refresh(db_ingestion)

            logger.info(f"Successfully created ingestion record for folder: {folder.folder_path}")
            return db_ingestion
        except Exception as e:
            # If Lambda trigger fails, update status to FAILED
            db_ingestion.status = IngestionStatus.FAILED
            db_ingestion.error_message = str(e)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start ingestion process: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating folder ingestion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/folders/ingestions", response_model=PaginatedIngestionResponse)
async def list_folder_ingestions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all folder ingestion records for the current user with pagination"""
    try:
        logger.info(f"Listing folder ingestions for user: {current_user.id}, page: {page}, page_size: {page_size}")
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get total count
        total_count = db.query(FolderIngestion).filter(
            FolderIngestion.user_id == current_user.id
        ).count()
        
        # Get paginated results
        ingestions = db.query(FolderIngestion).filter(
            FolderIngestion.user_id == current_user.id
        ).order_by(FolderIngestion.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size
        
        logger.info(f"Found {len(ingestions)} ingestion records out of {total_count} total")
        
        return {
            "items": ingestions,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error listing folder ingestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/folders/ingestions/{ingestion_id}", response_model=FolderIngestionResponse)
async def get_folder_ingestion(
    ingestion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific folder ingestion"""
    ingestion = db.query(FolderIngestion).filter(
        FolderIngestion.id == ingestion_id,
        FolderIngestion.user_id == current_user.id
    ).first()
    
    if not ingestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder ingestion not found"
        )
    
    return ingestion

@router.patch("/folders/ingestions/{ingestion_id}", response_model=FolderIngestionResponse)
async def update_folder_ingestion(
    ingestion_id: int,
    update: FolderIngestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a folder ingestion record (typically called by AWS Lambda callback)"""
    ingestion = db.query(FolderIngestion).filter(
        FolderIngestion.id == ingestion_id,
        FolderIngestion.user_id == current_user.id
    ).first()
    
    if not ingestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder ingestion not found"
        )
    
    for field, value in update.dict(exclude_unset=True).items():
        setattr(ingestion, field, value)
    
    db.commit()
    db.refresh(ingestion)
    return ingestion 