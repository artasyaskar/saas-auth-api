"""
Background task service for async operations.
In production, this would use Celery or RQ.
For now, uses asyncio background tasks.
"""
import asyncio
from typing import Callable, Any, Optional
from datetime import datetime
import threading
from queue import Queue


class BackgroundTaskService:
    """Service for managing background tasks."""
    
    def __init__(self):
        self._task_queue: Queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """Start the background worker."""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
    
    def _worker_loop(self):
        """Main worker loop."""
        while self._running:
            try:
                task = self._task_queue.get(timeout=1.0)
                if task:
                    func, args, kwargs = task
                    try:
                        func(*args, **kwargs)
                    except Exception as e:
                        print(f"Background task error: {e}")
            except Exception:
                continue
    
    def add_task(self, func: Callable, *args, **kwargs):
        """Add a task to be executed in the background."""
        if not self._running:
            self.start()
        self._task_queue.put((func, args, kwargs))
    
    async def add_async_task(self, coro: Any):
        """Add an async coroutine to be executed."""
        asyncio.create_task(coro)


# Global instance
background_service = BackgroundTaskService()


class EmailTask:
    """Email background tasks."""
    
    @staticmethod
    def send_password_reset(email: str, username: str, token: str):
        """Queue password reset email."""
        from app.services.email import email_service
        background_service.add_task(
            email_service.send_password_reset,
            email, username, token
        )
    
    @staticmethod
    def send_email_verification(email: str, username: str, token: str):
        """Queue email verification."""
        from app.services.email import email_service
        background_service.add_task(
            email_service.send_email_verification,
            email, username, token
        )
    
    @staticmethod
    def send_security_alert(email: str, username: str, alert_title: str, 
                           alert_description: str, ip_address: str):
        """Queue security alert."""
        from app.services.email import email_service
        background_service.add_task(
            email_service.send_security_alert,
            email, username, alert_title, alert_description, ip_address
        )


class CleanupTask:
    """Cleanup background tasks."""
    
    @staticmethod
    def cleanup_expired_tokens(db_session_factory):
        """Clean up expired tokens from database."""
        def _cleanup():
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker()
            db = Session()
            try:
                from app.services.token_blacklist import get_token_blacklist_service
                service = get_token_blacklist_service(db)
                deleted = service.cleanup_database_blacklist(days_to_keep=7)
                print(f"Cleaned up {deleted} expired blacklist entries")
                
                from app.services.password_reset import get_password_reset_service
                reset_service = get_password_reset_service(db)
                deleted_reset = reset_service.cleanup_expired_tokens(days_to_keep=7)
                print(f"Cleaned up {deleted_reset} expired reset tokens")
            finally:
                db.close()
        
        background_service.add_task(_cleanup)
    
    @staticmethod
    def cleanup_old_audit_logs(db_session_factory, days_to_keep: int = 90):
        """Clean up old audit logs."""
        def _cleanup():
            from sqlalchemy.orm import sessionmaker
            from datetime import datetime, timedelta
            from app.db.models import AuditLog
            
            Session = sessionmaker()
            db = Session()
            try:
                cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
                deleted = db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete()
                db.commit()
                print(f"Cleaned up {deleted} old audit log entries")
            finally:
                db.close()
        
        background_service.add_task(_cleanup)


def get_background_service() -> BackgroundTaskService:
    """Get the background task service."""
    return background_service
