from sqlalchemy import create_engine, Column, DateTime
from sqlalchemy.sql import text
from app.core.config import settings

def upgrade():
    # Create database engine using the correct URL format
    database_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    engine = create_engine(database_url)
    
    # Add last_login column
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN last_login DATETIME NULL
        """))
        conn.commit()

if __name__ == "__main__":
    upgrade() 