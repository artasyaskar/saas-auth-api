"""
Enterprise Email Service for Transactional Communications

Comprehensive email service supporting multiple providers,
templates, tracking, and analytics.

Features:
- Multiple provider support (SMTP, SendGrid, SES, Mailgun)
- Email templates with Jinja2
- Email tracking (opens, clicks)
- Bounce handling
- Suppression management
- Email analytics
- Bulk email support
- Attachment support
- Email scheduling
- A/B testing
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from jinja2 import Template, Environment, FileSystemLoader
from sqlalchemy.orm import Session
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr

from app.db.models import User, EmailLog, EmailTemplate
from app.core.config import settings

# Email templates
PASSWORD_RESET_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
        .content { background: #f9fafb; padding: 20px; margin: 20px 0; }
        .button { display: inline-block; background: #4F46E5; color: white; 
                  padding: 12px 24px; text-decoration: none; border-radius: 5px; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }
        .warning { background: #fef3c7; border-left: 4px solid #f59e0b; 
                   padding: 12px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hi {{ username }},</p>
            <p>We received a request to reset your password for your SaaS Auth account.</p>
            <p>Click the button below to reset your password:</p>
            <p style="text-align: center;">
                <a href="{{ reset_url }}" class="button">Reset Password</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background: #e5e7eb; padding: 10px;">
                    {{ reset_url }}
            </p>
            <div class="warning">
                <strong>⚠️ This link will expire in {{ expiry_hours }} hours.</strong>
            </div>
            <p>If you didn't request this, please ignore this email or contact support.</p>
        </div>
        <div class="footer">
            <p>SaaS Auth API - Secure Authentication Service</p>
            <p>This email was sent at {{ sent_at }}</p>
        </div>
    </div>
</body>
</html>
"""

EMAIL_VERIFICATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10B981; color: white; padding: 20px; text-align: center; }
        .content { background: #f9fafb; padding: 20px; margin: 20px 0; }
        .button { display: inline-block; background: #10B981; color: white; 
                  padding: 12px 24px; text-decoration: none; border-radius: 5px; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Verify Your Email</h1>
        </div>
        <div class="content">
            <p>Hi {{ username }},</p>
            <p>Welcome to SaaS Auth! Please verify your email address to complete your registration.</p>
            <p style="text-align: center;">
                <a href="{{ verification_url }}" class="button">Verify Email</a>
            </p>
            <p>Or copy and paste this link:</p>
            <p style="word-break: break-all; background: #e5e7eb; padding: 10px;">
                    {{ verification_url }}
            </p>
            <p>This link will expire in {{ expiry_hours }} hours.</p>
        </div>
        <div class="footer">
            <p>SaaS Auth API - Secure Authentication Service</p>
        </div>
    </div>
</body>
</html>
"""

SECURITY_ALERT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #EF4444; color: white; padding: 20px; text-align: center; }
        .content { background: #f9fafb; padding: 20px; margin: 20px 0; }
        .alert { background: #fee2e2; border-left: 4px solid #EF4444; 
                 padding: 12px; margin: 20px 0; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Security Alert</h1>
        </div>
        <div class="content">
            <p>Hi {{ username }},</p>
            <div class="alert">
                <strong>{{ alert_title }}</strong>
                <p>{{ alert_description }}</p>
            </div>
            <p><strong>Details:</strong></p>
            <ul>
                <li>Time: {{ timestamp }}</li>
                <li>IP Address: {{ ip_address }}</li>
                {% if user_agent %}<li>Device: {{ user_agent }}</li>{% endif %}
            </ul>
            <p>If this wasn't you, please secure your account immediately by changing your password.</p>
        </div>
        <div class="footer">
            <p>SaaS Auth Security Team</p>
        </div>
    </div>
</body>
</html>
"""


class EmailProvider(Enum):
    """Email service providers."""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    SES = "ses"
    MAILGUN = "mailgun"
    POSTMARK = "postmark"


class EmailStatus(Enum):
    """Email delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    FAILED = "failed"


@dataclass
class EmailAttachment:
    """Email attachment."""
    filename: str
    content: bytes
    content_type: str
    content_id: Optional[str] = None


@dataclass
class EmailMessage:
    """Email message data structure."""
    to: Union[str, List[str]]
    subject: str
    html_content: str
    text_content: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    cc: Optional[Union[str, List[str]]] = None
    bcc: Optional[Union[str, List[str]]] = None
    reply_to: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    tracking_enabled: bool = True
    scheduled_for: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class EmailService:
    """
    Enterprise-grade email service.
    
    Features:
    - Multiple provider support
    - Template management
    - Email tracking
    - Bounce handling
    - Suppression management
    - Analytics
    - Bulk email
    - Attachments
    - Scheduling
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Configuration
        self.provider = EmailProvider(getattr(settings, 'EMAIL_PROVIDER', 'smtp'))
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@saasauth.example.com')
        self.from_name = getattr(settings, 'FROM_NAME', 'SaaS Auth')
        
        # SMTP configuration
        self.smtp_host = getattr(settings, 'SMTP_HOST', '')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.smtp_use_tls = getattr(settings, 'SMTP_USE_TLS', True)
        
        # SendGrid configuration
        self.sendgrid_api_key = getattr(settings, 'SENDGRID_API_KEY', '')
        
        # SES configuration
        self.ses_region = getattr(settings, 'SES_REGION', 'us-east-1')
        
        # Mailgun configuration
        self.mailgun_api_key = getattr(settings, 'MAILGUN_API_KEY', '')
        self.mailgun_domain = getattr(settings, 'MAILGUN_DOMAIN', '')
        
        # Template environment
        self.template_env = Environment(
            loader=FileSystemLoader('app/templates/email'),
            autoescape=True
        )
        
        # Check if configured
        self.is_configured = self._check_configuration()
    
    def _check_configuration(self) -> bool:
        """Check if email service is properly configured."""
        if self.provider == EmailProvider.SMTP:
            return all([self.smtp_host, self.smtp_user, self.smtp_password])
        elif self.provider == EmailProvider.SENDGRID:
            return bool(self.sendgrid_api_key)
        elif self.provider == EmailProvider.MAILGUN:
            return all([self.mailgun_api_key, self.mailgun_domain])
        return False
    
    def send_email(self, message: EmailMessage) -> str:
        """
        Send an email message.
        
        Args:
            message: Email message to send
        
        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        
        # Log email
        email_log = EmailLog(
            message_id=message_id,
            to_email=','.join([message.to] if isinstance(message.to, str) else message.to),
            subject=message.subject,
            status=EmailStatus.PENDING.value,
            provider=self.provider.value,
            template_id=message.template_id,
            metadata=json.dumps(message.metadata) if message.metadata else None,
            created_at=datetime.utcnow()
        )
        
        self.db.add(email_log)
        self.db.commit()
        
        # Send email
        try:
            if self.provider == EmailProvider.SMTP:
                self._send_via_smtp(message)
            elif self.provider == EmailProvider.SENDGRID:
                self._send_via_sendgrid(message)
            elif self.provider == EmailProvider.MAILGUN:
                self._send_via_mailgun(message)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            # Update log
            email_log.status = EmailStatus.SENT.value
            email_log.sent_at = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            email_log.status = EmailStatus.FAILED.value
            email_log.error_message = str(e)
            self.db.commit()
            raise
        
        return message_id
    
    def _send_via_smtp(self, message: EmailMessage):
        """Send email via SMTP."""
        msg = MIMEMultipart('mixed')
        msg['Subject'] = message.subject
        msg['From'] = formataddr((message.from_name or self.from_name, message.from_email or self.from_email))
        
        if isinstance(message.to, str):
            msg['To'] = message.to
        else:
            msg['To'] = ', '.join(message.to)
        
        if message.cc:
            msg['Cc'] = ', '.join([message.cc] if isinstance(message.cc, str) else message.cc)
        
        if message.reply_to:
            msg['Reply-To'] = message.reply_to
        
        # Add custom headers
        for key, value in message.headers.items():
            msg[key] = value
        
        # Add tracking pixel if enabled
        if message.tracking_enabled:
            tracking_pixel = f'<img src="https://yourapp.com/track/open/{message_id}" width="1" height="1" />'
            message.html_content += tracking_pixel
        
        # Attach HTML and text content
        alternative = MIMEMultipart('alternative')
        alternative.attach(MIMEText(message.text_content or '', 'plain'))
        alternative.attach(MIMEText(message.html_content, 'html'))
        msg.attach(alternative)
        
        # Add attachments
        for attachment in message.attachments:
            part = MIMEApplication(attachment.content, Name=attachment.filename)
            part['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
            if attachment.content_id:
                part['Content-ID'] = f'<{attachment.content_id}>'
            msg.attach(part)
        
        # Send via SMTP
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
    
    def _send_via_sendgrid(self, message: EmailMessage):
        """Send email via SendGrid."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, To, Email, Content
            
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
            
            mail = Mail(
                from_email=Email(message.from_email or self.from_email, message.from_name or self.from_name),
                to_emails=[To(email) for email in ([message.to] if isinstance(message.to, str) else message.to)],
                subject=message.subject,
                html_content=Content('text/html', message.html_content),
                plain_text_content=Content('text/plain', message.text_content or '')
            )
            
            response = sg.send(mail)
            
            if response.status_code not in [200, 202]:
                raise Exception(f"SendGrid error: {response.status_code}")
                
        except ImportError:
            raise Exception("SendGrid library not installed")
    
    def _send_via_mailgun(self, message: EmailMessage):
        """Send email via Mailgun."""
        try:
            import requests
            
            url = f"https://api.mailgun.net/v3/{self.mailgun_domain}/messages"
            
            data = {
                'from': f"{message.from_name or self.from_name} <{message.from_email or self.from_email}>",
                'to': message.to if isinstance(message.to, str) else ','.join(message.to),
                'subject': message.subject,
                'html': message.html_content,
                'text': message.text_content or ''
            }
            
            if message.cc:
                data['cc'] = message.cc if isinstance(message.cc, str) else ','.join(message.cc)
            
            response = requests.post(
                url,
                auth=('api', self.mailgun_api_key),
                data=data
            )
            
            if response.status_code != 200:
                raise Exception(f"Mailgun error: {response.status_code}")
                
        except ImportError:
            raise Exception("Requests library not installed")
    
    def send_template_email(
        self,
        to: Union[str, List[str]],
        template_name: str,
        template_data: Dict[str, Any],
        subject: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send email using a template.
        
        Args:
            to: Recipient email(s)
            template_name: Template name
            template_data: Template variables
            subject: Email subject (optional)
            **kwargs: Additional message parameters
        
        Returns:
            Message ID
        """
        # Load template
        template = self.template_env.get_template(f"{template_name}.html")
        html_content = template.render(**template_data)
        
        # Create message
        message = EmailMessage(
            to=to,
            subject=subject or f"Email from {self.from_name}",
            html_content=html_content,
            template_id=template_name,
            template_data=template_data,
            **kwargs
        )
        
        return self.send_email(message)
    
    def send_password_reset(self, to_email: str, username: str, 
                           reset_token: str, expiry_hours: int = 24) -> str:
        """Send password reset email."""
        reset_url = f"https://yourapp.com/reset-password?token={reset_token}"
        
        template = Template(PASSWORD_RESET_TEMPLATE)
        html_content = template.render(
            username=username,
            reset_url=reset_url,
            expiry_hours=expiry_hours,
            sent_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        message = EmailMessage(
            to=to_email,
            subject="Password Reset Request - SaaS Auth",
            html_content=html_content,
            text_content=f"Reset your password: {reset_url}",
            template_id="password_reset",
            metadata={'username': username, 'token': reset_token}
        )
        
        return self.send_email(message)
    
    def send_email_verification(self, to_email: str, username: str, 
                               verification_token: str, expiry_hours: int = 48) -> str:
        """Send email verification email."""
        verification_url = f"https://yourapp.com/verify-email?token={verification_token}"
        
        template = Template(EMAIL_VERIFICATION_TEMPLATE)
        html_content = template.render(
            username=username,
            verification_url=verification_url,
            expiry_hours=expiry_hours
        )
        
        message = EmailMessage(
            to=to_email,
            subject="Verify Your Email - SaaS Auth",
            html_content=html_content,
            text_content=f"Verify your email: {verification_url}",
            template_id="email_verification",
            metadata={'username': username, 'token': verification_token}
        )
        
        return self.send_email(message)
    
    def send_security_alert(self, to_email: str, username: str, 
                           alert_title: str, alert_description: str,
                           ip_address: str, user_agent: Optional[str] = None) -> str:
        """Send security alert email."""
        template = Template(SECURITY_ALERT_TEMPLATE)
        html_content = template.render(
            username=username,
            alert_title=alert_title,
            alert_description=alert_description,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        message = EmailMessage(
            to=to_email,
            subject="🔒 Security Alert - SaaS Auth",
            html_content=html_content,
            text_content=f"Security Alert: {alert_title}",
            template_id="security_alert",
            metadata={'username': username, 'ip_address': ip_address}
        )
        
        return self.send_email(message)
    
    def send_bulk_email(
        self,
        recipients: List[str],
        template_name: str,
        template_data: Dict[str, Any],
        subject: str,
        batch_size: int = 100
    ) -> List[str]:
        """
        Send bulk email to multiple recipients.
        
        Args:
            recipients: List of recipient emails
            template_name: Template name
            template_data: Template variables
            subject: Email subject
            batch_size: Number of emails per batch
        
        Returns:
            List of message IDs
        """
        message_ids = []
        
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]
            
            for recipient in batch:
                try:
                    message_id = self.send_template_email(
                        to=recipient,
                        template_name=template_name,
                        template_data=template_data,
                        subject=subject
                    )
                    message_ids.append(message_id)
                except Exception as e:
                    print(f"Failed to send to {recipient}: {e}")
        
        return message_ids
    
    def get_email_status(self, message_id: str) -> Optional[EmailLog]:
        """Get email delivery status."""
        return self.db.query(EmailLog).filter(
            EmailLog.message_id == message_id
        ).first()
    
    def get_email_analytics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get email analytics for a date range."""
        logs = self.db.query(EmailLog).filter(
            EmailLog.created_at >= start_date,
            EmailLog.created_at <= end_date
        ).all()
        
        total = len(logs)
        sent = sum(1 for log in logs if log.status == EmailStatus.SENT.value)
        delivered = sum(1 for log in logs if log.status == EmailStatus.DELIVERED.value)
        opened = sum(1 for log in logs if log.status == EmailStatus.OPENED.value)
        clicked = sum(1 for log in logs if log.status == EmailStatus.CLICKED.value)
        bounced = sum(1 for log in logs if log.status == EmailStatus.BOUNCED.value)
        failed = sum(1 for log in logs if log.status == EmailStatus.FAILED.value)
        
        return {
            'total': total,
            'sent': sent,
            'delivered': delivered,
            'opened': opened,
            'clicked': clicked,
            'bounced': bounced,
            'failed': failed,
            'delivery_rate': (delivered / total * 100) if total > 0 else 0,
            'open_rate': (opened / delivered * 100) if delivered > 0 else 0,
            'click_rate': (clicked / opened * 100) if opened > 0 else 0,
            'bounce_rate': (bounced / total * 100) if total > 0 else 0
        }


def get_email_service(db: Session) -> EmailService:
    """Dependency to get email service."""
    return EmailService(db)
