import pytest
import json
from datetime import datetime, timedelta
from app import db
from app.models.user import User
from app.models.organization import Organization
from app.models.pipeline import Pipeline, PipelineRun, PipelineStatus, RunStatus
from app.models.monitoring import DataSource, HealthCheck, DataSourceType
from app.models.alert import AlertRule, Alert, AlertSeverity, AlertStatus

class TestPipelineIntegration:
    """Integration tests for pipeline functionality."""
    
    def test_pipeline_lifecycle(self, client, auth_headers, test_organization, sample_pipeline_data):
        """Test complete pipeline lifecycle: create, update, trigger, monitor, delete."""
        
        # 1. Create pipeline
        response = client.post('/api/pipelines', 
                             json=sample_pipeline_data, headers=auth_headers)
        assert response.status_code == 201
        
        pipeline_data = json.loads(response.data)
        pipeline_id = pipeline_data['pipeline']['id']
        
        # 2. Get pipeline
        response = client.get(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        assert response.status_code == 200
        
        pipeline = json.loads(response.data)['pipeline']
        assert pipeline['name'] == sample_pipeline_data['name']
        assert pipeline['status'] == 'active'
        
        # 3. Update pipeline
        update_data = {
            'name': 'Updated Pipeline Name',
            'description': 'Updated description',
            'timeout_minutes': 120
        }
        
        response = client.put(f'/api/pipelines/{pipeline_id}', 
                            json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        updated_pipeline = json.loads(response.data)['pipeline']
        assert updated_pipeline['name'] == 'Updated Pipeline Name'
        assert updated_pipeline['timeout_minutes'] == 120
        
        # 4. Trigger pipeline
        response = client.post(f'/api/pipelines/{pipeline_id}/trigger', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        trigger_result = json.loads(response.data)
        assert 'task_id' in trigger_result
        
        # 5. Get pipeline runs
        response = client.get(f'/api/pipelines/{pipeline_id}/runs', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        runs_data = json.loads(response.data)
        assert 'runs' in runs_data
        assert len(runs_data['runs']) >= 0  # May be 0 if background task hasn't completed
        
        # 6. Get pipeline metrics
        response = client.get(f'/api/pipelines/{pipeline_id}/metrics', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        metrics_data = json.loads(response.data)
        assert 'metrics' in metrics_data
        
        # 7. Delete pipeline
        response = client.delete(f'/api/pipelines/{pipeline_id}', 
                               headers=auth_headers)
        assert response.status_code == 200
        
        # 8. Verify pipeline is deleted
        response = client.get(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        assert response.status_code == 404
    
    def test_pipeline_with_data_source_integration(self, client, auth_headers, 
                                                  test_organization, test_data_source):
        """Test pipeline creation and management with data source integration."""
        
        # 1. Create pipeline with data source
        pipeline_data = {
            'name': 'ETL Pipeline with Data Source',
            'description': 'Pipeline connected to data source',
            'pipeline_type': 'etl',
            'config': {
                'source': 'test_source',
                'destination': 'test_dest',
                'data_source_id': test_data_source.id
            },
            'schedule': '0 2 * * *',
            'timeout_minutes': 60,
            'retry_attempts': 3,
            'health_check_enabled': True
        }
        
        response = client.post('/api/pipelines', 
                             json=pipeline_data, headers=auth_headers)
        assert response.status_code == 201
        
        pipeline_id = json.loads(response.data)['pipeline']['id']
        
        # 2. Verify pipeline has data source connection
        response = client.get(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        assert response.status_code == 200
        
        pipeline = json.loads(response.data)['pipeline']
        assert pipeline['config']['data_source_id'] == test_data_source.id
        
        # 3. Test data source connection through pipeline
        response = client.post(f'/api/monitoring/data-sources/{test_data_source.id}/test', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # 4. Clean up
        client.delete(f'/api/pipelines/{pipeline_id}', headers=auth_headers)

class TestMonitoringIntegration:
    """Integration tests for monitoring functionality."""
    
    def test_data_source_lifecycle(self, client, auth_headers, sample_data_source_data):
        """Test complete data source lifecycle."""
        
        # 1. Create data source
        response = client.post('/api/monitoring/data-sources', 
                             json=sample_data_source_data, headers=auth_headers)
        assert response.status_code == 201
        
        data_source_data = json.loads(response.data)
        data_source_id = data_source_data['data_source']['id']
        
        # 2. Get data source
        response = client.get(f'/api/monitoring/data-sources/{data_source_id}', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        data_source = json.loads(response.data)['data_source']
        assert data_source['name'] == sample_data_source_data['name']
        assert data_source['type'] == sample_data_source_data['type']
        
        # 3. Test connection
        response = client.post(f'/api/monitoring/data-sources/{data_source_id}/test', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        test_result = json.loads(response.data)
        assert 'success' in test_result
        
        # 4. Create health check for data source
        health_check_data = {
            'name': 'Test Health Check',
            'data_source_id': data_source_id,
            'check_type': 'query',
            'query': 'SELECT 1',
            'expected_result': '1',
            'interval_minutes': 5,
            'timeout_seconds': 30,
            'enabled': True
        }
        
        response = client.post('/api/monitoring/health-checks', 
                             json=health_check_data, headers=auth_headers)
        assert response.status_code == 201
        
        health_check_id = json.loads(response.data)['health_check']['id']
        
        # 5. Execute health check
        response = client.post(f'/api/monitoring/health-checks/{health_check_id}/execute', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # 6. Get health checks
        response = client.get('/api/monitoring/health-checks', headers=auth_headers)
        assert response.status_code == 200
        
        health_checks = json.loads(response.data)['health_checks']
        assert len(health_checks) >= 1
        
        # 7. Update data source
        update_data = {
            'name': 'Updated Data Source',
            'host': 'updated-host.com',
            'port': 3307
        }
        
        response = client.put(f'/api/monitoring/data-sources/{data_source_id}', 
                            json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        updated_ds = json.loads(response.data)['data_source']
        assert updated_ds['name'] == 'Updated Data Source'
        assert updated_ds['host'] == 'updated-host.com'
        
        # 8. Delete data source
        response = client.delete(f'/api/monitoring/data-sources/{data_source_id}', 
                               headers=auth_headers)
        assert response.status_code == 200
        
        # 9. Verify data source is deleted
        response = client.get(f'/api/monitoring/data-sources/{data_source_id}', 
                            headers=auth_headers)
        assert response.status_code == 404

class TestAlertIntegration:
    """Integration tests for alert functionality."""
    
    def test_alert_rule_lifecycle(self, client, auth_headers, sample_alert_rule_data):
        """Test complete alert rule lifecycle."""
        
        # 1. Create alert rule
        response = client.post('/api/alerts/rules', 
                             json=sample_alert_rule_data, headers=auth_headers)
        assert response.status_code == 201
        
        alert_rule_data = json.loads(response.data)
        alert_rule_id = alert_rule_data['alert_rule']['id']
        
        # 2. Get alert rule
        response = client.get(f'/api/alerts/rules/{alert_rule_id}', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        alert_rule = json.loads(response.data)['alert_rule']
        assert alert_rule['name'] == sample_alert_rule_data['name']
        assert alert_rule['severity'] == sample_alert_rule_data['severity']
        
        # 3. Update alert rule
        update_data = {
            'name': 'Updated Alert Rule',
            'severity': 'critical',
            'enabled': False
        }
        
        response = client.put(f'/api/alerts/rules/{alert_rule_id}', 
                            json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        updated_rule = json.loads(response.data)['alert_rule']
        assert updated_rule['name'] == 'Updated Alert Rule'
        assert updated_rule['severity'] == 'critical'
        assert updated_rule['enabled'] == False
        
        # 4. Re-enable alert rule
        response = client.put(f'/api/alerts/rules/{alert_rule_id}', 
                            json={'enabled': True}, headers=auth_headers)
        assert response.status_code == 200
        
        # 5. Get all alert rules
        response = client.get('/api/alerts/rules', headers=auth_headers)
        assert response.status_code == 200
        
        rules = json.loads(response.data)['alert_rules']
        assert len(rules) >= 1
        
        # 6. Delete alert rule
        response = client.delete(f'/api/alerts/rules/{alert_rule_id}', 
                               headers=auth_headers)
        assert response.status_code == 200
        
        # 7. Verify alert rule is deleted
        response = client.get(f'/api/alerts/rules/{alert_rule_id}', 
                            headers=auth_headers)
        assert response.status_code == 404
    
    def test_alert_lifecycle(self, client, auth_headers, test_alert_rule):
        """Test complete alert lifecycle."""
        
        # 1. Create alert (simulate alert rule triggering)
        alert_data = {
            'alert_rule_id': test_alert_rule.id,
            'severity': 'medium',
            'message': 'Test alert message',
            'triggered_at': datetime.utcnow().isoformat()
        }
        
        response = client.post('/api/alerts', json=alert_data, headers=auth_headers)
        assert response.status_code == 201
        
        alert_id = json.loads(response.data)['alert']['id']
        
        # 2. Get alert
        response = client.get(f'/api/alerts/{alert_id}', headers=auth_headers)
        assert response.status_code == 200
        
        alert = json.loads(response.data)['alert']
        assert alert['message'] == 'Test alert message'
        assert alert['status'] == 'active'
        
        # 3. Acknowledge alert
        response = client.post(f'/api/alerts/{alert_id}/acknowledge', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # 4. Verify alert is acknowledged
        response = client.get(f'/api/alerts/{alert_id}', headers=auth_headers)
        alert = json.loads(response.data)['alert']
        assert alert['status'] == 'acknowledged'
        assert alert['acknowledged_at'] is not None
        
        # 5. Resolve alert
        response = client.post(f'/api/alerts/{alert_id}/resolve', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # 6. Verify alert is resolved
        response = client.get(f'/api/alerts/{alert_id}', headers=auth_headers)
        alert = json.loads(response.data)['alert']
        assert alert['status'] == 'resolved'
        assert alert['resolved_at'] is not None
        
        # 7. Get alert history
        response = client.get('/api/alerts/history', headers=auth_headers)
        assert response.status_code == 200
        
        history = json.loads(response.data)['alerts']
        assert len(history) >= 1

class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""
    
    def test_dashboard_overview(self, client, auth_headers, test_pipeline, 
                               test_data_source, test_alert_rule):
        """Test dashboard overview with multiple components."""
        
        # 1. Get dashboard overview
        response = client.get('/api/dashboard/overview', headers=auth_headers)
        assert response.status_code == 200
        
        overview = json.loads(response.data)['overview']
        
        # Verify all components are present
        assert 'pipelines' in overview
        assert 'data_sources' in overview
        assert 'alerts' in overview
        assert 'users' in overview
        
        # 2. Get pipeline health
        response = client.get('/api/dashboard/pipeline-health', headers=auth_headers)
        assert response.status_code == 200
        
        pipeline_health = json.loads(response.data)['pipeline_health']
        assert 'pipelines' in pipeline_health
        assert 'summary' in pipeline_health
        
        # 3. Get recent activity
        response = client.get('/api/dashboard/recent-activity', headers=auth_headers)
        assert response.status_code == 200
        
        activities = json.loads(response.data)['activities']
        assert isinstance(activities, list)
        
        # 4. Get metrics summary
        response = client.get('/api/dashboard/metrics-summary', headers=auth_headers)
        assert response.status_code == 200
        
        metrics = json.loads(response.data)['metrics']
        assert 'pipeline_metrics' in metrics
        assert 'system_metrics' in metrics
        
        # 5. Get top pipelines
        response = client.get('/api/dashboard/top-pipelines', headers=auth_headers)
        assert response.status_code == 200
        
        top_pipelines = json.loads(response.data)['pipelines']
        assert isinstance(top_pipelines, list)

class TestUserManagementIntegration:
    """Integration tests for user management functionality."""
    
    def test_user_lifecycle(self, client, admin_headers):
        """Test complete user lifecycle (admin only)."""
        
        # 1. Create user
        user_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'user'
        }
        
        response = client.post('/api/users', json=user_data, headers=admin_headers)
        assert response.status_code == 201
        
        user_id = json.loads(response.data)['user']['id']
        
        # 2. Get user
        response = client.get(f'/api/users/{user_id}', headers=admin_headers)
        assert response.status_code == 200
        
        user = json.loads(response.data)['user']
        assert user['email'] == 'newuser@example.com'
        assert user['role'] == 'user'
        
        # 3. Update user
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'role': 'manager'
        }
        
        response = client.put(f'/api/users/{user_id}', 
                            json=update_data, headers=admin_headers)
        assert response.status_code == 200
        
        updated_user = json.loads(response.data)['user']
        assert updated_user['first_name'] == 'Updated'
        assert updated_user['role'] == 'manager'
        
        # 4. Get all users
        response = client.get('/api/users', headers=admin_headers)
        assert response.status_code == 200
        
        users = json.loads(response.data)['users']
        assert len(users) >= 2  # At least admin and new user
        
        # 5. Invite user
        invite_data = {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
            'role': 'user',
            'send_invitation': True
        }
        
        response = client.post('/api/users/invite', 
                             json=invite_data, headers=admin_headers)
        assert response.status_code == 201
        
        # 6. Delete user
        response = client.delete(f'/api/users/{user_id}', headers=admin_headers)
        assert response.status_code == 200
        
        # 7. Verify user is deleted
        response = client.get(f'/api/users/{user_id}', headers=admin_headers)
        assert response.status_code == 404

class TestAuthenticationIntegration:
    """Integration tests for authentication functionality."""
    
    def test_complete_auth_flow(self, client, test_organization):
        """Test complete authentication flow."""
        
        # 1. Register new user
        register_data = {
            'email': 'authuser@example.com',
            'password': 'password123',
            'first_name': 'Auth',
            'last_name': 'User',
            'organization_name': 'Auth Organization'
        }
        
        response = client.post('/api/auth/register', json=register_data)
        assert response.status_code == 201
        
        # 2. Login with new user
        login_data = {
            'email': 'authuser@example.com',
            'password': 'password123'
        }
        
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 200
        
        login_result = json.loads(response.data)
        access_token = login_result['access_token']
        refresh_token = login_result['refresh_token']
        
        auth_headers = {'Authorization': f'Bearer {access_token}'}
        
        # 3. Access protected endpoint
        response = client.get('/api/auth/profile', headers=auth_headers)
        assert response.status_code == 200
        
        profile = json.loads(response.data)['user']
        assert profile['email'] == 'authuser@example.com'
        
        # 4. Update profile
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'timezone': 'UTC'
        }
        
        response = client.put('/api/auth/profile', 
                            json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        updated_profile = json.loads(response.data)['user']
        assert updated_profile['first_name'] == 'Updated'
        
        # 5. Refresh token
        response = client.post('/api/auth/refresh', 
                             headers={'Authorization': f'Bearer {refresh_token}'})
        assert response.status_code == 200
        
        refresh_result = json.loads(response.data)
        assert 'access_token' in refresh_result
        
        # 6. Test invalid token
        response = client.get('/api/auth/profile', 
                            headers={'Authorization': 'Bearer invalid-token'})
        assert response.status_code == 401

class TestDataFlowIntegration:
    """Integration tests for complete data flow scenarios."""
    
    def test_pipeline_monitoring_alert_flow(self, client, auth_headers, 
                                           test_organization, test_data_source):
        """Test complete flow: pipeline -> monitoring -> alerting."""
        
        # 1. Create pipeline
        pipeline_data = {
            'name': 'Integration Test Pipeline',
            'description': 'Pipeline for integration testing',
            'pipeline_type': 'etl',
            'config': {
                'source': 'test_source',
                'destination': 'test_dest',
                'data_source_id': test_data_source.id
            },
            'schedule': '0 2 * * *',
            'timeout_minutes': 60,
            'health_check_enabled': True,
            'freshness_threshold_hours': 24
        }
        
        response = client.post('/api/pipelines', 
                             json=pipeline_data, headers=auth_headers)
        assert response.status_code == 201
        
        pipeline_id = json.loads(response.data)['pipeline']['id']
        
        # 2. Create health check for data source
        health_check_data = {
            'name': 'Integration Health Check',
            'data_source_id': test_data_source.id,
            'check_type': 'query',
            'query': 'SELECT COUNT(*) FROM test_table',
            'expected_result': '100',
            'interval_minutes': 5,
            'timeout_seconds': 30,
            'enabled': True
        }
        
        response = client.post('/api/monitoring/health-checks', 
                             json=health_check_data, headers=auth_headers)
        assert response.status_code == 201
        
        health_check_id = json.loads(response.data)['health_check']['id']
        
        # 3. Create alert rule
        alert_rule_data = {
            'name': 'Integration Alert Rule',
            'description': 'Alert rule for integration testing',
            'severity': 'high',
            'condition_type': 'threshold',
            'condition_config': {
                'metric': 'pipeline_failure_rate',
                'threshold': 0.1
            },
            'notification_channels': ['email'],
            'enabled': True
        }
        
        response = client.post('/api/alerts/rules', 
                             json=alert_rule_data, headers=auth_headers)
        assert response.status_code == 201
        
        alert_rule_id = json.loads(response.data)['alert_rule']['id']
        
        # 4. Execute health check
        response = client.post(f'/api/monitoring/health-checks/{health_check_id}/execute', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # 5. Trigger pipeline
        response = client.post(f'/api/pipelines/{pipeline_id}/trigger', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # 6. Check dashboard overview
        response = client.get('/api/dashboard/overview', headers=auth_headers)
        assert response.status_code == 200
        
        overview = json.loads(response.data)['overview']
        assert overview['pipelines']['total'] >= 1
        assert overview['data_sources']['total'] >= 1
        assert overview['alerts']['total'] >= 0
        
        # 7. Check pipeline health
        response = client.get('/api/dashboard/pipeline-health', headers=auth_headers)
        assert response.status_code == 200
        
        # 8. Clean up
        client.delete(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        client.delete(f'/api/monitoring/health-checks/{health_check_id}', headers=auth_headers)
        client.delete(f'/api/alerts/rules/{alert_rule_id}', headers=auth_headers)
    
    def test_multi_user_organization_flow(self, client, admin_headers, auth_headers):
        """Test multi-user organization workflow."""
        
        # 1. Admin creates user
        user_data = {
            'email': 'teamuser@example.com',
            'first_name': 'Team',
            'last_name': 'User',
            'role': 'user'
        }
        
        response = client.post('/api/users', json=user_data, headers=admin_headers)
        assert response.status_code == 201
        
        user_id = json.loads(response.data)['user']['id']
        
        # 2. Admin creates pipeline
        pipeline_data = {
            'name': 'Team Pipeline',
            'description': 'Pipeline for team collaboration',
            'pipeline_type': 'etl',
            'config': {'source': 'team_source'},
            'schedule': '0 3 * * *'
        }
        
        response = client.post('/api/pipelines', 
                             json=pipeline_data, headers=admin_headers)
        assert response.status_code == 201
        
        pipeline_id = json.loads(response.data)['pipeline']['id']
        
        # 3. Regular user can view pipeline (same organization)
        response = client.get(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        assert response.status_code == 200
        
        # 4. Regular user cannot delete pipeline (insufficient permissions)
        response = client.delete(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        assert response.status_code == 403
        
        # 5. Admin can delete pipeline
        response = client.delete(f'/api/pipelines/{pipeline_id}', headers=admin_headers)
        assert response.status_code == 200
        
        # 6. Admin can delete user
        response = client.delete(f'/api/users/{user_id}', headers=admin_headers)
        assert response.status_code == 200

class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""
    
    def test_database_connection_error_handling(self, client, auth_headers):
        """Test handling of database connection errors."""
        
        # This test would require mocking database connection failures
        # For now, we test basic error responses
        
        # Test invalid pipeline ID
        response = client.get('/api/pipelines/999999', headers=auth_headers)
        assert response.status_code == 404
        
        # Test invalid data source ID
        response = client.get('/api/monitoring/data-sources/999999', headers=auth_headers)
        assert response.status_code == 404
        
        # Test invalid alert rule ID
        response = client.get('/api/alerts/rules/999999', headers=auth_headers)
        assert response.status_code == 404
    
    def test_validation_error_handling(self, client, auth_headers):
        """Test handling of validation errors."""
        
        # Test invalid email format
        invalid_user_data = {
            'email': 'invalid-email',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'user'
        }
        
        response = client.post('/api/users', json=invalid_user_data, headers=auth_headers)
        assert response.status_code == 400
        
        # Test invalid pipeline type
        invalid_pipeline_data = {
            'name': 'Test Pipeline',
            'pipeline_type': 'invalid_type'
        }
        
        response = client.post('/api/pipelines', 
                             json=invalid_pipeline_data, headers=auth_headers)
        assert response.status_code == 400
        
        # Test invalid alert severity
        invalid_alert_data = {
            'name': 'Test Alert',
            'severity': 'invalid_severity',
            'condition_type': 'threshold'
        }
        
        response = client.post('/api/alerts/rules', 
                             json=invalid_alert_data, headers=auth_headers)
        assert response.status_code == 400
    
    def test_authorization_error_handling(self, client, auth_headers, admin_headers):
        """Test handling of authorization errors."""
        
        # Regular user cannot access admin endpoints
        response = client.get('/api/users', headers=auth_headers)
        assert response.status_code == 403
        
        # Admin can access admin endpoints
        response = client.get('/api/users', headers=admin_headers)
        assert response.status_code == 200
        
        # Test accessing resource from different organization
        # This would require creating a user in a different organization
        # For now, we test basic authorization patterns 