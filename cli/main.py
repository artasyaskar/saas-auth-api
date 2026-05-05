"""
SaaS Auth API - CLI Management Tool

Comprehensive command-line interface for managing the SaaS Auth API.
Includes user management, database operations, monitoring, and more.
"""
import click
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal, engine
from app.db.models import Base, User, UserRole, SubscriptionPlan
from app.core.security import get_password_hash
from sqlalchemy.orm import Session


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """SaaS Auth API Management CLI"""
    pass


@cli.group()
def db():
    """Database operations"""
    pass


@db.command()
def init():
    """Initialize the database with all tables"""
    click.echo("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    click.echo("✓ Database initialized successfully")


@db.command()
def reset():
    """Reset the database (WARNING: deletes all data)"""
    if click.confirm("This will delete all data. Are you sure?"):
        click.echo("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        click.echo("Creating tables...")
        Base.metadata.create_all(bind=engine)
        click.echo("✓ Database reset successfully")


@db.command()
def seed():
    """Seed the database with initial data"""
    db = SessionLocal()
    try:
        # Create admin user
        admin_email = click.prompt("Admin email", default="admin@example.com")
        admin_password = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)
        
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            click.echo("Admin user already exists")
        else:
            admin = User(
                username="admin",
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                role=UserRole.ADMIN,
                is_active=True,
                subscription_plan=SubscriptionPlan.PRO
            )
            db.add(admin)
            db.commit()
            click.echo("✓ Admin user created")
        
        click.echo("✓ Database seeded successfully")
    finally:
        db.close()


@cli.group()
def user():
    """User management operations"""
    pass


@user.command()
@click.option("--username", required=True, help="Username")
@click.option("--email", required=True, help="Email address")
@click.option("--password", required=True, help="Password")
@click.option("--role", default="USER", help="User role (USER or ADMIN)")
@click.option("--plan", default="FREE", help="Subscription plan (FREE or PRO)")
def create(username: str, email: str, password: str, role: str, plan: str):
    """Create a new user"""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            click.echo("Error: User with this email already exists", err=True)
            sys.exit(1)
        
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole[role.upper()],
            is_active=True,
            subscription_plan=SubscriptionPlan[plan.upper()]
        )
        db.add(user)
        db.commit()
        click.echo(f"✓ User created: {email}")
    finally:
        db.close()


@user.command()
@click.option("--email", required=True, help="Email address")
def delete(email: str):
    """Delete a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            click.echo("Error: User not found", err=True)
            sys.exit(1)
        
        db.delete(user)
        db.commit()
        click.echo(f"✓ User deleted: {email}")
    finally:
        db.close()


@user.command()
def list():
    """List all users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        click.echo(f"Total users: {len(users)}")
        click.echo("-" * 80)
        for user in users:
            click.echo(f"ID: {user.id} | {user.username} | {user.email} | {user.role.value} | {user.subscription_plan.value}")
    finally:
        db.close()


@user.command()
@click.option("--email", required=True, help="Email address")
@click.option("--role", help="New role (USER or ADMIN)")
@click.option("--plan", help="New subscription plan (FREE or PRO)")
@click.option("--active", type=bool, help="Active status")
def update(email: str, role: Optional[str], plan: Optional[str], active: Optional[bool]):
    """Update a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            click.echo("Error: User not found", err=True)
            sys.exit(1)
        
        if role:
            user.role = UserRole[role.upper()]
        if plan:
            user.subscription_plan = SubscriptionPlan[plan.upper()]
        if active is not None:
            user.is_active = active
        
        db.commit()
        click.echo(f"✓ User updated: {email}")
    finally:
        db.close()


@cli.group()
def feature_flags():
    """Feature flag management"""
    pass


@feature_flags.command()
@click.option("--name", required=True, help="Flag name")
@click.option("--description", help="Flag description")
@click.option("--enabled", type=bool, default=False, help="Default enabled state")
@click.option("--strategy", default="all_users", help="Rollout strategy")
@click.option("--percentage", type=int, default=0, help="Rollout percentage")
def create(name: str, description: str, enabled: bool, strategy: str, percentage: int):
    """Create a feature flag"""
    from app.services.feature_flags import FeatureFlagService, RolloutStrategy
    
    db = SessionLocal()
    try:
        service = FeatureFlagService(db)
        flag = service.create_flag(
            name=name,
            description=description or f"Feature flag: {name}",
            default_value=enabled,
            strategy=RolloutStrategy(strategy),
            rollout_percentage=percentage
        )
        click.echo(f"✓ Feature flag created: {name}")
    finally:
        db.close()


@feature_flags.command()
def list():
    """List all feature flags"""
    from app.services.feature_flags import FeatureFlagService
    
    db = SessionLocal()
    try:
        service = FeatureFlagService(db)
        flags = service.get_all_flags()
        click.echo(f"Total flags: {len(flags)}")
        click.echo("-" * 80)
        for flag in flags:
            status = "✓" if flag.is_active else "✗"
            click.echo(f"{status} {flag.name} | {flag.strategy} | {flag.rollout_percentage}%")
    finally:
        db.close()


@feature_flags.command()
@click.option("--name", required=True, help="Flag name")
@click.option("--enabled", type=bool, help="Enable/disable flag")
@click.option("--percentage", type=int, help="Rollout percentage")
def update(name: str, enabled: Optional[bool], percentage: Optional[int]):
    """Update a feature flag"""
    from app.services.feature_flags import FeatureFlagService
    
    db = SessionLocal()
    try:
        service = FeatureFlagService(db)
        updates = {}
        if enabled is not None:
            updates["is_active"] = enabled
        if percentage is not None:
            updates["rollout_percentage"] = percentage
        
        flag = service.update_flag(name, **updates)
        if flag:
            click.echo(f"✓ Feature flag updated: {name}")
        else:
            click.echo("Error: Flag not found", err=True)
    finally:
        db.close()


@cli.group()
def monitoring():
    """Monitoring and analytics"""
    pass


@monitoring.command()
def stats():
    """Show system statistics"""
    db = SessionLocal()
    try:
        # User stats
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
        pro_users = db.query(User).filter(User.subscription_plan == SubscriptionPlan.PRO).count()
        
        click.echo("=== System Statistics ===")
        click.echo(f"Total Users: {total_users}")
        click.echo(f"Active Users: {active_users}")
        click.echo(f"Admin Users: {admin_users}")
        click.echo(f"Pro Subscribers: {pro_users}")
        
        # Feature flags
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService(db)
        flags = service.get_all_flags()
        active_flags = len([f for f in flags if f.is_active])
        click.echo(f"Active Feature Flags: {active_flags}/{len(flags)}")
        
    finally:
        db.close()


@monitoring.command()
@click.option("--days", type=int, default=30, help="Number of days")
def analytics(days: int):
    """Show analytics for the specified period"""
    from app.services.analytics import AnalyticsService
    
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        
        click.echo(f"=== Analytics (Last {days} Days) ===")
        
        # User growth
        growth = service.get_user_growth(days)
        click.echo(f"New Users: {growth.get('new_users', 0)}")
        click.echo(f"Growth Rate: {growth.get('growth_rate', 0):.2f}%")
        
        # Revenue
        revenue = service.get_revenue_metrics(days)
        click.echo(f"Total Revenue: ${revenue.get('total_revenue', 0):.2f}")
        click.echo(f"MRR: ${revenue.get('mrr', 0):.2f}")
        
    finally:
        db.close()


@cli.group()
def security():
    """Security operations"""
    pass


@security.command()
@click.option("--days", type=int, default=7, help="Number of days")
def audit(days: int):
    """Show security audit log"""
    from app.services.audit import AuditService
    
    db = SessionLocal()
    try:
        service = AuditService(db)
        events = service.get_security_events(days=days)
        
        click.echo(f"=== Security Events (Last {days} Days) ===")
        for event in events:
            severity = event.get("severity", "INFO")
            click.echo(f"[{severity}] {event.get('event_type')} - {event.get('timestamp')}")
    finally:
        db.close()


@security.command()
def cleanup():
    """Clean up expired tokens and sessions"""
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta
        
        # Clean expired password reset tokens
        from app.db.models import PasswordResetToken
        expired_tokens = db.query(PasswordResetToken).filter(
            PasswordResetToken.expires_at < datetime.utcnow()
        ).delete()
        
        # Clean expired email verifications
        from app.db.models import EmailVerification
        expired_verifications = db.query(EmailVerification).filter(
            EmailVerification.expires_at < datetime.utcnow()
        ).delete()
        
        # Clean expired sessions
        from app.db.models import UserSession
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        click.echo(f"✓ Cleaned up:")
        click.echo(f"  - {expired_tokens} expired password reset tokens")
        click.echo(f"  - {expired_verifications} expired email verifications")
        click.echo(f"  - {expired_sessions} expired sessions")
    finally:
        db.close()


@cli.command()
def health():
    """Check system health"""
    click.echo("=== System Health Check ===")
    
    # Database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        click.echo("✓ Database: OK")
    except Exception as e:
        click.echo(f"✗ Database: FAILED - {e}")
    
    # Redis (if configured)
    try:
        import redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        r = redis.Redis(host=redis_host, port=6379, db=0)
        r.ping()
        click.echo("✓ Redis: OK")
    except:
        click.echo("✗ Redis: NOT CONFIGURED or FAILED")
    
    # Elasticsearch (if configured)
    try:
        from elasticsearch import Elasticsearch
        es_host = os.getenv("ELASTICSEARCH_HOST", "localhost:9200")
        es = Elasticsearch([es_host])
        es.ping()
        click.echo("✓ Elasticsearch: OK")
    except:
        click.echo("✗ Elasticsearch: NOT CONFIGURED or FAILED")


if __name__ == "__main__":
    cli()
