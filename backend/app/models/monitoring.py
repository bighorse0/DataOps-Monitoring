from app import db
from datetime import datetime
from enum import Enum
import json

class DataSourceType(Enum):
    POSTGRESQL = 'postgresql'
    MYSQL = 'mysql'
    SNOWFLAKE = 'snowflake'
    BIGQUERY = 'bigquery'
    REDSHIFT = 'redshift'
    API = 'api'
    FILE = 'file'
    CUSTOM = 'custom'

class HealthCheckType(Enum):
    FRESHNESS = 'freshness'
    VOLUME = 'volume'
    QUALITY = 'quality'
    CONNECTIVITY = 'connectivity'
    CUSTOM = 'custom'

class HealthCheckStatus(Enum):
    HEALTHY = 'healthy'
    WARNING = 'warning'
    CRITICAL = 'critical'
    UNKNOWN = 'unknown'

class DataSource(db.Model):
    """Data source configuration for monitoring"""
    __tablename__ = 'data_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    source_type = db.Column(db.Enum(DataSourceType), nullable=False)
    
    # Connection details (encrypted in production)
    connection_config = db.Column(db.JSON, nullable=False)
    credentials = db.Column(db.JSON)  # Encrypted credentials
    
    # Monitoring settings
    is_active = db.Column(db.Boolean, default=True)
    check_interval_seconds = db.Column(db.Integer, default=300)  # 5 minutes
    timeout_seconds = db.Column(db.Integer, default=30)
    
    # Metadata
    tags = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked_at = db.Column(db.DateTime)
    
    # Foreign keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Relationships
    health_checks = db.relationship('HealthCheck', backref='data_source', lazy=True)
    pipelines = db.relationship('Pipeline', backref='data_source', lazy=True)
    
    def get_connection_string(self):
        """Get connection string based on source type"""
        config = self.connection_config
        
        if self.source_type == DataSourceType.POSTGRESQL:
            return f"postgresql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port', 5432)}/{config.get('database')}"
        elif self.source_type == DataSourceType.MYSQL:
            return f"mysql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port', 3306)}/{config.get('database')}"
        elif self.source_type == DataSourceType.SNOWFLAKE:
            return f"snowflake://{config.get('username')}:{config.get('password')}@{config.get('account')}/{config.get('database')}/{config.get('schema')}"
        elif self.source_type == DataSourceType.API:
            return config.get('base_url')
        
        return None
    
    def is_healthy(self):
        """Check if data source is healthy based on latest health checks"""
        latest_check = self.get_latest_health_check()
        if not latest_check:
            return False
        return latest_check.status == HealthCheckStatus.HEALTHY
    
    def get_latest_health_check(self):
        """Get the most recent health check result"""
        if not self.health_checks:
            return None
        return max(self.health_checks, key=lambda x: x.checked_at)
    
    def to_dict(self):
        """Convert data source to dictionary"""
        latest_check = self.get_latest_health_check()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'source_type': self.source_type.value,
            'connection_config': {k: v for k, v in self.connection_config.items() if k != 'password'},
            'is_active': self.is_active,
            'check_interval_seconds': self.check_interval_seconds,
            'timeout_seconds': self.timeout_seconds,
            'tags': self.tags,
            'organization_id': self.organization_id,
            'is_healthy': self.is_healthy(),
            'latest_health_check': latest_check.to_dict() if latest_check else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None
        }
    
    def __repr__(self):
        return f'<DataSource {self.name} ({self.source_type.value})>'

class HealthCheck(db.Model):
    """Health check configuration for data sources"""
    __tablename__ = 'health_checks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    check_type = db.Column(db.Enum(HealthCheckType), nullable=False)
    
    # Configuration
    config = db.Column(db.JSON, nullable=False)  # Check-specific configuration
    is_active = db.Column(db.Boolean, default=True)
    check_interval_seconds = db.Column(db.Integer, default=300)
    
    # Thresholds
    warning_threshold = db.Column(db.Float)
    critical_threshold = db.Column(db.Float)
    
    # Alerting
    alert_on_warning = db.Column(db.Boolean, default=True)
    alert_on_critical = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Relationships
    results = db.relationship('HealthCheckResult', backref='health_check', lazy=True, order_by='HealthCheckResult.checked_at.desc()')
    
    def get_latest_result(self):
        """Get the most recent health check result"""
        return self.results[0] if self.results else None
    
    def is_healthy(self):
        """Check if health check is currently healthy"""
        latest_result = self.get_latest_result()
        if not latest_result:
            return False
        return latest_result.status == HealthCheckStatus.HEALTHY
    
    def should_alert(self, status):
        """Check if alert should be sent for given status"""
        if status == HealthCheckStatus.WARNING and self.alert_on_warning:
            return True
        if status == HealthCheckStatus.CRITICAL and self.alert_on_critical:
            return True
        return False
    
    def to_dict(self):
        """Convert health check to dictionary"""
        latest_result = self.get_latest_result()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'check_type': self.check_type.value,
            'config': self.config,
            'is_active': self.is_active,
            'check_interval_seconds': self.check_interval_seconds,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'alert_on_warning': self.alert_on_warning,
            'alert_on_critical': self.alert_on_critical,
            'data_source_id': self.data_source_id,
            'organization_id': self.organization_id,
            'is_healthy': self.is_healthy(),
            'latest_result': latest_result.to_dict() if latest_result else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<HealthCheck {self.name} ({self.check_type.value})>'

class HealthCheckResult(db.Model):
    """Individual health check execution result"""
    __tablename__ = 'health_check_results'
    
    id = db.Column(db.Integer, primary_key=True)
    health_check_id = db.Column(db.Integer, db.ForeignKey('health_checks.id'), nullable=False)
    
    # Result details
    status = db.Column(db.Enum(HealthCheckStatus), nullable=False)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_seconds = db.Column(db.Float)
    
    # Metrics
    metric_value = db.Column(db.Float)
    metric_unit = db.Column(db.String(20))
    
    # Details
    message = db.Column(db.Text)
    details = db.Column(db.JSON)  # Additional result details
    error_message = db.Column(db.Text)
    
    # Context
    context_data = db.Column(db.JSON)  # Additional context when check was run
    
    def is_healthy(self):
        """Check if result indicates healthy status"""
        return self.status == HealthCheckStatus.HEALTHY
    
    def is_warning(self):
        """Check if result indicates warning status"""
        return self.status == HealthCheckStatus.WARNING
    
    def is_critical(self):
        """Check if result indicates critical status"""
        return self.status == HealthCheckStatus.CRITICAL
    
    def get_duration_formatted(self):
        """Get formatted duration string"""
        if not self.duration_seconds:
            return None
        
        if self.duration_seconds < 1:
            return f"{self.duration_seconds * 1000:.0f}ms"
        elif self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        else:
            minutes = int(self.duration_seconds // 60)
            seconds = self.duration_seconds % 60
            return f"{minutes}m {seconds:.1f}s"
    
    def to_dict(self):
        """Convert result to dictionary"""
        return {
            'id': self.id,
            'health_check_id': self.health_check_id,
            'status': self.status.value,
            'checked_at': self.checked_at.isoformat(),
            'duration_seconds': self.duration_seconds,
            'duration_formatted': self.get_duration_formatted(),
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'message': self.message,
            'details': self.details,
            'error_message': self.error_message,
            'context_data': self.context_data,
            'is_healthy': self.is_healthy(),
            'is_warning': self.is_warning(),
            'is_critical': self.is_critical()
        }
    
    def __repr__(self):
        return f'<HealthCheckResult {self.id} - {self.status.value}>' 