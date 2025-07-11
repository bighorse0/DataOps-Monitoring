from app import db
from datetime import datetime
from enum import Enum

class SubscriptionTier(Enum):
    STARTER = 'starter'
    PROFESSIONAL = 'professional'
    ENTERPRISE = 'enterprise'

class Organization(db.Model):
    """Organization model for multi-tenant support"""
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(100))
    subscription_tier = db.Column(db.Enum(SubscriptionTier), default=SubscriptionTier.STARTER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    settings = db.relationship('OrganizationSettings', backref='organization', uselist=False)
    pipelines = db.relationship('Pipeline', backref='organization', lazy=True)
    data_sources = db.relationship('DataSource', backref='organization', lazy=True)
    alerts = db.relationship('Alert', backref='organization', lazy=True)
    
    def get_pipeline_limit(self):
        """Get pipeline limit based on subscription tier"""
        limits = {
            SubscriptionTier.STARTER: 10,
            SubscriptionTier.PROFESSIONAL: 50,
            SubscriptionTier.ENTERPRISE: -1  # Unlimited
        }
        return limits.get(self.subscription_tier, 10)
    
    def can_add_pipeline(self):
        """Check if organization can add more pipelines"""
        if self.subscription_tier == SubscriptionTier.ENTERPRISE:
            return True
        current_count = len(self.pipelines)
        limit = self.get_pipeline_limit()
        return current_count < limit
    
    def to_dict(self):
        """Convert organization to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'domain': self.domain,
            'subscription_tier': self.subscription_tier.value,
            'is_active': self.is_active,
            'pipeline_limit': self.get_pipeline_limit(),
            'current_pipelines': len(self.pipelines),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Organization {self.name}>'

class OrganizationSettings(db.Model):
    """Organization-specific settings and configurations"""
    __tablename__ = 'organization_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Alert Settings
    default_alert_channels = db.Column(db.JSON, default=list)  # ['email', 'slack']
    alert_cooldown_minutes = db.Column(db.Integer, default=60)
    escalation_enabled = db.Column(db.Boolean, default=False)
    escalation_delay_minutes = db.Column(db.Integer, default=30)
    
    # Monitoring Settings
    default_check_interval_seconds = db.Column(db.Integer, default=300)  # 5 minutes
    max_retry_attempts = db.Column(db.Integer, default=3)
    data_retention_days = db.Column(db.Integer, default=90)
    
    # Integration Settings
    slack_webhook_url = db.Column(db.String(500))
    slack_channel = db.Column(db.String(100))
    email_notifications_enabled = db.Column(db.Boolean, default=True)
    sms_notifications_enabled = db.Column(db.Boolean, default=False)
    
    # Custom Branding
    logo_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(7), default='#3B82F6')  # Hex color
    company_name = db.Column(db.String(100))
    
    # Timezone and Locale
    timezone = db.Column(db.String(50), default='UTC')
    locale = db.Column(db.String(10), default='en')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert settings to dictionary"""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'default_alert_channels': self.default_alert_channels,
            'alert_cooldown_minutes': self.alert_cooldown_minutes,
            'escalation_enabled': self.escalation_enabled,
            'escalation_delay_minutes': self.escalation_delay_minutes,
            'default_check_interval_seconds': self.default_check_interval_seconds,
            'max_retry_attempts': self.max_retry_attempts,
            'data_retention_days': self.data_retention_days,
            'slack_webhook_url': self.slack_webhook_url,
            'slack_channel': self.slack_channel,
            'email_notifications_enabled': self.email_notifications_enabled,
            'sms_notifications_enabled': self.sms_notifications_enabled,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'company_name': self.company_name,
            'timezone': self.timezone,
            'locale': self.locale,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<OrganizationSettings {self.organization_id}>' 