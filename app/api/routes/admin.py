from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.user import User
from app.models.folder_ingestion import FolderIngestion
from app.core.auth import get_current_user, get_current_admin_user, get_password_hash
from app.core.config import settings
from app.schemas.admin import UserResponse, DashboardStats
from app.schemas.folder_ingestion import FolderIngestionResponse
from app.schemas.user import UserCreate

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new user"""
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        is_admin=user.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users"""
    users = db.query(User).all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_documents = db.query(FolderIngestion).count()
    
    return {
        "username": current_user.username,
        "total_users": total_users,
        "active_users": active_users,
        "total_documents": total_documents
    }

@router.get("/folders/ingestions", response_model=List[FolderIngestionResponse])
async def get_folder_ingestions(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all folder ingestions"""
    ingestions = db.query(FolderIngestion).all()
    return ingestions

@router.get("/folders/ingestions/{ingestion_id}", response_model=FolderIngestionResponse)
async def get_folder_ingestion(
    ingestion_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get folder ingestion details"""
    ingestion = db.query(FolderIngestion).filter(FolderIngestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder ingestion not found"
        )
    
    return ingestion 