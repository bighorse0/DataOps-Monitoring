import pytest
from datetime import datetime, timedelta
from app.models.user import User
from app.models.organization import Organization
from app.models.pipeline import Pipeline, PipelineRun, PipelineMetric, PipelineType, PipelineStatus, RunStatus
from app.models.monitoring import DataSource, HealthCheck, HealthCheckResult, DataSourceType, HealthCheckType
from app.models.alert import AlertRule, Alert, AlertRuleType, AlertSeverity, AlertStatus
from flask_bcrypt import Bcrypt

class TestUserModel:
    """Test cases for User model."""
    
    def test_create_user(self, app, bcrypt, test_organization):
        """Test creating a new user."""
        user = User(
            email='newuser@example.com',
            first_name='New',
            last_name='User',
            role='user',
            organization_id=test_organization.id,
            is_active=True
        )
        user.password_hash = bcrypt.generate_password_hash('password123').decode('utf-8')
        
        assert user.email == 'newuser@example.com'
        assert user.first_name == 'New'
        assert user.last_name == 'User'
        assert user.role == 'user'
        assert user.is_active == True
        assert user.organization_id == test_organization.id
    
    def test_user_password_verification(self, app, bcrypt, test_organization):
        """Test password verification."""
        user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='user',
            organization_id=test_organization.id
        )
        user.password_hash = bcrypt.generate_password_hash('password123').decode('utf-8')
        
        assert bcrypt.check_password_hash(user.password_hash, 'password123')
        assert not bcrypt.check_password_hash(user.password_hash, 'wrongpassword')
    
    def test_user_to_dict(self, test_user):
        """Test user serialization to dictionary."""
        user_dict = test_user.to_dict()
        
        assert user_dict['email'] == test_user.email
        assert user_dict['first_name'] == test_user.first_name
        assert user_dict['last_name'] == test_user.last_name
        assert user_dict['role'] == test_user.role
        assert user_dict['is_active'] == test_user.is_active
        assert 'password_hash' not in user_dict
    
    def test_user_role_permissions(self, test_user, admin_user, manager_user):
        """Test user role permissions."""
        assert test_user.has_permission('read_pipeline') == True
        assert test_user.has_permission('create_pipeline') == True
        assert test_user.has_permission('delete_user') == False
        
        assert admin_user.has_permission('delete_user') == True
        assert admin_user.has_permission('manage_organization') == True
        
        assert manager_user.has_permission('manage_users') == True
        assert manager_user.has_permission('delete_organization') == False

class TestOrganizationModel:
    """Test cases for Organization model."""
    
    def test_create_organization(self, app):
        """Test creating a new organization."""
        org = Organization(
            name='Test Org',
            plan='professional',
            max_pipelines=50,
            max_users=10
        )
        
        assert org.name == 'Test Org'
        assert org.plan == 'professional'
        assert org.max_pipelines == 50
        assert org.max_users == 10
    
    def test_organization_pipeline_limit(self, test_organization):
        """Test organization pipeline limit checking."""
        assert test_organization.can_add_pipeline() == True
        assert test_organization.get_pipeline_limit() == 50
    
    def test_organization_user_limit(self, test_organization):
        """Test organization user limit checking."""
        assert test_organization.can_add_user() == True
        assert test_organization.get_user_limit() == 10
    
    def test_organization_to_dict(self, test_organization):
        """Test organization serialization to dictionary."""
        org_dict = test_organization.to_dict()
        
        assert org_dict['name'] == test_organization.name
        assert org_dict['plan'] == test_organization.plan
        assert org_dict['max_pipelines'] == test_organization.max_pipelines
        assert org_dict['max_users'] == test_organization.max_users

class TestPipelineModel:
    """Test cases for Pipeline model."""
    
    def test_create_pipeline(self, app, test_user, test_organization):
        """Test creating a new pipeline."""
        pipeline = Pipeline(
            name='Test Pipeline',
            description='A test pipeline',
            pipeline_type=PipelineType.ETL,
            status=PipelineStatus.ACTIVE,
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
        
        assert pipeline.name == 'Test Pipeline'
        assert pipeline.pipeline_type == PipelineType.ETL
        assert pipeline.status == PipelineStatus.ACTIVE
        assert pipeline.health_check_enabled == True
    
    def test_pipeline_status_transitions(self, test_pipeline):
        """Test pipeline status transitions."""
        assert test_pipeline.status == PipelineStatus.ACTIVE
        
        test_pipeline.status = PipelineStatus.INACTIVE
        assert test_pipeline.status == PipelineStatus.INACTIVE
        
        test_pipeline.status = PipelineStatus.ERROR
        assert test_pipeline.status == PipelineStatus.ERROR
    
    def test_pipeline_to_dict(self, test_pipeline):
        """Test pipeline serialization to dictionary."""
        pipeline_dict = test_pipeline.to_dict()
        
        assert pipeline_dict['name'] == test_pipeline.name
        assert pipeline_dict['pipeline_type'] == test_pipeline.pipeline_type.value
        assert pipeline_dict['status'] == test_pipeline.status.value
        assert 'config' in pipeline_dict
    
    def test_pipeline_health_calculation(self, test_pipeline, test_pipeline_run):
        """Test pipeline health calculation."""
        # Add more runs to test health calculation
        run2 = PipelineRun(
            pipeline_id=test_pipeline.id,
            status=RunStatus.SUCCESS,
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=1),
            duration_seconds=200
        )
        
        # Calculate health metrics
        health_metrics = test_pipeline.calculate_health_metrics()
        
        assert 'uptime_percentage' in health_metrics
        assert 'average_duration' in health_metrics
        assert 'success_rate' in health_metrics

class TestPipelineRunModel:
    """Test cases for PipelineRun model."""
    
    def test_create_pipeline_run(self, app, test_pipeline):
        """Test creating a new pipeline run."""
        run = PipelineRun(
            pipeline_id=test_pipeline.id,
            status=RunStatus.SUCCESS,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow() + timedelta(minutes=5),
            duration_seconds=300,
            records_processed=1000,
            error_message=None
        )
        
        assert run.pipeline_id == test_pipeline.id
        assert run.status == RunStatus.SUCCESS
        assert run.duration_seconds == 300
        assert run.records_processed == 1000
    
    def test_pipeline_run_status_transitions(self, test_pipeline):
        """Test pipeline run status transitions."""
        run = PipelineRun(
            pipeline_id=test_pipeline.id,
            status=RunStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        assert run.status == RunStatus.RUNNING
        
        run.status = RunStatus.SUCCESS
        run.completed_at = datetime.utcnow()
        assert run.status == RunStatus.SUCCESS
    
    def test_pipeline_run_to_dict(self, test_pipeline_run):
        """Test pipeline run serialization to dictionary."""
        run_dict = test_pipeline_run.to_dict()
        
        assert run_dict['pipeline_id'] == test_pipeline_run.pipeline_id
        assert run_dict['status'] == test_pipeline_run.status.value
        assert 'started_at' in run_dict
        assert 'duration_seconds' in run_dict

class TestDataSourceModel:
    """Test cases for DataSource model."""
    
    def test_create_data_source(self, app, test_organization):
        """Test creating a new data source."""
        data_source = DataSource(
            name='Test Database',
            type=DataSourceType.POSTGRESQL,
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
        
        assert data_source.name == 'Test Database'
        assert data_source.type == DataSourceType.POSTGRESQL
        assert data_source.host == 'localhost'
        assert data_source.health_score == 95.0
    
    def test_data_source_connection_test(self, test_data_source):
        """Test data source connection testing."""
        # Mock the connection test
        result = test_data_source.test_connection()
        assert isinstance(result, dict)
        assert 'success' in result
    
    def test_data_source_to_dict(self, test_data_source):
        """Test data source serialization to dictionary."""
        ds_dict = test_data_source.to_dict()
        
        assert ds_dict['name'] == test_data_source.name
        assert ds_dict['type'] == test_data_source.type.value
        assert ds_dict['host'] == test_data_source.host
        assert 'password' not in ds_dict  # Password should be excluded
    
    def test_data_source_health_update(self, test_data_source):
        """Test data source health score update."""
        original_score = test_data_source.health_score
        test_data_source.update_health_score(85.0)
        
        assert test_data_source.health_score == 85.0
        assert test_data_source.last_check_at is not None

class TestHealthCheckModel:
    """Test cases for HealthCheck model."""
    
    def test_create_health_check(self, app, test_data_source):
        """Test creating a new health check."""
        health_check = HealthCheck(
            name='Test Health Check',
            data_source_id=test_data_source.id,
            check_type=HealthCheckType.QUERY,
            query='SELECT 1',
            expected_result='1',
            interval_minutes=5,
            timeout_seconds=30,
            enabled=True,
            last_run_at=datetime.utcnow(),
            last_status='success'
        )
        
        assert health_check.name == 'Test Health Check'
        assert health_check.check_type == HealthCheckType.QUERY
        assert health_check.query == 'SELECT 1'
        assert health_check.enabled == True
    
    def test_health_check_execution(self, test_health_check):
        """Test health check execution."""
        # Mock the health check execution
        result = test_health_check.execute()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'duration' in result
    
    def test_health_check_to_dict(self, test_health_check):
        """Test health check serialization to dictionary."""
        hc_dict = test_health_check.to_dict()
        
        assert hc_dict['name'] == test_health_check.name
        assert hc_dict['check_type'] == test_health_check.check_type.value
        assert hc_dict['enabled'] == test_health_check.enabled
    
    def test_health_check_scheduling(self, test_health_check):
        """Test health check scheduling."""
        # Test if health check is due for execution
        test_health_check.last_run_at = datetime.utcnow() - timedelta(minutes=10)
        assert test_health_check.is_due() == True
        
        test_health_check.last_run_at = datetime.utcnow()
        assert test_health_check.is_due() == False

class TestAlertRuleModel:
    """Test cases for AlertRule model."""
    
    def test_create_alert_rule(self, app, test_organization):
        """Test creating a new alert rule."""
        alert_rule = AlertRule(
            name='Test Alert Rule',
            description='A test alert rule',
            severity=AlertSeverity.MEDIUM,
            condition_type=AlertRuleType.THRESHOLD,
            condition_config={'metric': 'pipeline_failure_rate', 'threshold': 0.1},
            notification_channels=['email'],
            enabled=True,
            organization_id=test_organization.id
        )
        
        assert alert_rule.name == 'Test Alert Rule'
        assert alert_rule.severity == AlertSeverity.MEDIUM
        assert alert_rule.condition_type == AlertRuleType.THRESHOLD
        assert alert_rule.enabled == True
    
    def test_alert_rule_evaluation(self, test_alert_rule):
        """Test alert rule evaluation."""
        # Mock the alert rule evaluation
        result = test_alert_rule.evaluate({'pipeline_failure_rate': 0.15})
        assert isinstance(result, dict)
        assert 'triggered' in result
    
    def test_alert_rule_to_dict(self, test_alert_rule):
        """Test alert rule serialization to dictionary."""
        ar_dict = test_alert_rule.to_dict()
        
        assert ar_dict['name'] == test_alert_rule.name
        assert ar_dict['severity'] == test_alert_rule.severity.value
        assert ar_dict['enabled'] == test_alert_rule.enabled
        assert 'condition_config' in ar_dict
    
    def test_alert_rule_notification_sending(self, test_alert_rule, mock_sendgrid, mock_slack):
        """Test alert rule notification sending."""
        # Mock notification sending
        result = test_alert_rule.send_notifications('Test alert message')
        assert isinstance(result, dict)
        assert 'email_sent' in result

class TestAlertModel:
    """Test cases for Alert model."""
    
    def test_create_alert(self, app, test_alert_rule):
        """Test creating a new alert."""
        alert = Alert(
            alert_rule_id=test_alert_rule.id,
            severity=AlertSeverity.MEDIUM,
            message='Test alert message',
            status=AlertStatus.ACTIVE,
            triggered_at=datetime.utcnow(),
            acknowledged_at=None,
            resolved_at=None
        )
        
        assert alert.alert_rule_id == test_alert_rule.id
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.message == 'Test alert message'
        assert alert.status == AlertStatus.ACTIVE
    
    def test_alert_status_transitions(self, test_alert):
        """Test alert status transitions."""
        assert test_alert.status == AlertStatus.ACTIVE
        
        # Acknowledge alert
        test_alert.acknowledge()
        assert test_alert.status == AlertStatus.ACKNOWLEDGED
        assert test_alert.acknowledged_at is not None
        
        # Resolve alert
        test_alert.resolve()
        assert test_alert.status == AlertStatus.RESOLVED
        assert test_alert.resolved_at is not None
    
    def test_alert_to_dict(self, test_alert):
        """Test alert serialization to dictionary."""
        alert_dict = test_alert.to_dict()
        
        assert alert_dict['alert_rule_id'] == test_alert.alert_rule_id
        assert alert_dict['severity'] == test_alert.severity.value
        assert alert_dict['status'] == test_alert.status.value
        assert 'triggered_at' in alert_dict
    
    def test_alert_duration_calculation(self, test_alert):
        """Test alert duration calculation."""
        # Set resolved time
        test_alert.resolved_at = test_alert.triggered_at + timedelta(hours=2)
        test_alert.status = AlertStatus.RESOLVED
        
        duration = test_alert.get_duration()
        assert duration == 7200  # 2 hours in seconds

class TestPipelineMetricModel:
    """Test cases for PipelineMetric model."""
    
    def test_create_pipeline_metric(self, app, test_pipeline):
        """Test creating a new pipeline metric."""
        metric = PipelineMetric(
            pipeline_id=test_pipeline.id,
            metric_name='execution_time',
            metric_value=300.5,
            metric_unit='seconds',
            recorded_at=datetime.utcnow()
        )
        
        assert metric.pipeline_id == test_pipeline.id
        assert metric.metric_name == 'execution_time'
        assert metric.metric_value == 300.5
        assert metric.metric_unit == 'seconds'
    
    def test_pipeline_metric_to_dict(self, app, test_pipeline):
        """Test pipeline metric serialization to dictionary."""
        metric = PipelineMetric(
            pipeline_id=test_pipeline.id,
            metric_name='success_rate',
            metric_value=95.5,
            metric_unit='percentage',
            recorded_at=datetime.utcnow()
        )
        
        metric_dict = metric.to_dict()
        assert metric_dict['pipeline_id'] == test_pipeline.id
        assert metric_dict['metric_name'] == 'success_rate'
        assert metric_dict['metric_value'] == 95.5

class TestHealthCheckResultModel:
    """Test cases for HealthCheckResult model."""
    
    def test_create_health_check_result(self, app, test_health_check):
        """Test creating a new health check result."""
        result = HealthCheckResult(
            health_check_id=test_health_check.id,
            status='success',
            response_time=0.5,
            result_data={'rows': 1},
            error_message=None,
            executed_at=datetime.utcnow()
        )
        
        assert result.health_check_id == test_health_check.id
        assert result.status == 'success'
        assert result.response_time == 0.5
        assert result.error_message is None
    
    def test_health_check_result_to_dict(self, app, test_health_check):
        """Test health check result serialization to dictionary."""
        result = HealthCheckResult(
            health_check_id=test_health_check.id,
            status='failed',
            response_time=2.0,
            result_data={},
            error_message='Connection timeout',
            executed_at=datetime.utcnow()
        )
        
        result_dict = result.to_dict()
        assert result_dict['health_check_id'] == test_health_check.id
        assert result_dict['status'] == 'failed'
        assert result_dict['error_message'] == 'Connection timeout' 