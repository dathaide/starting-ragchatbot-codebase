"""Basic tests to identify core issues without external dependencies"""
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, '/Users/deirdreathaide/Documents/Claude Code/starting-ragchatbot-codebase/backend')

def test_imports():
    """Test that we can import basic modules"""
    try:
        from models import Course, Lesson, CourseChunk
        print("✓ Models import successful")
        
        from config import Config
        print("✓ Config import successful") 
        
        # Test config loading
        config = Config()
        print(f"✓ Config loaded - API key present: {bool(config.ANTHROPIC_API_KEY)}")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_anthropic_api_key():
    """Test that API key is configured"""
    try:
        from config import Config
        config = Config()
        
        if not config.ANTHROPIC_API_KEY:
            print("✗ ANTHROPIC_API_KEY not set in config")
            return False
        elif config.ANTHROPIC_API_KEY == "":
            print("✗ ANTHROPIC_API_KEY is empty")
            return False
        else:
            print(f"✓ ANTHROPIC_API_KEY configured (starts with: {config.ANTHROPIC_API_KEY[:10]}...)")
            return True
    except Exception as e:
        print(f"✗ API key test failed: {e}")
        return False

def test_anthropic_import():
    """Test Anthropic client import"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key="test-key")
        print("✓ Anthropic client import successful")
        return True
    except Exception as e:
        print(f"✗ Anthropic import failed: {e}")
        return False

def test_document_processor():
    """Test document processor basic functionality"""
    try:
        from document_processor import DocumentProcessor
        
        processor = DocumentProcessor(chunk_size=400, chunk_overlap=50)
        
        # Test text chunking
        test_text = "This is a test sentence. This is another sentence. And a third one for good measure."
        chunks = processor.chunk_text(test_text)
        
        if chunks:
            print(f"✓ Document processor working - created {len(chunks)} chunks")
            return True
        else:
            print("✗ Document processor created no chunks")
            return False
    except Exception as e:
        print(f"✗ Document processor test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Running Basic Diagnostic Tests ===")
    
    tests = [
        test_imports,
        test_anthropic_api_key,
        test_anthropic_import,
        test_document_processor
    ]
    
    results = []
    for test in tests:
        print(f"\n--- {test.__name__} ---")
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print(f"\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed < total:
        print("\n=== Issues Found ===")
        for i, (test, result) in enumerate(zip(tests, results)):
            if not result:
                print(f"- {test.__name__} failed")