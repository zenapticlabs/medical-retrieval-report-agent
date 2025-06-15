import os
import requests
import msal
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

    def _get_token(self) -> str:
        """Get Microsoft Graph API token"""
        if self.token:
            return self.token

        app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )
        
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        self.token = result.get("access_token")
        
        if not self.token:
            raise Exception(f"Failed to get token: {result}")
            
        return self.token

    def list_folder_contents(self, folder_path: str = "") -> List[Dict[str, Any]]:
        """List contents of a SharePoint folder"""
        try:
            headers = {
                "Authorization": f"Bearer {self._get_token()}",
                "Accept": "application/json"
            }
            
            # Construct URL based on whether we're at root or in a subfolder
            if not folder_path:
                url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root/children"
            else:
                url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{folder_path}:/children"
            
            logger.info(f"Fetching folder contents from: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 404:
                logger.error(f"Folder not found: {folder_path}")
                raise Exception(f"Folder not found: {folder_path}")
            elif response.status_code == 401:
                logger.error("Authentication failed. Please check your SharePoint credentials.")
                raise Exception("Authentication failed. Please check your SharePoint credentials.")
            elif response.status_code != 200:
                logger.error(f"Error from SharePoint API: {response.text}")
                raise Exception(f"Error from SharePoint API: {response.text}")
            
            response.raise_for_status()
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
                "Authorization": f"Bearer {self._get_token()}",
                "Accept": "application/json"
            }
            
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{folder_path}"
            logger.info(f"Fetching folder metadata from: {url}")
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 404:
                logger.error(f"Folder not found: {folder_path}")
                raise Exception(f"Folder not found: {folder_path}")
            elif response.status_code == 401:
                logger.error("Authentication failed. Please check your SharePoint credentials.")
                raise Exception("Authentication failed. Please check your SharePoint credentials.")
            elif response.status_code != 200:
                logger.error(f"Error from SharePoint API: {response.text}")
                raise Exception(f"Error from SharePoint API: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting folder metadata: {str(e)}")
            raise 