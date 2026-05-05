# Database Migration Guide

This guide covers the complete database migration workflow for the SaaS Auth API using Alembic.

## Overview

Database migrations allow you to:
- Version control your database schema
- Apply incremental changes safely
- Rollback to previous versions
- Collaborate with team members on schema changes

## Migration Commands

### Create a New Migration

When you modify SQLAlchemy models, generate a new migration:

```bash
python scripts/db_migrate.py create -m "add user profile fields"
```

For manual migration (empty):
```bash
python scripts/db_migrate.py create -m "custom migration" --no-autogenerate
```

### Apply Migrations

Run all pending migrations:
```bash
python scripts/db_migrate.py upgrade
```

Run to specific version:
```bash
python scripts/db_migrate.py upgrade <revision>
```

### View Status

Current database version:
```bash
python scripts/db_migrate.py current
```

Migration history:
```bash
python scripts/db_migrate.py history
```

Pending migrations:
```bash
python scripts/db_migrate.py pending
```

### Rollback Migrations

Downgrade one version:
```bash
python scripts/db_migrate.py downgrade -1
```

Downgrade to specific version:
```bash
python scripts/db_migrate.py downgrade <revision>
```

Downgrade to beginning:
```bash
python scripts/db_migrate.py downgrade base
```

### Other Commands

Verify database is current:
```bash
python scripts/db_migrate.py verify
```

Generate SQL only (dry run):
```bash
python scripts/db_migrate.py sql
```

## Migration File Structure

Each migration file contains:
- `revision`: Unique identifier
- `down_revision`: Previous migration
- `upgrade()`: Apply changes
- `downgrade()`: Revert changes

Example:
```python
revision = 'abc123'
down_revision = 'xyz789'

def upgrade():
    op.add_column('users', sa.Column('profile', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('users', 'profile')
```

## Best Practices

### 1. Always Review Auto-Generated Migrations

Alembic auto-detects model changes but may miss:
- Column constraints
- Custom indexes
- Data migrations

Always review generated migrations before applying.

### 2. Keep Migrations Small

- One logical change per migration
- Easier to debug and rollback
- Faster to apply

### 3. Test Migrations

Test both upgrade and downgrade:
```bash
python scripts/db_migrate.py upgrade
python scripts/db_migrate.py downgrade -1
python scripts/db_migrate.py upgrade
```

### 4. Don't Modify Applied Migrations

Once a migration is applied to production, never modify it.
Create a new migration to fix issues.

### 5. Include Data Migrations When Needed

```python
def upgrade():
    # Schema change
    op.add_column('users', sa.Column('status', sa.String()))
    
    # Data migration
    op.execute("UPDATE users SET status = 'active'")
```

## Environment-Specific Migrations

### Development
```bash
# Auto-generate from models
python scripts/db_migrate.py create -m "feature x"
python scripts/db_migrate.py upgrade
```

### Staging
```bash
# Verify and apply
python scripts/db_migrate.py verify
python scripts/db_migrate.py upgrade
```

### Production
```bash
# 1. Backup database first!
# 2. Generate SQL for review
python scripts/db_migrate.py sql

# 3. Apply in maintenance window
python scripts/db_migrate.py upgrade

# 4. Verify
python scripts/db_migrate.py verify
```

## Troubleshooting

### Migration Conflict

When two developers create migrations:
```bash
# Merge by creating new migration
python scripts/db_migrate.py create -m "merge heads" --no-autogenerate
```

### Failed Migration

Check error in migration output:
```bash
# View specific migration
alembic -c alembic.ini show <revision>
```

### Database Out of Sync

Force stamp to current (careful!):
```bash
python scripts/db_migrate.py stamp head
```

### Lock Issues

If migration is stuck:
```sql
-- Check for locks
SELECT * FROM pg_locks;

-- Kill blocking process if needed
SELECT pg_terminate_backend(<pid>);
```

## Migration Naming Convention

Use descriptive names:
- `add_user_profile_table`
- `create_oauth_accounts_index`
- `update_webhook_payload_column`

Avoid:
- `fix_stuff`
- `migration_1`
- `asdf`

## CI/CD Integration

### Pre-deployment
```yaml
- name: Check migrations
  run: python scripts/db_migrate.py verify

- name: Generate migration SQL
  run: python scripts/db_migrate.py sql > migration.sql
```

### Deployment
```yaml
- name: Run migrations
  run: python scripts/db_migrate.py upgrade
```

## Migration Safety Checklist

Before applying to production:

- [ ] Database backup created
- [ ] Migration reviewed for errors
- [ ] Rollback tested
- [ ] Maintenance window scheduled
- [ ] Rollback plan documented
- [ ] Team notified
- [ ] Monitoring in place

## Common Operations

### Add Column
```python
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20)))

def downgrade():
    op.drop_column('users', 'phone')
```

### Create Table
```python
def upgrade():
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )

def downgrade():
    op.drop_table('audit_logs')
```

### Create Index
```python
def upgrade():
    op.create_index('idx_user_email', 'users', ['email'])

def downgrade():
    op.drop_index('idx_user_email', 'users')
```

### Alter Column
```python
def upgrade():
    op.alter_column('users', 'email',
                    existing_type=sa.String(100),
                    type_=sa.String(255))

def downgrade():
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    type_=sa.String(100))
```

## Need Help?

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- Check migration: `alembic -c alembic.ini history --verbose`
- View SQL: `python scripts/db_migrate.py sql`
