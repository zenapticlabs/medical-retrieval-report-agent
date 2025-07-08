from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import asyncio
from datetime import datetime

from app.api.routes import search, documents, admin, folder_ingestion
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.auth import create_access_token, get_current_user, verify_password
from app.db.database import get_db, engine
from app.models.user import Base, User
from app.services.sharepoint_service import SharePointService

# Setup logging
logger = setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Medical Document Search System",
    description="A powerful medical document search system using AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(folder_ingestion.router, prefix="/api", tags=["folder_ingestion"])

# Global SharePoint service instance
sharepoint_service = SharePointService()

async def refresh_sharepoint_token_periodically():
    """Background task to refresh SharePoint token every 15 minutes"""
    while True:
        try:
            await asyncio.sleep(900)  # 15 minutes
            sharepoint_service.refresh_token_if_needed()
            logger.info("SharePoint token refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing SharePoint token: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    try:
        logger.info("Initializing database tables...")
        from app.db.database import init_db
        init_db()
        logger.info("Database initialization completed")
        
        # Start SharePoint token refresh task
        asyncio.create_task(refresh_sharepoint_token_periodically())
        logger.info("SharePoint token refresh task started")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Application will continue without database initialization")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main search interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Serve the admin dashboard"""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

@app.get("/folders", response_class=HTMLResponse)
async def folder_ingestion_page(request: Request):
    """Serve the folder ingestion page"""
    return templates.TemplateResponse("folder_ingestion.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Serve the search page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Try to find user by username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token with extended expiration
    access_token = create_access_token(data={"sub": user.username})
    
    response = JSONResponse(content={
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    })
    
    # Set cookie with better parameters
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Allow JavaScript access for better compatibility
        samesite="lax",
        secure=getattr(settings, 'ENVIRONMENT', 'development') == 'production',  # Only secure in production
        max_age=8 * 60 * 60,  # 8 hours in seconds
        path="/"
    )
    
    return response

@app.get("/api/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active
    }

@app.post("/api/logout")
async def logout():
    """Logout user by clearing cookie"""
    response = JSONResponse(content={"message": "Successfully logged out"})
    response.delete_cookie(key="access_token", path="/")
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page"""
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/api/test-auth")
async def test_auth(current_user: User = Depends(get_current_user)):
    """Test endpoint to verify authentication is working"""
    return {
        "message": "Authentication successful",
        "user": {
            "username": current_user.username,
            "email": current_user.email,
            "is_admin": current_user.is_admin
        }
    }

@app.get("/api/refresh-sharepoint-token")
async def refresh_sharepoint_token():
    """Manually refresh SharePoint token (for debugging)"""
    try:
        sharepoint_service.refresh_token_if_needed()
        return {"message": "SharePoint token refreshed successfully"}
    except Exception as e:
        logger.error(f"Failed to refresh SharePoint token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh SharePoint token: {str(e)}"
        )

@app.get("/api/force-refresh-sharepoint-token")
async def force_refresh_sharepoint_token():
    """Force refresh SharePoint token regardless of expiration"""
    try:
        token = sharepoint_service.force_refresh_token()
        return {
            "message": "SharePoint token force refreshed successfully",
            "token_length": len(token) if token else 0
        }
    except Exception as e:
        logger.error(f"Failed to force refresh SharePoint token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force refresh SharePoint token: {str(e)}"
        )

@app.get("/api/test-sharepoint")
async def test_sharepoint_connection():
    """Test SharePoint connection"""
    try:
        # Try to list root folder contents
        items = sharepoint_service.list_folder_contents("")
        return {
            "status": "success",
            "message": "SharePoint connection successful",
            "items_count": len(items)
        }
    except Exception as e:
        logger.error(f"SharePoint connection test failed: {e}")
        return {
            "status": "error",
            "message": f"SharePoint connection failed: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True if settings.ENVIRONMENT == "development" else False
    ) 