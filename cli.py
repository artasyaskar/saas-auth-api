#!/usr/bin/env python3
"""
SaaS Auth API - Management CLI Tool

A comprehensive command-line interface for managing the SaaS Auth API.
Supports database operations, user management, analytics export, and
system administration tasks.
"""

import os
import sys
import click
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import User, UserRole, UsageLog, SubscriptionPlan
from app.core.security import get_password_hash
from app.services.analytics import AnalyticsService
from app.services.usage import UsageService


@click.group()
def cli():
    """SaaS Auth API Management CLI"""
    pass


# ==================== User Management ====================

@cli.group()
def users():
    """User management commands"""
    pass


@users.command()
@click.option('--username', '-u', required=True, help='Username')
@click.option('--email', '-e', required=True, help='Email address')
@click.option('--password', '-p', required=True, help='Password')
@click.option('--role', '-r', type=click.Choice(['user', 'admin', 'moderator']), 
              default='user', help='User role')
@click.option('--plan', type=click.Choice(['free', 'pro', 'enterprise']),
              default='free', help='Subscription plan')
def create(username: str, email: str, password: str, role: str, plan: str):
    """Create a new user account"""
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if existing:
            click.echo(f"Error: User already exists", err=True)
            sys.exit(1)
        
        # Create user
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole(role.upper()),
            subscription_plan=SubscriptionPlan(plan.upper()),
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        
        click.echo(f"✓ Created user: {username} (ID: {user.id})")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        db.close()


@users.command()
@click.option('--role', '-r', type=click.Choice(['user', 'admin', 'moderator']),
              help='Filter by role')
@click.option('--active/--inactive', default=None, help='Filter by status')
@click.option('--limit', '-l', default=20, help='Number of results')
@click.option('--format', '-f', 'output_format', type=click.Choice(['table', 'json']),
              default='table', help='Output format')
def list(role: Optional[str], active: Optional[bool], limit: int, output_format: str):
    """List all users"""
    db = SessionLocal()
    try:
        query = db.query(User)
        
        if role:
            query = query.filter(User.role == UserRole(role.upper()))
        
        if active is not None:
            query = query.filter(User.is_active == active)
        
        users = query.limit(limit).all()
        
        if output_format == 'json':
            output = [
                {
                    'id': u.id,
                    'username': u.username,
                    'email': u.email,
                    'role': u.role.value,
                    'is_active': u.is_active,
                    'plan': u.subscription_plan.value if u.subscription_plan else None,
                    'created_at': u.created_at.isoformat() if u.created_at else None
                }
                for u in users
            ]
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<10} {'Status':<10}")
            click.echo("-" * 80)
            for u in users:
                status = "✓ Active" if u.is_active else "✗ Inactive"
                click.echo(f"{u.id:<5} {u.username:<20} {u.email:<30} {u.role.value:<10} {status:<10}")
        
        click.echo(f"\nTotal: {len(users)} users")
        
    finally:
        db.close()


@users.command()
@click.argument('user_id', type=int)
def activate(user_id: int):
    """Activate a user account"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            click.echo(f"Error: User {user_id} not found", err=True)
            sys.exit(1)
        
        user.is_active = True
        db.commit()
        
        click.echo(f"✓ Activated user: {user.username}")
        
    finally:
        db.close()


@users.command()
@click.argument('user_id', type=int)
def deactivate(user_id: int):
    """Deactivate/suspend a user account"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            click.echo(f"Error: User {user_id} not found", err=True)
            sys.exit(1)
        
        user.is_active = False
        db.commit()
        
        click.echo(f"✓ Deactivated user: {user.username}")
        
    finally:
        db.close()


@users.command()
@click.argument('user_id', type=int)
@click.confirmation_option(prompt='Are you sure you want to delete this user?')
def delete(user_id: int):
    """Permanently delete a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            click.echo(f"Error: User {user_id} not found", err=True)
            sys.exit(1)
        
        username = user.username
        db.delete(user)
        db.commit()
        
        click.echo(f"✓ Deleted user: {username}")
        
    finally:
        db.close()


# ==================== Analytics Commands ====================

@cli.group()
def analytics():
    """Analytics and reporting commands"""
    pass


@analytics.command()
@click.option('--days', '-d', default=30, help='Number of days to analyze')
@click.option('--export', '-e', type=click.Path(), help='Export to file')
def growth(days: int, export: Optional[str]):
    """Show user growth metrics"""
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        metrics = service.get_user_growth_metrics(days)
        
        click.echo(f"\nUser Growth Metrics (Last {days} days)")
        click.echo("=" * 50)
        click.echo(f"Total New Users: {metrics['total_new_users']}")
        click.echo(f"Avg Daily Signups: {metrics['avg_daily_signups']:.1f}")
        
        if export:
            with open(export, 'w') as f:
                json.dump(metrics, f, indent=2)
            click.echo(f"\n✓ Exported to: {export}")
        
    finally:
        db.close()


@analytics.command()
def revenue():
    """Show revenue metrics"""
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        metrics = service.get_revenue_metrics()
        
        click.echo("\nRevenue Metrics")
        click.echo("=" * 50)
        click.echo(f"Monthly Recurring Revenue: ${metrics['mrr']:,.2f}")
        click.echo(f"Annual Recurring Revenue: ${metrics['arr']:,.2f}")
        click.echo(f"\nPlan Distribution:")
        for plan, count in metrics['plan_distribution'].items():
            click.echo(f"  {plan}: {count} users")
        
    finally:
        db.close()


@analytics.command()
@click.option('--days', '-d', default=7, help='Time period')
def endpoints(days: int):
    """Show API endpoint popularity"""
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        endpoints = service.get_endpoint_popularity(days)
        
        click.echo(f"\nPopular Endpoints (Last {days} days)")
        click.echo("=" * 80)
        click.echo(f"{'Endpoint':<40} {'Method':<8} {'Requests':<12} {'Avg Time (ms)':<15}")
        click.echo("-" * 80)
        
        for ep in endpoints[:10]:
            click.echo(
                f"{ep['endpoint']:<40} "
                f"{ep['method']:<8} "
                f"{ep['request_count']:<12} "
                f"{ep['avg_response_time_ms']:<15.2f}"
            )
        
    finally:
        db.close()


# ==================== Export Commands ====================

@cli.group()
def export():
    """Data export commands"""
    pass


@export.command()
@click.option('--start-date', '-s', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', required=True, help='End date (YYYY-MM-DD)')
@click.option('--output', '-o', required=True, help='Output file path')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['json', 'csv']), default='json')
def usage(start_date: str, end_date: str, output: str, output_format: str):
    """Export usage logs to file"""
    db = SessionLocal()
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        
        logs = db.query(UsageLog).filter(
            UsageLog.timestamp >= start,
            UsageLog.timestamp < end
        ).all()
        
        if output_format == 'json':
            data = [
                {
                    'user_id': log.user_id,
                    'endpoint': log.endpoint,
                    'method': log.method,
                    'status_code': log.status_code,
                    'timestamp': log.timestamp.isoformat(),
                    'response_time_ms': log.response_time_ms
                }
                for log in logs
            ]
            with open(output, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            import csv
            with open(output, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['user_id', 'endpoint', 'method', 'status_code', 
                               'timestamp', 'response_time_ms'])
                for log in logs:
                    writer.writerow([
                        log.user_id, log.endpoint, log.method,
                        log.status_code, log.timestamp.isoformat(),
                        log.response_time_ms
                    ])
        
        click.echo(f"✓ Exported {len(logs)} records to: {output}")
        
    finally:
        db.close()


@export.command()
@click.option('--output', '-o', required=True, help='Output file path')
def users_all(output: str):
    """Export all users to file"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        
        data = [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role.value,
                'is_active': u.is_active,
                'subscription_plan': u.subscription_plan.value if u.subscription_plan else None,
                'created_at': u.created_at.isoformat() if u.created_at else None,
                'last_login': u.last_login.isoformat() if hasattr(u, 'last_login') and u.last_login else None
            }
            for u in users
        ]
        
        with open(output, 'w') as f:
            json.dump(data, f, indent=2)
        
        click.echo(f"✓ Exported {len(users)} users to: {output}")
        
    finally:
        db.close()


# ==================== System Commands ====================

@cli.group()
def system():
    """System administration commands"""
    pass


@system.command()
def stats():
    """Show system statistics"""
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
        
        click.echo("\nSystem Statistics")
        click.echo("=" * 50)
        click.echo(f"Total Users: {total_users}")
        click.echo(f"Active Users: {active_users}")
        click.echo(f"Admin Users: {admin_users}")
        
        # Plan distribution
        plans = db.query(
            User.subscription_plan,
            db.func.count(User.id)
        ).group_by(User.subscription_plan).all()
        
        click.echo("\nSubscription Plans:")
        for plan, count in plans:
            plan_name = plan.value if plan else 'unknown'
            click.echo(f"  {plan_name}: {count}")
        
    finally:
        db.close()


@system.command()
def health():
    """Check system health"""
    click.echo("\nSystem Health Check")
    click.echo("=" * 50)
    
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        click.echo("✓ Database connection: OK")
        db.close()
    except Exception as e:
        click.echo(f"✗ Database connection: FAILED ({e})")
    
    click.echo("✓ Application: Running")


# Import for users list command
from sqlalchemy import or_

if __name__ == '__main__':
    cli()
