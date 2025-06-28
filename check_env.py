#!/usr/bin/env python3
"""
Environment variable checker for the medical application
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_required_vars():
    """Check if all required environment variables are set"""
    required_vars = [
        'MYSQL_ROOT_PASSWORD',
        'MYSQL_DATABASE', 
        'MYSQL_USER',
        'MYSQL_PASSWORD',
        'SHAREPOINT_TENANT_ID',
        'SHAREPOINT_CLIENT_ID',
        'SHAREPOINT_CLIENT_SECRET',
        'SHAREPOINT_SITE_ID'
    ]
    
    optional_vars = [
        'JWT_SECRET_KEY',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'LAMBDA_FUNCTION_NAME',
        'BASE_URL'
    ]
    
    print("=== Environment Variable Check ===")
    print()
    
    # Check required variables
    print("Required Variables:")
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {'*' * len(value)} (set)")
        else:
            print(f"✗ {var}: NOT SET")
            missing_required.append(var)
    
    print()
    print("Optional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {'*' * len(value)} (set)")
        else:
            print(f"- {var}: not set (optional)")
    
    print()
    if missing_required:
        print("❌ MISSING REQUIRED VARIABLES:")
        for var in missing_required:
            print(f"   - {var}")
        print()
        print("Please set these variables in your .env file")
        return False
    else:
        print("✅ All required variables are set!")
        return True

def check_database_config():
    """Check database configuration"""
    print("=== Database Configuration ===")
    
    mysql_host = os.getenv('MYSQL_HOST', 'mysql')
    mysql_port = os.getenv('MYSQL_PORT', '3306')
    mysql_database = os.getenv('MYSQL_DATABASE')
    mysql_user = os.getenv('MYSQL_USER')
    
    print(f"Host: {mysql_host}")
    print(f"Port: {mysql_port}")
    print(f"Database: {mysql_database}")
    print(f"User: {mysql_user}")
    
    # Test if we can construct the connection URL
    if all([mysql_database, mysql_user]):
        password = os.getenv('MYSQL_PASSWORD', '')
        connection_url = f"mysql+pymysql://{mysql_user}:{'*' * len(password)}@{mysql_host}:{mysql_port}/{mysql_database}"
        print(f"Connection URL: {connection_url}")
    else:
        print("Cannot construct connection URL - missing required variables")

if __name__ == "__main__":
    check_required_vars()
    print()
    check_database_config() 