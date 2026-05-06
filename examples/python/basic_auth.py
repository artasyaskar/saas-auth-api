"""
Basic Authentication Example

Demonstrates user registration, login, and basic API usage.
"""

import os
from saas_auth import SaaSAuthClient

def main():
    # Initialize client
    client = SaaSAuthClient(
        base_url='https://api.saas-auth.com',
        # or use API key: api_key='your-api-key'
    )
    
    try:
        # Register a new user
        print("Registering new user...")
        user = client.auth.register(
            email='user@example.com',
            password='SecurePassword123!',
            username='testuser',
            first_name='Test',
            last_name='User'
        )
        print(f"User registered: {user['id']}")
        
        # Login with credentials
        print("\nLogging in...")
        tokens = client.auth.login(
            username='user@example.com',
            password='SecurePassword123!'
        )
        print(f"Access token: {tokens['access_token'][:20]}...")
        
        # Get current user info
        print("\nGetting user info...")
        current_user = client.users.me()
        print(f"Current user: {current_user['email']}")
        
        # Update user profile
        print("\nUpdating user profile...")
        updated_user = client.users.update(
            first_name='Updated',
            last_name='Name',
            bio='Software developer'
        )
        print(f"Updated: {updated_user['first_name']} {updated_user['last_name']}")
        
        # Logout
        print("\nLogging out...")
        client.auth.logout()
        print("Logged out successfully")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
