#!/usr/bin/env python3
"""
SharePoint connectivity test script
"""
import requests
import json
import time

BASE_URL = "http://localhost:8080"

def test_sharepoint_connection():
    """Test SharePoint connection"""
    print("=== Testing SharePoint Connection ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/test-sharepoint")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SharePoint test result: {data}")
            return data.get('status') == 'success'
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing SharePoint connection: {e}")
        return False

def refresh_sharepoint_token():
    """Manually refresh SharePoint token"""
    print("\n=== Refreshing SharePoint Token ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/refresh-sharepoint-token")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Token refresh result: {data}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return False

def test_folder_listing():
    """Test folder listing functionality"""
    print("\n=== Testing Folder Listing ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/folders/list", 
                              params={"path": ""},
                              headers={"Accept": "application/json"})
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            folders = response.json()
            print(f"Found {len(folders)} folders")
            for folder in folders[:5]:  # Show first 5 folders
                print(f"  - {folder['name']}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing folder listing: {e}")
        return False

def monitor_sharepoint_health(duration_minutes=5):
    """Monitor SharePoint health for a period of time"""
    print(f"\n=== Monitoring SharePoint Health ({duration_minutes} minutes) ===")
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        current_time = time.strftime("%H:%M:%S")
        
        try:
            response = requests.get(f"{BASE_URL}/api/test-sharepoint")
            if response.status_code == 200:
                data = response.json()
                status = "✅" if data.get('status') == 'success' else "❌"
                print(f"[{current_time}] {status} SharePoint: {data.get('message', 'Unknown')}")
            else:
                print(f"[{current_time}] ❌ SharePoint: HTTP {response.status_code}")
        except Exception as e:
            print(f"[{current_time}] ❌ SharePoint: {str(e)}")
        
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    print("SharePoint Connectivity Test")
    print("=" * 40)
    
    # Test basic connection
    if test_sharepoint_connection():
        print("✅ SharePoint connection successful")
    else:
        print("❌ SharePoint connection failed")
        print("\nTrying to refresh token...")
        if refresh_sharepoint_token():
            print("✅ Token refresh successful")
            if test_sharepoint_connection():
                print("✅ SharePoint connection now working")
            else:
                print("❌ SharePoint still not working after token refresh")
        else:
            print("❌ Token refresh failed")
    
    # Test folder listing
    if test_folder_listing():
        print("✅ Folder listing working")
    else:
        print("❌ Folder listing failed")
    
    # Ask if user wants to monitor
    try:
        monitor = input("\nDo you want to monitor SharePoint health for 5 minutes? (y/n): ")
        if monitor.lower() == 'y':
            monitor_sharepoint_health(5)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user") 