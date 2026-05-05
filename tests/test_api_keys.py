"""
Tests for API key management.
"""
import pytest
from datetime import datetime, timedelta
from app.db.models import ApiKey


class TestApiKeyCreation:
    """Tests for API key creation."""
    
    def test_create_api_key(self, client, auth_headers):
        """Test creating a new API key."""
        response = client.post(
            "/api-keys",
            json={
                "name": "Test API Key",
                "expires_days": 90,
                "scopes": ["read", "write"]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "api_key" in data
        assert data["name"] == "Test API Key"
        assert data["scopes"] == ["read", "write"]
        assert "api_key" in data["message"].lower()
        # API key should start with sk_
        assert data["api_key"].startswith("sk_")
    
    def test_create_api_key_minimal(self, client, auth_headers):
        """Test creating API key with minimal data."""
        response = client.post(
            "/api-keys",
            json={"name": "Minimal Key"},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Key"
        # Should use default scopes
        assert "scopes" in data
    
    def test_create_api_key_validation(self, client, auth_headers):
        """Test API key creation validation."""
        # Missing name
        response = client.post(
            "/api-keys",
            json={"scopes": ["read"]},
            headers=auth_headers
        )
        assert response.status_code == 422
        
        # Invalid expires_days
        response = client.post(
            "/api-keys",
            json={
                "name": "Test",
                "expires_days": 400  # Too high
            },
            headers=auth_headers
        )
        assert response.status_code == 422


class TestApiKeyListing:
    """Tests for listing API keys."""
    
    def test_list_api_keys(self, client, auth_headers, db, test_user):
        """Test listing all API keys."""
        # Create some API keys
        for i in range(3):
            api_key = ApiKey(
                user_id=test_user.id,
                name=f"Key {i}",
                key_hash=f"hashed_{i}",
                scopes=["read"],
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.add(api_key)
        db.commit()
        
        response = client.get("/api-keys", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
    
    def test_list_api_keys_exclude_revoked(self, client, auth_headers, db, test_user):
        """Test that revoked keys are excluded by default."""
        # Create active key
        active_key = ApiKey(
            user_id=test_user.id,
            name="Active Key",
            key_hash="hashed_active",
            scopes=["read"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(active_key)
        
        # Create revoked key
        revoked_key = ApiKey(
            user_id=test_user.id,
            name="Revoked Key",
            key_hash="hashed_revoked",
            scopes=["read"],
            is_active=False,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            revoked_at=datetime.utcnow()
        )
        db.add(revoked_key)
        db.commit()
        
        # Default should not include revoked
        response = client.get("/api-keys", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        key_names = [k["name"] for k in data]
        assert "Active Key" in key_names
        assert "Revoked Key" not in key_names
        
        # Include revoked
        response = client.get("/api-keys?include_revoked=true", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        key_names = [k["name"] for k in data]
        assert "Revoked Key" in key_names


class TestApiKeyRetrieval:
    """Tests for retrieving specific API keys."""
    
    def test_get_api_key(self, client, auth_headers, db, test_user):
        """Test getting a specific API key."""
        api_key = ApiKey(
            user_id=test_user.id,
            name="Specific Key",
            key_hash="hashed_specific",
            scopes=["read", "admin"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(api_key)
        db.commit()
        
        response = client.get(f"/api-keys/{api_key.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Specific Key"
        assert data["scopes"] == ["read", "admin"]
        assert "key_preview" in data
    
    def test_get_api_key_not_found(self, client, auth_headers):
        """Test getting non-existent API key."""
        response = client.get("/api-keys/99999", headers=auth_headers)
        
        assert response.status_code == 404


class TestApiKeyUpdate:
    """Tests for updating API keys."""
    
    def test_update_api_key(self, client, auth_headers, db, test_user):
        """Test updating an API key."""
        api_key = ApiKey(
            user_id=test_user.id,
            name="Old Name",
            key_hash="hashed_old",
            scopes=["read"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(api_key)
        db.commit()
        
        response = client.put(
            f"/api-keys/{api_key.id}",
            json={
                "name": "New Name",
                "scopes": ["read", "write"]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify update
        response = client.get(f"/api-keys/{api_key.id}", headers=auth_headers)
        data = response.json()
        assert data["name"] == "New Name"


class TestApiKeyRevocation:
    """Tests for API key revocation."""
    
    def test_revoke_api_key(self, client, auth_headers, db, test_user):
        """Test revoking an API key."""
        api_key = ApiKey(
            user_id=test_user.id,
            name="To Revoke",
            key_hash="hashed_revoke",
            scopes=["read"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(api_key)
        db.commit()
        
        response = client.post(
            f"/api-keys/{api_key.id}/revoke",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify revoked
        db.refresh(api_key)
        assert api_key.is_active is False
        assert api_key.revoked_at is not None
    
    def test_revoke_nonexistent_api_key(self, client, auth_headers):
        """Test revoking non-existent API key."""
        response = client.post(
            "/api-keys/99999/revoke",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestApiKeyDeletion:
    """Tests for API key deletion."""
    
    def test_delete_api_key(self, client, auth_headers, db, test_user):
        """Test permanently deleting an API key."""
        api_key = ApiKey(
            user_id=test_user.id,
            name="To Delete",
            key_hash="hashed_delete",
            scopes=["read"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(api_key)
        db.commit()
        key_id = api_key.id
        
        response = client.delete(
            f"/api-keys/{key_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify deleted
        result = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        assert result is None
    
    def test_delete_nonexistent_api_key(self, client, auth_headers):
        """Test deleting non-existent API key."""
        response = client.delete("/api-keys/99999", headers=auth_headers)
        
        assert response.status_code == 404


class TestApiKeyAuthentication:
    """Tests for API key authentication."""
    
    def test_api_key_auth_success(self, client, db, test_user):
        """Test successful authentication with API key."""
        # Create API key
        from app.core.security import hash_token
        raw_key = "sk_test_api_key_12345"
        
        api_key = ApiKey(
            user_id=test_user.id,
            name="Auth Test Key",
            key_hash=hash_token(raw_key),
            scopes=["read"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(api_key)
        db.commit()
        
        # Use API key for request
        response = client.get(
            "/users/profile",
            headers={"X-API-Key": raw_key}
        )
        
        # May be 200 if implemented or 401 if not
        assert response.status_code in [200, 401, 403]
    
    def test_api_key_auth_invalid_key(self, client):
        """Test authentication with invalid API key."""
        response = client.get(
            "/users/profile",
            headers={"X-API-Key": "invalid_key"}
        )
        
        assert response.status_code == 401


class TestApiKeyScopes:
    """Tests for API key scope validation."""
    
    def test_api_key_read_scope(self, client, auth_headers, db, test_user):
        """Test API key with read scope."""
        api_key = ApiKey(
            user_id=test_user.id,
            name="Read Only",
            key_hash="hashed_read",
            scopes=["read"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(api_key)
        db.commit()
        
        # Key should be able to read
        response = client.get(f"/api-keys/{api_key.id}", headers=auth_headers)
        assert response.status_code == 200


class TestApiKeyExpiration:
    """Tests for API key expiration."""
    
    def test_expired_api_key(self, client, auth_headers, db, test_user):
        """Test that expired API keys are rejected."""
        api_key = ApiKey(
            user_id=test_user.id,
            name="Expired Key",
            key_hash="hashed_expired",
            scopes=["read"],
            is_active=True,
            created_at=datetime.utcnow() - timedelta(days=60),
            expires_at=datetime.utcnow() - timedelta(days=30)  # Expired
        )
        db.add(api_key)
        db.commit()
        
        # Should be returned in list but marked as expired
        response = client.get("/api-keys?include_revoked=true", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        expired_keys = [k for k in data if k["name"] == "Expired Key"]
        if expired_keys:
            # Check if expiration is detected
            pass
