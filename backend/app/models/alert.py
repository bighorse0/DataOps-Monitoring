from app import db
from datetime import datetime
from enum import Enum
import json

class AlertSeverity(Enum):
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'
    EMERGENCY = 'emergency'

class AlertStatus(Enum):
    ACTIVE = 'active'
    ACKNOWLEDGED = 'acknowledged'
    RESOLVED = 'resolved'
    SUPPRESSED = 'suppressed'

class AlertChannel(Enum):
    EMAIL = 'email'
    SLACK = 'slack'
    SMS = 'sms'
    WEBHOOK = 'webhook'
    IN_APP = 'in_app'

class AlertRule(db.Model):
    """Alert rule configuration"""
    __tablename__ = 'alert_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Rule configuration
    rule_type = db.Column(db.String(50), nullable=False)  # pipeline_failure, health_check, custom
    conditions = db.Column(db.JSON, nullable=False)  # Rule conditions
    severity = db.Column(db.Enum(AlertSeverity), default=AlertSeverity.WARNING)
    
    # Alerting settings
    channels = db.Column(db.JSON, default=list)  # ['email', 'slack']
    recipients = db.Column(db.JSON, default=list)  # List of recipient emails/IDs
    cooldown_minutes = db.Column(db.Integer, default=60)
    
    # Escalation
    escalation_enabled = db.Column(db.Boolean, default=False)
    escalation_delay_minutes = db.Column(db.Integer, default=30)
    escalation_recipients = db.Column(db.JSON, default=list)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pipeline_id = db.Column(db.Integer, db.ForeignKey('pipelines.id'))
    health_check_id = db.Column(db.Integer, db.ForeignKey('health_checks.id'))
    
    # Relationships
    alerts = db.relationship('Alert', backref='alert_rule', lazy=True)
    
    def should_trigger(self, context_data):
        """Check if alert rule should trigger based on context"""
        if not self.is_active:
            return False
        
        # Check cooldown
        if self.cooldown_minutes:
            last_alert = self.get_last_alert()
            if last_alert:
                time_since_last = (datetime.utcnow() - last_alert.created_at).total_seconds() / 60
                if time_since_last < self.cooldown_minutes:
                    return False
        
        # Evaluate conditions based on rule type
        if self.rule_type == 'pipeline_failure':
            return self._evaluate_pipeline_conditions(context_data)
        elif self.rule_type == 'health_check':
            return self._evaluate_health_check_conditions(context_data)
        elif self.rule_type == 'custom':
            return self._evaluate_custom_conditions(context_data)
        
        return False
    
    def _evaluate_pipeline_conditions(self, context_data):
        """Evaluate pipeline-specific conditions"""
        conditions = self.conditions
        
        # Check pipeline status
        if 'status' in conditions:
            if context_data.get('status') != conditions['status']:
                return False
        
        # Check failure count
        if 'failure_count' in conditions:
            if context_data.get('failure_count', 0) < conditions['failure_count']:
                return False
        
        # Check duration threshold
        if 'duration_threshold' in conditions:
            if context_data.get('duration_seconds', 0) < conditions['duration_threshold']:
                return False
        
        return True
    
    def _evaluate_health_check_conditions(self, context_data):
        """Evaluate health check-specific conditions"""
        conditions = self.conditions
        
        # Check health check status
        if 'status' in conditions:
            if context_data.get('status') != conditions['status']:
                return False
        
        # Check metric thresholds
        if 'metric_threshold' in conditions:
            metric_value = context_data.get('metric_value', 0)
            threshold = conditions['metric_threshold']
            operator = conditions.get('operator', '>')
            
            if operator == '>' and metric_value <= threshold:
                return False
            elif operator == '<' and metric_value >= threshold:
                return False
            elif operator == '==' and metric_value != threshold:
                return False
        
        return True
    
    def _evaluate_custom_conditions(self, context_data):
        """Evaluate custom conditions"""
        # This would be implemented based on custom logic
        # For now, return True if conditions are met
        return True
    
    def get_last_alert(self):
        """Get the most recent alert for this rule"""
        if not self.alerts:
            return None
        return max(self.alerts, key=lambda x: x.created_at)
    
    def to_dict(self):
        """Convert alert rule to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'rule_type': self.rule_type,
            'conditions': self.conditions,
            'severity': self.severity.value,
            'channels': self.channels,
            'recipients': self.recipients,
            'cooldown_minutes': self.cooldown_minutes,
            'escalation_enabled': self.escalation_enabled,
            'escalation_delay_minutes': self.escalation_delay_minutes,
            'escalation_recipients': self.escalation_recipients,
            'is_active': self.is_active,
            'organization_id': self.organization_id,
            'created_by': self.created_by,
            'pipeline_id': self.pipeline_id,
            'health_check_id': self.health_check_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<AlertRule {self.name} ({self.rule_type})>'

class Alert(db.Model):
    """Individual alert instance"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_rule_id = db.Column(db.Integer, db.ForeignKey('alert_rules.id'), nullable=False)
    
    # Alert details
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Enum(AlertSeverity), nullable=False)
    status = db.Column(db.Enum(AlertStatus), default=AlertStatus.ACTIVE)
    
    # Context
    context_data = db.Column(db.JSON)  # Data that triggered the alert
    source_type = db.Column(db.String(50))  # pipeline, health_check, custom
    source_id = db.Column(db.Integer)  # ID of the source that triggered alert
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    acknowledged_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Foreign keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pipeline_id = db.Column(db.Integer, db.ForeignKey('pipelines.id'))
    
    # Relationships
    history = db.relationship('AlertHistory', backref='alert', lazy=True, order_by='AlertHistory.created_at.desc()')
    
    def is_active(self):
        """Check if alert is currently active"""
        return self.status == AlertStatus.ACTIVE
    
    def is_acknowledged(self):
        """Check if alert has been acknowledged"""
        return self.status == AlertStatus.ACKNOWLEDGED
    
    def is_resolved(self):
        """Check if alert has been resolved"""
        return self.status == AlertStatus.RESOLVED
    
    def acknowledge(self, user_id):
        """Acknowledge the alert"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user_id
        self.updated_at = datetime.utcnow()
    
    def resolve(self, user_id):
        """Resolve the alert"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user_id
        self.updated_at = datetime.utcnow()
    
    def get_duration_minutes(self):
        """Get duration of alert in minutes"""
        if self.is_resolved() and self.resolved_at:
            return (self.resolved_at - self.created_at).total_seconds() / 60
        elif self.is_acknowledged() and self.acknowledged_at:
            return (self.acknowledged_at - self.created_at).total_seconds() / 60
        else:
            return (datetime.utcnow() - self.created_at).total_seconds() / 60
    
    def to_dict(self):
        """Convert alert to dictionary"""
        return {
            'id': self.id,
            'alert_rule_id': self.alert_rule_id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'status': self.status.value,
            'context_data': self.context_data,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'organization_id': self.organization_id,
            'created_by': self.created_by,
            'pipeline_id': self.pipeline_id,
            'is_active': self.is_active(),
            'is_acknowledged': self.is_acknowledged(),
            'is_resolved': self.is_resolved(),
            'duration_minutes': self.get_duration_minutes(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_by': self.acknowledged_by,
            'resolved_by': self.resolved_by
        }
    
    def __repr__(self):
        return f'<Alert {self.id} - {self.title}>'

class AlertHistory(db.Model):
    """Alert history for tracking changes and notifications"""
    __tablename__ = 'alert_history'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id'), nullable=False)
    
    # History details
    action = db.Column(db.String(50), nullable=False)  # created, acknowledged, resolved, notification_sent
    description = db.Column(db.Text)
    
    # Notification details
    channel = db.Column(db.Enum(AlertChannel))
    recipient = db.Column(db.String(200))
    sent_at = db.Column(db.DateTime)
    success = db.Column(db.Boolean)
    error_message = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def to_dict(self):
        """Convert alert history to dictionary"""
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'action': self.action,
            'description': self.description,
            'channel': self.channel.value if self.channel else None,
            'recipient': self.recipient,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'success': self.success,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }
    
    def __repr__(self):
        return f'<AlertHistory {self.id} - {self.action}>' 