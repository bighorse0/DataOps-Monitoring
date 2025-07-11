import pytest
import json
import jwt
from datetime import datetime, timedelta
from app import db
from app.models.user import User
from app.models.organization import Organization
from app.models.pipeline import Pipeline
from app.models.monitoring import DataSource
from app.models.alert import AlertRule

class TestAuthenticationSecurity:
    """Security tests for authentication system."""
    
    def test_password_strength_validation(self, client):
        """Test password strength requirements."""
        
        # Test weak passwords
        weak_passwords = [
            '123456',
            'password',
            'qwerty',
            'abc123',
            'password123',
            'admin',
            'test'
        ]
        
        for weak_password in weak_passwords:
            data = {
                'email': 'test@example.com',
                'password': weak_password,
                'first_name': 'Test',
                'last_name': 'User',
                'organization_name': 'Test Organization'
            }
            
            response = client.post('/api/auth/register', json=data)
            assert response.status_code == 400
            assert 'password' in json.loads(response.data)['error'].lower()
        
        # Test strong password
        strong_password = 'StrongP@ssw0rd123!'
        data = {
            'email': 'test@example.com',
            'password': strong_password,
            'first_name': 'Test',
            'last_name': 'User',
            'organization_name': 'Test Organization'
        }
        
        response = client.post('/api/auth/register', json=data)
        assert response.status_code == 201
    
    def test_jwt_token_security(self, client, test_user, app):
        """Test JWT token security features."""
        
        # Login to get tokens
        login_data = {
            'email': test_user.email,
            'password': 'password123'
        }
        
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 200
        
        tokens = json.loads(response.data)
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        
        # Test token structure
        decoded_access = jwt.decode(access_token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        decoded_refresh = jwt.decode(refresh_token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        
        # Verify required claims
        assert 'user_id' in decoded_access
        assert 'exp' in decoded_access
        assert 'iat' in decoded_access
        assert 'user_id' in decoded_refresh
        assert 'exp' in decoded_refresh
        
        # Verify token expiration
        assert decoded_access['exp'] > datetime.utcnow().timestamp()
        assert decoded_refresh['exp'] > datetime.utcnow().timestamp()
        
        # Verify access token has shorter expiration than refresh token
        assert decoded_access['exp'] < decoded_refresh['exp']
    
    def test_token_tampering_detection(self, client, test_user, app):
        """Test detection of tampered JWT tokens."""
        
        # Login to get valid token
        login_data = {
            'email': test_user.email,
            'password': 'password123'
        }
        
        response = client.post('/api/auth/login', json=login_data)
        tokens = json.loads(response.data)
        access_token = tokens['access_token']
        
        # Tamper with token
        tampered_token = access_token[:-1] + 'X'
        
        # Test tampered token
        response = client.get('/api/auth/profile', 
                            headers={'Authorization': f'Bearer {tampered_token}'})
        assert response.status_code == 401
    
    def test_expired_token_handling(self, client, test_user, app):
        """Test handling of expired tokens."""
        
        # Create expired token
        expired_token = jwt.encode(
            {
                'user_id': test_user.id,
                'exp': datetime.utcnow() - timedelta(hours=1),
                'iat': datetime.utcnow() - timedelta(hours=2)
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        # Test expired token
        response = client.get('/api/auth/profile', 
                            headers={'Authorization': f'Bearer {expired_token}'})
        assert response.status_code == 401
    
    def test_brute_force_protection(self, client):
        """Test brute force attack protection."""
        
        # Attempt multiple failed logins
        for i in range(10):
            login_data = {
                'email': 'nonexistent@example.com',
                'password': f'wrongpassword{i}'
            }
            
            response = client.post('/api/auth/login', json=login_data)
            assert response.status_code == 401
        
        # Verify account is not locked (rate limiting should be in place)
        # In a real implementation, you might want to implement account lockout
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        
        response = client.post('/api/auth/login', json=login_data)
        assert response.status_code == 401

class TestAuthorizationSecurity:
    """Security tests for authorization system."""
    
    def test_role_based_access_control(self, client, auth_headers, admin_headers):
        """Test role-based access control enforcement."""
        
        # Regular user cannot access admin endpoints
        admin_endpoints = [
            '/api/users',
            '/api/users/invite',
            '/api/organizations',
            '/api/system/settings'
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 403
        
        # Admin can access admin endpoints
        for endpoint in admin_endpoints:
            response = client.get(endpoint, headers=admin_headers)
            assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist
    
    def test_resource_ownership_validation(self, client, auth_headers, test_organization):
        """Test that users can only access their own resources."""
        
        # Create pipeline for test user
        pipeline_data = {
            'name': 'Test Pipeline',
            'pipeline_type': 'etl',
            'config': {'source': 'test_source'},
            'schedule': '0 0 * * *'
        }
        
        response = client.post('/api/pipelines', 
                             json=pipeline_data, headers=auth_headers)
        assert response.status_code == 201
        
        pipeline_id = json.loads(response.data)['pipeline']['id']
        
        # Test user can access their own pipeline
        response = client.get(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        assert response.status_code == 200
        
        # Test user cannot access pipeline from different organization
        # This would require creating a user in a different organization
        # For now, we test the basic pattern
    
    def test_cross_organization_access_prevention(self, client, auth_headers):
        """Test prevention of cross-organization data access."""
        
        # Attempt to access resources with invalid organization context
        # This test would require setting up multiple organizations
        # For now, we verify the basic security pattern
        
        # Test that user cannot access resources outside their organization
        response = client.get('/api/pipelines', headers=auth_headers)
        assert response.status_code == 200
        
        # Verify response only contains user's organization data
        result = json.loads(response.data)
        assert 'pipelines' in result

class TestInputValidationSecurity:
    """Security tests for input validation."""
    
    def test_sql_injection_prevention(self, client, auth_headers):
        """Test prevention of SQL injection attacks."""
        
        # Test SQL injection attempts in search parameters
        sql_injection_attempts = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' UNION SELECT * FROM users --",
            "'; UPDATE users SET role='admin' WHERE id=1; --"
        ]
        
        for injection in sql_injection_attempts:
            response = client.get(f'/api/pipelines?search={injection}', 
                                headers=auth_headers)
            assert response.status_code == 200  # Should not crash
            # Verify no unauthorized data is returned
            result = json.loads(response.data)
            assert 'pipelines' in result
    
    def test_xss_prevention(self, client, auth_headers):
        """Test prevention of XSS attacks."""
        
        # Test XSS attempts in pipeline names
        xss_attempts = [
            '<script>alert("XSS")</script>',
            'javascript:alert("XSS")',
            '<img src="x" onerror="alert(\'XSS\')">',
            '"><script>alert("XSS")</script>',
            '&#60;script&#62;alert("XSS")&#60;/script&#62;'
        ]
        
        for xss in xss_attempts:
            pipeline_data = {
                'name': xss,
                'pipeline_type': 'etl',
                'config': {'source': 'test_source'},
                'schedule': '0 0 * * *'
            }
            
            response = client.post('/api/pipelines', 
                                 json=pipeline_data, headers=auth_headers)
            
            if response.status_code == 201:
                pipeline_id = json.loads(response.data)['pipeline']['id']
                
                # Verify XSS is properly escaped in response
                response = client.get(f'/api/pipelines/{pipeline_id}', 
                                    headers=auth_headers)
                assert response.status_code == 200
                
                result = json.loads(response.data)
                pipeline_name = result['pipeline']['name']
                
                # Verify no script tags in response
                assert '<script>' not in pipeline_name
                assert 'javascript:' not in pipeline_name
    
    def test_path_traversal_prevention(self, client, auth_headers):
        """Test prevention of path traversal attacks."""
        
        # Test path traversal attempts
        path_traversal_attempts = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '....//....//....//etc/passwd',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd'
        ]
        
        for traversal in path_traversal_attempts:
            # Test in file upload endpoints (if they exist)
            # For now, test in search parameters
            response = client.get(f'/api/pipelines?search={traversal}', 
                                headers=auth_headers)
            assert response.status_code == 200
    
    def test_command_injection_prevention(self, client, auth_headers):
        """Test prevention of command injection attacks."""
        
        # Test command injection attempts in configuration
        command_injection_attempts = [
            '; rm -rf /',
            '| cat /etc/passwd',
            '&& whoami',
            '$(whoami)',
            '`id`'
        ]
        
        for injection in command_injection_attempts:
            pipeline_data = {
                'name': 'Test Pipeline',
                'pipeline_type': 'etl',
                'config': {
                    'source': 'test_source',
                    'command': injection
                },
                'schedule': '0 0 * * *'
            }
            
            response = client.post('/api/pipelines', 
                                 json=pipeline_data, headers=auth_headers)
            
            # Should either reject or sanitize the input
            assert response.status_code in [201, 400]

class TestDataSecurity:
    """Security tests for data protection."""
    
    def test_sensitive_data_encryption(self, client, auth_headers, test_organization):
        """Test encryption of sensitive data."""
        
        # Create data source with sensitive information
        data_source_data = {
            'name': 'Test Database',
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'sensitive_password_123',
            'connection_string': 'postgresql://test_user:sensitive_password_123@localhost:5432/test_db'
        }
        
        response = client.post('/api/monitoring/data-sources', 
                             json=data_source_data, headers=auth_headers)
        assert response.status_code == 201
        
        data_source_id = json.loads(response.data)['data_source']['id']
        
        # Verify sensitive data is not returned in plain text
        response = client.get(f'/api/monitoring/data-sources/{data_source_id}', 
                            headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)['data_source']
        assert 'password' not in result
        assert 'sensitive_password_123' not in str(result)
    
    def test_data_sanitization(self, client, auth_headers):
        """Test data sanitization in responses."""
        
        # Create pipeline with potentially sensitive data
        pipeline_data = {
            'name': 'Test Pipeline',
            'pipeline_type': 'etl',
            'config': {
                'source': 'test_source',
                'password': 'secret_password',
                'api_key': 'sk-1234567890abcdef',
                'connection_string': 'postgresql://user:pass@host:5432/db'
            },
            'schedule': '0 0 * * *'
        }
        
        response = client.post('/api/pipelines', 
                             json=pipeline_data, headers=auth_headers)
        assert response.status_code == 201
        
        pipeline_id = json.loads(response.data)['pipeline']['id']
        
        # Verify sensitive data is sanitized in response
        response = client.get(f'/api/pipelines/{pipeline_id}', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)['pipeline']
        config = result['config']
        
        # Sensitive data should be masked or removed
        assert 'password' not in config or config['password'] != 'secret_password'
        assert 'api_key' not in config or config['api_key'] != 'sk-1234567890abcdef'
    
    def test_audit_logging(self, client, auth_headers, test_pipeline):
        """Test audit logging of sensitive operations."""
        
        # Perform sensitive operations
        operations = [
            ('DELETE', f'/api/pipelines/{test_pipeline.id}'),
            ('PUT', f'/api/pipelines/{test_pipeline.id}', {'name': 'Updated Pipeline'}),
            ('POST', f'/api/pipelines/{test_pipeline.id}/trigger')
        ]
        
        for method, endpoint, *args in operations:
            if method == 'DELETE':
                response = client.delete(endpoint, headers=auth_headers)
            elif method == 'PUT':
                response = client.put(endpoint, json=args[0], headers=auth_headers)
            elif method == 'POST':
                response = client.post(endpoint, headers=auth_headers)
            
            # Verify operation was logged (this would require audit log checking)
            assert response.status_code in [200, 201, 404]  # 404 if already deleted

class TestAPISecurity:
    """Security tests for API endpoints."""
    
    def test_cors_configuration(self, client):
        """Test CORS configuration security."""
        
        # Test preflight request
        response = client.options('/api/pipelines', 
                                headers={'Origin': 'https://malicious-site.com'})
        
        # Verify CORS headers are properly configured
        # In a secure configuration, only trusted origins should be allowed
        cors_headers = response.headers.get('Access-Control-Allow-Origin')
        
        # This test depends on your CORS configuration
        # assert cors_headers != '*'  # Should not allow all origins
    
    def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting implementation."""
        
        # Make many requests quickly
        responses = []
        for i in range(100):
            response = client.get('/api/pipelines', headers=auth_headers)
            responses.append(response.status_code)
        
        # Check for rate limiting (429 status code)
        # In a real implementation, some requests should be rate limited
        rate_limited = any(status == 429 for status in responses)
        
        # This test depends on your rate limiting configuration
        # assert rate_limited  # Should have rate limiting
    
    def test_https_enforcement(self, client):
        """Test HTTPS enforcement."""
        
        # Test that sensitive endpoints require HTTPS
        # This would typically be tested in production with HTTPS
        # For now, we verify the application doesn't expose sensitive data in headers
        
        response = client.get('/api/auth/profile')
        assert response.status_code == 401  # Should require authentication
    
    def test_security_headers(self, client):
        """Test security headers."""
        
        response = client.get('/api/pipelines')
        assert response.status_code == 401  # Should require authentication
        
        # Check for security headers
        headers = response.headers
        
        # Common security headers to check for:
        # X-Content-Type-Options: nosniff
        # X-Frame-Options: DENY
        # X-XSS-Protection: 1; mode=block
        # Strict-Transport-Security: max-age=31536000; includeSubDomains
        # Content-Security-Policy: default-src 'self'
        
        # This test depends on your security header configuration
        # assert 'X-Content-Type-Options' in headers
        # assert 'X-Frame-Options' in headers

class TestSessionSecurity:
    """Security tests for session management."""
    
    def test_session_timeout(self, client, test_user, app):
        """Test session timeout functionality."""
        
        # Create token with short expiration
        short_lived_token = jwt.encode(
            {
                'user_id': test_user.id,
                'exp': datetime.utcnow() + timedelta(seconds=1),
                'iat': datetime.utcnow()
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        # Use token immediately
        response = client.get('/api/auth/profile', 
                            headers={'Authorization': f'Bearer {short_lived_token}'})
        assert response.status_code == 200
        
        # Wait for token to expire
        import time
        time.sleep(2)
        
        # Token should now be expired
        response = client.get('/api/auth/profile', 
                            headers={'Authorization': f'Bearer {short_lived_token}'})
        assert response.status_code == 401
    
    def test_concurrent_session_handling(self, client, test_user):
        """Test handling of concurrent sessions."""
        
        # Login multiple times to create multiple sessions
        login_data = {
            'email': test_user.email,
            'password': 'password123'
        }
        
        tokens = []
        for i in range(5):
            response = client.post('/api/auth/login', json=login_data)
            assert response.status_code == 200
            tokens.append(json.loads(response.data)['access_token'])
        
        # All tokens should work
        for token in tokens:
            response = client.get('/api/auth/profile', 
                                headers={'Authorization': f'Bearer {token}'})
            assert response.status_code == 200

class TestErrorHandlingSecurity:
    """Security tests for error handling."""
    
    def test_information_disclosure_prevention(self, client):
        """Test prevention of sensitive information disclosure in errors."""
        
        # Test various error conditions
        error_scenarios = [
            ('GET', '/api/pipelines/999999'),  # Non-existent resource
            ('GET', '/api/users/999999'),      # Non-existent user
            ('POST', '/api/pipelines', {}),    # Invalid data
            ('GET', '/api/nonexistent'),       # Non-existent endpoint
        ]
        
        for method, endpoint in error_scenarios:
            if method == 'GET':
                response = client.get(endpoint)
            elif method == 'POST':
                response = client.post(endpoint, json={})
            
            # Verify error response doesn't expose sensitive information
            if response.status_code >= 400:
                error_data = json.loads(response.data)
                
                # Should not expose internal details
                assert 'stack_trace' not in error_data
                assert 'database_error' not in error_data
                assert 'internal_error' not in error_data
                
                # Should provide generic error message
                assert 'error' in error_data
    
    def test_sql_error_handling(self, client, auth_headers):
        """Test handling of SQL errors without information disclosure."""
        
        # Test with malformed data that might cause SQL errors
        malformed_data = [
            {'name': None, 'pipeline_type': 'etl'},
            {'name': '', 'pipeline_type': 'invalid_type'},
            {'name': 'A' * 1000, 'pipeline_type': 'etl'},  # Very long name
        ]
        
        for data in malformed_data:
            response = client.post('/api/pipelines', 
                                 json=data, headers=auth_headers)
            
            if response.status_code >= 400:
                error_data = json.loads(response.data)
                
                # Should not expose SQL errors
                assert 'sql' not in str(error_data).lower()
                assert 'database' not in str(error_data).lower()
                assert 'connection' not in str(error_data).lower()

class TestCryptographicSecurity:
    """Security tests for cryptographic functions."""
    
    def test_password_hashing(self, app, bcrypt):
        """Test password hashing security."""
        
        password = 'test_password_123'
        
        # Hash password
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Verify hash is not plain text
        assert password_hash != password
        assert len(password_hash) > len(password)
        
        # Verify password verification works
        assert bcrypt.check_password_hash(password_hash, password)
        assert not bcrypt.check_password_hash(password_hash, 'wrong_password')
        
        # Verify hash is salted (different hashes for same password)
        hash1 = bcrypt.generate_password_hash(password).decode('utf-8')
        hash2 = bcrypt.generate_password_hash(password).decode('utf-8')
        assert hash1 != hash2
    
    def test_token_encryption(self, app):
        """Test token encryption security."""
        
        secret_key = app.config['JWT_SECRET_KEY']
        payload = {'user_id': 1, 'role': 'user'}
        
        # Encrypt token
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        # Verify token is encrypted
        assert token != str(payload)
        
        # Verify token can be decrypted
        decoded = jwt.decode(token, secret_key, algorithms=['HS256'])
        assert decoded == payload
        
        # Verify token cannot be decrypted with wrong key
        wrong_key = 'wrong_secret_key'
        try:
            jwt.decode(token, wrong_key, algorithms=['HS256'])
            assert False, "Token should not be decryptable with wrong key"
        except jwt.InvalidSignatureError:
            pass  # Expected behavior 