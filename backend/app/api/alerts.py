from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Alert, AlertRule, AlertHistory, User, Organization
from app.models.alert import AlertSeverity, AlertStatus, AlertChannel
from datetime import datetime, timedelta
from sqlalchemy import desc
import json

alerts_bp = Blueprint('alerts', __name__)

def get_current_user_org():
    """Get current user and organization"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user, user.organization if user else None

@alerts_bp.route('/rules', methods=['GET'])
@jwt_required()
def get_alert_rules():
    """Get all alert rules for the organization"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Query parameters
    rule_type = request.args.get('type')
    is_active = request.args.get('is_active')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Build query
    query = AlertRule.query.filter_by(organization_id=org.id)
    
    if rule_type:
        query = query.filter_by(rule_type=rule_type)
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')
    
    # Pagination
    alert_rules = query.order_by(desc(AlertRule.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'alert_rules': [rule.to_dict() for rule in alert_rules.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': alert_rules.total,
            'pages': alert_rules.pages,
            'has_next': alert_rules.has_next,
            'has_prev': alert_rules.has_prev
        }
    }), 200

@alerts_bp.route('/rules/<int:rule_id>', methods=['GET'])
@jwt_required()
def get_alert_rule(rule_id):
    """Get specific alert rule details"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    alert_rule = AlertRule.query.filter_by(
        id=rule_id, 
        organization_id=org.id
    ).first()
    
    if not alert_rule:
        return jsonify({'error': 'Alert rule not found'}), 404
    
    return jsonify({'alert_rule': alert_rule.to_dict()}), 200

@alerts_bp.route('/rules', methods=['POST'])
@jwt_required()
def create_alert_rule():
    """Create a new alert rule"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'rule_type', 'conditions']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate severity
    try:
        severity = AlertSeverity(data.get('severity', 'warning'))
    except ValueError:
        return jsonify({'error': 'Invalid severity level'}), 400
    
    try:
        alert_rule = AlertRule(
            name=data['name'],
            description=data.get('description'),
            rule_type=data['rule_type'],
            conditions=data['conditions'],
            severity=severity,
            channels=data.get('channels', ['email']),
            recipients=data.get('recipients', []),
            cooldown_minutes=data.get('cooldown_minutes', 60),
            escalation_enabled=data.get('escalation_enabled', False),
            escalation_delay_minutes=data.get('escalation_delay_minutes', 30),
            escalation_recipients=data.get('escalation_recipients', []),
            is_active=data.get('is_active', True),
            organization_id=org.id,
            created_by=user.id,
            pipeline_id=data.get('pipeline_id'),
            health_check_id=data.get('health_check_id')
        )
        
        db.session.add(alert_rule)
        db.session.commit()
        
        return jsonify({
            'message': 'Alert rule created successfully',
            'alert_rule': alert_rule.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create alert rule', 'details': str(e)}), 500

@alerts_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@jwt_required()
def update_alert_rule(rule_id):
    """Update alert rule"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    alert_rule = AlertRule.query.filter_by(
        id=rule_id, 
        organization_id=org.id
    ).first()
    
    if not alert_rule:
        return jsonify({'error': 'Alert rule not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if data.get('name'):
        alert_rule.name = data['name']
    
    if data.get('description') is not None:
        alert_rule.description = data['description']
    
    if data.get('rule_type'):
        alert_rule.rule_type = data['rule_type']
    
    if data.get('conditions') is not None:
        alert_rule.conditions = data['conditions']
    
    if data.get('severity'):
        try:
            alert_rule.severity = AlertSeverity(data['severity'])
        except ValueError:
            return jsonify({'error': 'Invalid severity level'}), 400
    
    if data.get('channels') is not None:
        alert_rule.channels = data['channels']
    
    if data.get('recipients') is not None:
        alert_rule.recipients = data['recipients']
    
    if data.get('cooldown_minutes') is not None:
        alert_rule.cooldown_minutes = data['cooldown_minutes']
    
    if data.get('escalation_enabled') is not None:
        alert_rule.escalation_enabled = data['escalation_enabled']
    
    if data.get('escalation_delay_minutes') is not None:
        alert_rule.escalation_delay_minutes = data['escalation_delay_minutes']
    
    if data.get('escalation_recipients') is not None:
        alert_rule.escalation_recipients = data['escalation_recipients']
    
    if data.get('is_active') is not None:
        alert_rule.is_active = data['is_active']
    
    if data.get('pipeline_id') is not None:
        alert_rule.pipeline_id = data['pipeline_id']
    
    if data.get('health_check_id') is not None:
        alert_rule.health_check_id = data['health_check_id']
    
    alert_rule.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Alert rule updated successfully',
            'alert_rule': alert_rule.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update alert rule', 'details': str(e)}), 500

@alerts_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@jwt_required()
def delete_alert_rule(rule_id):
    """Delete alert rule"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    alert_rule = AlertRule.query.filter_by(
        id=rule_id, 
        organization_id=org.id
    ).first()
    
    if not alert_rule:
        return jsonify({'error': 'Alert rule not found'}), 404
    
    try:
        db.session.delete(alert_rule)
        db.session.commit()
        
        return jsonify({'message': 'Alert rule deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete alert rule', 'details': str(e)}), 500

@alerts_bp.route('/', methods=['GET'])
@jwt_required()
def get_alerts():
    """Get all alerts for the organization"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Query parameters
    status = request.args.get('status')
    severity = request.args.get('severity')
    source_type = request.args.get('source_type')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Build query
    query = Alert.query.filter_by(organization_id=org.id)
    
    if status:
        query = query.filter_by(status=AlertStatus(status))
    if severity:
        query = query.filter_by(severity=AlertSeverity(severity))
    if source_type:
        query = query.filter_by(source_type=source_type)
    
    # Pagination
    alerts = query.order_by(desc(Alert.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'alerts': [alert.to_dict() for alert in alerts.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': alerts.total,
            'pages': alerts.pages,
            'has_next': alerts.has_next,
            'has_prev': alerts.has_prev
        }
    }), 200

@alerts_bp.route('/<int:alert_id>', methods=['GET'])
@jwt_required()
def get_alert(alert_id):
    """Get specific alert details"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    alert = Alert.query.filter_by(
        id=alert_id, 
        organization_id=org.id
    ).first()
    
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    
    return jsonify({'alert': alert.to_dict()}), 200

@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['POST'])
@jwt_required()
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    alert = Alert.query.filter_by(
        id=alert_id, 
        organization_id=org.id
    ).first()
    
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    
    if alert.is_acknowledged():
        return jsonify({'error': 'Alert is already acknowledged'}), 400
    
    try:
        alert.acknowledge(user.id)
        
        # Create history entry
        history = AlertHistory(
            alert_id=alert_id,
            action='acknowledged',
            description=f'Alert acknowledged by {user.username}',
            created_by=user.id
        )
        db.session.add(history)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Alert acknowledged successfully',
            'alert': alert.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to acknowledge alert', 'details': str(e)}), 500

@alerts_bp.route('/<int:alert_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_alert(alert_id):
    """Resolve an alert"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    alert = Alert.query.filter_by(
        id=alert_id, 
        organization_id=org.id
    ).first()
    
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    
    if alert.is_resolved():
        return jsonify({'error': 'Alert is already resolved'}), 400
    
    try:
        alert.resolve(user.id)
        
        # Create history entry
        history = AlertHistory(
            alert_id=alert_id,
            action='resolved',
            description=f'Alert resolved by {user.username}',
            created_by=user.id
        )
        db.session.add(history)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Alert resolved successfully',
            'alert': alert.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to resolve alert', 'details': str(e)}), 500

@alerts_bp.route('/<int:alert_id>/history', methods=['GET'])
@jwt_required()
def get_alert_history(alert_id):
    """Get alert history"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    alert = Alert.query.filter_by(
        id=alert_id, 
        organization_id=org.id
    ).first()
    
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    
    history = AlertHistory.query.filter_by(alert_id=alert_id).order_by(
        desc(AlertHistory.created_at)
    ).all()
    
    return jsonify({
        'history': [entry.to_dict() for entry in history]
    }), 200 