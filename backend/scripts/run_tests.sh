#!/bin/bash

# DataOps Monitoring Platform - Test Runner Script
# This script provides various options for running tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=true
VERBOSE=false
PARALLEL=false
FAIL_FAST=false
GENERATE_REPORT=false
CLEANUP=true

# Function to print usage
print_usage() {
    echo -e "${BLUE}DataOps Monitoring Platform - Test Runner${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE          Test type: all, unit, integration, api, security, performance, smoke"
    echo "  -c, --coverage           Enable coverage reporting (default: true)"
    echo "  -v, --verbose            Verbose output"
    echo "  -p, --parallel           Run tests in parallel"
    echo "  -f, --fail-fast          Stop on first failure"
    echo "  -r, --report             Generate HTML report"
    echo "  -n, --no-cleanup         Don't cleanup test artifacts"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                        # Run all tests with coverage"
    echo "  $0 -t unit               # Run only unit tests"
    echo "  $0 -t api -v             # Run API tests with verbose output"
    echo "  $0 -t security -p        # Run security tests in parallel"
    echo "  $0 -t performance -r     # Run performance tests and generate report"
    echo ""
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to setup test environment
setup_test_env() {
    print_status "Setting up test environment..."
    
    # Check if we're in the right directory
    if [ ! -f "requirements.txt" ] || [ ! -d "tests" ]; then
        print_error "Please run this script from the backend directory"
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip install -r requirements.txt
    pip install -r requirements-test.txt
    
    # Set environment variables for testing
    export FLASK_ENV=testing
    export TESTING=true
    export DATABASE_URL=sqlite:///test.db
    
    print_status "Test environment setup complete"
}

# Function to cleanup test artifacts
cleanup_test_artifacts() {
    if [ "$CLEANUP" = true ]; then
        print_status "Cleaning up test artifacts..."
        
        # Remove test database
        rm -f test.db
        rm -f test.db-journal
        
        # Remove coverage files
        rm -f .coverage
        rm -rf htmlcov/
        rm -f coverage.xml
        
        # Remove pytest cache
        rm -rf .pytest_cache/
        rm -rf tests/__pycache__/
        rm -rf tests/*/__pycache__/
        
        # Remove test reports
        rm -f test-results.xml
        rm -f test-report.html
        
        print_status "Cleanup complete"
    fi
}

# Function to run specific test type
run_test_type() {
    local test_type=$1
    local pytest_args=""
    
    case $test_type in
        "unit")
            print_status "Running unit tests..."
            pytest_args="tests/test_models.py tests/test_services.py -m unit"
            ;;
        "integration")
            print_status "Running integration tests..."
            pytest_args="tests/test_integration.py -m integration"
            ;;
        "api")
            print_status "Running API tests..."
            pytest_args="tests/test_api.py -m api"
            ;;
        "security")
            print_status "Running security tests..."
            pytest_args="tests/test_security.py -m security"
            ;;
        "performance")
            print_status "Running performance tests..."
            pytest_args="tests/test_performance.py -m performance"
            ;;
        "smoke")
            print_status "Running smoke tests..."
            pytest_args="tests/ -m smoke"
            ;;
        "all")
            print_status "Running all tests..."
            pytest_args="tests/"
            ;;
        *)
            print_error "Unknown test type: $test_type"
            exit 1
            ;;
    esac
    
    # Build pytest command
    local cmd="pytest $pytest_args"
    
    # Add coverage if enabled
    if [ "$COVERAGE" = true ]; then
        cmd="$cmd --cov=app --cov-report=term-missing"
        if [ "$GENERATE_REPORT" = true ]; then
            cmd="$cmd --cov-report=html --cov-report=xml"
        fi
    fi
    
    # Add other options
    if [ "$VERBOSE" = true ]; then
        cmd="$cmd -v"
    fi
    
    if [ "$PARALLEL" = true ]; then
        cmd="$cmd -n auto"
    fi
    
    if [ "$FAIL_FAST" = true ]; then
        cmd="$cmd -x"
    fi
    
    # Add HTML report if requested
    if [ "$GENERATE_REPORT" = true ]; then
        cmd="$cmd --html=test-report.html --self-contained-html"
    fi
    
    # Run the tests
    print_status "Executing: $cmd"
    eval $cmd
}

# Function to run linting and code quality checks
run_code_quality_checks() {
    print_status "Running code quality checks..."
    
    # Run flake8
    if command_exists flake8; then
        print_status "Running flake8..."
        flake8 app/ tests/ --max-line-length=120 --ignore=E501,W503
    else
        print_warning "flake8 not found, skipping linting"
    fi
    
    # Run black check
    if command_exists black; then
        print_status "Running black check..."
        black --check app/ tests/
    else
        print_warning "black not found, skipping formatting check"
    fi
    
    # Run isort check
    if command_exists isort; then
        print_status "Running isort check..."
        isort --check-only app/ tests/
    else
        print_warning "isort not found, skipping import sorting check"
    fi
    
    # Run mypy
    if command_exists mypy; then
        print_status "Running mypy..."
        mypy app/ --ignore-missing-imports
    else
        print_warning "mypy not found, skipping type checking"
    fi
    
    # Run bandit security check
    if command_exists bandit; then
        print_status "Running bandit security check..."
        bandit -r app/ -f json -o bandit-report.json || true
    else
        print_warning "bandit not found, skipping security check"
    fi
    
    print_status "Code quality checks complete"
}

# Function to run performance benchmarks
run_performance_benchmarks() {
    print_status "Running performance benchmarks..."
    
    if command_exists pytest-benchmark; then
        pytest tests/test_performance.py -m performance --benchmark-only
    else
        print_warning "pytest-benchmark not found, skipping benchmarks"
    fi
}

# Function to generate test report
generate_test_report() {
    if [ "$GENERATE_REPORT" = true ]; then
        print_status "Generating test report..."
        
        # Create reports directory
        mkdir -p reports
        
        # Move coverage reports
        if [ -d "htmlcov" ]; then
            mv htmlcov reports/
        fi
        
        if [ -f "coverage.xml" ]; then
            mv coverage.xml reports/
        fi
        
        # Move test reports
        if [ -f "test-report.html" ]; then
            mv test-report.html reports/
        fi
        
        if [ -f "bandit-report.json" ]; then
            mv bandit-report.json reports/
        fi
        
        print_status "Test reports generated in reports/ directory"
    fi
}

# Function to show test summary
show_test_summary() {
    print_status "Test execution complete!"
    
    if [ "$GENERATE_REPORT" = true ] && [ -d "reports" ]; then
        echo ""
        echo -e "${BLUE}Test Reports:${NC}"
        echo "  - Coverage HTML: reports/htmlcov/index.html"
        echo "  - Coverage XML: reports/coverage.xml"
        echo "  - Test Report: reports/test-report.html"
        echo "  - Security Report: reports/bandit-report.json"
        echo ""
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -f|--fail-fast)
            FAIL_FAST=true
            shift
            ;;
        -r|--report)
            GENERATE_REPORT=true
            shift
            ;;
        -n|--no-cleanup)
            CLEANUP=false
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Starting test execution..."
    
    # Setup test environment
    setup_test_env
    
    # Run code quality checks first
    run_code_quality_checks
    
    # Run tests
    run_test_type "$TEST_TYPE"
    
    # Run performance benchmarks if requested
    if [ "$TEST_TYPE" = "performance" ] || [ "$TEST_TYPE" = "all" ]; then
        run_performance_benchmarks
    fi
    
    # Generate reports
    generate_test_report
    
    # Show summary
    show_test_summary
    
    # Cleanup
    cleanup_test_artifacts
    
    print_status "All tests completed successfully!"
}

# Run main function
main "$@" 