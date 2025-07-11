from app import db
from datetime import datetime
from enum import Enum
import json

class PipelineType(Enum):
    ETL = 'etl'
    ELT = 'elt'
    API = 'api'
    DATABASE = 'database'
    CRON = 'cron'
    AIRFLOW = 'airflow'
    DBT = 'dbt'
    CUSTOM = 'custom'

class PipelineStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    MAINTENANCE = 'maintenance'
    DEPRECATED = 'deprecated'

class RunStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'

class Pipeline(db.Model):
    """Data pipeline model"""
    __tablename__ = 'pipelines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    pipeline_type = db.Column(db.Enum(PipelineType), nullable=False)
    status = db.Column(db.Enum(PipelineStatus), default=PipelineStatus.ACTIVE)
    
    # Configuration
    config = db.Column(db.JSON)  # Pipeline-specific configuration
    schedule = db.Column(db.String(100))  # Cron expression or interval
    timeout_minutes = db.Column(db.Integer, default=60)
    retry_attempts = db.Column(db.Integer, default=3)
    retry_delay_minutes = db.Column(db.Integer, default=5)
    
    # Health checks
    health_check_enabled = db.Column(db.Boolean, default=True)
    freshness_threshold_hours = db.Column(db.Integer, default=24)
    volume_threshold_percent = db.Column(db.Float, default=10.0)  # 10% variance allowed
    
    # Self-healing
    auto_heal_enabled = db.Column(db.Boolean, default=False)
    heal_script = db.Column(db.Text)  # Custom healing script
    
    # Metadata
    tags = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run_at = db.Column(db.DateTime)
    next_run_at = db.Column(db.DateTime)
    
    # Foreign keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'))
    
    # Relationships
    runs = db.relationship('PipelineRun', backref='pipeline', lazy=True, order_by='PipelineRun.started_at.desc()')
    metrics = db.relationship('PipelineMetric', backref='pipeline', lazy=True)
    alerts = db.relationship('Alert', backref='pipeline', lazy=True)
    
    def get_latest_run(self):
        """Get the most recent pipeline run"""
        return self.runs[0] if self.runs else None
    
    def get_latest_successful_run(self):
        """Get the most recent successful pipeline run"""
        for run in self.runs:
            if run.status == RunStatus.SUCCESS:
                return run
        return None
    
    def is_healthy(self):
        """Check if pipeline is healthy based on latest run and metrics"""
        latest_run = self.get_latest_run()
        if not latest_run:
            return False
        
        # Check if last run was successful
        if latest_run.status != RunStatus.SUCCESS:
            return False
        
        # Check freshness
        if self.freshness_threshold_hours:
            hours_since_run = (datetime.utcnow() - latest_run.started_at).total_seconds() / 3600
            if hours_since_run > self.freshness_threshold_hours:
                return False
        
        return True
    
    def get_uptime_percentage(self, days=30):
        """Calculate uptime percentage for the last N days"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_runs = [run for run in self.runs if run.started_at >= cutoff_date]
        
        if not recent_runs:
            return 0.0
        
        successful_runs = [run for run in recent_runs if run.status == RunStatus.SUCCESS]
        return (len(successful_runs) / len(recent_runs)) * 100
    
    def to_dict(self):
        """Convert pipeline to dictionary"""
        latest_run = self.get_latest_run()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'pipeline_type': self.pipeline_type.value,
            'status': self.status.value,
            'config': self.config,
            'schedule': self.schedule,
            'timeout_minutes': self.timeout_minutes,
            'retry_attempts': self.retry_attempts,
            'retry_delay_minutes': self.retry_delay_minutes,
            'health_check_enabled': self.health_check_enabled,
            'freshness_threshold_hours': self.freshness_threshold_hours,
            'volume_threshold_percent': self.volume_threshold_percent,
            'auto_heal_enabled': self.auto_heal_enabled,
            'tags': self.tags,
            'organization_id': self.organization_id,
            'created_by': self.created_by,
            'data_source_id': self.data_source_id,
            'is_healthy': self.is_healthy(),
            'uptime_percentage': self.get_uptime_percentage(),
            'latest_run': latest_run.to_dict() if latest_run else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None
        }
    
    def __repr__(self):
        return f'<Pipeline {self.name}>'

class PipelineRun(db.Model):
    """Individual pipeline execution run"""
    __tablename__ = 'pipeline_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey('pipelines.id'), nullable=False)
    
    # Run details
    status = db.Column(db.Enum(RunStatus), default=RunStatus.PENDING)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)
    
    # Execution details
    input_data = db.Column(db.JSON)  # Input parameters/data
    output_data = db.Column(db.JSON)  # Output results
    error_message = db.Column(db.Text)
    error_details = db.Column(db.JSON)
    
    # Metrics
    records_processed = db.Column(db.Integer)
    records_failed = db.Column(db.Integer)
    data_volume_mb = db.Column(db.Float)
    
    # Retry information
    retry_count = db.Column(db.Integer, default=0)
    is_retry = db.Column(db.Boolean, default=False)
    original_run_id = db.Column(db.Integer, db.ForeignKey('pipeline_runs.id'))
    
    # Relationships
    retries = db.relationship('PipelineRun', backref=db.backref('original_run', remote_side=[id]))
    
    def is_completed(self):
        """Check if run is completed (success or failed)"""
        return self.status in [RunStatus.SUCCESS, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.TIMEOUT]
    
    def is_successful(self):
        """Check if run was successful"""
        return self.status == RunStatus.SUCCESS
    
    def is_failed(self):
        """Check if run failed"""
        return self.status in [RunStatus.FAILED, RunStatus.TIMEOUT]
    
    def get_duration_formatted(self):
        """Get formatted duration string"""
        if not self.duration_seconds:
            return None
        
        hours = int(self.duration_seconds // 3600)
        minutes = int((self.duration_seconds % 3600) // 60)
        seconds = int(self.duration_seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def to_dict(self):
        """Convert run to dictionary"""
        return {
            'id': self.id,
            'pipeline_id': self.pipeline_id,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'duration_formatted': self.get_duration_formatted(),
            'input_data': self.input_data,
            'output_data': self.output_data,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'records_processed': self.records_processed,
            'records_failed': self.records_failed,
            'data_volume_mb': self.data_volume_mb,
            'retry_count': self.retry_count,
            'is_retry': self.is_retry,
            'original_run_id': self.original_run_id,
            'is_completed': self.is_completed(),
            'is_successful': self.is_successful(),
            'is_failed': self.is_failed()
        }
    
    def __repr__(self):
        return f'<PipelineRun {self.id} - {self.status.value}>'

class PipelineMetric(db.Model):
    """Pipeline performance and health metrics"""
    __tablename__ = 'pipeline_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey('pipelines.id'), nullable=False)
    
    # Metric details
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    metric_unit = db.Column(db.String(20))  # seconds, records, MB, etc.
    
    # Context
    run_id = db.Column(db.Integer, db.ForeignKey('pipeline_runs.id'))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional data
    metadata = db.Column(db.JSON)  # Additional context
    
    def to_dict(self):
        """Convert metric to dictionary"""
        return {
            'id': self.id,
            'pipeline_id': self.pipeline_id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'run_id': self.run_id,
            'recorded_at': self.recorded_at.isoformat(),
            'metadata': self.metadata
        }
    
    def __repr__(self):
        return f'<PipelineMetric {self.metric_name}: {self.metric_value} {self.metric_unit}>' 