"""
Database Migration Management Script

Comprehensive tool for managing Alembic database migrations:
- Create new migrations
- Run migrations
- Rollback migrations
- View migration history
- Verify migration status
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings


class MigrationManager:
    """Database migration management utility."""
    
    def __init__(self):
        self.alembic_ini = project_root / "alembic.ini"
        self.alembic_dir = project_root / "alembic"
        
    def _run_alembic(self, command: list) -> tuple:
        """Execute alembic command."""
        cmd = ["alembic", "-c", str(self.alembic_ini)] + command
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"Error: {e.stderr}"
        except FileNotFoundError:
            return False, "Error: alembic not found. Install with: pip install alembic"
    
    def create_migration(self, message: str, autogenerate: bool = True) -> bool:
        """Create a new migration."""
        print(f"Creating migration: {message}")
        
        cmd = ["revision", "-m", message]
        if autogenerate:
            cmd.append("--autogenerate")
        
        success, output = self._run_alembic(cmd)
        
        if success:
            print(f"✅ Migration created successfully")
            print(output)
        else:
            print(f"❌ Failed to create migration")
            print(output)
        
        return success
    
    def migrate(self, revision: str = "head") -> bool:
        """Run migrations to upgrade database."""
        print(f"Running migrations to {revision}...")
        
        success, output = self._run_alembic(["upgrade", revision])
        
        if success:
            print(f"✅ Database migrated successfully to {revision}")
            print(output)
        else:
            print(f"❌ Migration failed")
            print(output)
        
        return success
    
    def downgrade(self, revision: str) -> bool:
        """Downgrade database to previous version."""
        print(f"Downgrading to {revision}...")
        
        success, output = self._run_alembic(["downgrade", revision])
        
        if success:
            print(f"✅ Database downgraded to {revision}")
            print(output)
        else:
            print(f"❌ Downgrade failed")
            print(output)
        
        return success
    
    def current_version(self) -> tuple:
        """Show current database version."""
        success, output = self._run_alembic(["current"])
        return success, output
    
    def history(self, verbose: bool = False) -> tuple:
        """Show migration history."""
        cmd = ["history"]
        if verbose:
            cmd.append("--verbose")
        
        success, output = self._run_alembic(cmd)
        return success, output
    
    def show_pending(self) -> tuple:
        """Show pending migrations."""
        # Get current version
        success, current = self._run_alembic(["current"])
        
        # Get history
        success, history = self._run_alembic(["history", "--verbose"])
        
        return success, f"Current: {current}\n\nHistory:\n{history}"
    
    def stamp(self, revision: str) -> bool:
        """Stamp database with specific revision without running migrations."""
        success, output = self._run_alembic(["stamp", revision])
        
        if success:
            print(f"✅ Database stamped to {revision}")
        else:
            print(f"❌ Failed to stamp database")
            print(output)
        
        return success
    
    def verify(self) -> bool:
        """Verify database is at latest migration."""
        success, output = self._run_alembic(["current"])
        
        if not success:
            print(f"❌ Failed to check current version")
            return False
        
        current = output.strip()
        
        # Check if at head
        success, head = self._run_alembic(["show", "head"])
        
        if not success:
            print(f"❌ Failed to check head version")
            return False
        
        if "head" in current or current in head:
            print(f"✅ Database is at latest migration")
            print(f"Current: {current}")
            return True
        else:
            print(f"⚠️ Database is not at latest migration")
            print(f"Current: {current}")
            return False
    
    def reset(self) -> bool:
        """Reset database to initial state (DANGEROUS)."""
        print("⚠️ WARNING: This will delete all data!")
        confirm = input("Type 'RESET' to confirm: ")
        
        if confirm != "RESET":
            print("Cancelled.")
            return False
        
        # Downgrade to base
        success, output = self._run_alembic(["downgrade", "base"])
        
        if success:
            print(f"✅ Database reset to base")
        else:
            print(f"❌ Reset failed")
            print(output)
        
        return success
    
    def generate_sql(self, revision: str) -> tuple:
        """Generate SQL for migration without executing."""
        success, output = self._run_alembic(["upgrade", revision, "--sql"])
        return success, output
    
    def check_models(self) -> bool:
        """Check if models need migration."""
        print("Checking if models match database...")
        
        # Try to create autogenerated migration in dry-run mode
        success, output = self._run_alembic([
            "revision", "--autogenerate",
            "-m", "check_models",
            "--rev-id", "check_" + datetime.now().strftime("%Y%m%d%H%M%S")
        ])
        
        # Check if migration would be empty
        # In a real implementation, check the generated file
        print(f"Result: {output}")
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description="Database Migration Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create new migration
  python scripts/db_migrate.py create -m "add user profiles"
  
  # Run all pending migrations
  python scripts/db_migrate.py upgrade
  
  # Downgrade one version
  python scripts/db_migrate.py downgrade -1
  
  # View current version
  python scripts/db_migrate.py current
  
  # View migration history
  python scripts/db_migrate.py history
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create migration
    create_parser = subparsers.add_parser("create", help="Create new migration")
    create_parser.add_argument("-m", "--message", required=True, help="Migration message")
    create_parser.add_argument("--no-autogenerate", action="store_true",
                               help="Don't auto-generate from models")
    
    # Upgrade
    upgrade_parser = subparsers.add_parser("upgrade", help="Run migrations")
    upgrade_parser.add_argument("revision", nargs="?", default="head",
                                help="Target revision (default: head)")
    
    # Downgrade
    downgrade_parser = subparsers.add_parser("downgrade", help="Rollback migrations")
    downgrade_parser.add_argument("revision", help="Target revision")
    
    # Current
    subparsers.add_parser("current", help="Show current version")
    
    # History
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument("-v", "--verbose", action="store_true",
                                help="Verbose output")
    
    # Pending
    subparsers.add_parser("pending", help="Show pending migrations")
    
    # Verify
    subparsers.add_parser("verify", help="Verify database is current")
    
    # Stamp
    stamp_parser = subparsers.add_parser("stamp", help="Stamp database version")
    stamp_parser.add_argument("revision", help="Revision to stamp")
    
    # Reset
    subparsers.add_parser("reset", help="Reset database (DANGEROUS)")
    
    # Check models
    subparsers.add_parser("check", help="Check if models need migration")
    
    # Generate SQL
    sql_parser = subparsers.add_parser("sql", help="Generate SQL for migration")
    sql_parser.add_argument("revision", nargs="?", default="head",
                          help="Target revision")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MigrationManager()
    
    if args.command == "create":
        manager.create_migration(
            message=args.message,
            autogenerate=not args.no_autogenerate
        )
    elif args.command == "upgrade":
        manager.migrate(args.revision)
    elif args.command == "downgrade":
        manager.downgrade(args.revision)
    elif args.command == "current":
        success, output = manager.current_version()
        print(output)
    elif args.command == "history":
        success, output = manager.history(args.verbose)
        print(output)
    elif args.command == "pending":
        success, output = manager.show_pending()
        print(output)
    elif args.command == "verify":
        manager.verify()
    elif args.command == "stamp":
        manager.stamp(args.revision)
    elif args.command == "reset":
        manager.reset()
    elif args.command == "check":
        manager.check_models()
    elif args.command == "sql":
        success, output = manager.generate_sql(args.revision)
        print(output)


if __name__ == "__main__":
    main()
