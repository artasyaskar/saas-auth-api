"""
Enhanced email queue service for async email processing.

Handles email queue management, async processing, retry mechanism,
and comprehensive email delivery with proper error handling.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import redis
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings
from app.core.exceptions import (
    ValidationError, ExternalServiceError,
    DatabaseError
)
from app.db.models import EmailQueue, EmailTemplate


class EmailStatus(str, Enum):
    """Email status enumeration."""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class EmailPriority(str, Enum):
    """Email priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class EmailMessage:
    """Email message data structure."""
    id: str
    to_email: str
    from_email: str
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] None
    priority: EmailPriority = EmailPriority.NORMAL
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None


class EnhancedEmailQueueService:
    """
    Enhanced email queue service with async processing.
    
    Handles email queue management, async processing, retry mechanism,
    and comprehensive email delivery with proper error handling.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = structlog.get_logger()
        
        # Initialize Redis if available
        try:
            self.redis_client = redis.from_url(
                settings.redis.get_redis_url(),
                decode_responses=True
            )
            self.use_redis = True
        except Exception:
            self.redis_client = None
            self.use_redis = False
            self._memory_queue = []
        
        # Worker configuration
        self.worker_count = 5
        self.batch_size = 10
        self.retry_delays = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour
        
        # TODO: Add email provider support (SendGrid, AWS SES)
        # TODO: Add email template rendering
        # TODO: Add email analytics
        # TODO: Add bounce handling
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        from_email: Optional[str] = None,
        priority: EmailPriority = EmailPriority.NORMAL,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Queue email for sending.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            from_email: Sender email address
            priority: Email priority
            template_id: Email template ID
            template_data: Template data
            attachments: Email attachments
            metadata: Additional metadata
            
        Returns:
            Email queue ID
        """
        try:
            # Validate email data
            self._validate_email_data(to_email, subject, html_body, text_body)
            
            # Generate email ID
            email_id = str(uuid.uuid4())
            
            # Create email message
            email_message = EmailMessage(
                id=email_id,
                to_email=to_email,
                from_email=from_email or settings.email.from_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                attachments=attachments,
                priority=priority,
                template_id=template_id,
                template_data=template_data,
                metadata=metadata,
                created_at=datetime.utcnow(),
                retry_count=0,
                max_retries=self._get_max_retries(priority)
            )
            
            # Queue email
            if self.use_redis:
                await self._queue_email_redis(email_message)
            else:
                await self._queue_email_memory(email_message)
            
            self.logger.info(
                "email_queued",
                email_id=email_id,
                to_email=to_email,
                subject=subject,
                priority=priority.value
            )
            
            return email_id
            
        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to queue email: {str(e)}")
    
    async def send_bulk_emails(
        self,
        emails: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Queue multiple emails for sending.
        
        Args:
            emails: List of email data dictionaries
            
        Returns:
            List of email queue IDs
        """
        email_ids = []
        
        for email_data in emails:
            try:
                email_id = await self.send_email(**email_data)
                email_ids.append(email_id)
            except Exception as e:
                self.logger.error(
                    "bulk_email_failed",
                    email_data=email_data,
                    error=str(e)
                )
        
        return email_ids
    
    async def get_email_status(self, email_id: str) -> Dict[str, Any]:
        """
        Get email delivery status.
        
        Args:
            email_id: Email queue ID
            
        Returns:
            Email status information
        """
        try:
            if self.use_redis:
                status = await self._get_email_status_redis(email_id)
            else:
                status = await self._get_email_status_memory(email_id)
            
            return status
            
        except Exception as e:
            raise DatabaseError(f"Failed to get email status: {str(e)}")
    
    async def cancel_email(self, email_id: str) -> bool:
        """
        Cancel queued email.
        
        Args:
            email_id: Email queue ID
            
        Returns:
            True if cancelled successfully
        """
        try:
            if self.use_redis:
                success = await self._cancel_email_redis(email_id)
            else:
                success = await self._cancel_email_memory(email_id)
            
            if success:
                self.logger.info(
                    "email_cancelled",
                    email_id=email_id
                )
            
            return success
            
        except Exception as e:
            raise DatabaseError(f"Failed to cancel email: {str(e)}")
    
    async def retry_failed_emails(self) -> int:
        """
        Retry failed emails based on retry schedule.
        
        Returns:
            Number of emails retried
        """
        try:
            retried_count = 0
            
            # Get emails ready for retry
            if self.use_redis:
                emails_to_retry = await self._get_emails_to_retry_redis()
            else:
                emails_to_retry = await self._get_emails_to_retry_memory()
            
            for email_data in emails_to_retry:
                try:
                    await self._retry_email(email_data)
                    retried_count += 1
                except Exception as e:
                    self.logger.error(
                        "email_retry_failed",
                        email_id=email_data.get("id"),
                        error=str(e)
                    )
            
            return retried_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to retry emails: {str(e)}")
    
    async def process_email_queue(self) -> int:
        """
        Process email queue with batch processing.
        
        Returns:
            Number of emails processed
        """
        try:
            processed_count = 0
            
            # Get batch of pending emails
            if self.use_redis:
                emails_to_process = await self._get_pending_emails_redis(self.batch_size)
            else:
                emails_to_process = await self._get_pending_emails_memory(self.batch_size)
            
            # Process emails in parallel
            semaphore = asyncio.Semaphore(self.worker_count)
            
            tasks = [
                self._process_single_email(semaphore, email_data)
                for email_data in emails_to_process
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful processing
            for result in results:
                if not isinstance(result, Exception):
                    processed_count += 1
                else:
                    self.logger.error(
                        "email_processing_error",
                        error=str(result)
                    )
            
            return processed_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to process email queue: {str(e)}")
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """
        Get email queue statistics.
        
        Returns:
            Queue statistics
        """
        try:
            if self.use_redis:
                stats = await self._get_queue_stats_redis()
            else:
                stats = await self._get_queue_stats_memory()
            
            return stats
            
        except Exception as e:
            raise DatabaseError(f"Failed to get queue statistics: {str(e)}")
    
    async def _queue_email_redis(self, email_message: EmailMessage):
        """Queue email in Redis."""
        try:
            # Serialize email message
            email_data = {
                "id": email_message.id,
                "to_email": email_message.to_email,
                "from_email": email_message.from_email,
                "subject": email_message.subject,
                "html_body": email_message.html_body,
                "text_body": email_message.text_body,
                "attachments": email_message.attachments,
                "priority": email_message.priority.value,
                "template_id": email_message.template_id,
                "template_data": email_message.template_data,
                "metadata": email_message.metadata,
                "created_at": email_message.created_at.isoformat(),
                "retry_count": email_message.retry_count,
                "max_retries": email_message.max_retries,
                "status": EmailStatus.PENDING.value
            }
            
            # Add to queue
            await self.redis_client.lpush("email_queue", json.dumps(email_data))
            
            # Add to tracking set
            await self.redis_client.hset(
                "email_tracking",
                email_message.id,
                json.dumps(email_data)
            )
            
        except Exception as e:
            raise ExternalServiceError(f"Failed to queue email in Redis: {str(e)}")
    
    async def _queue_email_memory(self, email_message: EmailMessage):
        """Queue email in memory."""
        try:
            email_data = {
                "id": email_message.id,
                "to_email": email_message.to_email,
                "from_email": email_message.from_email,
                "subject": email_message.subject,
                "html_body": email_message.html_body,
                "text_body": email_message.text_body,
                "attachments": email_message.attachments,
                "priority": email_message.priority.value,
                "template_id": email_message.template_id,
                "template_data": email_message.template_data,
                "metadata": email_message.metadata,
                "created_at": email_message.created_at.isoformat(),
                "retry_count": email_message.retry_count,
                "max_retries": email_message.max_retries,
                "status": EmailStatus.PENDING.value
            }
            
            self._memory_queue.append(email_data)
            
        except Exception as e:
            raise DatabaseError(f"Failed to queue email in memory: {str(e)}")
    
    async def _process_single_email(self, semaphore: asyncio.Semaphore, email_data: Dict[str, Any]) -> bool:
        """Process single email with semaphore control."""
        async with semaphore:
            try:
                # Update status to sending
                await self._update_email_status(email_data["id"], EmailStatus.SENDING)
                
                # Send email
                success = await self._send_email_smtp(email_data)
                
                if success:
                    # Update status to sent
                    await self._update_email_status(email_data["id"], EmailStatus.SENT)
                    return True
                else:
                    # Handle retry logic
                    await self._handle_email_failure(email_data)
                    return False
                    
            except Exception as e:
                self.logger.error(
                    "email_send_error",
                    email_id=email_data.get("id"),
                    error=str(e)
                )
                await self._handle_email_failure(email_data)
                return False
    
    async def _send_email_smtp(self, email_data: Dict[str, Any]) -> bool:
        """Send email using SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            
            # Add headers
            msg['From'] = email_data["from_email"]
            msg['To'] = email_data["to_email"]
            msg['Subject'] = email_data["subject"]
            
            # Add body
            if email_data.get("text_body"):
                text_part = MIMEText(email_data["text_body"], 'plain', 'utf-8')
                msg.attach(text_part)
            
            if email_data.get("html_body"):
                html_part = MIMEText(email_data["html_body"], 'html', 'utf-8')
                msg.attach(html_part)
            
            # Add attachments
            attachments = email_data.get("attachments", [])
            for attachment in attachments:
                # TODO: Implement attachment handling
                pass
            
            # Send email
            smtp_config = settings.email
            server = smtplib.SMTP(smtp_config.smtp_host, smtp_config.smtp_port)
            
            if smtp_config.smtp_tls:
                server.starttls()
            
            server.login(smtp_config.smtp_user, smtp_config.smtp_password)
            
            text = msg.as_string()
            server.sendmail(email_data["from_email"], [email_data["to_email"]], text)
            server.quit()
            
            return True
            
        except Exception as e:
            self.logger.error(
                "smtp_send_failed",
                email_id=email_data.get("id"),
                to_email=email_data.get("to_email"),
                error=str(e)
            )
            return False
    
    async def _update_email_status(self, email_id: str, status: EmailStatus):
        """Update email status in storage."""
        try:
            if self.use_redis:
                await self._update_email_status_redis(email_id, status)
            else:
                await self._update_email_status_memory(email_id, status)
        except Exception as e:
            self.logger.error(
                "email_status_update_failed",
                email_id=email_id,
                status=status.value,
                error=str(e)
            )
    
    async def _handle_email_failure(self, email_data: Dict[str, Any]):
        """Handle email sending failure with retry logic."""
        try:
            retry_count = email_data.get("retry_count", 0) + 1
            max_retries = email_data.get("max_retries", 3)
            
            if retry_count < max_retries:
                # Calculate next retry time
                delay_index = min(retry_count - 1, len(self.retry_delays) - 1)
                delay = self.retry_delays[delay_index]
                next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                
                # Update email data for retry
                email_data["retry_count"] = retry_count
                email_data["next_retry_at"] = next_retry_at
                email_data["status"] = EmailStatus.RETRYING.value
                
                # Update in storage
                await self._update_email_status_data(email_data)
                
                self.logger.info(
                    "email_retry_scheduled",
                    email_id=email_data.get("id"),
                    retry_count=retry_count,
                    next_retry_at=next_retry_at.isoformat()
                )
            else:
                # Mark as failed after max retries
                await self._update_email_status(email_data.get("id"), EmailStatus.FAILED)
                
                self.logger.error(
                    "email_failed_permanently",
                    email_id=email_data.get("id"),
                    retry_count=retry_count,
                    max_retries=max_retries
                )
                
        except Exception as e:
            self.logger.error(
                "email_failure_handling_failed",
                email_id=email_data.get("id"),
                error=str(e)
            )
    
    def _validate_email_data(self, to_email: str, subject: str, html_body: Optional[str], text_body: Optional[str]):
        """Validate email data."""
        errors = []
        
        # Validate email
        if not to_email or "@" not in to_email:
            errors.append("Invalid recipient email")
        
        # Validate subject
        if not subject or len(subject.strip()) < 1:
            errors.append("Email subject is required")
        
        if len(subject) > 200:
            errors.append("Email subject too long (max 200 characters)")
        
        # Validate body
        if not html_body and not text_body:
            errors.append("Email body is required (either HTML or text)")
        
        if errors:
            raise ValidationError("Email validation failed", errors=errors)
    
    def _get_max_retries(self, priority: EmailPriority) -> int:
        """Get maximum retries based on priority."""
        retry_limits = {
            EmailPriority.LOW: 1,
            EmailPriority.NORMAL: 3,
            EmailPriority.HIGH: 5,
            EmailPriority.URGENT: 7
        }
        return retry_limits.get(priority, 3)
    
    # Redis-based methods
    async def _get_email_status_redis(self, email_id: str) -> Dict[str, Any]:
        """Get email status from Redis."""
        try:
            data = await self.redis_client.hget("email_tracking", email_id)
            return json.loads(data) if data else {}
        except Exception:
            return {}
    
    async def _cancel_email_redis(self, email_id: str) -> bool:
        """Cancel email in Redis."""
        try:
            # Update status
            await self.redis_client.hset(
                "email_tracking",
                email_id,
                json.dumps({"status": EmailStatus.CANCELLED.value})
            )
            
            # Remove from queue
            await self._remove_from_queue_redis(email_id)
            
            return True
        except Exception:
            return False
    
    async def _get_emails_to_retry_redis(self) -> List[Dict[str, Any]]:
        """Get emails ready for retry from Redis."""
        try:
            # Get all emails with RETRYING status and past retry time
            now = datetime.utcnow().isoformat()
            
            # This is a simplified implementation
            # TODO: Implement proper Redis query for retry logic
            return []
        except Exception:
            return []
    
    async def _get_pending_emails_redis(self, limit: int) -> List[Dict[str, Any]]:
        """Get pending emails from Redis."""
        try:
            emails = []
            
            for _ in range(limit):
                data = await self.redis_client.rpop("email_queue")
                if data:
                    emails.append(json.loads(data))
                else:
                    break
            
            return emails
        except Exception:
            return []
    
    async def _get_queue_stats_redis(self) -> Dict[str, Any]:
        """Get queue statistics from Redis."""
        try:
            queue_length = await self.redis_client.llen("email_queue")
            tracking_data = await self.redis_client.hgetall("email_tracking")
            
            stats = {
                "queue_length": queue_length,
                "total_tracked": len(tracking_data),
                "pending": 0,
                "sending": 0,
                "sent": 0,
                "failed": 0,
                "retrying": 0
            }
            
            # Count by status
            for email_data in tracking_data.values():
                try:
                    data = json.loads(email_data)
                    status = data.get("status", EmailStatus.PENDING.value)
                    stats[status] = stats.get(status, 0) + 1
                except:
                    pass
            
            return stats
        except Exception:
            return {"error": "Failed to get Redis stats"}
    
    # Memory-based methods
    async def _get_email_status_memory(self, email_id: str) -> Dict[str, Any]:
        """Get email status from memory."""
        for email_data in self._memory_queue:
            if email_data.get("id") == email_id:
                return email_data
        return {}
    
    async def _cancel_email_memory(self, email_id: str) -> bool:
        """Cancel email in memory."""
        try:
            for i, email_data in enumerate(self._memory_queue):
                if email_data.get("id") == email_id:
                    email_data["status"] = EmailStatus.CANCELLED.value
                    self._memory_queue[i] = email_data
                    return True
            return False
        except Exception:
            return False
    
    async def _get_emails_to_retry_memory(self) -> List[Dict[str, Any]]:
        """Get emails ready for retry from memory."""
        now = datetime.utcnow()
        retry_emails = []
        
        for email_data in self._memory_queue:
            if (email_data.get("status") == EmailStatus.RETRYING.value and
                email_data.get("next_retry_at") and
                now >= datetime.fromisoformat(email_data["next_retry_at"])):
                retry_emails.append(email_data)
        
        return retry_emails
    
    async def _get_pending_emails_memory(self, limit: int) -> List[Dict[str, Any]]:
        """Get pending emails from memory."""
        pending_emails = []
        
        for email_data in self._memory_queue:
            if email_data.get("status") == EmailStatus.PENDING.value:
                pending_emails.append(email_data)
                if len(pending_emails) >= limit:
                    break
        
        return pending_emails[:limit]
    
    async def _get_queue_stats_memory(self) -> Dict[str, Any]:
        """Get queue statistics from memory."""
        stats = {
            "queue_length": len(self._memory_queue),
            "total_tracked": len(self._memory_queue),
            "pending": 0,
            "sending": 0,
            "sent": 0,
            "failed": 0,
            "retrying": 0
        }
        
        for email_data in self._memory_queue:
            status = email_data.get("status", EmailStatus.PENDING.value)
            stats[status] = stats.get(status, 0) + 1
        
        return stats
    
    async def _update_email_status_redis(self, email_id: str, status: EmailStatus):
        """Update email status in Redis."""
        try:
            await self.redis_client.hset(
                "email_tracking",
                email_id,
                json.dumps({"status": status.value, "updated_at": datetime.utcnow().isoformat()})
            )
        except Exception:
            pass
    
    async def _update_email_status_memory(self, email_id: str, status: EmailStatus):
        """Update email status in memory."""
        try:
            for i, email_data in enumerate(self._memory_queue):
                if email_data.get("id") == email_id:
                    email_data["status"] = status.value
                    email_data["updated_at"] = datetime.utcnow().isoformat()
                    self._memory_queue[i] = email_data
                    break
        except Exception:
            pass
    
    async def _update_email_status_data(self, email_data: Dict[str, Any]):
        """Update complete email status data."""
        try:
            if self.use_redis:
                await self.redis_client.hset(
                    "email_tracking",
                    email_data["id"],
                    json.dumps(email_data)
                )
            else:
                for i, stored_data in enumerate(self._memory_queue):
                    if stored_data.get("id") == email_data["id"]:
                        self._memory_queue[i] = email_data
                        break
        except Exception:
            pass
    
    async def _remove_from_queue_redis(self, email_id: str):
        """Remove email from Redis queue."""
        try:
            # This is a simplified implementation
            # TODO: Implement proper queue removal
            pass
        except Exception:
            pass


# Factory function
def get_enhanced_email_queue_service(db: Session) -> EnhancedEmailQueueService:
    """
    Get enhanced email queue service instance.
    
    Args:
        db: Database session
        
    Returns:
        EnhancedEmailQueueService instance
    """
    return EnhancedEmailQueueService(db)
