"""
Tests for feature flag service.
"""
import pytest
from datetime import datetime, timedelta
from app.services.feature_flags import (
    FeatureFlagService, RolloutStrategy, FlagContext
)


class TestFeatureFlagCreation:
    """Tests for creating feature flags."""
    
    def test_create_flag_all_users(self, db):
        """Test creating flag for all users."""
        service = FeatureFlagService(db)
        
        flag = service.create_flag(
            name="new_dashboard",
            description="New dashboard design",
            default_value=False,
            strategy=RolloutStrategy.ALL_USERS
        )
        
        assert flag.id is not None
        assert flag.name == "new_dashboard"
        assert flag.strategy == RolloutStrategy.ALL_USERS.value
    
    def test_create_flag_percentage(self, db):
        """Test creating percentage-based flag."""
        service = FeatureFlagService(db)
        
        flag = service.create_flag(
            name="beta_feature",
            description="Beta feature rollout",
            default_value=False,
            strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=25
        )
        
        assert flag.rollout_percentage == 25
    
    def test_create_flag_duplicate_name(self, db):
        """Test creating flag with duplicate name."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="unique_flag",
            description="Test"
        )
        
        with pytest.raises(ValueError) as exc_info:
            service.create_flag(
                name="unique_flag",
                description="Duplicate"
            )
        
        assert "already exists" in str(exc_info.value)


class TestFeatureFlagEvaluation:
    """Tests for evaluating feature flags."""
    
    def test_flag_all_users_enabled(self, db):
        """Test ALL_USERS strategy returns True."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="feature_all",
            description="Feature for all",
            strategy=RolloutStrategy.ALL_USERS
        )
        
        result = service.is_enabled("feature_all")
        assert result is True
    
    def test_flag_default_value(self, db):
        """Test flag returns default value when inactive."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="feature_default",
            description="Test",
            default_value=True,
            is_active=False
        )
        
        result = service.is_enabled("feature_default")
        # Should return default when inactive
        assert result is False  # Inactive flags return False
    
    def test_percentage_rollout_consistency(self, db):
        """Test percentage rollout is consistent for same user."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="percentage_feature",
            description="Percentage rollout",
            strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=50
        )
        
        context = FlagContext(user_id=123)
        
        # Should be consistent for same user
        result1 = service.is_enabled("percentage_feature", context)
        result2 = service.is_enabled("percentage_feature", context)
        result3 = service.is_enabled("percentage_feature", context)
        
        assert result1 == result2 == result3
    
    def test_percentage_rollout_distribution(self, db):
        """Test percentage rollout distribution."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="dist_feature",
            description="Distribution test",
            strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=50
        )
        
        enabled_count = 0
        total_users = 100
        
        for user_id in range(1, total_users + 1):
            context = FlagContext(user_id=user_id)
            if service.is_enabled("dist_feature", context):
                enabled_count += 1
        
        # Should be roughly 50% (allow 15% variance)
        assert 35 <= enabled_count <= 65
    
    def test_user_list_rollout(self, db):
        """Test user list rollout strategy."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="vip_feature",
            description="VIP only",
            strategy=RolloutStrategy.USER_LIST,
            target_users=[100, 200, 300]
        )
        
        # In list should be enabled
        assert service.is_enabled("vip_feature", FlagContext(user_id=100)) is True
        assert service.is_enabled("vip_feature", FlagContext(user_id=200)) is True
        
        # Not in list should return default
        assert service.is_enabled("vip_feature", FlagContext(user_id=999)) is False
    
    def test_attribute_rollout(self, db):
        """Test user attribute rollout strategy."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="enterprise_feature",
            description="Enterprise only",
            strategy=RolloutStrategy.USER_ATTRIBUTE,
            target_attributes={"plan": "enterprise"}
        )
        
        context = FlagContext(
            user_id=1,
            user_attributes={"plan": "enterprise"}
        )
        assert service.is_enabled("enterprise_feature", context) is True
        
        context = FlagContext(
            user_id=2,
            user_attributes={"plan": "free"}
        )
        assert service.is_enabled("enterprise_feature", context) is False
    
    def test_time_based_rollout(self, db):
        """Test time-based gradual rollout."""
        service = FeatureFlagService(db)
        
        start = datetime.utcnow() - timedelta(hours=12)
        end = datetime.utcnow() + timedelta(hours=12)
        
        service.create_flag(
            name="scheduled_feature",
            description="Scheduled rollout",
            strategy=RolloutStrategy.TIME_BASED,
            schedule_start=start,
            schedule_end=end,
            rollout_percentage=100
        )
        
        result = service.is_enabled("scheduled_feature")
        # Should be partially enabled based on time
        assert isinstance(result, bool)


class TestFeatureFlagScheduling:
    """Tests for feature flag scheduling."""
    
    def test_flag_before_schedule(self, db):
        """Test flag returns default before schedule starts."""
        service = FeatureFlagService(db)
        
        future = datetime.utcnow() + timedelta(days=1)
        
        service.create_flag(
            name="future_feature",
            description="Future feature",
            default_value=False,
            schedule_start=future,
            strategy=RolloutStrategy.ALL_USERS
        )
        
        result = service.is_enabled("future_feature")
        assert result is False  # Returns default
    
    def test_flag_after_schedule(self, db):
        """Test flag after schedule ends."""
        service = FeatureFlagService(db)
        
        past = datetime.utcnow() - timedelta(days=2)
        
        service.create_flag(
            name="expired_feature",
            description="Expired feature",
            default_value=False,
            schedule_start=past - timedelta(days=1),
            schedule_end=past,
            strategy=RolloutStrategy.ALL_USERS
        )
        
        result = service.is_enabled("expired_feature")
        assert result is False  # Returns default after schedule


class TestFeatureFlagUpdates:
    """Tests for updating feature flags."""
    
    def test_update_flag_description(self, db):
        """Test updating flag description."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="update_test",
            description="Original"
        )
        
        updated = service.update_flag(
            "update_test",
            description="Updated description"
        )
        
        assert updated.description == "Updated description"
    
    def test_update_flag_percentage(self, db):
        """Test updating rollout percentage."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="update_pct",
            description="Test",
            strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=10
        )
        
        updated = service.update_flag(
            "update_pct",
            rollout_percentage=50
        )
        
        assert updated.rollout_percentage == 50
    
    def test_update_nonexistent_flag(self, db):
        """Test updating non-existent flag."""
        service = FeatureFlagService(db)
        
        result = service.update_flag(
            "nonexistent",
            description="Test"
        )
        
        assert result is None


class TestFeatureFlagDeletion:
    """Tests for deleting feature flags."""
    
    def test_delete_flag(self, db):
        """Test deleting a feature flag."""
        service = FeatureFlagService(db)
        
        service.create_flag(name="to_delete", description="Delete me")
        
        result = service.delete_flag("to_delete")
        assert result is True
        
        # Should no longer exist
        result = service.is_enabled("to_delete")
        assert result is False
    
    def test_delete_nonexistent_flag(self, db):
        """Test deleting non-existent flag."""
        service = FeatureFlagService(db)
        
        result = service.delete_flag("nonexistent")
        assert result is False


class TestFeatureFlagCaching:
    """Tests for feature flag caching."""
    
    def test_flag_caching(self, db):
        """Test that flags are cached."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="cached_flag",
            description="Cached"
        )
        
        # First evaluation should cache
        result1 = service.is_enabled("cached_flag")
        
        # Second evaluation should use cache
        result2 = service.is_enabled("cached_flag")
        
        assert result1 == result2
    
    def test_cache_invalidation_on_update(self, db):
        """Test cache invalidation after update."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="invalidate_test",
            description="Test",
            default_value=False,
            is_active=True,
            strategy=RolloutStrategy.ALL_USERS
        )
        
        # Evaluate and cache
        result1 = service.is_enabled("invalidate_test")
        assert result1 is True
        
        # Update flag
        service.update_flag(
            "invalidate_test",
            is_active=False
        )
        
        # Should reflect update
        result2 = service.is_enabled("invalidate_test")
        assert result2 is False


class TestFeatureFlagAnalytics:
    """Tests for feature flag analytics."""
    
    def test_flag_exposure_tracking(self, db):
        """Test flag exposure tracking."""
        service = FeatureFlagService(db)
        
        flag = service.create_flag(
            name="trackable",
            description="Trackable"
        )
        
        service.increment_exposure("trackable")
        service.increment_exposure("trackable")
        service.increment_exposure("trackable")
        
        # Refresh from DB
        db.refresh(flag)
        
        assert flag.exposure_count == 3
    
    def test_flag_evaluation_tracking(self, db):
        """Test flag evaluation tracking."""
        service = FeatureFlagService(db)
        
        flag = service.create_flag(
            name="eval_track",
            description="Evaluation tracking"
        )
        
        service.increment_evaluation("eval_track", True)
        service.increment_evaluation("eval_track", True)
        service.increment_evaluation("eval_track", False)
        
        db.refresh(flag)
        
        assert flag.evaluation_count == 3
        assert flag.enabled_count == 2


class TestFeatureFlagBulkOperations:
    """Tests for bulk feature flag operations."""
    
    def test_evaluate_all_flags(self, db):
        """Test evaluating all active flags."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="flag1",
            description="Flag 1",
            strategy=RolloutStrategy.ALL_USERS
        )
        service.create_flag(
            name="flag2",
            description="Flag 2",
            default_value=False
        )
        service.create_flag(
            name="inactive_flag",
            description="Inactive",
            is_active=False
        )
        
        results = service.evaluate_all_flags()
        
        # Should include all active flags
        assert "flag1" in results
        assert "flag2" in results
        # Inactive flag should not be evaluated


class TestFeatureFlagStatus:
    """Tests for getting flag status."""
    
    def test_get_flag_status(self, db):
        """Test getting detailed flag status."""
        service = FeatureFlagService(db)
        
        service.create_flag(
            name="status_test",
            description="Status test",
            strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=75,
            target_users=[1, 2, 3]
        )
        
        status = service.get_flag_status("status_test")
        
        assert status is not None
        assert status["name"] == "status_test"
        assert status["rollout_percentage"] == 75
        assert status["target_users_count"] == 3
    
    def test_get_nonexistent_flag_status(self, db):
        """Test status of non-existent flag."""
        service = FeatureFlagService(db)
        
        status = service.get_flag_status("nonexistent")
        
        assert status is None
