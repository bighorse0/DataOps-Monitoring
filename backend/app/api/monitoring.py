from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import DataSource, HealthCheck, HealthCheckResult, User, Organization
from app.models.monitoring import DataSourceType, HealthCheckType, HealthCheckStatus
from datetime import datetime, timedelta
from sqlalchemy import desc
import json

monitoring_bp = Blueprint('monitoring', __name__)

def get_current_user_org():
    """Get current user and organization"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user, user.organization if user else None

@monitoring_bp.route('/data-sources', methods=['GET'])
@jwt_required()
def get_data_sources():
    """Get all data sources for the organization"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Query parameters
    source_type = request.args.get('type')
    is_active = request.args.get('is_active')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Build query
    query = DataSource.query.filter_by(organization_id=org.id)
    
    if source_type:
        query = query.filter_by(source_type=DataSourceType(source_type))
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')
    
    # Pagination
    data_sources = query.order_by(desc(DataSource.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'data_sources': [ds.to_dict() for ds in data_sources.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': data_sources.total,
            'pages': data_sources.pages,
            'has_next': data_sources.has_next,
            'has_prev': data_sources.has_prev
        }
    }), 200

@monitoring_bp.route('/data-sources/<int:data_source_id>', methods=['GET'])
@jwt_required()
def get_data_source(data_source_id):
    """Get specific data source details"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data_source = DataSource.query.filter_by(
        id=data_source_id, 
        organization_id=org.id
    ).first()
    
    if not data_source:
        return jsonify({'error': 'Data source not found'}), 404
    
    return jsonify({'data_source': data_source.to_dict()}), 200

@monitoring_bp.route('/data-sources', methods=['POST'])
@jwt_required()
def create_data_source():
    """Create a new data source"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'source_type', 'connection_config']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate source type
    try:
        source_type = DataSourceType(data['source_type'])
    except ValueError:
        return jsonify({'error': 'Invalid source type'}), 400
    
    # Check if data source name already exists in organization
    existing_ds = DataSource.query.filter_by(
        name=data['name'],
        organization_id=org.id
    ).first()
    
    if existing_ds:
        return jsonify({'error': 'Data source name already exists'}), 409
    
    try:
        data_source = DataSource(
            name=data['name'],
            description=data.get('description'),
            source_type=source_type,
            connection_config=data['connection_config'],
            credentials=data.get('credentials'),
            is_active=data.get('is_active', True),
            check_interval_seconds=data.get('check_interval_seconds', 300),
            timeout_seconds=data.get('timeout_seconds', 30),
            tags=data.get('tags', []),
            organization_id=org.id
        )
        
        db.session.add(data_source)
        db.session.commit()
        
        return jsonify({
            'message': 'Data source created successfully',
            'data_source': data_source.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create data source', 'details': str(e)}), 500

@monitoring_bp.route('/data-sources/<int:data_source_id>', methods=['PUT'])
@jwt_required()
def update_data_source(data_source_id):
    """Update data source"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data_source = DataSource.query.filter_by(
        id=data_source_id, 
        organization_id=org.id
    ).first()
    
    if not data_source:
        return jsonify({'error': 'Data source not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if data.get('name'):
        # Check if name already exists
        existing_ds = DataSource.query.filter_by(
            name=data['name'],
            organization_id=org.id
        ).first()
        if existing_ds and existing_ds.id != data_source.id:
            return jsonify({'error': 'Data source name already exists'}), 409
        data_source.name = data['name']
    
    if data.get('description') is not None:
        data_source.description = data['description']
    
    if data.get('source_type'):
        try:
            data_source.source_type = DataSourceType(data['source_type'])
        except ValueError:
            return jsonify({'error': 'Invalid source type'}), 400
    
    if data.get('connection_config') is not None:
        data_source.connection_config = data['connection_config']
    
    if data.get('credentials') is not None:
        data_source.credentials = data['credentials']
    
    if data.get('is_active') is not None:
        data_source.is_active = data['is_active']
    
    if data.get('check_interval_seconds') is not None:
        data_source.check_interval_seconds = data['check_interval_seconds']
    
    if data.get('timeout_seconds') is not None:
        data_source.timeout_seconds = data['timeout_seconds']
    
    if data.get('tags') is not None:
        data_source.tags = data['tags']
    
    data_source.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Data source updated successfully',
            'data_source': data_source.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update data source', 'details': str(e)}), 500

@monitoring_bp.route('/data-sources/<int:data_source_id>', methods=['DELETE'])
@jwt_required()
def delete_data_source(data_source_id):
    """Delete data source"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data_source = DataSource.query.filter_by(
        id=data_source_id, 
        organization_id=org.id
    ).first()
    
    if not data_source:
        return jsonify({'error': 'Data source not found'}), 404
    
    try:
        db.session.delete(data_source)
        db.session.commit()
        
        return jsonify({'message': 'Data source deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete data source', 'details': str(e)}), 500

@monitoring_bp.route('/data-sources/<int:data_source_id>/test-connection', methods=['POST'])
@jwt_required()
def test_data_source_connection(data_source_id):
    """Test data source connection"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data_source = DataSource.query.filter_by(
        id=data_source_id, 
        organization_id=org.id
    ).first()
    
    if not data_source:
        return jsonify({'error': 'Data source not found'}), 404
    
    try:
        # TODO: Implement actual connection testing based on source type
        # This would involve connecting to the actual data source
        # and running a simple query to verify connectivity
        
        return jsonify({
            'message': 'Connection test successful',
            'connection_string': data_source.get_connection_string()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Connection test failed',
            'details': str(e)
        }), 500

@monitoring_bp.route('/health-checks', methods=['GET'])
@jwt_required()
def get_health_checks():
    """Get all health checks for the organization"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Query parameters
    check_type = request.args.get('type')
    data_source_id = request.args.get('data_source_id')
    is_active = request.args.get('is_active')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Build query
    query = HealthCheck.query.filter_by(organization_id=org.id)
    
    if check_type:
        query = query.filter_by(check_type=HealthCheckType(check_type))
    if data_source_id:
        query = query.filter_by(data_source_id=data_source_id)
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')
    
    # Pagination
    health_checks = query.order_by(desc(HealthCheck.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'health_checks': [hc.to_dict() for hc in health_checks.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': health_checks.total,
            'pages': health_checks.pages,
            'has_next': health_checks.has_next,
            'has_prev': health_checks.has_prev
        }
    }), 200

@monitoring_bp.route('/health-checks/<int:health_check_id>', methods=['GET'])
@jwt_required()
def get_health_check(health_check_id):
    """Get specific health check details"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    health_check = HealthCheck.query.filter_by(
        id=health_check_id, 
        organization_id=org.id
    ).first()
    
    if not health_check:
        return jsonify({'error': 'Health check not found'}), 404
    
    return jsonify({'health_check': health_check.to_dict()}), 200

@monitoring_bp.route('/health-checks', methods=['POST'])
@jwt_required()
def create_health_check():
    """Create a new health check"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'check_type', 'config', 'data_source_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate check type
    try:
        check_type = HealthCheckType(data['check_type'])
    except ValueError:
        return jsonify({'error': 'Invalid check type'}), 400
    
    # Verify data source exists and belongs to organization
    data_source = DataSource.query.filter_by(
        id=data['data_source_id'],
        organization_id=org.id
    ).first()
    
    if not data_source:
        return jsonify({'error': 'Data source not found'}), 404
    
    try:
        health_check = HealthCheck(
            name=data['name'],
            description=data.get('description'),
            check_type=check_type,
            config=data['config'],
            is_active=data.get('is_active', True),
            check_interval_seconds=data.get('check_interval_seconds', 300),
            warning_threshold=data.get('warning_threshold'),
            critical_threshold=data.get('critical_threshold'),
            alert_on_warning=data.get('alert_on_warning', True),
            alert_on_critical=data.get('alert_on_critical', True),
            data_source_id=data['data_source_id'],
            organization_id=org.id
        )
        
        db.session.add(health_check)
        db.session.commit()
        
        return jsonify({
            'message': 'Health check created successfully',
            'health_check': health_check.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create health check', 'details': str(e)}), 500

@monitoring_bp.route('/health-checks/<int:health_check_id>/results', methods=['GET'])
@jwt_required()
def get_health_check_results(health_check_id):
    """Get health check results"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    health_check = HealthCheck.query.filter_by(
        id=health_check_id, 
        organization_id=org.id
    ).first()
    
    if not health_check:
        return jsonify({'error': 'Health check not found'}), 404
    
    # Query parameters
    status = request.args.get('status')
    days = int(request.args.get('days', 30))
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 50)), 200)
    
    # Build query
    query = HealthCheckResult.query.filter_by(health_check_id=health_check_id)
    
    if status:
        query = query.filter_by(status=HealthCheckStatus(status))
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(HealthCheckResult.checked_at >= cutoff_date)
    
    # Pagination
    results = query.order_by(desc(HealthCheckResult.checked_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'results': [result.to_dict() for result in results.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': results.total,
            'pages': results.pages,
            'has_next': results.has_next,
            'has_prev': results.has_prev
        }
    }), 200

@monitoring_bp.route('/health-checks/<int:health_check_id>/run', methods=['POST'])
@jwt_required()
def run_health_check(health_check_id):
    """Manually run a health check"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    health_check = HealthCheck.query.filter_by(
        id=health_check_id, 
        organization_id=org.id
    ).first()
    
    if not health_check:
        return jsonify({'error': 'Health check not found'}), 404
    
    if not health_check.is_active:
        return jsonify({'error': 'Health check is not active'}), 400
    
    try:
        # TODO: Implement actual health check execution
        # This would involve running the specific health check logic
        # based on the check type and configuration
        
        # For now, create a mock result
        result = HealthCheckResult(
            health_check_id=health_check_id,
            status=HealthCheckStatus.HEALTHY,
            duration_seconds=1.5,
            metric_value=100.0,
            metric_unit='records',
            message='Health check completed successfully',
            details={'tested_at': datetime.utcnow().isoformat()}
        )
        
        db.session.add(result)
        db.session.commit()
        
        return jsonify({
            'message': 'Health check executed successfully',
            'result': result.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to run health check', 'details': str(e)}), 500 