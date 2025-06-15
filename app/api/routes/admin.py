from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.core.auth import get_current_admin_user, get_password_hash
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
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
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
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

@router.get("/dashboard")
async def get_admin_dashboard_data(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    # Get total users count
    total_users = db.query(User).count()
    
    # Get total documents count (you'll need to implement this based on your document model)
    total_documents = 0  # Replace with actual document count
    
    # Get active users (users who have logged in recently)
    active_users = db.query(User).filter(User.last_login >= datetime.utcnow() - timedelta(days=7)).count()
    
    return {
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "total_users": total_users,
        "total_documents": total_documents,
        "active_users": active_users
    } 