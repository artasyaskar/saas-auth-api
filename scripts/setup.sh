#!/bin/bash
# SaaS Auth API - Setup Script
# This script sets up the development environment

set -e

echo "=========================================="
echo "SaaS Auth API - Development Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    echo "Checking Python installation..."
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        REQUIRED_VERSION="3.11"
        
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then 
            print_status "Python $PYTHON_VERSION is installed"
        else
            print_error "Python 3.11 or higher is required (found $PYTHON_VERSION)"
            exit 1
        fi
    else
        print_error "Python 3 is not installed"
        exit 1
    fi
}

# Check PostgreSQL
check_postgres() {
    echo "Checking PostgreSQL..."
    
    if command_exists psql; then
        POSTGRES_VERSION=$(psql --version | awk '{print $3}')
        print_status "PostgreSQL $POSTGRES_VERSION is installed"
    else
        print_warning "PostgreSQL is not installed. Please install PostgreSQL 14+"
        echo "  Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
        echo "  macOS: brew install postgresql"
        echo "  Or use Docker: docker run -d -p 5432:5432 postgres:14"
    fi
}

# Check Redis
check_redis() {
    echo "Checking Redis..."
    
    if command_exists redis-cli; then
        REDIS_VERSION=$(redis-cli --version | awk '{print $2}')
        print_status "Redis is installed"
    else
        print_warning "Redis is not installed. Please install Redis 6+"
        echo "  Ubuntu/Debian: sudo apt-get install redis-server"
        echo "  macOS: brew install redis"
        echo "  Or use Docker: docker run -d -p 6379:6379 redis:6"
    fi
}

# Create virtual environment
setup_venv() {
    echo "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Recreate? (y/N): " recreate
        if [[ $recreate =~ ^[Yy]$ ]]; then
            rm -rf venv
            python3 -m venv venv
            print_status "Virtual environment recreated"
        fi
    else
        python3 -m venv venv
        print_status "Virtual environment created"
    fi
}

# Install dependencies
install_dependencies() {
    echo "Installing dependencies..."
    
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_status "Production dependencies installed"
    fi
    
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
        print_status "Development dependencies installed"
    fi
}

# Create environment file
setup_env() {
    echo "Setting up environment configuration..."
    
    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Overwrite? (y/N): " overwrite
        if [[ ! $overwrite =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    # Generate secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    cat > .env << EOF
# Application
APP_NAME=SaaS Auth API
APP_ENV=development
DEBUG=true
APP_VERSION=1.0.0
APP_PORT=8000

# Security
SECRET_KEY=$SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/saas_auth
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=20

# Email (development)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=dev@localhost.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_MONTHLY_QUOTA=1000

# Logging
LOG_LEVEL=DEBUG
EOF
    
    print_status "Environment file created (.env)"
}

# Setup database
setup_database() {
    echo "Setting up database..."
    
    source venv/bin/activate
    
    # Check if database exists
    if command_exists psql; then
        if psql -lqt | cut -d \| -f 1 | grep -qw saas_auth; then
            print_warning "Database 'saas_auth' already exists"
            read -p "Recreate? (y/N): " recreate_db
            if [[ $recreate_db =~ ^[Yy]$ ]]; then
                dropdb saas_auth
                createdb saas_auth
                print_status "Database recreated"
            fi
        else
            createdb saas_auth
            print_status "Database 'saas_auth' created"
        fi
        
        # Run migrations
        if [ -d "alembic" ]; then
            alembic upgrade head
            print_status "Database migrations applied"
        fi
    else
        print_warning "Cannot setup database - PostgreSQL not available"
    fi
}

# Setup pre-commit hooks
setup_precommit() {
    echo "Setting up pre-commit hooks..."
    
    if [ -f ".pre-commit-config.yaml" ]; then
        if command_exists pre-commit; then
            pre-commit install
            print_status "Pre-commit hooks installed"
        else
            print_warning "pre-commit not installed. Install with: pip install pre-commit"
        fi
    fi
}

# Create necessary directories
create_directories() {
    echo "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p uploads
    mkdir -p backups
    mkdir -p tmp
    
    print_status "Directories created"
}

# Run tests
run_tests() {
    echo "Running tests..."
    
    source venv/bin/activate
    
    if pytest --version >/dev/null 2>&1; then
        pytest -xvs tests/ -k "test_register" || true
        print_status "Quick tests completed"
    else
        print_warning "pytest not available"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "=========================================="
    echo "Setup Complete!"
    echo "=========================================="
    echo ""
    echo "To start development:"
    echo "  1. Activate virtual environment:"
    echo "     source venv/bin/activate"
    echo ""
    echo "  2. Start development server:"
    echo "     make dev"
    echo "     or: uvicorn app.main:app --reload --port 8000"
    echo ""
    echo "  3. Run tests:"
    echo "     make test"
    echo "     or: pytest"
    echo ""
    echo "  4. API documentation:"
    echo "     http://localhost:8000/docs"
    echo "     http://localhost:8000/redoc"
    echo ""
    echo "Useful commands:"
    echo "  make install    - Install dependencies"
    echo "  make test       - Run tests"
    echo "  make lint       - Run linters"
    echo "  make format     - Format code"
    echo "  make migrate    - Run database migrations"
    echo ""
}

# Main setup function
main() {
    check_python
    check_postgres
    check_redis
    setup_venv
    install_dependencies
    setup_env
    create_directories
    setup_database
    setup_precommit
    run_tests
    print_summary
}

# Run main function
main
