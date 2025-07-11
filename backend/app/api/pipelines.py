from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Pipeline, PipelineRun, PipelineMetric, User, Organization
from app.models.pipeline import PipelineType, PipelineStatus, RunStatus
from datetime import datetime, timedelta
from sqlalchemy import desc
import json

pipelines_bp = Blueprint('pipelines', __name__)

def get_current_user_org():
    """Get current user and organization"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user, user.organization if user else None

@pipelines_bp.route('/', methods=['GET'])
@jwt_required()
def get_pipelines():
    """Get all pipelines for the organization"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Query parameters
    status = request.args.get('status')
    pipeline_type = request.args.get('type')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Build query
    query = Pipeline.query.filter_by(organization_id=org.id)
    
    if status:
        query = query.filter_by(status=PipelineStatus(status))
    if pipeline_type:
        query = query.filter_by(pipeline_type=PipelineType(pipeline_type))
    
    # Pagination
    pipelines = query.order_by(desc(Pipeline.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'pipelines': [pipeline.to_dict() for pipeline in pipelines.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pipelines.total,
            'pages': pipelines.pages,
            'has_next': pipelines.has_next,
            'has_prev': pipelines.has_prev
        }
    }), 200

@pipelines_bp.route('/<int:pipeline_id>', methods=['GET'])
@jwt_required()
def get_pipeline(pipeline_id):
    """Get specific pipeline details"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    pipeline = Pipeline.query.filter_by(
        id=pipeline_id, 
        organization_id=org.id
    ).first()
    
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    
    return jsonify({'pipeline': pipeline.to_dict()}), 200

@pipelines_bp.route('/', methods=['POST'])
@jwt_required()
def create_pipeline():
    """Create a new pipeline"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Check pipeline limit
    if not org.can_add_pipeline():
        return jsonify({
            'error': f'Pipeline limit reached ({org.get_pipeline_limit()} pipelines)'
        }), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'pipeline_type']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate pipeline type
    try:
        pipeline_type = PipelineType(data['pipeline_type'])
    except ValueError:
        return jsonify({'error': 'Invalid pipeline type'}), 400
    
    # Check if pipeline name already exists in organization
    existing_pipeline = Pipeline.query.filter_by(
        name=data['name'],
        organization_id=org.id
    ).first()
    
    if existing_pipeline:
        return jsonify({'error': 'Pipeline name already exists'}), 409
    
    try:
        pipeline = Pipeline(
            name=data['name'],
            description=data.get('description'),
            pipeline_type=pipeline_type,
            status=PipelineStatus.ACTIVE,
            config=data.get('config', {}),
            schedule=data.get('schedule'),
            timeout_minutes=data.get('timeout_minutes', 60),
            retry_attempts=data.get('retry_attempts', 3),
            retry_delay_minutes=data.get('retry_delay_minutes', 5),
            health_check_enabled=data.get('health_check_enabled', True),
            freshness_threshold_hours=data.get('freshness_threshold_hours', 24),
            volume_threshold_percent=data.get('volume_threshold_percent', 10.0),
            auto_heal_enabled=data.get('auto_heal_enabled', False),
            heal_script=data.get('heal_script'),
            tags=data.get('tags', []),
            organization_id=org.id,
            created_by=user.id,
            data_source_id=data.get('data_source_id')
        )
        
        db.session.add(pipeline)
        db.session.commit()
        
        return jsonify({
            'message': 'Pipeline created successfully',
            'pipeline': pipeline.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create pipeline', 'details': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>', methods=['PUT'])
@jwt_required()
def update_pipeline(pipeline_id):
    """Update pipeline"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    pipeline = Pipeline.query.filter_by(
        id=pipeline_id, 
        organization_id=org.id
    ).first()
    
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if data.get('name'):
        # Check if name already exists
        existing_pipeline = Pipeline.query.filter_by(
            name=data['name'],
            organization_id=org.id
        ).first()
        if existing_pipeline and existing_pipeline.id != pipeline.id:
            return jsonify({'error': 'Pipeline name already exists'}), 409
        pipeline.name = data['name']
    
    if data.get('description') is not None:
        pipeline.description = data['description']
    
    if data.get('pipeline_type'):
        try:
            pipeline.pipeline_type = PipelineType(data['pipeline_type'])
        except ValueError:
            return jsonify({'error': 'Invalid pipeline type'}), 400
    
    if data.get('status'):
        try:
            pipeline.status = PipelineStatus(data['status'])
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if data.get('config') is not None:
        pipeline.config = data['config']
    
    if data.get('schedule') is not None:
        pipeline.schedule = data['schedule']
    
    if data.get('timeout_minutes') is not None:
        pipeline.timeout_minutes = data['timeout_minutes']
    
    if data.get('retry_attempts') is not None:
        pipeline.retry_attempts = data['retry_attempts']
    
    if data.get('retry_delay_minutes') is not None:
        pipeline.retry_delay_minutes = data['retry_delay_minutes']
    
    if data.get('health_check_enabled') is not None:
        pipeline.health_check_enabled = data['health_check_enabled']
    
    if data.get('freshness_threshold_hours') is not None:
        pipeline.freshness_threshold_hours = data['freshness_threshold_hours']
    
    if data.get('volume_threshold_percent') is not None:
        pipeline.volume_threshold_percent = data['volume_threshold_percent']
    
    if data.get('auto_heal_enabled') is not None:
        pipeline.auto_heal_enabled = data['auto_heal_enabled']
    
    if data.get('heal_script') is not None:
        pipeline.heal_script = data['heal_script']
    
    if data.get('tags') is not None:
        pipeline.tags = data['tags']
    
    if data.get('data_source_id') is not None:
        pipeline.data_source_id = data['data_source_id']
    
    pipeline.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Pipeline updated successfully',
            'pipeline': pipeline.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update pipeline', 'details': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>', methods=['DELETE'])
@jwt_required()
def delete_pipeline(pipeline_id):
    """Delete pipeline"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    pipeline = Pipeline.query.filter_by(
        id=pipeline_id, 
        organization_id=org.id
    ).first()
    
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    
    try:
        db.session.delete(pipeline)
        db.session.commit()
        
        return jsonify({'message': 'Pipeline deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete pipeline', 'details': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>/runs', methods=['GET'])
@jwt_required()
def get_pipeline_runs(pipeline_id):
    """Get pipeline runs"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    pipeline = Pipeline.query.filter_by(
        id=pipeline_id, 
        organization_id=org.id
    ).first()
    
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    
    # Query parameters
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Build query
    query = PipelineRun.query.filter_by(pipeline_id=pipeline_id)
    
    if status:
        query = query.filter_by(status=RunStatus(status))
    
    # Pagination
    runs = query.order_by(desc(PipelineRun.started_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'runs': [run.to_dict() for run in runs.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': runs.total,
            'pages': runs.pages,
            'has_next': runs.has_next,
            'has_prev': runs.has_prev
        }
    }), 200

@pipelines_bp.route('/<int:pipeline_id>/runs/<int:run_id>', methods=['GET'])
@jwt_required()
def get_pipeline_run(pipeline_id, run_id):
    """Get specific pipeline run"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    pipeline = Pipeline.query.filter_by(
        id=pipeline_id, 
        organization_id=org.id
    ).first()
    
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    
    run = PipelineRun.query.filter_by(
        id=run_id,
        pipeline_id=pipeline_id
    ).first()
    
    if not run:
        return jsonify({'error': 'Pipeline run not found'}), 404
    
    return jsonify({'run': run.to_dict()}), 200

@pipelines_bp.route('/<int:pipeline_id>/trigger', methods=['POST'])
@jwt_required()
def trigger_pipeline(pipeline_id):
    """Manually trigger pipeline execution"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    pipeline = Pipeline.query.filter_by(
        id=pipeline_id, 
        organization_id=org.id
    ).first()
    
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    
    if pipeline.status != PipelineStatus.ACTIVE:
        return jsonify({'error': 'Pipeline is not active'}), 400
    
    data = request.get_json() or {}
    
    try:
        # Create pipeline run
        run = PipelineRun(
            pipeline_id=pipeline_id,
            status=RunStatus.PENDING,
            input_data=data.get('input_data', {}),
            retry_count=0,
            is_retry=False
        )
        
        db.session.add(run)
        db.session.commit()
        
        # TODO: Trigger actual pipeline execution via Celery task
        # from app.tasks import execute_pipeline
        # execute_pipeline.delay(run.id)
        
        return jsonify({
            'message': 'Pipeline triggered successfully',
            'run': run.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to trigger pipeline', 'details': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>/metrics', methods=['GET'])
@jwt_required()
def get_pipeline_metrics(pipeline_id):
    """Get pipeline metrics"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    pipeline = Pipeline.query.filter_by(
        id=pipeline_id, 
        organization_id=org.id
    ).first()
    
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    
    # Query parameters
    metric_name = request.args.get('metric_name')
    days = int(request.args.get('days', 30))
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 100)), 1000)
    
    # Build query
    query = PipelineMetric.query.filter_by(pipeline_id=pipeline_id)
    
    if metric_name:
        query = query.filter_by(metric_name=metric_name)
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(PipelineMetric.recorded_at >= cutoff_date)
    
    # Pagination
    metrics = query.order_by(desc(PipelineMetric.recorded_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'metrics': [metric.to_dict() for metric in metrics.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': metrics.total,
            'pages': metrics.pages,
            'has_next': metrics.has_next,
            'has_prev': metrics.has_prev
        }
    }), 200 