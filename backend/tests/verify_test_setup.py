#!/usr/bin/env python3
"""
Simple test verification script that doesn't require pytest
This verifies our test setup works before running the full test suite
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_basic_imports():
    """Test that all required modules can be imported"""
    print("Testing basic imports...")
    
    try:
        from models import Course, Lesson, CourseChunk
        print("✓ Models imported successfully")
    except ImportError as e:
        print(f"✗ Models import failed: {e}")
        return False
    
    try:
        from config import Config
        print("✓ Config imported successfully")
    except ImportError as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    return True

def test_fastapi_imports():
    """Test FastAPI related imports"""
    print("\nTesting FastAPI imports...")
    
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient
        from pydantic import BaseModel
        print("✓ FastAPI components imported successfully")
        return True
    except ImportError as e:
        print(f"✗ FastAPI import failed: {e}")
        return False

def test_mock_functionality():
    """Test that we can create mocks for testing"""
    print("\nTesting mock functionality...")
    
    try:
        from unittest.mock import Mock, MagicMock
        
        # Test basic mock creation
        mock_obj = Mock()
        mock_obj.test_method.return_value = "test_result"
        
        result = mock_obj.test_method()
        assert result == "test_result", f"Expected 'test_result', got {result}"
        
        print("✓ Mock functionality working")
        return True
    except Exception as e:
        print(f"✗ Mock functionality failed: {e}")
        return False

def test_conftest_fixtures():
    """Test that our conftest fixtures can be created"""
    print("\nTesting conftest fixture creation...")
    
    try:
        # Import our test configuration
        from config import Config
        from models import Course, Lesson, CourseChunk
        from unittest.mock import Mock
        
        # Create test config (similar to conftest fixture)
        test_config = Config()
        test_config.ANTHROPIC_API_KEY = "test-api-key"
        test_config.CHUNK_SIZE = 400
        
        # Create sample course (similar to conftest fixture)
        lesson1 = Lesson(
            lesson_number=1,
            title="Test Lesson",
            lesson_link="https://example.com/lesson1"
        )
        
        course = Course(
            title="Test Course",
            course_link="https://example.com/course",
            instructor="Test Instructor",
            lessons=[lesson1]
        )
        
        # Create sample chunk
        chunk = CourseChunk(
            content="Test content",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0
        )
        
        print("✓ Test fixtures can be created successfully")
        print(f"  - Config: API key present = {bool(test_config.ANTHROPIC_API_KEY)}")
        print(f"  - Course: '{course.title}' with {len(course.lessons)} lessons")
        print(f"  - Chunk: {len(chunk.content)} characters")
        
        return True
    except Exception as e:
        print(f"✗ Test fixture creation failed: {e}")
        return False

def test_fastapi_app_creation():
    """Test that we can create a basic FastAPI app for testing"""
    print("\nTesting FastAPI app creation...")
    
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from pydantic import BaseModel
        
        # Create simple test app
        app = FastAPI(title="Test App")
        
        class TestResponse(BaseModel):
            message: str
        
        @app.get("/test", response_model=TestResponse)
        async def test_endpoint():
            return TestResponse(message="Test successful")
        
        # Create test client
        client = TestClient(app)
        
        # Test the endpoint
        response = client.get("/test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["message"] == "Test successful", f"Unexpected response: {data}"
        
        print("✓ FastAPI app and test client working")
        print(f"  - Response status: {response.status_code}")
        print(f"  - Response data: {data}")
        
        return True
    except Exception as e:
        print(f"✗ FastAPI app creation failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("=" * 50)
    print("VERIFYING TEST SETUP")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_fastapi_imports,
        test_mock_functionality,
        test_conftest_fixtures,
        test_fastapi_app_creation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
        
        print()  # Add spacing between tests
    
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All verification tests passed!")
        print("Your test setup is ready for pytest execution.")
        print("\nTo run the full test suite:")
        print("1. Install pytest: python3 -m pip install pytest pytest-asyncio")
        print("2. Run tests: python3 -m pytest backend/tests/ -v")
        print("3. Run only API tests: python3 -m pytest backend/tests/ -m api -v")
    else:
        print(f"\n❌ {total - passed} test(s) failed.")
        print("Please address the issues above before running the full test suite.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)