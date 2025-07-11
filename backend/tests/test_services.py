import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from app.services.pipeline_service import PipelineService
from app.services.monitoring_service import MonitoringService
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService
from app.services.health_check_service import HealthCheckService
from app.services.metrics_service import MetricsService
from app.models.pipeline import Pipeline, PipelineRun, PipelineStatus, RunStatus
from app.models.monitoring import DataSource, HealthCheck, DataSourceType
from app.models.alert import AlertRule, Alert, AlertSeverity, AlertStatus
from app.models.user import User
from app.models.organization import Organization

class TestPipelineService:
    """Test cases for PipelineService."""
    
    def test_create_pipeline(self, app, test_user, test_organization):
        """Test creating a new pipeline."""
        service = PipelineService()
        pipeline_data = {
            'name': 'Test Pipeline',
            'description': 'A test pipeline',
            'pipeline_type': 'etl',
            'config': {'source': 'test_source'},
            'schedule': '0 0 * * *',
            'timeout_minutes': 60,
            'retry_attempts': 3,
            'retry_delay_minutes': 5,
            'health_check_enabled': True,
            'freshness_threshold_hours': 24,
            'volume_threshold_percent': 10.0,
            'auto_heal_enabled': False,
            'organization_id': test_organization.id,
            'created_by': test_user.id
        }
        
        with app.app_context():
            pipeline = service.create_pipeline(pipeline_data)
            
            assert pipeline.name == 'Test Pipeline'
            assert pipeline.pipeline_type.value == 'etl'
            assert pipeline.status == PipelineStatus.ACTIVE
            assert pipeline.organization_id == test_organization.id
    
    def test_create_pipeline_duplicate_name(self, app, test_user, test_organization, test_pipeline):
        """Test creating pipeline with duplicate name."""
        service = PipelineService()
        pipeline_data = {
            'name': test_pipeline.name,
            'pipeline_type': 'etl',
            'organization_id': test_organization.id,
            'created_by': test_user.id
        }
        
        with app.app_context():
            with pytest.raises(ValueError, match='Pipeline name already exists'):
                service.create_pipeline(pipeline_data)
    
    def test_update_pipeline(self, app, test_pipeline):
        """Test updating a pipeline."""
        service = PipelineService()
        update_data = {
            'name': 'Updated Pipeline',
            'description': 'Updated description',
            'status': 'inactive'
        }
        
        with app.app_context():
            updated_pipeline = service.update_pipeline(test_pipeline.id, update_data)
            
            assert updated_pipeline.name == 'Updated Pipeline'
            assert updated_pipeline.description == 'Updated description'
            assert updated_pipeline.status == PipelineStatus.INACTIVE
    
    def test_delete_pipeline(self, app, test_pipeline):
        """Test deleting a pipeline."""
        service = PipelineService()
        
        with app.app_context():
            service.delete_pipeline(test_pipeline.id)
            
            # Verify pipeline is deleted
            deleted_pipeline = Pipeline.query.get(test_pipeline.id)
            assert deleted_pipeline is None
    
    def test_trigger_pipeline(self, app, test_pipeline, mock_celery):
        """Test triggering a pipeline."""
        service = PipelineService()
        
        with app.app_context():
            task_id = service.trigger_pipeline(test_pipeline.id)
            
            assert task_id == 'test-task-id'
            mock_celery.send_task.assert_called_once()
    
    def test_get_pipeline_metrics(self, app, test_pipeline, test_pipeline_run):
        """Test getting pipeline metrics."""
        service = PipelineService()
        
        with app.app_context():
            metrics = service.get_pipeline_metrics(test_pipeline.id, days=30)
            
            assert 'success_rate' in metrics
            assert 'average_duration' in metrics
            assert 'total_runs' in metrics
            assert 'uptime_percentage' in metrics
    
    def test_calculate_pipeline_health(self, app, test_pipeline, test_pipeline_run):
        """Test calculating pipeline health."""
        service = PipelineService()
        
        with app.app_context():
            health_metrics = service.calculate_pipeline_health(test_pipeline.id)
            
            assert 'uptime_percentage' in health_metrics
            assert 'average_duration' in health_metrics
            assert 'success_rate' in health_metrics
            assert 'last_run_status' in health_metrics
    
    def test_get_pipeline_runs(self, app, test_pipeline, test_pipeline_run):
        """Test getting pipeline runs."""
        service = PipelineService()
        
        with app.app_context():
            runs = service.get_pipeline_runs(test_pipeline.id, page=1, per_page=10)
            
            assert len(runs['runs']) == 1
            assert runs['runs'][0]['id'] == test_pipeline_run.id
            assert 'pagination' in runs

class TestMonitoringService:
    """Test cases for MonitoringService."""
    
    def test_create_data_source(self, app, test_organization):
        """Test creating a new data source."""
        service = MonitoringService()
        data_source_data = {
            'name': 'Test Database',
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password',
            'organization_id': test_organization.id
        }
        
        with app.app_context():
            data_source = service.create_data_source(data_source_data)
            
            assert data_source.name == 'Test Database'
            assert data_source.type.value == 'postgresql'
            assert data_source.host == 'localhost'
    
    def test_test_data_source_connection(self, app, test_data_source):
        """Test testing data source connection."""
        service = MonitoringService()
        
        with app.app_context():
            with patch('psycopg2.connect') as mock_connect:
                mock_connect.return_value = Mock()
                result = service.test_data_source_connection(test_data_source.id)
                
                assert result['success'] == True
                assert 'duration' in result
    
    def test_update_data_source_health(self, app, test_data_source):
        """Test updating data source health."""
        service = MonitoringService()
        
        with app.app_context():
            service.update_data_source_health(test_data_source.id, 85.0)
            
            updated_ds = DataSource.query.get(test_data_source.id)
            assert updated_ds.health_score == 85.0
            assert updated_ds.last_check_at is not None
    
    def test_create_health_check(self, app, test_data_source):
        """Test creating a new health check."""
        service = MonitoringService()
        health_check_data = {
            'name': 'Test Health Check',
            'data_source_id': test_data_source.id,
            'check_type': 'query',
            'query': 'SELECT 1',
            'expected_result': '1',
            'interval_minutes': 5,
            'timeout_seconds': 30,
            'enabled': True
        }
        
        with app.app_context():
            health_check = service.create_health_check(health_check_data)
            
            assert health_check.name == 'Test Health Check'
            assert health_check.check_type.value == 'query'
            assert health_check.enabled == True
    
    def test_execute_health_check(self, app, test_health_check):
        """Test executing a health check."""
        service = MonitoringService()
        
        with app.app_context():
            with patch('psycopg2.connect') as mock_connect:
                mock_cursor = Mock()
                mock_cursor.fetchone.return_value = ['1']
                mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cursor
                
                result = service.execute_health_check(test_health_check.id)
                
                assert result['success'] == True
                assert 'duration' in result
                assert result['result'] == '1'
    
    def test_get_health_check_results(self, app, test_health_check):
        """Test getting health check results."""
        service = MonitoringService()
        
        with app.app_context():
            results = service.get_health_check_results(test_health_check.id, days=7)
            
            assert isinstance(results, list)
    
    def test_schedule_health_checks(self, app, test_health_check, mock_celery):
        """Test scheduling health checks."""
        service = MonitoringService()
        
        with app.app_context():
            service.schedule_health_checks()
            
            # Verify Celery task was called
            mock_celery.send_task.assert_called()

class TestAlertService:
    """Test cases for AlertService."""
    
    def test_create_alert_rule(self, app, test_organization):
        """Test creating a new alert rule."""
        service = AlertService()
        alert_rule_data = {
            'name': 'Test Alert Rule',
            'description': 'A test alert rule',
            'severity': 'medium',
            'condition_type': 'threshold',
            'condition_config': {'metric': 'pipeline_failure_rate', 'threshold': 0.1},
            'notification_channels': ['email'],
            'enabled': True,
            'organization_id': test_organization.id
        }
        
        with app.app_context():
            alert_rule = service.create_alert_rule(alert_rule_data)
            
            assert alert_rule.name == 'Test Alert Rule'
            assert alert_rule.severity.value == 'medium'
            assert alert_rule.enabled == True
    
    def test_evaluate_alert_rules(self, app, test_alert_rule, test_pipeline):
        """Test evaluating alert rules."""
        service = AlertService()
        
        with app.app_context():
            # Mock pipeline metrics
            metrics = {'pipeline_failure_rate': 0.15}
            
            triggered_alerts = service.evaluate_alert_rules(metrics)
            
            assert isinstance(triggered_alerts, list)
    
    def test_create_alert(self, app, test_alert_rule):
        """Test creating a new alert."""
        service = AlertService()
        alert_data = {
            'alert_rule_id': test_alert_rule.id,
            'severity': 'medium',
            'message': 'Test alert message',
            'triggered_at': datetime.utcnow()
        }
        
        with app.app_context():
            alert = service.create_alert(alert_data)
            
            assert alert.alert_rule_id == test_alert_rule.id
            assert alert.severity.value == 'medium'
            assert alert.status == AlertStatus.ACTIVE
    
    def test_acknowledge_alert(self, app, test_alert):
        """Test acknowledging an alert."""
        service = AlertService()
        
        with app.app_context():
            service.acknowledge_alert(test_alert.id)
            
            updated_alert = Alert.query.get(test_alert.id)
            assert updated_alert.status == AlertStatus.ACKNOWLEDGED
            assert updated_alert.acknowledged_at is not None
    
    def test_resolve_alert(self, app, test_alert):
        """Test resolving an alert."""
        service = AlertService()
        
        with app.app_context():
            service.resolve_alert(test_alert.id)
            
            updated_alert = Alert.query.get(test_alert.id)
            assert updated_alert.status == AlertStatus.RESOLVED
            assert updated_alert.resolved_at is not None
    
    def test_get_alert_statistics(self, app, test_alert):
        """Test getting alert statistics."""
        service = AlertService()
        
        with app.app_context():
            stats = service.get_alert_statistics(days=30)
            
            assert 'total_alerts' in stats
            assert 'active_alerts' in stats
            assert 'acknowledged_alerts' in stats
            assert 'resolved_alerts' in stats
            assert 'alerts_by_severity' in stats

class TestNotificationService:
    """Test cases for NotificationService."""
    
    def test_send_email_notification(self, app, mock_sendgrid):
        """Test sending email notification."""
        service = NotificationService()
        
        with app.app_context():
            result = service.send_email_notification(
                to_email='test@example.com',
                subject='Test Alert',
                message='This is a test alert'
            )
            
            assert result['success'] == True
            mock_sendgrid.send.assert_called_once()
    
    def test_send_slack_notification(self, app, mock_slack):
        """Test sending Slack notification."""
        service = NotificationService()
        
        with app.app_context():
            result = service.send_slack_notification(
                webhook_url='https://hooks.slack.com/test',
                message='Test alert message'
            )
            
            assert result['success'] == True
            mock_slack.send.assert_called_once()
    
    def test_send_sms_notification(self, app, mock_twilio):
        """Test sending SMS notification."""
        service = NotificationService()
        
        with app.app_context():
            result = service.send_sms_notification(
                to_number='+1234567890',
                message='Test alert message'
            )
            
            assert result['success'] == True
            mock_twilio.messages.create.assert_called_once()
    
    def test_send_notification_multiple_channels(self, app, mock_sendgrid, mock_slack):
        """Test sending notifications to multiple channels."""
        service = NotificationService()
        
        with app.app_context():
            result = service.send_notification(
                channels=['email', 'slack'],
                recipients={
                    'email': 'test@example.com',
                    'slack_webhook': 'https://hooks.slack.com/test'
                },
                subject='Test Alert',
                message='Test alert message'
            )
            
            assert result['email_sent'] == True
            assert result['slack_sent'] == True
    
    def test_notification_failure_handling(self, app, mock_sendgrid):
        """Test handling notification failures."""
        service = NotificationService()
        mock_sendgrid.send.side_effect = Exception('SendGrid error')
        
        with app.app_context():
            result = service.send_email_notification(
                to_email='test@example.com',
                subject='Test Alert',
                message='This is a test alert'
            )
            
            assert result['success'] == False
            assert 'error' in result

class TestHealthCheckService:
    """Test cases for HealthCheckService."""
    
    def test_execute_health_checks(self, app, test_health_check):
        """Test executing all health checks."""
        service = HealthCheckService()
        
        with app.app_context():
            with patch('psycopg2.connect') as mock_connect:
                mock_cursor = Mock()
                mock_cursor.fetchone.return_value = ['1']
                mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cursor
                
                results = service.execute_health_checks()
                
                assert isinstance(results, list)
                assert len(results) >= 1
    
    def test_check_data_freshness(self, app, test_data_source):
        """Test checking data freshness."""
        service = HealthCheckService()
        
        with app.app_context():
            with patch('psycopg2.connect') as mock_connect:
                mock_cursor = Mock()
                mock_cursor.fetchone.return_value = [datetime.utcnow()]
                mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cursor
                
                result = service.check_data_freshness(test_data_source.id, 'test_table')
                
                assert 'fresh' in result
                assert 'last_update' in result
    
    def test_check_data_volume(self, app, test_data_source):
        """Test checking data volume."""
        service = HealthCheckService()
        
        with app.app_context():
            with patch('psycopg2.connect') as mock_connect:
                mock_cursor = Mock()
                mock_cursor.fetchone.return_value = [1000]
                mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cursor
                
                result = service.check_data_volume(test_data_source.id, 'test_table')
                
                assert 'current_count' in result
                assert 'expected_count' in result
                assert 'anomaly_detected' in result
    
    def test_check_connection_health(self, app, test_data_source):
        """Test checking connection health."""
        service = HealthCheckService()
        
        with app.app_context():
            with patch('psycopg2.connect') as mock_connect:
                mock_connect.return_value = Mock()
                
                result = service.check_connection_health(test_data_source.id)
                
                assert 'connected' in result
                assert 'response_time' in result
    
    def test_schedule_health_checks(self, app, test_health_check, mock_celery):
        """Test scheduling health checks."""
        service = HealthCheckService()
        
        with app.app_context():
            service.schedule_health_checks()
            
            # Verify Celery task was called
            mock_celery.send_task.assert_called()

class TestMetricsService:
    """Test cases for MetricsService."""
    
    def test_calculate_pipeline_metrics(self, app, test_pipeline, test_pipeline_run):
        """Test calculating pipeline metrics."""
        service = MetricsService()
        
        with app.app_context():
            metrics = service.calculate_pipeline_metrics(test_pipeline.id, days=30)
            
            assert 'success_rate' in metrics
            assert 'average_duration' in metrics
            assert 'total_runs' in metrics
            assert 'uptime_percentage' in metrics
    
    def test_calculate_organization_metrics(self, app, test_organization, test_pipeline):
        """Test calculating organization metrics."""
        service = MetricsService()
        
        with app.app_context():
            metrics = service.calculate_organization_metrics(test_organization.id)
            
            assert 'total_pipelines' in metrics
            assert 'active_pipelines' in metrics
            assert 'total_data_sources' in metrics
            assert 'total_alerts' in metrics
    
    def test_get_metrics_trends(self, app, test_pipeline):
        """Test getting metrics trends."""
        service = MetricsService()
        
        with app.app_context():
            trends = service.get_metrics_trends(test_pipeline.id, days=30)
            
            assert 'success_rate_trend' in trends
            assert 'duration_trend' in trends
            assert 'volume_trend' in trends
    
    def test_store_pipeline_metric(self, app, test_pipeline):
        """Test storing pipeline metric."""
        service = MetricsService()
        
        with app.app_context():
            metric_data = {
                'pipeline_id': test_pipeline.id,
                'metric_name': 'execution_time',
                'metric_value': 300.5,
                'metric_unit': 'seconds'
            }
            
            metric = service.store_pipeline_metric(metric_data)
            
            assert metric.pipeline_id == test_pipeline.id
            assert metric.metric_name == 'execution_time'
            assert metric.metric_value == 300.5
    
    def test_get_metrics_summary(self, app, test_organization):
        """Test getting metrics summary."""
        service = MetricsService()
        
        with app.app_context():
            summary = service.get_metrics_summary(test_organization.id)
            
            assert 'pipeline_health' in summary
            assert 'data_quality' in summary
            assert 'system_performance' in summary
            assert 'alert_summary' in summary

class TestBackgroundTasks:
    """Test cases for background tasks."""
    
    def test_execute_pipeline_task(self, app, test_pipeline, mock_celery):
        """Test executing pipeline background task."""
        from app.tasks.pipeline_tasks import execute_pipeline
        
        with app.app_context():
            result = execute_pipeline.delay(test_pipeline.id)
            
            assert result.id == 'test-task-id'
            mock_celery.send_task.assert_called()
    
    def test_execute_health_checks_task(self, app, test_health_check, mock_celery):
        """Test executing health checks background task."""
        from app.tasks.monitoring_tasks import execute_health_checks
        
        with app.app_context():
            result = execute_health_checks.delay()
            
            assert result.id == 'test-task-id'
            mock_celery.send_task.assert_called()
    
    def test_evaluate_alerts_task(self, app, test_alert_rule, mock_celery):
        """Test evaluating alerts background task."""
        from app.tasks.alert_tasks import evaluate_alerts
        
        with app.app_context():
            result = evaluate_alerts.delay()
            
            assert result.id == 'test-task-id'
            mock_celery.send_task.assert_called()
    
    def test_send_notifications_task(self, app, mock_sendgrid, mock_slack):
        """Test sending notifications background task."""
        from app.tasks.notification_tasks import send_notification
        
        with app.app_context():
            notification_data = {
                'channels': ['email', 'slack'],
                'recipients': {
                    'email': 'test@example.com',
                    'slack_webhook': 'https://hooks.slack.com/test'
                },
                'subject': 'Test Alert',
                'message': 'Test alert message'
            }
            
            result = send_notification.delay(notification_data)
            
            assert result.id == 'test-task-id'
            mock_celery.send_task.assert_called()

class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_validate_email(self):
        """Test email validation."""
        from app.utils.validators import validate_email
        
        assert validate_email('test@example.com') == True
        assert validate_email('invalid-email') == False
        assert validate_email('') == False
    
    def test_validate_pipeline_config(self):
        """Test pipeline configuration validation."""
        from app.utils.validators import validate_pipeline_config
        
        valid_config = {
            'source': 'test_source',
            'destination': 'test_dest',
            'transformations': ['clean', 'aggregate']
        }
        
        assert validate_pipeline_config(valid_config) == True
        
        invalid_config = {'invalid_key': 'value'}
        assert validate_pipeline_config(invalid_config) == False
    
    def test_calculate_uptime_percentage(self):
        """Test uptime percentage calculation."""
        from app.utils.metrics import calculate_uptime_percentage
        
        # Mock pipeline runs
        runs = [
            {'status': 'success', 'duration_seconds': 300},
            {'status': 'success', 'duration_seconds': 250},
            {'status': 'failed', 'duration_seconds': 100},
            {'status': 'success', 'duration_seconds': 280}
        ]
        
        uptime = calculate_uptime_percentage(runs)
        assert uptime == 75.0  # 3 out of 4 successful
    
    def test_detect_anomalies(self):
        """Test anomaly detection."""
        from app.utils.anomaly_detection import detect_anomalies
        
        # Mock metrics data
        metrics = [100, 105, 98, 102, 95, 150, 103, 99, 101, 97]  # 150 is anomaly
        
        anomalies = detect_anomalies(metrics, threshold=2.0)
        assert len(anomalies) == 1
        assert anomalies[0]['index'] == 5
        assert anomalies[0]['value'] == 150
    
    def test_format_duration(self):
        """Test duration formatting."""
        from app.utils.formatters import format_duration
        
        assert format_duration(3661) == '1h 1m 1s'  # 1 hour, 1 minute, 1 second
        assert format_duration(65) == '1m 5s'  # 1 minute, 5 seconds
        assert format_duration(30) == '30s'  # 30 seconds
    
    def test_format_file_size(self):
        """Test file size formatting."""
        from app.utils.formatters import format_file_size
        
        assert format_file_size(1024) == '1.0 KB'
        assert format_file_size(1048576) == '1.0 MB'
        assert format_file_size(1073741824) == '1.0 GB'
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from app.utils.sanitizers import sanitize_filename
        
        assert sanitize_filename('test file.txt') == 'test_file.txt'
        assert sanitize_filename('file/with\\path') == 'file_with_path'
        assert sanitize_filename('file.with.dots.txt') == 'file.with.dots.txt'
    
    def test_encrypt_sensitive_data(self):
        """Test sensitive data encryption."""
        from app.utils.encryption import encrypt_data, decrypt_data
        
        secret_key = 'test-secret-key'
        sensitive_data = 'password123'
        
        encrypted = encrypt_data(sensitive_data, secret_key)
        decrypted = decrypt_data(encrypted, secret_key)
        
        assert decrypted == sensitive_data
        assert encrypted != sensitive_data 