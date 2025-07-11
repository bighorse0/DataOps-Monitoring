# DataOps Monitoring Platform - Test Suite

This directory contains comprehensive tests for the DataOps Monitoring Platform backend.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Database model unit tests
├── test_api.py              # API endpoint tests
├── test_services.py         # Service layer tests
├── test_integration.py      # Integration tests
├── test_security.py         # Security tests
├── test_performance.py      # Performance and load tests
├── test_factories.py        # Test data factories
└── README.md               # This file
```

## Test Categories

### 1. Unit Tests (`test_models.py`)
- **Purpose**: Test individual model classes and their methods
- **Coverage**: Database models, validation, serialization, business logic
- **Examples**: User creation, pipeline status transitions, alert rule evaluation

### 2. API Tests (`test_api.py`)
- **Purpose**: Test REST API endpoints
- **Coverage**: Authentication, CRUD operations, error handling, authorization
- **Examples**: Pipeline creation, user management, alert acknowledgment

### 3. Service Tests (`test_services.py`)
- **Purpose**: Test business logic and service layer
- **Coverage**: Pipeline execution, monitoring, alerting, notifications
- **Examples**: Health check execution, alert rule evaluation, metrics calculation

### 4. Integration Tests (`test_integration.py`)
- **Purpose**: Test complete workflows and system integration
- **Coverage**: End-to-end scenarios, data flow, cross-component interaction
- **Examples**: Pipeline lifecycle, monitoring setup, alert workflows

### 5. Security Tests (`test_security.py`)
- **Purpose**: Test security features and vulnerability prevention
- **Coverage**: Authentication, authorization, input validation, data protection
- **Examples**: JWT token security, SQL injection prevention, XSS protection

### 6. Performance Tests (`test_performance.py`)
- **Purpose**: Test system performance and scalability
- **Coverage**: Response times, concurrent access, memory usage, load handling
- **Examples**: Large dataset queries, concurrent pipeline execution, stress testing

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r requirements-test.txt
```

### Basic Test Execution
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestUserModel

# Run specific test method
pytest tests/test_models.py::TestUserModel::test_create_user
```

### Using the Test Runner Script
```bash
# Run all tests with coverage
./scripts/run_tests.sh

# Run specific test types
./scripts/run_tests.sh -t unit
./scripts/run_tests.sh -t api
./scripts/run_tests.sh -t security
./scripts/run_tests.sh -t performance

# Run with additional options
./scripts/run_tests.sh -t all -v -p -r
```

### Test Options
- `-t, --type`: Test type (unit, integration, api, security, performance, smoke, all)
- `-v, --verbose`: Verbose output
- `-p, --parallel`: Run tests in parallel
- `-f, --fail-fast`: Stop on first failure
- `-r, --report`: Generate HTML report
- `-c, --coverage`: Enable coverage reporting

## Test Data Management

### Using Factories
The test suite uses Factory Boy for generating test data:

```python
from tests.test_factories import UserFactory, PipelineFactory

# Create a user
user = UserFactory()

# Create a pipeline with runs
pipeline = PipelineWithRunsFactory()

# Create complete test environment
env = create_complete_test_environment()
```

### Available Factories
- `UserFactory`: Create users with different roles
- `OrganizationFactory`: Create organizations with plans
- `PipelineFactory`: Create pipelines with configurations
- `PipelineRunFactory`: Create pipeline execution records
- `DataSourceFactory`: Create data sources with connections
- `HealthCheckFactory`: Create health check configurations
- `AlertRuleFactory`: Create alert rules with conditions
- `AlertFactory`: Create alert instances

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings (minimum 80%)
- Markers for test categorization
- Output formatting options

### Test Fixtures (`conftest.py`)
- Database setup and teardown
- Authentication helpers
- Mock services
- Test data creation

## Coverage Requirements

The test suite requires:
- **Minimum coverage**: 80%
- **Coverage reports**: HTML, XML, and terminal output
- **Coverage exclusions**: Configuration files, migrations, CLI scripts

## Continuous Integration

Tests are automatically run in CI/CD pipelines:
- Unit tests on every commit
- Integration tests on pull requests
- Security tests on deployment
- Performance tests on release candidates

## Best Practices

### Writing Tests
1. **Use descriptive test names**: `test_user_cannot_access_other_organization_data`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Test one thing per test**: Single responsibility
4. **Use factories for test data**: Avoid hardcoded values
5. **Mock external dependencies**: Database, APIs, services

### Test Organization
1. **Group related tests**: Use test classes for related functionality
2. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
3. **Keep tests independent**: No test should depend on another
4. **Clean up after tests**: Use fixtures for setup/teardown

### Performance Considerations
1. **Use database transactions**: Rollback after each test
2. **Minimize external calls**: Mock APIs and services
3. **Use appropriate test data size**: Don't create unnecessary large datasets
4. **Run tests in parallel**: Use pytest-xdist for faster execution

## Troubleshooting

### Common Issues
1. **Database connection errors**: Check test database configuration
2. **Import errors**: Ensure all dependencies are installed
3. **Test failures**: Check test data and mock configurations
4. **Performance issues**: Use smaller test datasets or parallel execution

### Debugging Tests
```bash
# Run with debug output
pytest -v -s

# Run single test with debugger
pytest tests/test_models.py::TestUserModel::test_create_user -s

# Run with coverage and show missing lines
pytest --cov=app --cov-report=term-missing
```

## Test Reports

After running tests with the `-r` flag, reports are generated in the `reports/` directory:
- `htmlcov/index.html`: Coverage report
- `test-report.html`: Test execution report
- `bandit-report.json`: Security scan results
- `coverage.xml`: Coverage data for CI tools

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain coverage above 80%
4. Add appropriate test markers
5. Update this documentation if needed 