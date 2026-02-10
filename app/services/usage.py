from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import UsageLog, User


class UsageService:
    def __init__(self, db: Session):
        self.db = db
    
    def log_usage(
        self,
        user_id: int,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: Optional[float] = None
    ):
        """Log API usage for tracking and billing"""
        usage_log = UsageLog(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            timestamp=datetime.utcnow(),
            response_time_ms=response_time_ms
        )
        
        self.db.add(usage_log)
        self.db.commit()
        
        return usage_log
    
    def get_user_usage(self, user_id: int, limit: int = 100):
        """Get recent usage logs for a specific user"""
        return self.db.query(UsageLog).filter(
            UsageLog.user_id == user_id
        ).order_by(
            UsageLog.timestamp.desc()
        ).limit(limit).all()
    
    def get_endpoint_usage(self, endpoint: str, limit: int = 100):
        """Get recent usage logs for a specific endpoint"""
        return self.db.query(UsageLog).filter(
            UsageLog.endpoint == endpoint
        ).order_by(
            UsageLog.timestamp.desc()
        ).limit(limit).all()
