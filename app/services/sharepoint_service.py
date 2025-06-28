import os
import requests
import msal
import time
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging()

class SharePointService:
    def __init__(self):
        self.tenant_id = settings.SHAREPOINT_TENANT_ID
        self.client_id = settings.SHAREPOINT_CLIENT_ID
        self.client_secret = settings.SHAREPOINT_CLIENT_SECRET
        self.site_id = settings.SHAREPOINT_SITE_ID
        self.token = None
        self.token_expires_at = 0
        self.msal_app = None

    def _get_msal_app(self):
        """Get or create MSAL application"""
        if not self.msal_app:
            self.msal_app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}"
            )
        return self.msal_app

    def _get_token(self) -> str:
        """Get Microsoft Graph API token with automatic refresh"""
        current_time = time.time()
        
        # Check if token is still valid (with 5 minute buffer)
        if self.token and current_time < (self.token_expires_at - 300):
            return self.token

        logger.info("Acquiring new SharePoint token...")
        
        app = self._get_msal_app()
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" not in result:
            logger.error(f"Failed to acquire token: {result}")
            raise Exception(f"Failed to get token: {result}")
        
        self.token = result["access_token"]
        
        # Calculate expiration time (tokens typically expire in 1 hour)
        expires_in = result.get("expires_in", 3600)  # Default to 1 hour
        self.token_expires_at = current_time + expires_in
        
        logger.info(f"Token acquired successfully, expires in {expires_in} seconds")
        return self.token

    def _make_request_with_retry(self, url: str, headers: Dict[str, str], max_retries: int = 2) -> requests.Response:
        """Make HTTP request with automatic token refresh on 401 errors"""
        for attempt in range(max_retries):
            try:
                # Get fresh token for each attempt
                headers["Authorization"] = f"Bearer {self._get_token()}"
                
                logger.debug(f"Making request to: {url} (attempt {attempt + 1})")
                response = requests.get(url, headers=headers)
                
                if response.status_code == 401 and attempt < max_retries - 1:
                    logger.warning("Token expired, refreshing and retrying...")
                    # Clear token to force refresh
                    self.token = None
                    self.token_expires_at = 0
                    continue
                
                return response
                
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)  # Brief delay before retry
        
        return None  # Should never reach here

    def list_folder_contents(self, folder_path: str = "") -> List[Dict[str, Any]]:
        """List contents of a SharePoint folder"""
        try:
            headers = {
                "Accept": "application/json"
            }
            
            # Construct URL based on whether we're at root or in a subfolder
            if not folder_path:
                url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root/children"
            else:
                url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{folder_path}:/children"
            
            logger.info(f"Fetching folder contents from: {url}")
            response = self._make_request_with_retry(url, headers)
            
            if response.status_code == 404:
                logger.error(f"Folder not found: {folder_path}")
                raise Exception(f"Folder not found: {folder_path}")
            elif response.status_code == 401:
                logger.error("Authentication failed after retries. Please check your SharePoint credentials.")
                raise Exception("Authentication failed. Please check your SharePoint credentials.")
            elif response.status_code != 200:
                logger.error(f"Error from SharePoint API: {response.text}")
                raise Exception(f"Error from SharePoint API: {response.text}")
            
            items = response.json().get("value", [])
            
            # Log the items found
            logger.info(f"Found {len(items)} items in folder: {folder_path}")
            for item in items:
                logger.debug(f"Item: {item.get('name')} (type: {item.get('folder') is not None and 'folder' or 'file'})")
            
            return items
        except Exception as e:
            logger.error(f"Error listing folder contents: {str(e)}")
            raise

    def get_folder_metadata(self, folder_path: str) -> Dict[str, Any]:
        """Get metadata for a specific folder"""
        try:
            headers = {
                "Accept": "application/json"
            }
            
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{folder_path}"
            logger.info(f"Fetching folder metadata from: {url}")
            
            response = self._make_request_with_retry(url, headers)
            
            if response.status_code == 404:
                logger.error(f"Folder not found: {folder_path}")
                raise Exception(f"Folder not found: {folder_path}")
            elif response.status_code == 401:
                logger.error("Authentication failed after retries. Please check your SharePoint credentials.")
                raise Exception("Authentication failed. Please check your SharePoint credentials.")
            elif response.status_code != 200:
                logger.error(f"Error from SharePoint API: {response.text}")
                raise Exception(f"Error from SharePoint API: {response.text}")
            
            return response.json()
        except Exception as e:
            logger.error(f"Error getting folder metadata: {str(e)}")
            raise

    def refresh_token_if_needed(self):
        """Proactively refresh token if it's close to expiring"""
        current_time = time.time()
        
        # Refresh if token expires in less than 10 minutes
        if not self.token or current_time > (self.token_expires_at - 600):
            logger.info("Proactively refreshing SharePoint token...")
            self.token = None
            self.token_expires_at = 0
            self._get_token() 