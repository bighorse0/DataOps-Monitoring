import factory
from factory import Faker, SubFactory, LazyAttribute
from datetime import datetime, timedelta
from app.models.user import User
from app.models.organization import Organization
from app.models.pipeline import Pipeline, PipelineRun, PipelineMetric, PipelineType, PipelineStatus, RunStatus
from app.models.monitoring import DataSource, HealthCheck, HealthCheckResult, DataSourceType, HealthCheckType
from app.models.alert import AlertRule, Alert, AlertRuleType, AlertSeverity, AlertStatus
from flask_bcrypt import Bcrypt

class OrganizationFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating Organization instances."""
    
    class Meta:
        model = Organization
        sqlalchemy_session = None  # Will be set in conftest.py
    
    name = Faker('company')
    plan = Faker('random_element', elements=['basic', 'professional', 'enterprise'])
    max_pipelines = Faker('random_int', min=10, max=1000)
    max_users = Faker('random_int', min=5, max=100)
    created_at = Faker('date_time_this_year')
    updated_at = LazyAttribute(lambda obj: obj.created_at)

class UserFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
        sqlalchemy_session = None  # Will be set in conftest.py
    
    email = Faker('email')
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    role = Faker('random_element', elements=['user', 'manager', 'admin'])
    organization = SubFactory(OrganizationFactory)
    is_active = True
    last_login_at = Faker('date_time_this_year')
    created_at = Faker('date_time_this_year')
    updated_at = LazyAttribute(lambda obj: obj.created_at)
    
    @factory.post_generation
    def password_hash(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            self.password_hash = extracted
        else:
            bcrypt = Bcrypt()
            self.password_hash = bcrypt.generate_password_hash('password123').decode('utf-8')

class PipelineFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating Pipeline instances."""
    
    class Meta:
        model = Pipeline
        sqlalchemy_session = None  # Will be set in conftest.py
    
    name = Faker('sentence', nb_words=3)
    description = Faker('text', max_nb_chars=200)
    pipeline_type = Faker('random_element', elements=list(PipelineType))
    status = Faker('random_element', elements=list(PipelineStatus))
    config = LazyAttribute(lambda obj: {
        'source': f'source_{Faker("word").generate()}',
        'destination': f'dest_{Faker("word").generate()}',
        'transformations': ['clean', 'aggregate', 'validate']
    })
    schedule = Faker('random_element', elements=['0 0 * * *', '0 2 * * *', '0 4 * * *', '*/15 * * * *'])
    timeout_minutes = Faker('random_int', min=30, max=480)
    retry_attempts = Faker('random_int', min=0, max=5)
    retry_delay_minutes = Faker('random_int', min=1, max=30)
    health_check_enabled = Faker('boolean')
    freshness_threshold_hours = Faker('random_int', min=1, max=168)
    volume_threshold_percent = Faker('pyfloat', min_value=1.0, max_value=50.0)
    auto_heal_enabled = Faker('boolean')
    heal_script = LazyAttribute(lambda obj: 'echo "healing pipeline"' if obj.auto_heal_enabled else None)
    tags = LazyAttribute(lambda obj: [Faker('word').generate() for _ in range(Faker('random_int', min=0, max=5).generate())])
    organization = SubFactory(OrganizationFactory)
    created_by = SubFactory(UserFactory)
    created_at = Faker('date_time_this_year')
    updated_at = LazyAttribute(lambda obj: obj.created_at)

class PipelineRunFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating PipelineRun instances."""
    
    class Meta:
        model = PipelineRun
        sqlalchemy_session = None  # Will be set in conftest.py
    
    pipeline = SubFactory(PipelineFactory)
    status = Faker('random_element', elements=list(RunStatus))
    started_at = Faker('date_time_this_month')
    completed_at = LazyAttribute(lambda obj: obj.started_at + timedelta(minutes=Faker('random_int', min=1, max=60).generate()))
    duration_seconds = LazyAttribute(lambda obj: int((obj.completed_at - obj.started_at).total_seconds()))
    records_processed = Faker('random_int', min=100, max=1000000)
    error_message = LazyAttribute(lambda obj: Faker('sentence').generate() if obj.status == RunStatus.FAILED else None)
    created_at = LazyAttribute(lambda obj: obj.started_at)

class PipelineMetricFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating PipelineMetric instances."""
    
    class Meta:
        model = PipelineMetric
        sqlalchemy_session = None  # Will be set in conftest.py
    
    pipeline = SubFactory(PipelineFactory)
    metric_name = Faker('random_element', elements=['execution_time', 'success_rate', 'records_processed', 'error_rate'])
    metric_value = Faker('pyfloat', min_value=0.0, max_value=1000.0)
    metric_unit = LazyAttribute(lambda obj: {
        'execution_time': 'seconds',
        'success_rate': 'percentage',
        'records_processed': 'count',
        'error_rate': 'percentage'
    }.get(obj.metric_name, 'unit'))
    recorded_at = Faker('date_time_this_month')

class DataSourceFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating DataSource instances."""
    
    class Meta:
        model = DataSource
        sqlalchemy_session = None  # Will be set in conftest.py
    
    name = Faker('sentence', nb_words=3)
    type = Faker('random_element', elements=list(DataSourceType))
    host = Faker('hostname')
    port = LazyAttribute(lambda obj: {
        DataSourceType.POSTGRESQL: 5432,
        DataSourceType.MYSQL: 3306,
        DataSourceType.MONGODB: 27017,
        DataSourceType.REDIS: 6379,
        DataSourceType.ELASTICSEARCH: 9200
    }.get(obj.type, 5432))
    database = Faker('word')
    username = Faker('user_name')
    password = Faker('password')
    connection_string = LazyAttribute(lambda obj: f"{obj.type.value}://{obj.username}:{obj.password}@{obj.host}:{obj.port}/{obj.database}")
    status = Faker('random_element', elements=['connected', 'disconnected', 'error'])
    health_score = Faker('pyfloat', min_value=0.0, max_value=100.0)
    last_check_at = Faker('date_time_this_month')
    organization = SubFactory(OrganizationFactory)
    created_at = Faker('date_time_this_year')
    updated_at = LazyAttribute(lambda obj: obj.created_at)

class HealthCheckFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating HealthCheck instances."""
    
    class Meta:
        model = HealthCheck
        sqlalchemy_session = None  # Will be set in conftest.py
    
    name = Faker('sentence', nb_words=4)
    data_source = SubFactory(DataSourceFactory)
    check_type = Faker('random_element', elements=list(HealthCheckType))
    query = LazyAttribute(lambda obj: {
        HealthCheckType.QUERY: 'SELECT 1',
        HealthCheckType.CONNECTION: 'ping',
        HealthCheckType.RESPONSE_TIME: 'SELECT COUNT(*) FROM test_table',
        HealthCheckType.DATA_FRESHNESS: 'SELECT MAX(updated_at) FROM test_table',
        HealthCheckType.DATA_VOLUME: 'SELECT COUNT(*) FROM test_table'
    }.get(obj.check_type, 'SELECT 1'))
    expected_result = LazyAttribute(lambda obj: {
        HealthCheckType.QUERY: '1',
        HealthCheckType.CONNECTION: 'pong',
        HealthCheckType.RESPONSE_TIME: '1000',
        HealthCheckType.DATA_FRESHNESS: '2023-01-01 00:00:00',
        HealthCheckType.DATA_VOLUME: '1000'
    }.get(obj.check_type, '1'))
    interval_minutes = Faker('random_int', min=1, max=60)
    timeout_seconds = Faker('random_int', min=10, max=300)
    enabled = Faker('boolean')
    last_run_at = Faker('date_time_this_month')
    last_status = Faker('random_element', elements=['success', 'failed', 'timeout'])
    created_at = Faker('date_time_this_year')
    updated_at = LazyAttribute(lambda obj: obj.created_at)

class HealthCheckResultFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating HealthCheckResult instances."""
    
    class Meta:
        model = HealthCheckResult
        sqlalchemy_session = None  # Will be set in conftest.py
    
    health_check = SubFactory(HealthCheckFactory)
    status = Faker('random_element', elements=['success', 'failed', 'timeout'])
    response_time = Faker('pyfloat', min_value=0.1, max_value=10.0)
    result_data = LazyAttribute(lambda obj: {
        'rows': Faker('random_int', min=1, max=100).generate(),
        'value': Faker('word').generate(),
        'timestamp': Faker('iso8601').generate()
    })
    error_message = LazyAttribute(lambda obj: Faker('sentence').generate() if obj.status != 'success' else None)
    executed_at = Faker('date_time_this_month')

class AlertRuleFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating AlertRule instances."""
    
    class Meta:
        model = AlertRule
        sqlalchemy_session = None  # Will be set in conftest.py
    
    name = Faker('sentence', nb_words=4)
    description = Faker('text', max_nb_chars=200)
    severity = Faker('random_element', elements=list(AlertSeverity))
    condition_type = Faker('random_element', elements=list(AlertRuleType))
    condition_config = LazyAttribute(lambda obj: {
        AlertRuleType.THRESHOLD: {
            'metric': 'pipeline_failure_rate',
            'threshold': Faker('pyfloat', min_value=0.0, max_value=1.0).generate(),
            'operator': Faker('random_element', elements=['>', '<', '>=', '<=']).generate()
        },
        AlertRuleType.ANOMALY: {
            'metric': 'data_freshness',
            'threshold': Faker('random_int', min=1, max=72).generate(),
            'window': Faker('random_element', elements=['1h', '6h', '24h']).generate()
        },
        AlertRuleType.TREND: {
            'metric': 'execution_time',
            'direction': Faker('random_element', elements=['increasing', 'decreasing']).generate(),
            'threshold': Faker('pyfloat', min_value=0.1, max_value=2.0).generate()
        }
    }.get(obj.condition_type, {'metric': 'test_metric', 'threshold': 0.5}))
    notification_channels = LazyAttribute(lambda obj: Faker('random_elements', elements=['email', 'slack', 'sms', 'webhook'], unique=True).generate())
    enabled = Faker('boolean')
    organization = SubFactory(OrganizationFactory)
    created_at = Faker('date_time_this_year')
    updated_at = LazyAttribute(lambda obj: obj.created_at)

class AlertFactory(factory.SQLAlchemyModelFactory):
    """Factory for creating Alert instances."""
    
    class Meta:
        model = Alert
        sqlalchemy_session = None  # Will be set in conftest.py
    
    alert_rule = SubFactory(AlertRuleFactory)
    severity = LazyAttribute(lambda obj: obj.alert_rule.severity)
    message = Faker('sentence', nb_words=10)
    status = Faker('random_element', elements=list(AlertStatus))
    triggered_at = Faker('date_time_this_month')
    acknowledged_at = LazyAttribute(lambda obj: Faker('date_time_between', start_date=obj.triggered_at).generate() if obj.status in [AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED] else None)
    resolved_at = LazyAttribute(lambda obj: Faker('date_time_between', start_date=obj.triggered_at).generate() if obj.status == AlertStatus.RESOLVED else None)
    created_at = LazyAttribute(lambda obj: obj.triggered_at)
    updated_at = LazyAttribute(lambda obj: obj.created_at)

# Composite factories for complex scenarios
class PipelineWithRunsFactory(PipelineFactory):
    """Factory for creating a pipeline with multiple runs."""
    
    @factory.post_generation
    def runs(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            self.runs = extracted
        else:
            # Create 5-15 runs for the pipeline
            num_runs = Faker('random_int', min=5, max=15).generate()
            runs = []
            for i in range(num_runs):
                run = PipelineRunFactory(
                    pipeline=self,
                    started_at=self.created_at + timedelta(hours=i*2),
                    status=Faker('random_element', elements=[RunStatus.SUCCESS, RunStatus.FAILED, RunStatus.RUNNING]).generate()
                )
                runs.append(run)
            return runs

class OrganizationWithUsersFactory(OrganizationFactory):
    """Factory for creating an organization with multiple users."""
    
    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            self.users = extracted
        else:
            # Create 3-10 users for the organization
            num_users = Faker('random_int', min=3, max=10).generate()
            users = []
            for i in range(num_users):
                user = UserFactory(
                    organization=self,
                    role=Faker('random_element', elements=['user', 'manager', 'admin']).generate()
                )
                users.append(user)
            return users

class DataSourceWithHealthChecksFactory(DataSourceFactory):
    """Factory for creating a data source with health checks."""
    
    @factory.post_generation
    def health_checks(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            self.health_checks = extracted
        else:
            # Create 2-5 health checks for the data source
            num_checks = Faker('random_int', min=2, max=5).generate()
            checks = []
            for i in range(num_checks):
                check = HealthCheckFactory(
                    data_source=self,
                    check_type=Faker('random_element', elements=list(HealthCheckType)).generate()
                )
                checks.append(check)
            return checks

# Utility functions for common test scenarios
def create_test_organization_with_users(num_users=5):
    """Create an organization with users for testing."""
    org = OrganizationWithUsersFactory()
    return org

def create_test_pipeline_with_runs(num_runs=10):
    """Create a pipeline with runs for testing."""
    pipeline = PipelineWithRunsFactory()
    return pipeline

def create_test_data_source_with_health_checks(num_checks=3):
    """Create a data source with health checks for testing."""
    data_source = DataSourceWithHealthChecksFactory()
    return data_source

def create_test_alert_rule_with_alerts(num_alerts=5):
    """Create an alert rule with alerts for testing."""
    alert_rule = AlertRuleFactory()
    alerts = []
    for i in range(num_alerts):
        alert = AlertFactory(alert_rule=alert_rule)
        alerts.append(alert)
    return alert_rule, alerts

def create_complete_test_environment():
    """Create a complete test environment with all components."""
    # Create organization with users
    org = OrganizationWithUsersFactory()
    
    # Create data sources with health checks
    data_sources = []
    for i in range(3):
        ds = DataSourceWithHealthChecksFactory(organization=org)
        data_sources.append(ds)
    
    # Create pipelines with runs
    pipelines = []
    for i in range(5):
        pipeline = PipelineWithRunsFactory(organization=org)
        pipelines.append(pipeline)
    
    # Create alert rules with alerts
    alert_rules = []
    for i in range(3):
        alert_rule, alerts = create_test_alert_rule_with_alerts(num_alerts=2)
        alert_rule.organization = org
        alert_rules.append(alert_rule)
    
    return {
        'organization': org,
        'users': org.users,
        'data_sources': data_sources,
        'pipelines': pipelines,
        'alert_rules': alert_rules
    } 