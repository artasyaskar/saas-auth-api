"""
Tests for data export service.
"""
import pytest
import json
from datetime import datetime, timedelta
from app.services.export import DataExportService, ExportFormat


class TestUserDataExport:
    """Tests for user data export functionality."""
    
    def test_export_user_data_json(self, db, test_user):
        """Test exporting user data in JSON format."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON
        )
        
        assert "error" not in result
        assert result["format"] == "json"
        assert "data" in result
        assert "export_metadata" in result["data"]
    
    def test_export_user_data_structure(self, db, test_user):
        """Test that export contains all expected sections."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON
        )
        
        data = result["data"]
        assert "profile" in data
        assert "usage_history" in data
        assert "security_events" in data
        assert "subscriptions" in data
        assert "rate_limits" in data
        assert "audit_logs" in data
        assert "export_metadata" in data
    
    def test_export_user_not_found(self, db):
        """Test exporting data for non-existent user."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=99999,
            format=ExportFormat.JSON
        )
        
        assert "error" in result
        assert result["error"] == "User not found"
    
    def test_export_anonymized_data(self, db, test_user):
        """Test exporting anonymized user data."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON,
            anonymize=True
        )
        
        data = result["data"]
        # Username should be anonymized
        assert data["profile"]["username"].startswith("ANON_")
        # Email should be anonymized
        assert "@example.com" in data["profile"]["email"]
    
    def test_export_to_csv(self, db, test_user):
        """Test exporting user data to CSV format."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.CSV
        )
        
        assert result["format"] == "csv"
        assert "content" in result
        assert "export_timestamp" in result
    
    def test_export_to_zip(self, db, test_user):
        """Test exporting user data to ZIP format."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.ZIP
        )
        
        assert result["format"] == "zip"
        assert "content" in result
        assert "filename" in result
        assert result["filename"].endswith(".zip")


class TestBulkExport:
    """Tests for bulk export functionality."""
    
    def test_export_all_users_json(self, db, test_user):
        """Test exporting all users in JSON format."""
        service = DataExportService(db)
        
        # Create additional users
        from app.db.models import User
        for i in range(3):
            user = User(
                username=f"bulkuser{i}",
                email=f"bulk{i}@test.com",
                hashed_password="hashed",
                role="USER"
            )
            db.add(user)
        db.commit()
        
        result = service.export_all_users(format=ExportFormat.JSON)
        
        assert result["format"] == "json"
        assert result["data"]["export_metadata"]["total_users"] >= 4
        assert len(result["data"]["users"]) >= 4
    
    def test_export_all_users_csv(self, db, test_user):
        """Test exporting all users to CSV."""
        service = DataExportService(db)
        
        result = service.export_all_users(format=ExportFormat.CSV)
        
        assert result["format"] == "csv"
        assert "content" in result
        assert "filename" in result
    
    def test_export_with_filters(self, db, test_user):
        """Test exporting users with filters."""
        service = DataExportService(db)
        
        from app.db.models import User
        admin_user = User(
            username="admin_export",
            email="admin_export@test.com",
            hashed_password="hashed",
            role="ADMIN"
        )
        db.add(admin_user)
        db.commit()
        
        result = service.export_all_users(
            format=ExportFormat.JSON,
            filters={"role": "ADMIN"}
        )
        
        # Should only include admin users
        users = result["data"]["users"]
        assert all(u["role"] == "ADMIN" for u in users)


class TestExportDataSections:
    """Tests for specific export data sections."""
    
    def test_usage_history_export(self, db, test_user):
        """Test usage history export section."""
        # Add some usage logs
        from app.db.models import UsageLog
        for i in range(5):
            log = UsageLog(
                user_id=test_user.id,
                endpoint="/api/test",
                method="GET",
                status_code=200,
                timestamp=datetime.utcnow() - timedelta(hours=i),
                response_time_ms=50.0
            )
            db.add(log)
        db.commit()
        
        service = DataExportService(db)
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON,
            include_analytics=True
        )
        
        usage = result["data"]["usage_history"]
        assert usage["total_requests"] == 5
        assert len(usage["entries"]) == 5
        assert "analytics" in usage
    
    def test_profile_export_structure(self, db, test_user):
        """Test profile export structure."""
        service = DataExportService(db)
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON
        )
        
        profile = result["data"]["profile"]
        assert "id" in profile
        assert "username" in profile
        assert "email" in profile
        assert "role" in profile
        assert "is_active" in profile
        assert "created_at" in profile
    
    def test_security_events_export(self, db, test_user):
        """Test security events export section."""
        service = DataExportService(db)
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON
        )
        
        security = result["data"]["security_events"]
        assert "password_resets" in security
        assert "token_blacklist_events" in security


class TestExportFormatConversion:
    """Tests for export format conversion."""
    
    def test_json_conversion(self, db, test_user):
        """Test JSON format conversion."""
        service = DataExportService(db)
        result = service._to_json({"test": "data"})
        
        assert result["format"] == "json"
        assert result["data"]["test"] == "data"
        assert "export_timestamp" in result
    
    def test_csv_conversion(self, db, test_user):
        """Test CSV format conversion."""
        service = DataExportService(db)
        
        data = {
            "profile": {"id": 1, "username": "test"},
            "usage_history": {"total_requests": 100}
        }
        
        result = service._to_csv(data)
        
        assert result["format"] == "csv"
        assert "content" in result
        assert "export_timestamp" in result
    
    def test_zip_conversion(self, db, test_user):
        """Test ZIP format conversion."""
        service = DataExportService(db)
        
        data = {
            "export_metadata": {"user_id": test_user.id},
            "profile": {"id": test_user.id, "username": test_user.username},
            "usage_history": {
                "entries": [
                    {
                        "id": 1,
                        "endpoint": "/test",
                        "method": "GET",
                        "status_code": 200,
                        "timestamp": datetime.utcnow().isoformat(),
                        "response_time_ms": 50.0
                    }
                ]
            }
        }
        
        result = service._to_zip(data)
        
        assert result["format"] == "zip"
        assert "content" in result
        assert "filename" in result


class TestExportEdgeCases:
    """Tests for export edge cases and error handling."""
    
    def test_export_empty_usage_history(self, db, test_user):
        """Test exporting user with no usage history."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON
        )
        
        assert result["data"]["usage_history"]["total_requests"] == 0
        assert result["data"]["usage_history"]["entries"] == []
    
    def test_export_unsupported_format(self, db, test_user):
        """Test exporting to unsupported format."""
        service = DataExportService(db)
        
        result = service.export_user_data(
            user_id=test_user.id,
            format="xml"  # Unsupported
        )
        
        assert "error" in result
        assert "Unsupported format" in result["error"]
    
    def test_bulk_export_unsupported_format(self, db, test_user):
        """Test bulk export with unsupported format."""
        service = DataExportService(db)
        
        result = service.export_all_users(format="pdf")
        
        assert "error" in result


class TestExportTimestamp:
    """Tests for export timestamps."""
    
    def test_export_timestamp_included(self, db, test_user):
        """Test that export timestamp is included."""
        service = DataExportService(db)
        
        before_export = datetime.utcnow()
        result = service.export_user_data(
            user_id=test_user.id,
            format=ExportFormat.JSON
        )
        after_export = datetime.utcnow()
        
        export_time = datetime.fromisoformat(
            result["data"]["export_metadata"]["export_date"]
        )
        
        assert before_export <= export_time <= after_export
