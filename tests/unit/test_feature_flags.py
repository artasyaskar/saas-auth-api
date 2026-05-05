"""
Unit tests for Feature Flag Service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.feature_flags import (
    FeatureFlagService,
    RolloutStrategy,
    FlagContext
)
from app.db.models import FeatureFlag


@pytest.fixture
def db_session():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def feature_flag_service(db_session):
    """Feature flag service fixture"""
    return FeatureFlagService(db_session)


@pytest.fixture
def sample_flag():
    """Sample feature flag"""
    flag = FeatureFlag(
        id=1,
        name="test_feature",
        description="Test feature flag",
        default_value=False,
        strategy="percentage",
        rollout_percentage=50,
        target_users=[1, 2, 3],
        target_attributes={"plan": "pro"},
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    return flag


class TestFeatureFlagService:
    """Test suite for FeatureFlagService"""
    
    def test_create_flag(self, feature_flag_service, db_session):
        """Test creating a new feature flag"""
        db_session.add = MagicMock()
        db_session.commit = MagicMock()
        db_session.refresh = MagicMock()
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        flag = feature_flag_service.create_flag(
            name="new_feature",
            description="New feature",
            default_value=True,
            strategy=RolloutStrategy.ALL_USERS
        )
        
        assert flag.name == "new_feature"
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    def test_create_flag_duplicate(self, feature_flag_service, db_session, sample_flag):
        """Test creating duplicate flag raises error"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        with pytest.raises(ValueError, match="already exists"):
            feature_flag_service.create_flag(
                name="test_feature",
                description="Test"
            )
    
    def test_is_enabled_all_users(self, feature_flag_service, db_session, sample_flag):
        """Test flag enabled for all users"""
        sample_flag.strategy = "all_users"
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        result = feature_flag_service.is_enabled("test_feature")
        assert result is True
    
    def test_is_enabled_percentage_rollout(self, feature_flag_service, db_session, sample_flag):
        """Test percentage-based rollout"""
        sample_flag.strategy = "percentage"
        sample_flag.rollout_percentage = 50
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        context = FlagContext(user_id=123)
        result = feature_flag_service.is_enabled("test_feature", context)
        assert isinstance(result, bool)
    
    def test_is_enabled_user_list(self, feature_flag_service, db_session, sample_flag):
        """Test user list-based rollout"""
        sample_flag.strategy = "user_list"
        sample_flag.target_users = [1, 2, 3]
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        context = FlagContext(user_id=2)
        result = feature_flag_service.is_enabled("test_feature", context)
        assert result is True
        
        context = FlagContext(user_id=99)
        result = feature_flag_service.is_enabled("test_feature", context)
        assert result is False
    
    def test_is_enabled_attribute_based(self, feature_flag_service, db_session, sample_flag):
        """Test attribute-based rollout"""
        sample_flag.strategy = "user_attribute"
        sample_flag.target_attributes = {"plan": "pro"}
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        context = FlagContext(user_id=1, user_attributes={"plan": "pro"})
        result = feature_flag_service.is_enabled("test_feature", context)
        assert result is True
        
        context = FlagContext(user_id=1, user_attributes={"plan": "free"})
        result = feature_flag_service.is_enabled("test_feature", context)
        assert result is False
    
    def test_is_flag_not_active(self, feature_flag_service, db_session, sample_flag):
        """Test inactive flag returns False"""
        sample_flag.is_active = False
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        result = feature_flag_service.is_enabled("test_feature")
        assert result is False
    
    def test_update_flag(self, feature_flag_service, db_session, sample_flag):
        """Test updating a flag"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        db_session.commit = MagicMock()
        db_session.refresh = MagicMock()
        
        updated = feature_flag_service.update_flag("test_feature", is_active=False)
        assert updated.is_active is False
        db_session.commit.assert_called_once()
    
    def test_delete_flag(self, feature_flag_service, db_session, sample_flag):
        """Test deleting a flag"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        db_session.delete = MagicMock()
        db_session.commit = MagicMock()
        
        result = feature_flag_service.delete_flag("test_feature")
        assert result is True
        db_session.delete.assert_called_once()
    
    def test_get_all_flags(self, feature_flag_service, db_session):
        """Test getting all flags"""
        db_session.query = MagicMock()
        db_session.query.return_value.all.return_value = []
        
        flags = feature_flag_service.get_all_flags()
        assert isinstance(flags, list)
    
    def test_get_all_flags_active_only(self, feature_flag_service, db_session):
        """Test getting only active flags"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.all.return_value = []
        
        flags = feature_flag_service.get_all_flags(active_only=True)
        assert isinstance(flags, list)
    
    def test_add_flag_dependency(self, feature_flag_service):
        """Test adding flag dependency"""
        result = feature_flag_service.add_flag_dependency("feature_a", "feature_b")
        assert result is True
        assert "feature_b" in feature_flag_service._flag_dependencies["feature_a"]
    
    def test_check_dependencies(self, feature_flag_service):
        """Test checking flag dependencies"""
        feature_flag_service._flag_dependencies["feature_a"] = ["feature_b"]
        
        # Mock is_enabled to return True
        feature_flag_service.is_enabled = MagicMock(return_value=True)
        
        result = feature_flag_service.check_dependencies("feature_a")
        assert result is True
    
    def test_rollback_flag(self, feature_flag_service, db_session, sample_flag):
        """Test rolling back a flag"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        db_session.commit = MagicMock()
        
        result = feature_flag_service.rollback_flag("test_feature")
        assert result is True
        assert sample_flag.is_active is False
        assert "test_feature" in feature_flag_service._flag_history
    
    def test_set_environment_override(self, feature_flag_service, db_session, sample_flag):
        """Test setting environment override"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        db_session.commit = MagicMock()
        
        result = feature_flag_service.set_environment_override("test_feature", "staging", True)
        assert result is True
        assert sample_flag.environment_overrides["staging"] is True
    
    def test_create_variant(self, feature_flag_service, db_session, sample_flag):
        """Test creating A/B test variant"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        db_session.commit = MagicMock()
        
        result = feature_flag_service.create_variant("test_feature", "variant_a", 50)
        assert result is True
        assert "variant_a" in sample_flag.variants
    
    def test_get_variant(self, feature_flag_service, db_session, sample_flag):
        """Test getting variant for user"""
        sample_flag.variants = {"variant_a": {"percentage": 50, "config": {}}}
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        context = FlagContext(user_id=123)
        variant = feature_flag_service.get_variant("test_feature", context)
        assert variant in ["variant_a", None]
    
    def test_get_flag_analytics(self, feature_flag_service, db_session, sample_flag):
        """Test getting flag analytics"""
        sample_flag.evaluation_count = 1000
        sample_flag.enabled_count = 500
        sample_flag.exposure_count = 300
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        
        analytics = feature_flag_service.get_flag_analytics("test_feature", datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        assert analytics["flag_name"] == "test_feature"
        assert analytics["evaluation_count"] == 1000
        assert analytics["enable_rate"] == 50.0
    
    def test_bulk_update_flags(self, feature_flag_service, db_session, sample_flag):
        """Test bulk updating flags"""
        db_session.query = MagicMock()
        db_session.query.return_value.filter.return_value.first.return_value = sample_flag
        db_session.commit = MagicMock()
        
        updates = {
            "test_feature": {"is_active": False},
            "other_feature": {"is_active": True}
        }
        
        results = feature_flag_service.bulk_update_flags(updates)
        assert "test_feature" in results
        assert "other_feature" in results
    
    def test_export_flags(self, feature_flag_service, db_session):
        """Test exporting flags to JSON"""
        db_session.query = MagicMock()
        db_session.query.return_value.all.return_value = []
        
        exported = feature_flag_service.export_flags("json")
        assert isinstance(exported, str)
    
    def test_import_flags(self, feature_flag_service, db_session):
        """Test importing flags from JSON"""
        import json
        data = json.dumps([
            {
                "name": "imported_feature",
                "description": "Imported",
                "default_value": True,
                "strategy": "all_users",
                "rollout_percentage": 0,
                "target_users": [],
                "target_attributes": {},
                "schedule_start": None,
                "schedule_end": None
            }
        ])
        
        feature_flag_service.create_flag = MagicMock()
        count = feature_flag_service.import_flags(data, "json")
        assert count == 1
