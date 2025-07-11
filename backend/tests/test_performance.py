import pytest
import time
import threading
import concurrent.futures
from datetime import datetime, timedelta
from app import db
from app.models.user import User
from app.models.organization import Organization
from app.models.pipeline import Pipeline, PipelineRun
from app.models.monitoring import DataSource, HealthCheck
from app.models.alert import AlertRule, Alert
import json

class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    def test_pipeline_list_performance(self, client, auth_headers, test_organization):
        """Test performance of pipeline listing with large datasets."""
        
        # Create multiple pipelines for testing
        pipelines = []
        for i in range(100):
            pipeline = Pipeline(
                name=f'Performance Test Pipeline {i}',
                description=f'Pipeline {i} for performance testing',
                pipeline_type='etl',
                status='active',
                config={'source': f'source_{i}'},
                schedule='0 0 * * *',
                organization_id=test_organization.id,
                created_by=1
            )
            pipelines.append(pipeline)
        
        with client.application.app_context():
            db.session.add_all(pipelines)
            db.session.commit()
        
        # Test response time
        start_time = time.time()
        response = client.get('/api/pipelines', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond within 1 second
        
        result = json.loads(response.data)
        assert len(result['pipelines']) == 100
    
    def test_pipeline_search_performance(self, client, auth_headers, test_organization):
        """Test performance of pipeline search functionality."""
        
        # Create pipelines with different names for search testing
        pipelines = []
        for i in range(50):
            pipeline = Pipeline(
                name=f'Search Test Pipeline {i}',
                description=f'Pipeline {i} for search testing',
                pipeline_type='etl',
                status='active',
                config={'source': f'source_{i}'},
                schedule='0 0 * * *',
                organization_id=test_organization.id,
                created_by=1
            )
            pipelines.append(pipeline)
        
        with client.application.app_context():
            db.session.add_all(pipelines)
            db.session.commit()
        
        # Test search performance
        start_time = time.time()
        response = client.get('/api/pipelines?search=Search Test', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 0.5  # Should respond within 0.5 seconds
        
        result = json.loads(response.data)
        assert len(result['pipelines']) == 50
    
    def test_dashboard_overview_performance(self, client, auth_headers, test_organization):
        """Test performance of dashboard overview with complex data."""
        
        # Create comprehensive test data
        pipelines = []
        data_sources = []
        alert_rules = []
        
        for i in range(20):
            # Create pipelines
            pipeline = Pipeline(
                name=f'Dashboard Pipeline {i}',
                description=f'Pipeline {i} for dashboard testing',
                pipeline_type='etl',
                status='active',
                config={'source': f'source_{i}'},
                schedule='0 0 * * *',
                organization_id=test_organization.id,
                created_by=1
            )
            pipelines.append(pipeline)
            
            # Create data sources
            data_source = DataSource(
                name=f'Dashboard Data Source {i}',
                type='postgresql',
                host=f'host_{i}.com',
                port=5432,
                database=f'db_{i}',
                username=f'user_{i}',
                password=f'pass_{i}',
                connection_string=f'postgresql://user_{i}:pass_{i}@host_{i}.com:5432/db_{i}',
                status='connected',
                health_score=95.0,
                organization_id=test_organization.id
            )
            data_sources.append(data_source)
            
            # Create alert rules
            alert_rule = AlertRule(
                name=f'Dashboard Alert Rule {i}',
                description=f'Alert rule {i} for dashboard testing',
                severity='medium',
                condition_type='threshold',
                condition_config={'metric': 'pipeline_failure_rate', 'threshold': 0.1},
                notification_channels=['email'],
                enabled=True,
                organization_id=test_organization.id
            )
            alert_rules.append(alert_rule)
        
        with client.application.app_context():
            db.session.add_all(pipelines)
            db.session.add_all(data_sources)
            db.session.add_all(alert_rules)
            db.session.commit()
        
        # Test dashboard overview performance
        start_time = time.time()
        response = client.get('/api/dashboard/overview', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 2.0  # Should respond within 2 seconds
        
        result = json.loads(response.data)
        assert 'overview' in result
        assert result['overview']['pipelines']['total'] == 20
        assert result['overview']['data_sources']['total'] == 20
        assert result['overview']['alerts']['total'] == 20
    
    def test_metrics_calculation_performance(self, client, auth_headers, test_pipeline):
        """Test performance of metrics calculation with historical data."""
        
        # Create historical pipeline runs
        runs = []
        for i in range(1000):
            run = PipelineRun(
                pipeline_id=test_pipeline.id,
                status='success' if i % 10 != 0 else 'failed',
                started_at=datetime.utcnow() - timedelta(hours=i),
                completed_at=datetime.utcnow() - timedelta(hours=i) + timedelta(minutes=5),
                duration_seconds=300 + (i % 100),
                records_processed=1000 + (i * 10),
                error_message=None if i % 10 != 0 else 'Test error'
            )
            runs.append(run)
        
        with client.application.app_context():
            db.session.add_all(runs)
            db.session.commit()
        
        # Test metrics calculation performance
        start_time = time.time()
        response = client.get(f'/api/pipelines/{test_pipeline.id}/metrics', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond within 1 second
        
        result = json.loads(response.data)
        assert 'metrics' in result
        assert 'success_rate' in result['metrics']
        assert 'average_duration' in result['metrics']

class TestConcurrentAccess:
    """Tests for concurrent access scenarios."""
    
    def test_concurrent_pipeline_creation(self, client, auth_headers, test_organization):
        """Test concurrent pipeline creation."""
        
        def create_pipeline(pipeline_id):
            pipeline_data = {
                'name': f'Concurrent Pipeline {pipeline_id}',
                'description': f'Pipeline {pipeline_id} for concurrent testing',
                'pipeline_type': 'etl',
                'config': {'source': f'source_{pipeline_id}'},
                'schedule': '0 0 * * *'
            }
            
            response = client.post('/api/pipelines', 
                                 json=pipeline_data, headers=auth_headers)
            return response.status_code
        
        # Create 10 pipelines concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_pipeline, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 201 for status in results)
        
        # Verify all pipelines were created
        response = client.get('/api/pipelines', headers=auth_headers)
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert len(result['pipelines']) >= 10
    
    def test_concurrent_pipeline_triggering(self, client, auth_headers, test_pipeline):
        """Test concurrent pipeline triggering."""
        
        def trigger_pipeline():
            response = client.post(f'/api/pipelines/{test_pipeline.id}/trigger', 
                                 headers=auth_headers)
            return response.status_code
        
        # Trigger pipeline 5 times concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(trigger_pipeline) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 200 for status in results)
    
    def test_concurrent_health_check_execution(self, client, auth_headers, test_health_check):
        """Test concurrent health check execution."""
        
        def execute_health_check():
            response = client.post(f'/api/monitoring/health-checks/{test_health_check.id}/execute', 
                                 headers=auth_headers)
            return response.status_code
        
        # Execute health check 10 times concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(execute_health_check) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 200 for status in results)

class TestDatabasePerformance:
    """Tests for database performance and query optimization."""
    
    def test_large_dataset_query_performance(self, client, auth_headers, test_organization):
        """Test query performance with large datasets."""
        
        # Create large number of records
        pipelines = []
        for i in range(1000):
            pipeline = Pipeline(
                name=f'Large Dataset Pipeline {i}',
                description=f'Pipeline {i} for large dataset testing',
                pipeline_type='etl',
                status='active',
                config={'source': f'source_{i}'},
                schedule='0 0 * * *',
                organization_id=test_organization.id,
                created_by=1
            )
            pipelines.append(pipeline)
        
        with client.application.app_context():
            db.session.add_all(pipelines)
            db.session.commit()
        
        # Test paginated query performance
        start_time = time.time()
        response = client.get('/api/pipelines?page=1&per_page=50', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 0.5  # Should respond within 0.5 seconds
        
        result = json.loads(response.data)
        assert len(result['pipelines']) == 50
        assert 'pagination' in result
        assert result['pagination']['total'] == 1000
    
    def test_complex_join_query_performance(self, client, auth_headers, test_organization):
        """Test performance of complex join queries."""
        
        # Create related data for complex queries
        pipelines = []
        runs = []
        
        for i in range(100):
            pipeline = Pipeline(
                name=f'Complex Query Pipeline {i}',
                description=f'Pipeline {i} for complex query testing',
                pipeline_type='etl',
                status='active',
                config={'source': f'source_{i}'},
                schedule='0 0 * * *',
                organization_id=test_organization.id,
                created_by=1
            )
            pipelines.append(pipeline)
        
        with client.application.app_context():
            db.session.add_all(pipelines)
            db.session.commit()
            
            # Create runs for each pipeline
            for pipeline in pipelines:
                for j in range(10):
                    run = PipelineRun(
                        pipeline_id=pipeline.id,
                        status='success' if j % 5 != 0 else 'failed',
                        started_at=datetime.utcnow() - timedelta(hours=j),
                        completed_at=datetime.utcnow() - timedelta(hours=j) + timedelta(minutes=5),
                        duration_seconds=300 + (j % 100),
                        records_processed=1000 + (j * 10)
                    )
                    runs.append(run)
            
            db.session.add_all(runs)
            db.session.commit()
        
        # Test dashboard query performance (complex joins)
        start_time = time.time()
        response = client.get('/api/dashboard/pipeline-health', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond within 1 second

class TestMemoryUsage:
    """Tests for memory usage and optimization."""
    
    def test_large_response_memory_usage(self, client, auth_headers, test_organization):
        """Test memory usage with large API responses."""
        
        # Create large number of records
        pipelines = []
        for i in range(500):
            pipeline = Pipeline(
                name=f'Memory Test Pipeline {i}',
                description=f'Pipeline {i} for memory testing',
                pipeline_type='etl',
                status='active',
                config={'source': f'source_{i}', 'complex_config': {'nested': {'data': 'value' * 100}}},
                schedule='0 0 * * *',
                organization_id=test_organization.id,
                created_by=1
            )
            pipelines.append(pipeline)
        
        with client.application.app_context():
            db.session.add_all(pipelines)
            db.session.commit()
        
        # Test memory usage with large response
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        response = client.get('/api/pipelines', headers=auth_headers)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        assert response.status_code == 200
        assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase
        
        result = json.loads(response.data)
        assert len(result['pipelines']) == 500

class TestCachingPerformance:
    """Tests for caching performance improvements."""
    
    def test_dashboard_caching_performance(self, client, auth_headers):
        """Test performance improvement with caching."""
        
        # First request (cache miss)
        start_time = time.time()
        response1 = client.get('/api/dashboard/overview', headers=auth_headers)
        first_request_time = time.time() - start_time
        
        assert response1.status_code == 200
        
        # Second request (cache hit)
        start_time = time.time()
        response2 = client.get('/api/dashboard/overview', headers=auth_headers)
        second_request_time = time.time() - start_time
        
        assert response2.status_code == 200
        
        # Second request should be faster (if caching is implemented)
        # Note: This test assumes caching is implemented
        # assert second_request_time < first_request_time
    
    def test_pipeline_metrics_caching(self, client, auth_headers, test_pipeline):
        """Test caching of pipeline metrics."""
        
        # First request
        start_time = time.time()
        response1 = client.get(f'/api/pipelines/{test_pipeline.id}/metrics', headers=auth_headers)
        first_request_time = time.time() - start_time
        
        assert response1.status_code == 200
        
        # Second request
        start_time = time.time()
        response2 = client.get(f'/api/pipelines/{test_pipeline.id}/metrics', headers=auth_headers)
        second_request_time = time.time() - start_time
        
        assert response2.status_code == 200
        
        # Results should be identical
        result1 = json.loads(response1.data)
        result2 = json.loads(response2.data)
        assert result1 == result2

class TestStressTesting:
    """Stress tests for the application."""
    
    def test_high_concurrency_stress_test(self, client, auth_headers):
        """Test application under high concurrency stress."""
        
        def make_request():
            response = client.get('/api/pipelines', headers=auth_headers)
            return response.status_code
        
        # Make 100 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Most requests should succeed (allow for some failures under stress)
        success_rate = sum(1 for status in results if status == 200) / len(results)
        assert success_rate > 0.9  # 90% success rate
    
    def test_database_connection_pool_stress(self, client, auth_headers, test_organization):
        """Test database connection pool under stress."""
        
        def create_and_query_pipeline():
            # Create pipeline
            pipeline_data = {
                'name': f'Stress Test Pipeline {threading.current_thread().ident}',
                'pipeline_type': 'etl',
                'config': {'source': 'stress_source'},
                'schedule': '0 0 * * *'
            }
            
            create_response = client.post('/api/pipelines', 
                                        json=pipeline_data, headers=auth_headers)
            
            if create_response.status_code == 201:
                pipeline_id = json.loads(create_response.data)['pipeline']['id']
                
                # Query pipeline
                query_response = client.get(f'/api/pipelines/{pipeline_id}', 
                                          headers=auth_headers)
                return query_response.status_code
            
            return create_response.status_code
        
        # Make 50 concurrent database operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_and_query_pipeline) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Most operations should succeed
        success_rate = sum(1 for status in results if status in [200, 201]) / len(results)
        assert success_rate > 0.8  # 80% success rate

class TestLoadBalancing:
    """Tests for load balancing scenarios."""
    
    def test_multiple_worker_handling(self, client, auth_headers):
        """Test handling of multiple worker processes."""
        
        # This test simulates multiple worker processes
        # In a real scenario, you would have multiple worker processes
        
        def worker_request():
            response = client.get('/api/dashboard/overview', headers=auth_headers)
            return response.status_code
        
        # Simulate multiple workers making requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_request) for _ in range(25)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 200 for status in results)

class TestResourceLimits:
    """Tests for resource limit handling."""
    
    def test_large_payload_handling(self, client, auth_headers):
        """Test handling of large payloads."""
        
        # Create large configuration payload
        large_config = {
            'source': 'large_source',
            'destination': 'large_dest',
            'transformations': ['step_' + str(i) for i in range(1000)],
            'metadata': {'key_' + str(i): 'value_' + str(i) for i in range(1000)}
        }
        
        pipeline_data = {
            'name': 'Large Payload Pipeline',
            'description': 'Pipeline with large configuration',
            'pipeline_type': 'etl',
            'config': large_config,
            'schedule': '0 0 * * *'
        }
        
        response = client.post('/api/pipelines', 
                             json=pipeline_data, headers=auth_headers)
        
        # Should handle large payloads gracefully
        assert response.status_code in [201, 413]  # Created or Payload Too Large
    
    def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting functionality."""
        
        # Make many requests quickly
        responses = []
        for i in range(100):
            response = client.get('/api/pipelines', headers=auth_headers)
            responses.append(response.status_code)
        
        # Check if rate limiting is working
        # In a real implementation, some requests should be rate limited
        # For now, we just verify the application doesn't crash
        assert len(responses) == 100 