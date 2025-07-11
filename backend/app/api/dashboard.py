from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import (
    Pipeline, PipelineRun, PipelineMetric, 
    DataSource, HealthCheck, HealthCheckResult,
    Alert, AlertRule, User, Organization
)
from app.models.pipeline import PipelineStatus, RunStatus
from app.models.monitoring import HealthCheckStatus
from app.models.alert import AlertStatus, AlertSeverity
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
import json

dashboard_bp = Blueprint('dashboard', __name__)

def get_current_user_org():
    """Get current user and organization"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user, user.organization if user else None

@dashboard_bp.route('/overview', methods=['GET'])
@jwt_required()
def get_dashboard_overview():
    """Get dashboard overview data"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Get date range (default to last 30 days)
    days = int(request.args.get('days', 30))
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Pipeline statistics
    total_pipelines = Pipeline.query.filter_by(organization_id=org.id).count()
    active_pipelines = Pipeline.query.filter_by(
        organization_id=org.id, 
        status=PipelineStatus.ACTIVE
    ).count()
    
    # Get pipeline runs in date range
    recent_runs = PipelineRun.query.join(Pipeline).filter(
        Pipeline.organization_id == org.id,
        PipelineRun.started_at >= cutoff_date
    ).all()
    
    successful_runs = [run for run in recent_runs if run.status == RunStatus.SUCCESS]
    failed_runs = [run for run in recent_runs if run.status == RunStatus.FAILED]
    
    # Calculate uptime percentage
    uptime_percentage = 0
    if recent_runs:
        uptime_percentage = (len(successful_runs) / len(recent_runs)) * 100
    
    # Data source statistics
    total_data_sources = DataSource.query.filter_by(organization_id=org.id).count()
    active_data_sources = DataSource.query.filter_by(
        organization_id=org.id, 
        is_active=True
    ).count()
    
    # Health check statistics
    total_health_checks = HealthCheck.query.filter_by(organization_id=org.id).count()
    active_health_checks = HealthCheck.query.filter_by(
        organization_id=org.id, 
        is_active=True
    ).count()
    
    # Get recent health check results
    recent_health_results = HealthCheckResult.query.join(HealthCheck).filter(
        HealthCheck.organization_id == org.id,
        HealthCheckResult.checked_at >= cutoff_date
    ).all()
    
    healthy_checks = [result for result in recent_health_results if result.status == HealthCheckStatus.HEALTHY]
    warning_checks = [result for result in recent_health_results if result.status == HealthCheckStatus.WARNING]
    critical_checks = [result for result in recent_health_results if result.status == HealthCheckStatus.CRITICAL]
    
    # Alert statistics
    total_alerts = Alert.query.filter_by(organization_id=org.id).count()
    active_alerts = Alert.query.filter_by(
        organization_id=org.id, 
        status=AlertStatus.ACTIVE
    ).count()
    
    # Recent alerts
    recent_alerts = Alert.query.filter_by(organization_id=org.id).order_by(
        desc(Alert.created_at)
    ).limit(5).all()
    
    return jsonify({
        'overview': {
            'pipelines': {
                'total': total_pipelines,
                'active': active_pipelines,
                'uptime_percentage': round(uptime_percentage, 2),
                'recent_runs': len(recent_runs),
                'successful_runs': len(successful_runs),
                'failed_runs': len(failed_runs)
            },
            'data_sources': {
                'total': total_data_sources,
                'active': active_data_sources
            },
            'health_checks': {
                'total': total_health_checks,
                'active': active_health_checks,
                'healthy': len(healthy_checks),
                'warnings': len(warning_checks),
                'critical': len(critical_checks)
            },
            'alerts': {
                'total': total_alerts,
                'active': active_alerts,
                'recent_alerts': [alert.to_dict() for alert in recent_alerts]
            }
        }
    }), 200

@dashboard_bp.route('/pipeline-health', methods=['GET'])
@jwt_required()
def get_pipeline_health():
    """Get pipeline health summary"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Get all pipelines with their health status
    pipelines = Pipeline.query.filter_by(organization_id=org.id).all()
    
    pipeline_health = []
    for pipeline in pipelines:
        latest_run = pipeline.get_latest_run()
        uptime = pipeline.get_uptime_percentage()
        
        pipeline_health.append({
            'id': pipeline.id,
            'name': pipeline.name,
            'type': pipeline.pipeline_type.value,
            'status': pipeline.status.value,
            'is_healthy': pipeline.is_healthy(),
            'uptime_percentage': uptime,
            'last_run': latest_run.to_dict() if latest_run else None,
            'health_status': 'healthy' if pipeline.is_healthy() else 'unhealthy'
        })
    
    # Calculate summary statistics
    healthy_pipelines = [p for p in pipeline_health if p['is_healthy']]
    unhealthy_pipelines = [p for p in pipeline_health if not p['is_healthy']]
    
    return jsonify({
        'pipelines': pipeline_health,
        'summary': {
            'total': len(pipelines),
            'healthy': len(healthy_pipelines),
            'unhealthy': len(unhealthy_pipelines),
            'health_percentage': round((len(healthy_pipelines) / len(pipelines)) * 100, 2) if pipelines else 0
        }
    }), 200

@dashboard_bp.route('/data-source-health', methods=['GET'])
@jwt_required()
def get_data_source_health():
    """Get data source health summary"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Get all data sources with their health status
    data_sources = DataSource.query.filter_by(organization_id=org.id).all()
    
    data_source_health = []
    for ds in data_sources:
        latest_check = ds.get_latest_health_check()
        
        data_source_health.append({
            'id': ds.id,
            'name': ds.name,
            'type': ds.source_type.value,
            'is_active': ds.is_active,
            'is_healthy': ds.is_healthy(),
            'last_checked': ds.last_checked_at.isoformat() if ds.last_checked_at else None,
            'latest_check': latest_check.to_dict() if latest_check else None,
            'health_status': 'healthy' if ds.is_healthy() else 'unhealthy'
        })
    
    # Calculate summary statistics
    healthy_sources = [ds for ds in data_source_health if ds['is_healthy']]
    unhealthy_sources = [ds for ds in data_source_health if not ds['is_healthy']]
    
    return jsonify({
        'data_sources': data_source_health,
        'summary': {
            'total': len(data_sources),
            'healthy': len(healthy_sources),
            'unhealthy': len(unhealthy_sources),
            'health_percentage': round((len(healthy_sources) / len(data_sources)) * 100, 2) if data_sources else 0
        }
    }), 200

@dashboard_bp.route('/recent-activity', methods=['GET'])
@jwt_required()
def get_recent_activity():
    """Get recent activity across all systems"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Get recent pipeline runs
    recent_runs = PipelineRun.query.join(Pipeline).filter(
        Pipeline.organization_id == org.id
    ).order_by(desc(PipelineRun.started_at)).limit(10).all()
    
    # Get recent health check results
    recent_health_results = HealthCheckResult.query.join(HealthCheck).filter(
        HealthCheck.organization_id == org.id
    ).order_by(desc(HealthCheckResult.checked_at)).limit(10).all()
    
    # Get recent alerts
    recent_alerts = Alert.query.filter_by(organization_id=org.id).order_by(
        desc(Alert.created_at)
    ).limit(10).all()
    
    # Combine and sort activities
    activities = []
    
    for run in recent_runs:
        activities.append({
            'type': 'pipeline_run',
            'timestamp': run.started_at,
            'title': f"Pipeline '{run.pipeline.name}' {run.status.value}",
            'description': f"Pipeline run {run.status.value}",
            'status': run.status.value,
            'data': run.to_dict()
        })
    
    for result in recent_health_results:
        activities.append({
            'type': 'health_check',
            'timestamp': result.checked_at,
            'title': f"Health check '{result.health_check.name}' {result.status.value}",
            'description': result.message or f"Health check {result.status.value}",
            'status': result.status.value,
            'data': result.to_dict()
        })
    
    for alert in recent_alerts:
        activities.append({
            'type': 'alert',
            'timestamp': alert.created_at,
            'title': f"Alert: {alert.title}",
            'description': alert.message,
            'status': alert.status.value,
            'severity': alert.severity.value,
            'data': alert.to_dict()
        })
    
    # Sort by timestamp (most recent first)
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({
        'activities': activities[:20]  # Return top 20 most recent activities
    }), 200

@dashboard_bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_dashboard_metrics():
    """Get aggregated metrics for dashboard charts"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Get date range
    days = int(request.args.get('days', 30))
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Pipeline run metrics over time
    pipeline_metrics = db.session.query(
        func.date(PipelineRun.started_at).label('date'),
        func.count(PipelineRun.id).label('total_runs'),
        func.sum(case((PipelineRun.status == RunStatus.SUCCESS, 1), else_=0)).label('successful_runs'),
        func.sum(case((PipelineRun.status == RunStatus.FAILED, 1), else_=0)).label('failed_runs')
    ).join(Pipeline).filter(
        Pipeline.organization_id == org.id,
        PipelineRun.started_at >= cutoff_date
    ).group_by(func.date(PipelineRun.started_at)).order_by(func.date(PipelineRun.started_at)).all()
    
    # Health check metrics over time
    health_metrics = db.session.query(
        func.date(HealthCheckResult.checked_at).label('date'),
        func.count(HealthCheckResult.id).label('total_checks'),
        func.sum(case((HealthCheckResult.status == HealthCheckStatus.HEALTHY, 1), else_=0)).label('healthy_checks'),
        func.sum(case((HealthCheckResult.status == HealthCheckStatus.WARNING, 1), else_=0)).label('warning_checks'),
        func.sum(case((HealthCheckResult.status == HealthCheckStatus.CRITICAL, 1), else_=0)).label('critical_checks')
    ).join(HealthCheck).filter(
        HealthCheck.organization_id == org.id,
        HealthCheckResult.checked_at >= cutoff_date
    ).group_by(func.date(HealthCheckResult.checked_at)).order_by(func.date(HealthCheckResult.checked_at)).all()
    
    # Alert metrics over time
    alert_metrics = db.session.query(
        func.date(Alert.created_at).label('date'),
        func.count(Alert.id).label('total_alerts'),
        func.sum(case((Alert.severity == AlertSeverity.CRITICAL, 1), else_=0)).label('critical_alerts'),
        func.sum(case((Alert.severity == AlertSeverity.WARNING, 1), else_=0)).label('warning_alerts')
    ).filter(
        Alert.organization_id == org.id,
        Alert.created_at >= cutoff_date
    ).group_by(func.date(Alert.created_at)).order_by(func.date(Alert.created_at)).all()
    
    return jsonify({
        'pipeline_metrics': [
            {
                'date': str(m.date),
                'total_runs': m.total_runs,
                'successful_runs': m.successful_runs,
                'failed_runs': m.failed_runs,
                'success_rate': round((m.successful_runs / m.total_runs) * 100, 2) if m.total_runs > 0 else 0
            }
            for m in pipeline_metrics
        ],
        'health_metrics': [
            {
                'date': str(m.date),
                'total_checks': m.total_checks,
                'healthy_checks': m.healthy_checks,
                'warning_checks': m.warning_checks,
                'critical_checks': m.critical_checks,
                'health_rate': round((m.healthy_checks / m.total_checks) * 100, 2) if m.total_checks > 0 else 0
            }
            for m in health_metrics
        ],
        'alert_metrics': [
            {
                'date': str(m.date),
                'total_alerts': m.total_alerts,
                'critical_alerts': m.critical_alerts,
                'warning_alerts': m.warning_alerts
            }
            for m in alert_metrics
        ]
    }), 200

@dashboard_bp.route('/top-pipelines', methods=['GET'])
@jwt_required()
def get_top_pipelines():
    """Get top performing and problematic pipelines"""
    user, org = get_current_user_org()
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
    
    # Get date range
    days = int(request.args.get('days', 30))
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Top performing pipelines (highest success rate)
    top_performers = db.session.query(
        Pipeline,
        func.count(PipelineRun.id).label('total_runs'),
        func.sum(case((PipelineRun.status == RunStatus.SUCCESS, 1), else_=0)).label('successful_runs')
    ).join(PipelineRun).filter(
        Pipeline.organization_id == org.id,
        PipelineRun.started_at >= cutoff_date
    ).group_by(Pipeline.id).having(
        func.count(PipelineRun.id) >= 5  # At least 5 runs in the period
    ).order_by(
        func.sum(case((PipelineRun.status == RunStatus.SUCCESS, 1), else_=0)).desc()
    ).limit(5).all()
    
    # Most problematic pipelines (highest failure rate)
    problematic = db.session.query(
        Pipeline,
        func.count(PipelineRun.id).label('total_runs'),
        func.sum(case((PipelineRun.status == RunStatus.FAILED, 1), else_=0)).label('failed_runs')
    ).join(PipelineRun).filter(
        Pipeline.organization_id == org.id,
        PipelineRun.started_at >= cutoff_date
    ).group_by(Pipeline.id).having(
        func.count(PipelineRun.id) >= 5  # At least 5 runs in the period
    ).order_by(
        func.sum(case((PipelineRun.status == RunStatus.FAILED, 1), else_=0)).desc()
    ).limit(5).all()
    
    return jsonify({
        'top_performers': [
            {
                'pipeline': pipeline.to_dict(),
                'total_runs': total_runs,
                'successful_runs': successful_runs,
                'success_rate': round((successful_runs / total_runs) * 100, 2)
            }
            for pipeline, total_runs, successful_runs in top_performers
        ],
        'problematic': [
            {
                'pipeline': pipeline.to_dict(),
                'total_runs': total_runs,
                'failed_runs': failed_runs,
                'failure_rate': round((failed_runs / total_runs) * 100, 2)
            }
            for pipeline, total_runs, failed_runs in problematic
        ]
    }), 200

# Import the case function for SQLAlchemy 