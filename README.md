# DataOps Monitoring Platform

A web-based DataOps Automation and Health Monitoring platform designed for mid-market enterprises to monitor data pipelines, catch errors early, and maintain data health without requiring a dedicated data engineering team.

## 🎯 What It Does

- **Pipeline Monitoring**: Monitor ETL/ELT jobs, database syncs, and API ingestions
- **Health Checks**: Detect data freshness, volume anomalies, and pipeline failures
- **Auto-Generated Dashboards**: Non-technical friendly visualizations
- **Smart Alerts**: Configurable notifications via Slack, Email, SMS
- **Self-Healing**: Auto-recovery for common pipeline issues
- **Role-Based Access**: Secure multi-user environment

## 🏗️ Architecture

```
Frontend (React + Tailwind) ←→ Backend API (Flask) ←→ Database (PostgreSQL)
                                    ↓
                            Task Queue (Celery + Redis)
                                    ↓
                            Pipeline Connectors
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Redis (for task queue)

### Installation

1. **Clone and setup backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Setup database:**
```bash
# Create PostgreSQL database
createdb dataops_monitoring

# Run migrations
flask db upgrade
```

3. **Setup frontend:**
```bash
cd frontend
npm install
npm start
```

4. **Start the application:**
```bash
# Terminal 1: Backend API
cd backend
flask run

# Terminal 2: Task Queue
cd backend
celery -A app.celery worker --loglevel=info

# Terminal 3: Frontend
cd frontend
npm start
```

## 📊 Features

### Core Monitoring
- **Pipeline Health**: Real-time status of all data pipelines
- **Data Freshness**: Track when data was last updated
- **Volume Monitoring**: Detect unusual data volumes or missing data
- **Error Tracking**: Comprehensive error logging and alerting

### Alerting System
- **Multi-channel**: Slack, Email, SMS, Webhook support
- **Smart Thresholds**: Configurable alert conditions
- **Escalation**: Automatic escalation for critical issues
- **Suppression**: Prevent alert fatigue with smart suppression

### Self-Healing
- **Retry Logic**: Automatic retry for transient failures
- **Rollback Capability**: Revert to last known good state
- **Custom Scripts**: User-defined recovery actions
- **Health Checks**: Proactive monitoring and prevention

### Dashboard & Reporting
- **Executive Dashboard**: High-level overview for leadership
- **Technical Dashboard**: Detailed metrics for data teams
- **Custom Reports**: Configurable reporting and exports
- **Historical Analysis**: Trend analysis and performance tracking

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/dataops_monitoring

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# External Services
SLACK_WEBHOOK_URL=your-slack-webhook
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USER=your-email
SMTP_PASS=your-password
```

### Pipeline Connectors
The platform supports various data pipeline connectors:
- **Airflow**: Direct integration with Apache Airflow
- **dbt**: Data Build Tool monitoring
- **Cron Jobs**: Traditional scheduled job monitoring
- **Custom APIs**: REST API monitoring
- **Database**: Direct database connection monitoring

## 🔬 Testing & Quality Assurance

The backend includes a **comprehensive, high-coverage test suite** to ensure reliability, security, and performance.

### Test Suite Overview
- **Unit tests** for all models and business logic
- **API tests** for every endpoint (auth, CRUD, error handling, permissions)
- **Service layer tests** for core business logic and background tasks
- **Integration tests** for end-to-end flows (pipelines, monitoring, alerts, user management, etc.)
- **Security tests** for authentication, authorization, input validation, and data protection
- **Performance and stress tests** for API, database, and concurrent access
- **Test data factories** for easy, maintainable test data generation
- **Mock services** for external APIs, databases, and queues

### Coverage & Quality
- **80%+ code coverage required** (enforced by CI)
- **Code quality checks**: linting (flake8), formatting (black), type checking (mypy), security scanning (bandit)
- **Automated test runner** with reporting and parallel execution

### Running Tests

#### Quick Start
```bash
cd backend
./scripts/run_tests.sh
```

#### Run Specific Test Types
```bash
./scripts/run_tests.sh -t unit
./scripts/run_tests.sh -t api
./scripts/run_tests.sh -t security
./scripts/run_tests.sh -t performance
```

#### Advanced Options
- `-v` for verbose output
- `-p` for parallel execution
- `-r` to generate HTML reports
- `-f` to fail fast on first error

#### Example:
```bash
./scripts/run_tests.sh -t all -v -p -r
```

#### Manual Pytest Usage
```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html

# Run a specific test file/class/method
pytest tests/test_models.py
pytest tests/test_models.py::TestUserModel
pytest tests/test_models.py::TestUserModel::test_create_user
```

#### Test Data Factories
- Use Factory Boy-based factories for all models (see `backend/tests/test_factories.py`)
- Easily create users, pipelines, data sources, alerts, and more for tests

#### More Details
See [`backend/tests/README.md`](backend/tests/README.md) for:
- Test structure and categories
- Factory usage
- Markers and configuration
- CI integration
- Best practices for writing and organizing tests

## 📈 Pricing Tiers

### Starter ($99/month)
- Up to 10 pipelines
- Basic monitoring
- Email alerts
- 7-day data retention

### Professional ($299/month)
- Up to 50 pipelines
- Advanced monitoring
- Slack + Email alerts
- Self-healing capabilities
- 30-day data retention

### Enterprise ($799/month)
- Unlimited pipelines
- Full feature set
- Custom integrations
- Priority support
- 90-day data retention

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- Documentation: [docs.dataops-monitoring.com](https://docs.dataops-monitoring.com)
- Email: support@dataops-monitoring.com
- Slack: [Join our community](https://slack.dataops-monitoring.com) 