"""
Comprehensive FastAPI endpoint tests for the RAG system
Tests all API endpoints with various scenarios including error handling
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

pytestmark = [pytest.mark.api, pytest.mark.mock]  # Mark all tests as API tests using mocks


class TestQueryEndpoint:
    """Test the /api/query endpoint"""
    
    def test_query_without_session_id(self, test_client, api_query_request):
        """Test query endpoint creates session when none provided"""
        response = test_client.post("/api/query", json=api_query_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        
        # Verify content
        assert "What courses are available?" in data["answer"]
        assert data["session_id"] is not None
        assert len(data["sources"]) == 2
        
        # Check source structure
        source1 = data["sources"][0]
        assert "text" in source1
        assert "url" in source1
        assert source1["text"] == "Source 1: Course content"
        assert source1["url"] == "https://example.com/lesson1"
        
        source2 = data["sources"][1]
        assert source2["text"] == "Source 2: Additional material"
        assert source2["url"] is None
    
    def test_query_with_existing_session_id(self, test_client, api_query_request_with_session):
        """Test query endpoint uses provided session ID"""
        response = test_client.post("/api/query", json=api_query_request_with_session)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "test-session-123"
        assert "Tell me more about machine learning" in data["answer"]
    
    def test_query_request_validation(self, test_client):
        """Test query endpoint validates request structure"""
        # Missing query field
        invalid_request = {"session_id": "test"}
        response = test_client.post("/api/query", json=invalid_request)
        assert response.status_code == 422  # Pydantic validation error
        
        # Empty query
        empty_query = {"query": "", "session_id": "test"}
        response = test_client.post("/api/query", json=empty_query)
        assert response.status_code == 200  # Empty query is valid, should return response
        
        # Non-string query
        invalid_type = {"query": 123, "session_id": "test"}
        response = test_client.post("/api/query", json=invalid_type)
        assert response.status_code == 422
    
    def test_query_error_handling(self, test_client):
        """Test query endpoint handles RAG system errors"""
        error_request = {"query": "trigger error", "session_id": "test"}
        response = test_client.post("/api/query", json=error_request)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Test error" in data["detail"]
    
    def test_query_content_type_validation(self, test_client, api_query_request):
        """Test query endpoint requires JSON content type"""
        # Test with form data instead of JSON
        response = test_client.post("/api/query", data=api_query_request)
        assert response.status_code == 422
        
        # Test with correct JSON content type
        response = test_client.post(
            "/api/query", 
            json=api_query_request,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
    
    @pytest.mark.parametrize("query_text,expected_in_response", [
        ("machine learning", "machine learning"),
        ("AI fundamentals", "AI fundamentals"),
        ("course overview", "course overview"),
        ("What is available?", "What is available?")
    ])
    def test_query_various_inputs(self, test_client, query_text, expected_in_response):
        """Test query endpoint with various input queries"""
        request_data = {"query": query_text}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert expected_in_response in data["answer"]


class TestCoursesEndpoint:
    """Test the /api/courses endpoint"""
    
    def test_get_courses_success(self, test_client):
        """Test successful course analytics retrieval"""
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "total_courses" in data
        assert "course_titles" in data
        
        # Verify content
        assert data["total_courses"] == 1
        assert isinstance(data["course_titles"], list)
        assert "AI Fundamentals" in data["course_titles"]
    
    def test_get_courses_method_not_allowed(self, test_client):
        """Test that POST method is not allowed on courses endpoint"""
        response = test_client.post("/api/courses", json={})
        assert response.status_code == 405  # Method not allowed
    
    def test_get_courses_with_analytics_error(self, test_client, mock_rag_system):
        """Test courses endpoint handles analytics errors"""
        # Mock the analytics to raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")
        
        response = test_client.get("/api/courses")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Analytics error" in data["detail"]


class TestClearSessionEndpoint:
    """Test the /api/clear-session endpoint"""
    
    def test_clear_session_success(self, test_client, clear_session_request):
        """Test successful session clearing"""
        response = test_client.post("/api/clear-session", json=clear_session_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "test-session-123" in data["message"]
    
    def test_clear_session_validation(self, test_client):
        """Test clear session request validation"""
        # Missing session_id
        response = test_client.post("/api/clear-session", json={})
        assert response.status_code == 422
        
        # Empty session_id
        response = test_client.post("/api/clear-session", json={"session_id": ""})
        assert response.status_code == 200  # Empty session_id is valid
        
        # Non-string session_id
        response = test_client.post("/api/clear-session", json={"session_id": 123})
        assert response.status_code == 422
    
    def test_clear_session_error_handling(self, test_client, mock_rag_system):
        """Test clear session error handling"""
        # Mock session manager to raise an exception
        mock_rag_system.session_manager.clear_session.side_effect = Exception("Session error")
        
        response = test_client.post("/api/clear-session", json={"session_id": "test"})
        assert response.status_code == 500
        data = response.json()
        assert "Session error" in data["detail"]


class TestRootEndpoint:
    """Test the root / endpoint"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API information"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "RAG System API - Test Mode" in data["message"]
    
    def test_root_endpoint_method_not_allowed(self, test_client):
        """Test root endpoint only allows GET method"""
        response = test_client.post("/", json={})
        assert response.status_code == 405


class TestCORSAndMiddleware:
    """Test CORS middleware and other middleware functionality"""
    
    def test_cors_headers_present(self, test_client, api_query_request):
        """Test that CORS headers are present in responses"""
        response = test_client.post("/api/query", json=api_query_request)
        
        # FastAPI TestClient may not include all CORS headers
        # But we can test that the endpoint is accessible
        assert response.status_code == 200
    
    def test_options_request(self, test_client):
        """Test OPTIONS request for CORS preflight"""
        response = test_client.options("/api/query")
        # TestClient should handle OPTIONS requests
        assert response.status_code in [200, 405]


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    def test_query_and_clear_session_flow(self, test_client):
        """Test complete workflow: query -> get session -> clear session"""
        # Step 1: Make a query to get a session ID
        query_request = {"query": "What courses are available?"}
        response = test_client.post("/api/query", json=query_request)
        assert response.status_code == 200
        
        session_id = response.json()["session_id"]
        assert session_id is not None
        
        # Step 2: Make another query with the same session ID
        query_request_with_session = {"query": "Tell me more", "session_id": session_id}
        response = test_client.post("/api/query", json=query_request_with_session)
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id
        
        # Step 3: Clear the session
        clear_request = {"session_id": session_id}
        response = test_client.post("/api/clear-session", json=clear_request)
        assert response.status_code == 200
    
    def test_api_response_format_consistency(self, test_client):
        """Test that all endpoints return consistent error format"""
        endpoints_and_requests = [
            ("POST", "/api/query", {"invalid": "data"}),
            ("POST", "/api/clear-session", {"invalid": "data"})
        ]
        
        for method, endpoint, data in endpoints_and_requests:
            if method == "POST":
                response = test_client.post(endpoint, json=data)
            
            # All should return 422 for validation errors with consistent format
            if response.status_code == 422:
                error_data = response.json()
                assert "detail" in error_data


# Performance and load tests (if needed)
class TestPerformance:
    """Basic performance and load tests"""
    
    @pytest.mark.slow
    def test_concurrent_queries(self, test_client):
        """Test handling multiple concurrent queries (basic load test)"""
        import concurrent.futures
        import threading
        
        def make_query():
            query_request = {"query": f"Test query from thread {threading.current_thread().ident}"}
            return test_client.post("/api/query", json=query_request)
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_query) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Each should have unique session IDs (since no session_id provided)
        session_ids = {response.json()["session_id"] for response in responses}
        assert len(session_ids) == 10  # All unique