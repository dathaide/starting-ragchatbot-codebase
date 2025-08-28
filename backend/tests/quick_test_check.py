#!/usr/bin/env python3
"""
Quick test to verify our enhanced testing framework is properly set up
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def main():
    print("🔍 Quick Test Framework Verification")
    print("=" * 40)
    
    # Test 1: Basic imports
    try:
        from models import Course, Lesson, CourseChunk
        print("✓ Core models import successfully")
    except ImportError as e:
        print(f"✗ Models import failed: {e}")
        return False
    
    # Test 2: FastAPI imports
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from pydantic import BaseModel
        print("✓ FastAPI testing components available")
    except ImportError as e:
        print(f"✗ FastAPI imports failed: {e}")
        return False
    
    # Test 3: Basic FastAPI app creation
    try:
        app = FastAPI()
        client = TestClient(app)
        print("✓ FastAPI app and test client creation works")
    except Exception as e:
        print(f"✗ FastAPI app creation failed: {e}")
        return False
    
    # Test 4: Check our test files exist
    test_files = [
        "conftest.py",
        "test_api_endpoints.py",
        "verify_test_setup.py"
    ]
    
    test_dir = os.path.dirname(__file__)
    missing_files = []
    
    for filename in test_files:
        filepath = os.path.join(test_dir, filename)
        if os.path.exists(filepath):
            print(f"✓ {filename} exists")
        else:
            print(f"✗ {filename} missing")
            missing_files.append(filename)
    
    if missing_files:
        print(f"Missing files: {missing_files}")
        return False
    
    # Test 5: Check pyproject.toml has pytest config
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        pyproject_path = os.path.join(project_root, "pyproject.toml")
        
        with open(pyproject_path, 'r') as f:
            content = f.read()
            if "[tool.pytest.ini_options]" in content:
                print("✓ pytest configuration found in pyproject.toml")
            else:
                print("✗ pytest configuration missing from pyproject.toml")
                return False
    except Exception as e:
        print(f"✗ Could not verify pyproject.toml: {e}")
        return False
    
    print("\n🎉 Test framework setup verification completed successfully!")
    print("\n📋 What was enhanced:")
    print("  • Enhanced conftest.py with FastAPI testing fixtures")
    print("  • Added comprehensive API endpoint tests")
    print("  • Added pytest configuration in pyproject.toml")
    print("  • Added test categorization with markers")
    print("  • Created isolated test app to avoid static file issues")
    
    print("\n🚀 To run the tests:")
    print("  1. Install pytest: python3 -m pip install pytest pytest-asyncio")
    print("  2. Run all tests: python3 -m pytest backend/tests/ -v")
    print("  3. Run only API tests: python3 -m pytest backend/tests/ -m api -v")
    print("  4. Run only mock tests: python3 -m pytest backend/tests/ -m mock -v")
    
    return True

if __name__ == "__main__":
    success = main()
    print(f"\nResult: {'✓ PASSED' if success else '✗ FAILED'}")
    sys.exit(0 if success else 1)