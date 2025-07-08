from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.sql import text
from app.core.config import settings

def upgrade():
    # Create database engine using the correct URL format
    database_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    engine = create_engine(database_url)
    
    # Drop existing table if it exists
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS folder_ingestions"))
        conn.commit()
    
    # Create folder_ingestions table with correct enum values
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS folder_ingestions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                folder_path VARCHAR(1000) NOT NULL,
                ingestion_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                status ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
                user_id INT NOT NULL,
                lambda_job_id VARCHAR(255),
                error_message VARCHAR(1000),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        conn.commit()

def downgrade():
    # Create database engine using the correct URL format
    database_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    engine = create_engine(database_url)
    
    # Drop folder_ingestions table
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS folder_ingestions"))
        conn.commit()

if __name__ == "__main__":
    upgrade() 