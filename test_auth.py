#!/usr/bin/env python3
"""
Simple authentication test script for debugging EC2 authentication issues
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Change this to your EC2 URL if needed

def test_login():
    """Test login functionality"""
    print("=== Testing Login ===")
    
    # Test data
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/token",
            data=login_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        print(f"Login response status: {response.status_code}")
        print(f"Login response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Login successful: {data}")
            
            # Test the /api/me endpoint
            cookies = response.cookies
            print(f"Cookies received: {dict(cookies)}")
            
            me_response = requests.get(
                f"{BASE_URL}/api/me",
                cookies=cookies
            )
            
            print(f"/api/me response status: {me_response.status_code}")
            if me_response.status_code == 200:
                me_data = me_response.json()
                print(f"User info: {me_data}")
            else:
                print(f"/api/me error: {me_response.text}")
                
        else:
            print(f"Login failed: {response.text}")
            
    except Exception as e:
        print(f"Error during login test: {e}")

def test_auth_endpoint():
    """Test the test-auth endpoint"""
    print("\n=== Testing /api/test-auth ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/test-auth")
        print(f"Test auth response status: {response.status_code}")
        print(f"Test auth response: {response.text}")
    except Exception as e:
        print(f"Error testing auth endpoint: {e}")

def test_me_endpoint():
    """Test the /api/me endpoint without cookies"""
    print("\n=== Testing /api/me without cookies ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/me")
        print(f"/api/me response status: {response.status_code}")
        print(f"/api/me response: {response.text}")
    except Exception as e:
        print(f"Error testing /api/me: {e}")

if __name__ == "__main__":
    print("Authentication Debug Test Script")
    print("=" * 40)
    
    test_me_endpoint()
    test_auth_endpoint()
    test_login() 