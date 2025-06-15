import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.core.auth import get_password_hash

def create_admin_user():
    db = SessionLocal()
    try:
        # Delete existing admin user if exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("Deleting existing admin user...")
            db.delete(existing_admin)
            db.commit()
            print("Existing admin user deleted")

        # Create new admin user
        admin_user = User(
            email="admin@medicialapp.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            is_admin=True
        )
        db.add(admin_user)
        db.commit()
        print("New admin user created successfully")
        
        # Verify the user was created
        created_admin = db.query(User).filter(User.username == "admin").first()
        if created_admin:
            print(f"Admin user details: username={created_admin.username}, email={created_admin.email}, is_admin={created_admin.is_admin}")
        else:
            print("Error: Admin user was not created successfully")
            
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user() 