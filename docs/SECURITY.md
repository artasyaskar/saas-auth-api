# Security Guide

## SaaS Auth API - Security Guide

This document outlines security practices, threat mitigation, and compliance guidelines for the SaaS Auth API.

## Table of Contents
- [Security Overview](#security-overview)
- [Authentication Security](#authentication-security)
- [Authorization Security](#authorization-security)
- [Data Protection](#data-protection)
- [API Security](#api-security)
- [Infrastructure Security](#infrastructure-security)
- [Compliance](#compliance)
- [Incident Response](#incident-response)
- [Security Checklist](#security-checklist)

---

## Security Overview

### Threat Model

The SaaS Auth API handles sensitive authentication and authorization data. Primary threats include:

- **Unauthorized Access**: Credential theft, session hijacking
- **Data Breaches**: Database compromises, API key leaks
- **Injection Attacks**: SQL injection, NoSQL injection
- **DoS Attacks**: Rate limiting bypass, resource exhaustion
- **Privilege Escalation**: Role manipulation, authorization bypass

### Security Principles

1. **Defense in Depth**: Multiple security layers
2. **Least Privilege**: Minimum necessary permissions
3. **Fail Secure**: Default to secure state on errors
4. **Zero Trust**: Verify every request
5. **Audit Everything**: Log all security events

---

## Authentication Security

### Password Security

**Requirements:**
- Minimum 8 characters
- Must include: uppercase, lowercase, number, special character
- Common password rejection (dictionary check)
- Maximum 128 characters (prevent DoS)
- No password reuse within last 5 passwords

**Storage:**
```python
# Uses bcrypt with salt
hashed_password = get_password_hash(password)
# bcrypt automatically handles salting
```

**Password Reset Flow:**
1. User requests reset
2. Generate cryptographically secure token (32 bytes)
3. Send token via email (expires in 1 hour)
4. Validate token on submission
5. Invalidate all existing sessions
6. Notify user of password change

### JWT Token Security

**Access Tokens:**
- Algorithm: HS256 (HMAC with SHA-256)
- Expiration: 30 minutes
- Contains: user_id, role, permissions
- Stored: Client-side (localStorage/secure cookie)

**Refresh Tokens:**
- Expiration: 7 days
- Single use (rotation)
- Stored: Database (hashed)
- Blacklist support for immediate revocation

**Token Validation:**
```python
# Always validate
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
except jwt.ExpiredSignatureError:
    raise HTTPException(status_code=401, detail="Token expired")
except jwt.InvalidTokenError:
    raise HTTPException(status_code=401, detail="Invalid token")
```

### Session Management

**Best Practices:**
- Short-lived access tokens
- Refresh token rotation
- Session binding to IP/User-Agent
- Concurrent session limits per user
- Automatic timeout after inactivity

**Logout Handling:**
```python
# Add tokens to blacklist
blacklist_service.blacklist_token(token, expires_at)
# Clear client storage
# Invalidate refresh token
```

---

## Authorization Security

### Role-Based Access Control (RBAC)

**Roles:**
- `user`: Standard user access
- `moderator`: Content moderation access
- `admin`: Full system access

**Permission Checks:**
```python
# Endpoint level protection
async def admin_only_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return {"data": "sensitive"}
```

**Resource-Level Access:**
```python
# Users can only access their own resources
if resource.user_id != current_user.id and current_user.role != UserRole.ADMIN:
    raise HTTPException(status_code=403, detail="Access denied")
```

### API Key Security

**Generation:**
- Cryptographically random 32-byte tokens
- Prefix: `sk_` for secret keys
- Format: `sk_[a-zA-Z0-9]{32}`

**Storage:**
- Hash API keys using SHA-256
- Store only hash in database
- Never log full API keys

**Scopes:**
- `read`: Read-only access
- `write`: Read and write
- `admin`: Administrative operations

**Rotation:**
- Automatic rotation every 90 days recommended
- Support for manual rotation
- Grace period during transition

---

## Data Protection

### Encryption at Rest

**Database:**
- PostgreSQL encryption (TDE if available)
- Sensitive fields encrypted (PII)
- Automatic backup encryption

**Configuration:**
```yaml
# docker-compose.yml for PostgreSQL
services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Encryption in Transit

**TLS Requirements:**
- Minimum TLS 1.2
- Strong cipher suites only
- HSTS headers enabled
- Certificate pinning (optional)

**Nginx Configuration:**
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### PII Handling

**Data Classification:**
- **High Risk**: Passwords, SSN, financial data
- **Medium Risk**: Email, phone, address
- **Low Risk**: Username, preferences

**PII Protection:**
- Mask in logs: `j***@example.com`
- Encrypt in database
- Anonymize in analytics
- GDPR right to erasure support

### Data Retention

**Policy:**
- Usage logs: 1 year
- Audit logs: 3 years
- Deleted accounts: 30 days grace period
- Password reset tokens: 1 hour
- Session tokens: Duration of session

---

## API Security

### Input Validation

**Validation Layers:**
1. Pydantic models (type checking)
2. Custom validators (business logic)
3. Database constraints (integrity)

**Example:**
```python
from pydantic import BaseModel, EmailStr, Field, validator

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain number')
        return v
```

### SQL Injection Prevention

**Safe Practices:**
```python
# Use ORM (SQLAlchemy) - parameterized queries
user = db.query(User).filter(User.id == user_id).first()

# Never use raw SQL with string formatting
# DANGEROUS: db.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

### Rate Limiting

**Implementation:**
```python
from app.core.rate_limit import RateLimiter

@router.get("/endpoint")
async def endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    rate_limiter = RateLimiter()
    if not rate_limiter.check_rate_limit(current_user.id, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    return {"data": "success"}
```

**Limits:**
- Authentication: 5 attempts/minute
- API endpoints: 60 requests/minute
- Admin endpoints: 30 requests/minute
- Burst allowance: 10 requests

### CORS Configuration

**Secure CORS:**
```python
# Only allow specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600
)
```

---

## Infrastructure Security

### Container Security

**Docker Best Practices:**
```dockerfile
# Use minimal base image
FROM python:3.11-slim

# Run as non-root user
RUN useradd -m appuser
USER appuser

# No secrets in environment
# Use secrets management
COPY --chown=appuser . /app

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1
```

### Network Security

**Firewall Rules:**
- Block all ports except 80, 443, 22 (SSH)
- Internal services not exposed
- Database accessible only from app network
- Redis accessible only from app network

**Security Groups:**
```hcl
# Terraform example
resource "aws_security_group" "app" {
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
```

### Secrets Management

**Environment Variables:**
```bash
# .env file (not in git!)
SECRET_KEY=<generate-with-openssl>
DATABASE_URL=postgresql://...:...@localhost/db
REDIS_URL=redis://localhost:6379/0
```

**Production Secrets:**
- Use AWS Secrets Manager / HashiCorp Vault
- Rotate regularly
- Never commit to git
- Encrypt at rest

**Generating Secrets:**
```bash
# Generate secure random key
openssl rand -base64 32

# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Compliance

### GDPR Compliance

**User Rights:**
1. **Right to Access**: Export all user data
2. **Right to Rectification**: Update user information
3. **Right to Erasure**: Delete user account and data
4. **Right to Portability**: Export in machine-readable format
5. **Right to Object**: Opt-out of processing

**Implementation:**
```python
# Data export endpoint
@router.get("/export/data")
async def export_user_data(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    export_service = DataExportService(db)
    return export_service.export_user_data(current_user.id)

# Account deletion
@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Soft delete with 30-day grace period
    current_user.is_active = False
    current_user.deletion_requested_at = datetime.utcnow()
    db.commit()
```

### SOC 2 Compliance

**Controls:**
- Access controls (AC)
- Change management (CM)
- Monitoring and logging (ML)
- Incident response (IR)
- Data encryption (DE)

### PCI DSS (if handling payments)

**Requirements:**
- Network segmentation
- Encrypted transmission
- No storage of CVV
- Regular security scans
- Access logging

---

## Incident Response

### Security Incident Types

| Severity | Examples | Response Time |
|----------|----------|---------------|
| Critical | Data breach, RCE | 1 hour |
| High | API key leak, unauthorized admin access | 4 hours |
| Medium | Rate limit bypass, XSS | 24 hours |
| Low | Misconfiguration, info disclosure | 7 days |

### Response Playbook

**1. Detection**
- Automated alerts (failed logins, rate limit exceeded)
- Security monitoring tools
- User reports

**2. Containment**
- Disable affected accounts
- Revoke compromised tokens
- Block suspicious IPs

**3. Investigation**
- Review audit logs
- Analyze access patterns
- Identify root cause

**4. Remediation**
- Fix vulnerability
- Rotate exposed secrets
- Update security measures

**5. Communication**
- Internal team notification
- Customer notification (if required)
- Public disclosure (if required)

**6. Post-Incident**
- Document lessons learned
- Update security measures
- Improve monitoring

### Emergency Contacts

```
Security Team: security@company.com
On-Call: +1-xxx-xxx-xxxx
Slack: #security-incidents
```

---

## Security Checklist

### Pre-Deployment

- [ ] All dependencies scanned for vulnerabilities
- [ ] No hardcoded secrets in code
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] HTTPS enforced
- [ ] Database encrypted
- [ ] Backups encrypted
- [ ] Logging configured
- [ ] Monitoring alerts set up

### Runtime

- [ ] Regular dependency updates
- [ ] Security patch management
- [ ] Access log review (weekly)
- [ ] Failed login monitoring
- [ ] API key rotation (quarterly)
- [ ] SSL certificate renewal
- [ ] Database backup testing
- [ ] Disaster recovery drills

### Periodic Audits

- [ ] Penetration testing (annual)
- [ ] Code security review
- [ ] Infrastructure audit
- [ ] Compliance review
- [ ] Third-party security assessment

---

## Security Tools

### Recommended Tools

**Static Analysis:**
- Bandit (Python security linter)
- Semgrep (pattern matching)
- Snyk (dependency scanning)

**Dynamic Testing:**
- OWASP ZAP (web scanner)
- Burp Suite (penetration testing)

**Monitoring:**
- Sentry (error tracking)
- Datadog (APM and security)
- ELK Stack (log analysis)

### Usage

```bash
# Run security checks
make security-check

# Dependency scan
safety check

# Code scan
bandit -r app/

# Full security audit
python scripts/security_audit.py
```

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [SANS Security Resources](https://www.sans.org/security-resources/)

## Contact

Security Team: security@company.com
Bug Bounty: [HackerOne/bugcrowd program]
Responsible Disclosure: security@company.com

---

**Last Updated:** 2024-01-20  
**Version:** 1.0  
**Classification:** Internal
