from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import boto3
import json
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
from app.core.config import settings
from datetime import datetime, date
from sqlalchemy import func

router = APIRouter()
logger = setup_logging()
sharepoint_service = SharePointService()

# Initialize AWS Lambda client
lambda_client = boto3.client(
    'lambda',
    region_name=getattr(settings, 'AWS_REGION', 'us-east-2'),
    aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
    aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
)

@router.get("/folders/list")
async def list_folders(
    path: Optional[str] = Query("", description="Path to list folders from")
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
            # Trigger AWS Lambda function
            # Extract patient name from folder path and format it properly
            patient_folder_name = folder.folder_path.split('/')[-1]  # Get last part of path
            patient_name = patient_folder_name.replace(', ', '_').replace(' ', '_')  # Format: "Adkisson, Patricia" -> "Adkisson_Patricia"
            
            lambda_payload = {
                "path": folder.folder_path,
                "patient_name": patient_name,
                "max_depth": 5,
                "use_mock_ai": False,
                "ingestion_id": db_ingestion.id,
                "user_id": current_user.id,
                "callback_url": f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/api/folders/ingestions/{db_ingestion.id}/callback"
            }
            
            logger.info(f"Invoking Lambda function with payload: {lambda_payload}")
            
            lambda_response = lambda_client.invoke(
                FunctionName=getattr(settings, 'LAMBDA_FUNCTION_NAME', 'chronology-summaries-SharePointChronologyFunction-j91ttACGYNQq'),
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(lambda_payload)
            )
            
            # Update status to PROCESSING and store Lambda job ID
            db_ingestion.status = IngestionStatus.PROCESSING
            db_ingestion.lambda_job_id = lambda_response.get('ResponseMetadata', {}).get('RequestId')
            db.commit()
            db.refresh(db_ingestion)

            logger.info(f"Successfully triggered Lambda function for folder: {folder.folder_path}")
            return db_ingestion
        except Exception as e:
            # If Lambda trigger fails, update status to FAILED
            logger.error(f"Failed to trigger Lambda function: {str(e)}")
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

@router.patch("/folders/ingestions/{ingestion_id}/callback")
async def lambda_callback_update(
    ingestion_id: int,
    update: FolderIngestionUpdate,
    db: Session = Depends(get_db)
):
    """Update a folder ingestion record via Lambda callback (no authentication required)"""
    try:
        ingestion = db.query(FolderIngestion).filter(
            FolderIngestion.id == ingestion_id
        ).first()
        
        if not ingestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder ingestion not found"
            )
        
        # Update the ingestion record
        for field, value in update.dict(exclude_unset=True).items():
            setattr(ingestion, field, value)
        
        # Set updated timestamp
        ingestion.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(ingestion)
        
        logger.info(f"Successfully updated ingestion {ingestion_id} via Lambda callback: status={ingestion.status}")
        
        return {
            "success": True,
            "message": "Ingestion status updated successfully",
            "ingestion_id": ingestion_id,
            "status": ingestion.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Lambda callback update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ingestion: {str(e)}"
        )

@router.get("/folders/ingestions/{ingestion_id}/download")
async def download_ingestion_file(
    ingestion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the completed ingestion file"""
    ingestion = db.query(FolderIngestion).filter(
        FolderIngestion.id == ingestion_id,
        FolderIngestion.user_id == current_user.id
    ).first()
    
    if not ingestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder ingestion not found"
        )
    
    if ingestion.status != IngestionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingestion is not completed yet"
        )
    
    if not ingestion.download_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download file not available"
        )
    
    # Generate a pre-signed URL for S3 download
    try:
        s3_client = boto3.client(
            's3',
            region_name=getattr(settings, 'AWS_REGION', 'us-east-2'),
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        )
        
        # Extract bucket and key from download_url
        # Assuming download_url format: s3://bucket-name/path/to/file
        if ingestion.download_url.startswith('s3://'):
            url_parts = ingestion.download_url[5:].split('/', 1)
            bucket_name = url_parts[0]
            object_key = url_parts[1] if len(url_parts) > 1 else ''
            
            # Generate pre-signed URL valid for 1 hour
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=3600
            )
            
            return {"download_url": presigned_url, "expires_in": 3600}
        else:
            # If it's already a direct URL, return it
            return {"download_url": ingestion.download_url, "expires_in": 3600}
            
    except Exception as e:
        logger.error(f"Error generating download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        ) 