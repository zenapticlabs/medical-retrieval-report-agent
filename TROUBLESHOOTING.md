# Troubleshooting Guide

## Common Issues and Solutions

### 1. MySQL Connection Refused

**Error**: `Can't connect to MySQL server on 'localhost' ([Errno 111] Connection refused)`

**Solutions**:
- Make sure MySQL container is running: `docker-compose ps`
- Check if all required environment variables are set: `python check_env.py`
- Restart the application: `docker-compose down && docker-compose up --build`
- Check MySQL logs: `docker-compose logs mysql`

### 2. Authentication Redirect Loop

**Symptoms**: Login page keeps redirecting to itself

**Solutions**:
- Clear browser cookies and cache
- Check browser console for JavaScript errors
- Verify the application is running on the correct port
- Test authentication with: `python test_auth.py`

### 3. Missing Environment Variables

**Error**: Application fails to start due to missing configuration

**Solutions**:
- Run environment check: `python check_env.py`
- Create or update `.env` file with required variables
- Ensure all required variables are set (see below)

### 4. Docker Issues

**Error**: Docker-related errors

**Solutions**:
- Make sure Docker is running: `docker info`
- Clean up Docker resources: `docker system prune`
- Rebuild containers: `docker-compose build --no-cache`

## Required Environment Variables

Create a `.env` file in the project root with these variables:

```bash
# MySQL Configuration
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_DATABASE=medical_db
MYSQL_USER=medical_user
MYSQL_PASSWORD=your_password

# SharePoint Configuration
SHAREPOINT_TENANT_ID=your_tenant_id
SHAREPOINT_CLIENT_ID=your_client_id
SHAREPOINT_CLIENT_SECRET=your_client_secret
SHAREPOINT_SITE_ID=your_site_id

# Optional Configuration
JWT_SECRET_KEY=your_jwt_secret_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
LAMBDA_FUNCTION_NAME=your_lambda_function
BASE_URL=http://localhost:8080
```

## Quick Start Commands

1. **Check environment**: `python check_env.py`
2. **Start application**: `./start_app.sh`
3. **Test authentication**: `python test_auth.py`
4. **Check health**: `curl http://localhost:8080/health`
5. **View logs**: `docker-compose logs -f app`

## Health Check Endpoints

- **Application Health**: `http://localhost:8080/health`
- **Authentication Test**: `http://localhost:8080/api/test-auth`
- **User Info**: `http://localhost:8080/api/me` (requires authentication)

## Database Issues

If you're having database issues:

1. **Reset database**: `docker-compose down -v && docker-compose up --build`
2. **Check MySQL status**: `docker-compose exec mysql mysqladmin ping`
3. **View MySQL logs**: `docker-compose logs mysql`

## Authentication Issues

If authentication isn't working:

1. **Clear browser data**: Clear cookies and cache
2. **Test with curl**: Use the test script: `python test_auth.py`
3. **Check logs**: `docker-compose logs app`
4. **Verify JWT secret**: Make sure `JWT_SECRET_KEY` is set

## Getting Help

If you're still having issues:

1. Check the application logs: `docker-compose logs app`
2. Check the database logs: `docker-compose logs mysql`
3. Run the environment check: `python check_env.py`
4. Test the health endpoint: `curl http://localhost:8080/health` 