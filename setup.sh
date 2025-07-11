#!/bin/bash

# DataOps Monitoring Platform Setup Script
# This script sets up the complete DataOps Monitoring platform

set -e

echo "🚀 Setting up DataOps Monitoring Platform..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed. Please install Python 3.8+"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is required but not installed. Please install Node.js 16+"
        exit 1
    fi
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        print_warning "PostgreSQL is not installed. You'll need to install it manually or use a cloud database."
    fi
    
    # Check Redis
    if ! command -v redis-server &> /dev/null; then
        print_warning "Redis is not installed. You'll need to install it manually or use a cloud Redis instance."
    fi
    
    print_success "System requirements check completed"
}

# Setup backend
setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating environment file..."
        cp env.example .env
        print_warning "Please edit .env file with your configuration before starting the application"
    fi
    
    cd ..
    print_success "Backend setup completed"
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    cd frontend
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    cd ..
    print_success "Frontend setup completed"
}

# Setup database
setup_database() {
    print_status "Setting up database..."
    
    # Check if PostgreSQL is running
    if command -v psql &> /dev/null; then
        print_status "Creating PostgreSQL database..."
        
        # Try to create database (this might fail if PostgreSQL is not running)
        if createdb dataops_monitoring 2>/dev/null; then
            print_success "Database 'dataops_monitoring' created successfully"
        else
            print_warning "Could not create database. Please ensure PostgreSQL is running and create the database manually:"
            echo "  createdb dataops_monitoring"
        fi
    else
        print_warning "PostgreSQL not found. Please install PostgreSQL and create the database manually:"
        echo "  createdb dataops_monitoring"
    fi
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    cd backend
    source venv/bin/activate
    
    # Set default database URL if not set
    export DATABASE_URL=${DATABASE_URL:-"postgresql://localhost/dataops_monitoring"}
    
    # Initialize migrations
    flask db init 2>/dev/null || true
    
    # Run migrations
    flask db migrate -m "Initial migration"
    flask db upgrade
    
    cd ..
    print_success "Database migrations completed"
}

# Create initial admin user
create_admin_user() {
    print_status "Creating initial admin user..."
    
    cd backend
    source venv/bin/activate
    
    # Set default database URL if not set
    export DATABASE_URL=${DATABASE_URL:-"postgresql://localhost/dataops_monitoring"}
    
    # Create admin user using Flask shell
    python3 -c "
from app import create_app, db
from app.models.user import User
from app.models.organization import Organization
from flask_bcrypt import Bcrypt

app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    # Create organization if it doesn't exist
    org = Organization.query.first()
    if not org:
        org = Organization(
            name='Default Organization',
            plan='professional',
            max_pipelines=50,
            max_users=10
        )
        db.session.add(org)
        db.session.commit()
    
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(email='admin@dataops.com').first()
    if not admin:
        admin = User(
            email='admin@dataops.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            organization_id=org.id,
            is_active=True
        )
        admin.password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: admin@dataops.com / admin123')
    else:
        print('Admin user already exists')
"
    
    cd ..
    print_success "Initial admin user created"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    print_status "Starting backend API server..."
    cd backend
    source venv/bin/activate
    export DATABASE_URL=${DATABASE_URL:-"postgresql://localhost/dataops_monitoring"}
    export FLASK_APP=run.py
    export FLASK_ENV=development
    
    # Start backend in background
    nohup flask run --host=0.0.0.0 --port=5000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    
    cd ..
    
    print_status "Starting Celery worker..."
    cd backend
    source venv/bin/activate
    export DATABASE_URL=${DATABASE_URL:-"postgresql://localhost/dataops_monitoring"}
    
    # Start Celery worker in background
    nohup celery -A app.celery worker --loglevel=info > ../celery.log 2>&1 &
    CELERY_PID=$!
    echo $CELERY_PID > ../celery.pid
    
    cd ..
    
    print_status "Starting frontend development server..."
    cd frontend
    
    # Start frontend in background
    nohup npm start > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    cd ..
    
    print_success "All services started"
    print_status "Backend API: http://localhost:5000"
    print_status "Frontend: http://localhost:3000"
    print_status "Admin login: admin@dataops.com / admin123"
}

# Stop services
stop_services() {
    print_status "Stopping services..."
    
    # Stop backend
    if [ -f "backend.pid" ]; then
        kill $(cat backend.pid) 2>/dev/null || true
        rm backend.pid
    fi
    
    # Stop Celery
    if [ -f "celery.pid" ]; then
        kill $(cat celery.pid) 2>/dev/null || true
        rm celery.pid
    fi
    
    # Stop frontend
    if [ -f "frontend.pid" ]; then
        kill $(cat frontend.pid) 2>/dev/null || true
        rm frontend.pid
    fi
    
    print_success "All services stopped"
}

# Show status
show_status() {
    print_status "Service Status:"
    
    if [ -f "backend.pid" ] && kill -0 $(cat backend.pid) 2>/dev/null; then
        print_success "Backend API: Running (PID: $(cat backend.pid))"
    else
        print_error "Backend API: Not running"
    fi
    
    if [ -f "celery.pid" ] && kill -0 $(cat celery.pid) 2>/dev/null; then
        print_success "Celery Worker: Running (PID: $(cat celery.pid))"
    else
        print_error "Celery Worker: Not running"
    fi
    
    if [ -f "frontend.pid" ] && kill -0 $(cat frontend.pid) 2>/dev/null; then
        print_success "Frontend: Running (PID: $(cat frontend.pid))"
    else
        print_error "Frontend: Not running"
    fi
}

# Show logs
show_logs() {
    local service=$1
    
    case $service in
        "backend")
            if [ -f "backend.log" ]; then
                tail -f backend.log
            else
                print_error "Backend log file not found"
            fi
            ;;
        "celery")
            if [ -f "celery.log" ]; then
                tail -f celery.log
            else
                print_error "Celery log file not found"
            fi
            ;;
        "frontend")
            if [ -f "frontend.log" ]; then
                tail -f frontend.log
            else
                print_error "Frontend log file not found"
            fi
            ;;
        *)
            print_error "Usage: $0 logs [backend|celery|frontend]"
            exit 1
            ;;
    esac
}

# Main script logic
case "${1:-setup}" in
    "setup")
        check_requirements
        setup_backend
        setup_frontend
        setup_database
        run_migrations
        create_admin_user
        print_success "Setup completed successfully!"
        print_status "To start the services, run: $0 start"
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        start_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs $2
        ;;
    "migrate")
        run_migrations
        ;;
    "admin")
        create_admin_user
        ;;
    "help"|"-h"|"--help")
        echo "DataOps Monitoring Platform Setup Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup     - Complete setup (default)"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show service status"
        echo "  logs      - Show logs (backend|celery|frontend)"
        echo "  migrate   - Run database migrations"
        echo "  admin     - Create admin user"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 setup              # Complete setup"
        echo "  $0 start              # Start services"
        echo "  $0 logs backend       # Show backend logs"
        echo "  $0 status             # Show service status"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac 