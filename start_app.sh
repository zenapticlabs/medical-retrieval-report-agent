#!/bin/bash

echo "=== Medical Application Startup Script ==="
echo

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with the required environment variables."
    echo "You can copy from .env.sample if available."
    exit 1
fi

echo "✅ .env file found"

# Check environment variables
echo "Checking environment variables..."
python check_env.py

if [ $? -ne 0 ]; then
    echo "❌ Environment check failed. Please fix the missing variables."
    exit 1
fi

echo
echo "=== Starting Application ==="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose down

# Start the application
echo "Starting application with Docker Compose..."
docker-compose up --build

echo
echo "Application startup completed!"
echo "You can access the application at: http://localhost:8080"
echo "Health check: http://localhost:8080/health" 