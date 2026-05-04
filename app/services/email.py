"""
Email service for sending transactional emails.
Supports SMTP and email service providers.
"""
import os
from typing import Optional
from datetime import datetime
from jinja2 import Template

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


class EmailService:
    """Service for sending transactional emails."""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@saasauth.example.com")
        self.from_name = os.getenv("FROM_NAME", "SaaS Auth")
        
        # Check if email is configured
        self.is_configured = all([self.smtp_host, self.smtp_user, self.smtp_password])
    
    def _send_email(self, to_email: str, subject: str, html_content: str, 
                   text_content: Optional[str] = None) -> bool:
        """Send an email using SMTP."""
        if not self.is_configured:
            # Log that email would be sent (for development)
            print(f"[EMAIL MOCK] To: {to_email}, Subject: {subject}")
            print(f"[EMAIL MOCK] Content: {html_content[:200]}...")
            return True
        
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Attach plain text if provided
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_password_reset(self, to_email: str, username: str, 
                           reset_token: str, expiry_hours: int = 24) -> bool:
        """Send password reset email."""
        reset_url = f"https://yourapp.com/reset-password?token={reset_token}"
        
        template = Template(PASSWORD_RESET_TEMPLATE)
        html_content = template.render(
            username=username,
            reset_url=reset_url,
            expiry_hours=expiry_hours,
            sent_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        return self._send_email(
            to_email=to_email,
            subject="Password Reset Request - SaaS Auth",
            html_content=html_content,
            text_content=f"Reset your password: {reset_url}"
        )
    
    def send_email_verification(self, to_email: str, username: str, 
                               verification_token: str, expiry_hours: int = 48) -> bool:
        """Send email verification email."""
        verification_url = f"https://yourapp.com/verify-email?token={verification_token}"
        
        template = Template(EMAIL_VERIFICATION_TEMPLATE)
        html_content = template.render(
            username=username,
            verification_url=verification_url,
            expiry_hours=expiry_hours
        )
        
        return self._send_email(
            to_email=to_email,
            subject="Verify Your Email - SaaS Auth",
            html_content=html_content,
            text_content=f"Verify your email: {verification_url}"
        )
    
    def send_security_alert(self, to_email: str, username: str, 
                           alert_title: str, alert_description: str,
                           ip_address: str, user_agent: Optional[str] = None) -> bool:
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
        
        return self._send_email(
            to_email=to_email,
            subject="🔒 Security Alert - SaaS Auth",
            html_content=html_content,
            text_content=f"Security Alert: {alert_title}"
        )


# Global email service instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the email service instance."""
    return email_service
