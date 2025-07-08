"""
Add download_url and processed_files_count fields to folder_ingestions table
"""

from sqlalchemy import text
from app.db.database import engine

def upgrade():
    """Add new columns to folder_ingestions table"""
    with engine.connect() as connection:
        # Add download_url column
        connection.execute(text("""
            ALTER TABLE folder_ingestions 
            ADD COLUMN download_url VARCHAR(1000) NULL
        """))
        
        # Add processed_files_count column
        connection.execute(text("""
            ALTER TABLE folder_ingestions 
            ADD COLUMN processed_files_count INT NULL DEFAULT 0
        """))
        
        connection.commit()
        print("Successfully added download_url and processed_files_count columns to folder_ingestions table")

def downgrade():
    """Remove the added columns"""
    with engine.connect() as connection:
        # Remove download_url column
        connection.execute(text("""
            ALTER TABLE folder_ingestions 
            DROP COLUMN download_url
        """))
        
        # Remove processed_files_count column
        connection.execute(text("""
            ALTER TABLE folder_ingestions 
            DROP COLUMN processed_files_count
        """))
        
        connection.commit()
        print("Successfully removed download_url and processed_files_count columns from folder_ingestions table")

if __name__ == "__main__":
    upgrade() 