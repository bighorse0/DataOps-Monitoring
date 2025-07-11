import pytest
import tempfile
import os
from flask import Flask
from app import create_app, db
from app.models.user import User
from app.models.organization import Organization
from app.models.pipeline import Pipeline, PipelineRun
from app.models.monitoring import DataSource, HealthCheck
from app.models.alert import AlertRule, Alert
from flask_bcrypt import Bcrypt
import jwt
from datetime import datetime, timedelta

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Create the database and load test data
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def bcrypt(app):
    """Bcrypt instance for password hashing."""
    return Bcrypt(app)

@pytest.fixture
def test_organization(app):
    """Create a test organization."""
    org = Organization(
        name='Test Organization',
        plan='professional',
        max_pipelines=50,
        max_users=10
    )
    db.session.add(org)
    db.session.commit()
    return org

@pytest.fixture
def test_user(app, bcrypt, test_organization):
    """Create a test user."""
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        role='user',
        organization_id=test_organization.id,
        is_active=True
    )
    user.password_hash = bcrypt.generate_password_hash('password123').decode('utf-8')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def admin_user(app, bcrypt, test_organization):
    """Create an admin user."""
    user = User(
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        role='admin',
        organization_id=test_organization.id,
        is_active=True
    )
    user.password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def manager_user(app, bcrypt, test_organization):
    """Create a manager user."""
    user = User(
        email='manager@example.com',
        first_name='Manager',
        last_name='User',
        role='manager',
        organization_id=test_organization.id,
        is_active=True
    )
    user.password_hash = bcrypt.generate_password_hash('manager123').decode('utf-8')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def auth_headers(app, test_user):
    """Generate authentication headers for API requests."""
    with app.app_context():
        access_token = jwt.encode(
            {
                'user_id': test_user.id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        return {'Authorization': f'Bearer {access_token}'}

@pytest.fixture
def admin_headers(app, admin_user):
    """Generate authentication headers for admin API requests."""
    with app.app_context():
        access_token = jwt.encode(
            {
                'user_id': admin_user.id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        return {'Authorization': f'Bearer {access_token}'}

@pytest.fixture
def test_pipeline(app, test_user, test_organization):
    """Create a test pipeline."""
    pipeline = Pipeline(
        name='Test Pipeline',
        description='A test pipeline',
        pipeline_type='etl',
        status='active',
        config={'source': 'test_source'},
        schedule='0 0 * * *',
        timeout_minutes=60,
        retry_attempts=3,
        retry_delay_minutes=5,
        health_check_enabled=True,
        freshness_threshold_hours=24,
        volume_threshold_percent=10.0,
        auto_heal_enabled=False,
        organization_id=test_organization.id,
        created_by=test_user.id
    )
    db.session.add(pipeline)
    db.session.commit()
    return pipeline

@pytest.fixture
def test_pipeline_run(app, test_pipeline):
    """Create a test pipeline run."""
    run = PipelineRun(
        pipeline_id=test_pipeline.id,
        status='success',
        started_at=datetime.utcnow() - timedelta(hours=1),
        completed_at=datetime.utcnow(),
        duration_seconds=300,
        records_processed=1000,
        error_message=None
    )
    db.session.add(run)
    db.session.commit()
    return run

@pytest.fixture
def test_data_source(app, test_organization):
    """Create a test data source."""
    data_source = DataSource(
        name='Test Database',
        type='postgresql',
        host='localhost',
        port=5432,
        database='test_db',
        username='test_user',
        password='test_password',
        connection_string='postgresql://test_user:test_password@localhost:5432/test_db',
        status='connected',
        health_score=95.0,
        last_check_at=datetime.utcnow(),
        organization_id=test_organization.id
    )
    db.session.add(data_source)
    db.session.commit()
    return data_source

@pytest.fixture
def test_health_check(app, test_data_source):
    """Create a test health check."""
    health_check = HealthCheck(
        name='Test Health Check',
        data_source_id=test_data_source.id,
        check_type='query',
        query='SELECT 1',
        expected_result='1',
        interval_minutes=5,
        timeout_seconds=30,
        enabled=True,
        last_run_at=datetime.utcnow(),
        last_status='success'
    )
    db.session.add(health_check)
    db.session.commit()
    return health_check

@pytest.fixture
def test_alert_rule(app, test_organization):
    """Create a test alert rule."""
    alert_rule = AlertRule(
        name='Test Alert Rule',
        description='A test alert rule',
        severity='medium',
        condition_type='threshold',
        condition_config={'metric': 'pipeline_failure_rate', 'threshold': 0.1},
        notification_channels=['email'],
        enabled=True,
        organization_id=test_organization.id
    )
    db.session.add(alert_rule)
    db.session.commit()
    return alert_rule

@pytest.fixture
def test_alert(app, test_alert_rule):
    """Create a test alert."""
    alert = Alert(
        alert_rule_id=test_alert_rule.id,
        severity='medium',
        message='Test alert message',
        status='active',
        triggered_at=datetime.utcnow(),
        acknowledged_at=None,
        resolved_at=None
    )
    db.session.add(alert)
    db.session.commit()
    return alert

@pytest.fixture
def sample_pipeline_data():
    """Sample pipeline data for testing."""
    return {
        'name': 'Sample Pipeline',
        'description': 'A sample pipeline for testing',
        'pipeline_type': 'etl',
        'config': {'source': 'sample_source', 'destination': 'sample_dest'},
        'schedule': '0 2 * * *',
        'timeout_minutes': 120,
        'retry_attempts': 3,
        'retry_delay_minutes': 10,
        'health_check_enabled': True,
        'freshness_threshold_hours': 48,
        'volume_threshold_percent': 15.0,
        'auto_heal_enabled': True,
        'heal_script': 'echo "healing pipeline"',
        'tags': ['test', 'sample']
    }

@pytest.fixture
def sample_data_source_data():
    """Sample data source data for testing."""
    return {
        'name': 'Sample Database',
        'type': 'mysql',
        'host': 'sample-host.com',
        'port': 3306,
        'database': 'sample_db',
        'username': 'sample_user',
        'password': 'sample_password',
        'connection_string': 'mysql://sample_user:sample_password@sample-host.com:3306/sample_db'
    }

@pytest.fixture
def sample_alert_rule_data():
    """Sample alert rule data for testing."""
    return {
        'name': 'Sample Alert Rule',
        'description': 'A sample alert rule for testing',
        'severity': 'high',
        'condition_type': 'anomaly',
        'condition_config': {
            'metric': 'data_freshness',
            'threshold': 24,
            'window': '1h'
        },
        'notification_channels': ['email', 'slack'],
        'enabled': True
    }

@pytest.fixture
def mock_celery(mocker):
    """Mock Celery for testing background tasks."""
    mock_celery = mocker.patch('app.celery')
    mock_celery.send_task.return_value.id = 'test-task-id'
    return mock_celery

@pytest.fixture
def mock_redis(mocker):
    """Mock Redis for testing."""
    mock_redis = mocker.patch('redis.Redis')
    mock_redis_instance = mocker.Mock()
    mock_redis.return_value = mock_redis_instance
    return mock_redis_instance

@pytest.fixture
def mock_sendgrid(mocker):
    """Mock SendGrid for testing email notifications."""
    mock_sendgrid = mocker.patch('sendgrid.SendGridAPIClient')
    mock_client = mocker.Mock()
    mock_sendgrid.return_value = mock_client
    return mock_client

@pytest.fixture
def mock_slack(mocker):
    """Mock Slack for testing notifications."""
    mock_slack = mocker.patch('slack_sdk.webhook.WebhookClient')
    mock_client = mocker.Mock()
    mock_slack.return_value = mock_client
    return mock_client

@pytest.fixture
def mock_twilio(mocker):
    """Mock Twilio for testing SMS notifications."""
    mock_twilio = mocker.patch('twilio.rest.Client')
    mock_client = mocker.Mock()
    mock_twilio.return_value = mock_client
    return mock_client 