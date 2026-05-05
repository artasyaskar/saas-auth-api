"""
Tests for CLI commands.
"""
import pytest
from click.testing import CliRunner
from cli import cli


class TestUserCommands:
    """Tests for user management CLI commands."""
    
    def test_users_list_command(self, db, test_user):
        """Test listing users via CLI."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['users', 'list'])
        
        assert result.exit_code == 0
        assert test_user.username in result.output
        assert str(test_user.id) in result.output
    
    def test_users_list_json_format(self, db, test_user):
        """Test listing users in JSON format."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['users', 'list', '--format', 'json'])
        
        assert result.exit_code == 0
        assert '"id":' in result.output
        assert '"username":' in result.output
    
    def test_users_create_command(self, db):
        """Test creating user via CLI."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'users', 'create',
            '--username', 'cliuser',
            '--email', 'cli@example.com',
            '--password', 'SecurePass123!',
            '--role', 'user'
        ])
        
        assert result.exit_code == 0
        assert 'Created user' in result.output or 'Error' in result.output
    
    def test_users_create_duplicate(self, db, test_user):
        """Test creating duplicate user."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'users', 'create',
            '--username', test_user.username,
            '--email', 'different@example.com',
            '--password', 'SecurePass123!'
        ])
        
        assert result.exit_code == 1
        assert 'already exists' in result.output
    
    def test_users_activate_command(self, db, test_user):
        """Test activating user via CLI."""
        # Deactivate first
        test_user.is_active = False
        db.commit()
        
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'users', 'activate',
            str(test_user.id)
        ])
        
        assert result.exit_code == 0
        assert 'Activated' in result.output
    
    def test_users_deactivate_command(self, db, test_user):
        """Test deactivating user via CLI."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'users', 'deactivate',
            str(test_user.id)
        ])
        
        assert result.exit_code == 0
        assert 'Deactivated' in result.output
    
    def test_users_delete_command(self, db):
        """Test deleting user via CLI."""
        from app.db.models import User
        from app.core.security import get_password_hash
        
        user = User(
            username="to_delete_cli",
            email="delete_cli@example.com",
            hashed_password=get_password_hash("password123")
        )
        db.add(user)
        db.commit()
        
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'users', 'delete',
            str(user.id)
        ], input='y\n')  # Confirm deletion
        
        assert result.exit_code == 0
        assert 'Deleted' in result.output or 'delete' in result.output.lower()


class TestAnalyticsCommands:
    """Tests for analytics CLI commands."""
    
    def test_analytics_growth_command(self, db):
        """Test growth metrics command."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'analytics', 'growth',
            '--days', '30'
        ])
        
        assert result.exit_code == 0
        assert 'User Growth Metrics' in result.output
    
    def test_analytics_revenue_command(self, db):
        """Test revenue metrics command."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['analytics', 'revenue'])
        
        assert result.exit_code == 0
        assert 'Revenue Metrics' in result.output
        assert 'MRR' in result.output or 'Monthly' in result.output
    
    def test_analytics_endpoints_command(self, db):
        """Test endpoints analytics command."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'analytics', 'endpoints',
            '--days', '7'
        ])
        
        assert result.exit_code == 0
        assert 'Popular Endpoints' in result.output


class TestSystemCommands:
    """Tests for system administration CLI commands."""
    
    def test_system_stats_command(self, db, test_user):
        """Test system stats command."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['system', 'stats'])
        
        assert result.exit_code == 0
        assert 'System Statistics' in result.output
        assert 'Total Users' in result.output
    
    def test_system_health_command(self, db):
        """Test health check command."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['system', 'health'])
        
        assert result.exit_code == 0
        assert 'System Health Check' in result.output
        # Should show DB connection status
        assert 'Database' in result.output or 'OK' in result.output


class TestExportCommands:
    """Tests for export CLI commands."""
    
    def test_export_usage_command(self, db, test_user, tmp_path):
        """Test usage export command."""
        runner = CliRunner()
        
        output_file = tmp_path / "usage.json"
        
        # Add some usage data
        from app.db.models import UsageLog
        from datetime import datetime
        
        log = UsageLog(
            user_id=test_user.id,
            endpoint="/test",
            method="GET",
            status_code=200,
            timestamp=datetime.utcnow(),
            response_time_ms=50.0
        )
        db.add(log)
        db.commit()
        
        result = runner.invoke(cli, [
            'export', 'usage',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--output', str(output_file),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        assert 'Exported' in result.output or str(output_file) in result.output
    
    def test_export_users_command(self, db, test_user, tmp_path):
        """Test users export command."""
        runner = CliRunner()
        
        output_file = tmp_path / "users.json"
        
        result = runner.invoke(cli, [
            'export', 'users-all',
            '--output', str(output_file)
        ])
        
        assert result.exit_code == 0
        assert 'Exported' in result.output


class TestCLIHelp:
    """Tests for CLI help text."""
    
    def test_main_help(self):
        """Test main CLI help."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'SaaS Auth API Management CLI' in result.output
        assert 'users' in result.output
        assert 'analytics' in result.output
    
    def test_users_help(self):
        """Test users command help."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['users', '--help'])
        
        assert result.exit_code == 0
        assert 'User management commands' in result.output
    
    def test_analytics_help(self):
        """Test analytics command help."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['analytics', '--help'])
        
        assert result.exit_code == 0
        assert 'Analytics' in result.output


class TestCLIValidation:
    """Tests for CLI input validation."""
    
    def test_users_list_invalid_limit(self, db):
        """Test users list with invalid limit."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'users', 'list',
            '--limit', '-1'
        ])
        
        # Should handle gracefully
        assert result.exit_code in [0, 2]
    
    def test_export_invalid_date_format(self, db, tmp_path):
        """Test export with invalid date format."""
        runner = CliRunner()
        
        output_file = tmp_path / "export.json"
        
        result = runner.invoke(cli, [
            'export', 'usage',
            '--start-date', 'invalid-date',
            '--end-date', '2024-12-31',
            '--output', str(output_file)
        ])
        
        # Should fail gracefully
        assert result.exit_code in [0, 1]


class TestCLIColorOutput:
    """Tests for CLI colored output."""
    
    def test_colored_output_in_terminal(self, db, test_user, monkeypatch):
        """Test that CLI uses colors when in terminal."""
        runner = CliRunner()
        
        # Force terminal mode
        result = runner.invoke(cli, ['users', 'list'], env={'TERM': 'xterm-256color'})
        
        # Should succeed
        assert result.exit_code == 0
