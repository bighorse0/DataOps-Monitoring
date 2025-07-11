import pytest
import json
from datetime import datetime, timedelta
from app import db
from app.models.user import User
from app.models.organization import Organization
from app.models.pipeline import Pipeline, PipelineRun
from app.models.monitoring import DataSource, HealthCheck
from app.models.alert import AlertRule, Alert

class TestAuthAPI:
    """Test cases for authentication API endpoints."""
    
    def test_register_user(self, client):
        """Test user registration."""
        data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'first_name': 'New',
            'last_name': 'User',
            'organization_name': 'New Organization'
        }
        
        response = client.post('/api/auth/register', json=data)
        assert response.status_code == 201
        
        result = json.loads(response.data)
        assert result['message'] == 'User registered successfully'
        assert 'user' in result
        assert result['user']['email'] == 'newuser@example.com'
    
    def test_register_user_existing_email(self, client, test_user):
        """Test registration with existing email."""
        data = {
            'email': test_user.email,
            'password': 'password123',
            'first_name': 'Test',
            'last_name': 'User',
            'organization_name': 'Test Organization'
        }
        
        response = client.post('/api/auth/register', json=data)
        assert response.status_code == 409
        assert 'already exists' in json.loads(response.data)['error']
    
    def test_login_user(self, client, test_user):
        """Test user login."""
        data = {
            'email': test_user.email,
            'password': 'password123'
        }
        
        response = client.post('/api/auth/login', json=data)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'access_token' in result
        assert 'refresh_token' in result
        assert 'user' in result
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        
        response = client.post('/api/auth/login', json=data)
        assert response.status_code == 401
        assert 'Invalid credentials' in json.loads(response.data)['error']
    
    def test_refresh_token(self, client, test_user):
        """Test token refresh."""
        # First login to get tokens
        login_data = {
            'email': test_user.email,
            'password': 'password123'
        }
        login_response = client.post('/api/auth/login', json=login_data)
        refresh_token = json.loads(login_response.data)['refresh_token']
        
        # Refresh the token
        response = client.post('/api/auth/refresh', 
                             headers={'Authorization': f'Bearer {refresh_token}'})
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'access_token' in result
    
    def test_get_profile(self, client, auth_headers):
        """Test getting user profile."""
        response = client.get('/api/auth/profile', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'user' in result
        assert result['user']['email'] == 'test@example.com'
    
    def test_update_profile(self, client, auth_headers):
        """Test updating user profile."""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'timezone': 'UTC'
        }
        
        response = client.put('/api/auth/profile', 
                            json=data, headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'Profile updated successfully'
        assert result['user']['first_name'] == 'Updated'

class TestPipelinesAPI:
    """Test cases for pipelines API endpoints."""
    
    def test_get_pipelines(self, client, auth_headers, test_pipeline):
        """Test getting all pipelines."""
        response = client.get('/api/pipelines', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'pipelines' in result
        assert len(result['pipelines']) == 1
        assert result['pipelines'][0]['name'] == test_pipeline.name
    
    def test_get_pipeline(self, client, auth_headers, test_pipeline):
        """Test getting a specific pipeline."""
        response = client.get(f'/api/pipelines/{test_pipeline.id}', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'pipeline' in result
        assert result['pipeline']['id'] == test_pipeline.id
    
    def test_get_pipeline_not_found(self, client, auth_headers):
        """Test getting non-existent pipeline."""
        response = client.get('/api/pipelines/999', headers=auth_headers)
        assert response.status_code == 404
    
    def test_create_pipeline(self, client, auth_headers, sample_pipeline_data):
        """Test creating a new pipeline."""
        response = client.post('/api/pipelines', 
                             json=sample_pipeline_data, headers=auth_headers)
        assert response.status_code == 201
        
        result = json.loads(response.data)
        assert result['message'] == 'Pipeline created successfully'
        assert 'pipeline' in result
        assert result['pipeline']['name'] == sample_pipeline_data['name']
    
    def test_create_pipeline_missing_required_fields(self, client, auth_headers):
        """Test creating pipeline with missing required fields."""
        data = {'description': 'Test pipeline'}
        
        response = client.post('/api/pipelines', json=data, headers=auth_headers)
        assert response.status_code == 400
        assert 'required' in json.loads(response.data)['error']
    
    def test_create_pipeline_duplicate_name(self, client, auth_headers, test_pipeline):
        """Test creating pipeline with duplicate name."""
        data = {
            'name': test_pipeline.name,
            'pipeline_type': 'etl'
        }
        
        response = client.post('/api/pipelines', json=data, headers=auth_headers)
        assert response.status_code == 409
        assert 'already exists' in json.loads(response.data)['error']
    
    def test_update_pipeline(self, client, auth_headers, test_pipeline):
        """Test updating a pipeline."""
        data = {
            'name': 'Updated Pipeline',
            'description': 'Updated description'
        }
        
        response = client.put(f'/api/pipelines/{test_pipeline.id}', 
                            json=data, headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'Pipeline updated successfully'
        assert result['pipeline']['name'] == 'Updated Pipeline'
    
    def test_delete_pipeline(self, client, auth_headers, test_pipeline):
        """Test deleting a pipeline."""
        response = client.delete(f'/api/pipelines/{test_pipeline.id}', 
                               headers=auth_headers)
        assert response.status_code == 200
        assert 'deleted successfully' in json.loads(response.data)['message']
    
    def test_get_pipeline_runs(self, client, auth_headers, test_pipeline, test_pipeline_run):
        """Test getting pipeline runs."""
        response = client.get(f'/api/pipelines/{test_pipeline.id}/runs', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'runs' in result
        assert len(result['runs']) == 1
    
    def test_get_pipeline_run(self, client, auth_headers, test_pipeline, test_pipeline_run):
        """Test getting a specific pipeline run."""
        response = client.get(f'/api/pipelines/{test_pipeline.id}/runs/{test_pipeline_run.id}', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'run' in result
        assert result['run']['id'] == test_pipeline_run.id
    
    def test_trigger_pipeline(self, client, auth_headers, test_pipeline, mock_celery):
        """Test triggering a pipeline."""
        response = client.post(f'/api/pipelines/{test_pipeline.id}/trigger', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'Pipeline triggered successfully'
        assert 'task_id' in result
    
    def test_get_pipeline_metrics(self, client, auth_headers, test_pipeline):
        """Test getting pipeline metrics."""
        response = client.get(f'/api/pipelines/{test_pipeline.id}/metrics', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'metrics' in result

class TestMonitoringAPI:
    """Test cases for monitoring API endpoints."""
    
    def test_get_data_sources(self, client, auth_headers, test_data_source):
        """Test getting all data sources."""
        response = client.get('/api/monitoring/data-sources', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'data_sources' in result
        assert len(result['data_sources']) == 1
        assert result['data_sources'][0]['name'] == test_data_source.name
    
    def test_get_data_source(self, client, auth_headers, test_data_source):
        """Test getting a specific data source."""
        response = client.get(f'/api/monitoring/data-sources/{test_data_source.id}', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'data_source' in result
        assert result['data_source']['id'] == test_data_source.id
    
    def test_create_data_source(self, client, auth_headers, sample_data_source_data):
        """Test creating a new data source."""
        response = client.post('/api/monitoring/data-sources', 
                             json=sample_data_source_data, headers=auth_headers)
        assert response.status_code == 201
        
        result = json.loads(response.data)
        assert result['message'] == 'Data source created successfully'
        assert 'data_source' in result
        assert result['data_source']['name'] == sample_data_source_data['name']
    
    def test_update_data_source(self, client, auth_headers, test_data_source):
        """Test updating a data source."""
        data = {
            'name': 'Updated Data Source',
            'host': 'updated-host.com'
        }
        
        response = client.put(f'/api/monitoring/data-sources/{test_data_source.id}', 
                            json=data, headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'Data source updated successfully'
        assert result['data_source']['name'] == 'Updated Data Source'
    
    def test_delete_data_source(self, client, auth_headers, test_data_source):
        """Test deleting a data source."""
        response = client.delete(f'/api/monitoring/data-sources/{test_data_source.id}', 
                               headers=auth_headers)
        assert response.status_code == 200
        assert 'deleted successfully' in json.loads(response.data)['message']
    
    def test_test_data_source_connection(self, client, auth_headers, test_data_source):
        """Test testing data source connection."""
        response = client.post(f'/api/monitoring/data-sources/{test_data_source.id}/test', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'success' in result
    
    def test_get_health_checks(self, client, auth_headers, test_health_check):
        """Test getting all health checks."""
        response = client.get('/api/monitoring/health-checks', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'health_checks' in result
        assert len(result['health_checks']) == 1
    
    def test_create_health_check(self, client, auth_headers, test_data_source):
        """Test creating a new health check."""
        data = {
            'name': 'Test Health Check',
            'data_source_id': test_data_source.id,
            'check_type': 'query',
            'query': 'SELECT 1',
            'expected_result': '1',
            'interval_minutes': 5,
            'timeout_seconds': 30,
            'enabled': True
        }
        
        response = client.post('/api/monitoring/health-checks', 
                             json=data, headers=auth_headers)
        assert response.status_code == 201
        
        result = json.loads(response.data)
        assert result['message'] == 'Health check created successfully'
        assert 'health_check' in result
    
    def test_execute_health_check(self, client, auth_headers, test_health_check):
        """Test executing a health check."""
        response = client.post(f'/api/monitoring/health-checks/{test_health_check.id}/execute', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'success' in result

class TestAlertsAPI:
    """Test cases for alerts API endpoints."""
    
    def test_get_alert_rules(self, client, auth_headers, test_alert_rule):
        """Test getting all alert rules."""
        response = client.get('/api/alerts/rules', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'alert_rules' in result
        assert len(result['alert_rules']) == 1
        assert result['alert_rules'][0]['name'] == test_alert_rule.name
    
    def test_get_alert_rule(self, client, auth_headers, test_alert_rule):
        """Test getting a specific alert rule."""
        response = client.get(f'/api/alerts/rules/{test_alert_rule.id}', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'alert_rule' in result
        assert result['alert_rule']['id'] == test_alert_rule.id
    
    def test_create_alert_rule(self, client, auth_headers, sample_alert_rule_data):
        """Test creating a new alert rule."""
        response = client.post('/api/alerts/rules', 
                             json=sample_alert_rule_data, headers=auth_headers)
        assert response.status_code == 201
        
        result = json.loads(response.data)
        assert result['message'] == 'Alert rule created successfully'
        assert 'alert_rule' in result
        assert result['alert_rule']['name'] == sample_alert_rule_data['name']
    
    def test_update_alert_rule(self, client, auth_headers, test_alert_rule):
        """Test updating an alert rule."""
        data = {
            'name': 'Updated Alert Rule',
            'severity': 'high'
        }
        
        response = client.put(f'/api/alerts/rules/{test_alert_rule.id}', 
                            json=data, headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'Alert rule updated successfully'
        assert result['alert_rule']['name'] == 'Updated Alert Rule'
    
    def test_delete_alert_rule(self, client, auth_headers, test_alert_rule):
        """Test deleting an alert rule."""
        response = client.delete(f'/api/alerts/rules/{test_alert_rule.id}', 
                               headers=auth_headers)
        assert response.status_code == 200
        assert 'deleted successfully' in json.loads(response.data)['message']
    
    def test_get_alerts(self, client, auth_headers, test_alert):
        """Test getting all alerts."""
        response = client.get('/api/alerts', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'alerts' in result
        assert len(result['alerts']) == 1
    
    def test_get_alert(self, client, auth_headers, test_alert):
        """Test getting a specific alert."""
        response = client.get(f'/api/alerts/{test_alert.id}', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'alert' in result
        assert result['alert']['id'] == test_alert.id
    
    def test_acknowledge_alert(self, client, auth_headers, test_alert):
        """Test acknowledging an alert."""
        response = client.post(f'/api/alerts/{test_alert.id}/acknowledge', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'Alert acknowledged successfully'
    
    def test_resolve_alert(self, client, auth_headers, test_alert):
        """Test resolving an alert."""
        response = client.post(f'/api/alerts/{test_alert.id}/resolve', 
                             headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'Alert resolved successfully'
    
    def test_get_alert_history(self, client, auth_headers, test_alert):
        """Test getting alert history."""
        response = client.get('/api/alerts/history', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'alerts' in result

class TestDashboardAPI:
    """Test cases for dashboard API endpoints."""
    
    def test_get_dashboard_overview(self, client, auth_headers, test_pipeline, test_data_source):
        """Test getting dashboard overview."""
        response = client.get('/api/dashboard/overview', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'overview' in result
        assert 'pipelines' in result['overview']
        assert 'data_sources' in result['overview']
        assert 'alerts' in result['overview']
    
    def test_get_pipeline_health(self, client, auth_headers, test_pipeline):
        """Test getting pipeline health summary."""
        response = client.get('/api/dashboard/pipeline-health', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'pipeline_health' in result
        assert 'pipelines' in result['pipeline_health']
    
    def test_get_recent_activity(self, client, auth_headers, test_pipeline_run):
        """Test getting recent activity."""
        response = client.get('/api/dashboard/recent-activity', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'activities' in result
    
    def test_get_metrics_summary(self, client, auth_headers, test_pipeline):
        """Test getting metrics summary."""
        response = client.get('/api/dashboard/metrics-summary', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'metrics' in result
    
    def test_get_top_pipelines(self, client, auth_headers, test_pipeline):
        """Test getting top pipelines."""
        response = client.get('/api/dashboard/top-pipelines', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'pipelines' in result

class TestUsersAPI:
    """Test cases for users API endpoints."""
    
    def test_get_users(self, client, admin_headers, test_user):
        """Test getting all users (admin only)."""
        response = client.get('/api/users', headers=admin_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'users' in result
        assert len(result['users']) >= 1
    
    def test_get_users_unauthorized(self, client, auth_headers):
        """Test getting users without admin privileges."""
        response = client.get('/api/users', headers=auth_headers)
        assert response.status_code == 403
    
    def test_get_user(self, client, admin_headers, test_user):
        """Test getting a specific user."""
        response = client.get(f'/api/users/{test_user.id}', headers=admin_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'user' in result
        assert result['user']['id'] == test_user.id
    
    def test_create_user(self, client, admin_headers):
        """Test creating a new user."""
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'user'
        }
        
        response = client.post('/api/users', json=data, headers=admin_headers)
        assert response.status_code == 201
        
        result = json.loads(response.data)
        assert result['message'] == 'User created successfully'
        assert 'user' in result
    
    def test_update_user(self, client, admin_headers, test_user):
        """Test updating a user."""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'role': 'manager'
        }
        
        response = client.put(f'/api/users/{test_user.id}', 
                            json=data, headers=admin_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert result['message'] == 'User updated successfully'
        assert result['user']['first_name'] == 'Updated'
    
    def test_delete_user(self, client, admin_headers, test_user):
        """Test deleting a user."""
        response = client.delete(f'/api/users/{test_user.id}', 
                               headers=admin_headers)
        assert response.status_code == 200
        assert 'deleted successfully' in json.loads(response.data)['message']
    
    def test_invite_user(self, client, admin_headers):
        """Test inviting a user."""
        data = {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
            'role': 'user',
            'send_invitation': True
        }
        
        response = client.post('/api/users/invite', json=data, headers=admin_headers)
        assert response.status_code == 201
        
        result = json.loads(response.data)
        assert result['message'] == 'User invitation sent successfully'

class TestAPIAuthentication:
    """Test cases for API authentication and authorization."""
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get('/api/pipelines')
        assert response.status_code == 401
    
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = client.get('/api/pipelines', headers=headers)
        assert response.status_code == 401
    
    def test_protected_endpoint_with_expired_token(self, client, app, test_user):
        """Test accessing protected endpoint with expired token."""
        with app.app_context():
            import jwt
            expired_token = jwt.encode(
                {
                    'user_id': test_user.id,
                    'exp': datetime.utcnow() - timedelta(hours=1)
                },
                app.config['JWT_SECRET_KEY'],
                algorithm='HS256'
            )
        
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = client.get('/api/pipelines', headers=headers)
        assert response.status_code == 401
    
    def test_role_based_access_control(self, client, auth_headers, admin_headers):
        """Test role-based access control."""
        # Regular user should not access admin endpoints
        response = client.get('/api/users', headers=auth_headers)
        assert response.status_code == 403
        
        # Admin should access admin endpoints
        response = client.get('/api/users', headers=admin_headers)
        assert response.status_code == 200

class TestAPIErrorHandling:
    """Test cases for API error handling."""
    
    def test_invalid_json_request(self, client, auth_headers):
        """Test handling invalid JSON in request."""
        response = client.post('/api/pipelines', 
                             data='invalid json', 
                             headers=auth_headers)
        assert response.status_code == 400
    
    def test_missing_required_fields(self, client, auth_headers):
        """Test handling missing required fields."""
        response = client.post('/api/pipelines', 
                             json={}, 
                             headers=auth_headers)
        assert response.status_code == 400
    
    def test_invalid_data_types(self, client, auth_headers):
        """Test handling invalid data types."""
        data = {
            'name': 123,  # Should be string
            'pipeline_type': 'invalid_type'
        }
        
        response = client.post('/api/pipelines', 
                             json=data, 
                             headers=auth_headers)
        assert response.status_code == 400
    
    def test_resource_not_found(self, client, auth_headers):
        """Test handling resource not found."""
        response = client.get('/api/pipelines/999999', headers=auth_headers)
        assert response.status_code == 404
    
    def test_duplicate_resource(self, client, auth_headers, test_pipeline):
        """Test handling duplicate resource creation."""
        data = {
            'name': test_pipeline.name,
            'pipeline_type': 'etl'
        }
        
        response = client.post('/api/pipelines', 
                             json=data, 
                             headers=auth_headers)
        assert response.status_code == 409 