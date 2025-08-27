"""Simple test for search tools without ChromaDB dependencies"""
import sys
import os
from unittest.mock import Mock, patch

# Add backend directory to path for imports
sys.path.insert(0, '/Users/deirdreathaide/Documents/Claude Code/starting-ragchatbot-codebase/backend')

def test_mock_search_tool():
    """Test CourseSearchTool with mocked vector store"""
    try:
        from search_tools import CourseSearchTool, ToolManager
        from vector_store import SearchResults
        
        # Create mock vector store
        mock_store = Mock()
        
        # Mock successful search
        mock_search_result = SearchResults(
            documents=["This is test content about machine learning concepts."],
            metadata=[{
                'course_title': 'AI Fundamentals',
                'lesson_number': 1,
                'chunk_index': 0
            }],
            distances=[0.2]
        )
        mock_store.search.return_value = mock_search_result
        
        # Mock course catalog for lesson links
        mock_catalog = Mock()
        mock_catalog.query.return_value = {
            'documents': [['AI Fundamentals']],
            'metadatas': [[{
                'title': 'AI Fundamentals',
                'instructor': 'Dr. Smith',
                'course_link': 'https://example.com/course',
                'lessons_json': '[{"lesson_number": 1, "lesson_title": "Introduction", "lesson_link": "https://example.com/lesson1"}]',
                'lesson_count': 1
            }]]
        }
        mock_store.course_catalog = mock_catalog
        
        # Test the tool
        tool = CourseSearchTool(mock_store)
        result = tool.execute("machine learning")
        
        print(f"✓ Search tool executed successfully")
        print(f"✓ Result: {result[:100]}...")
        
        # Verify result contains expected content
        assert "AI Fundamentals" in result
        assert "Lesson 1" in result
        assert "machine learning" in result
        
        # Verify sources were created
        assert len(tool.last_sources) == 1
        source = tool.last_sources[0]
        assert source["text"] == "AI Fundamentals - Lesson 1"
        assert source["url"] == "https://example.com/lesson1"
        
        print("✓ Search result formatting verified")
        print("✓ Sources tracking working")
        
        return True
        
    except Exception as e:
        print(f"✗ Mock search tool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_manager():
    """Test ToolManager functionality"""
    try:
        from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
        from vector_store import SearchResults
        
        # Create mock vector store
        mock_store = Mock()
        mock_search_result = SearchResults(
            documents=["Test content"],
            metadata=[{'course_title': 'Test Course', 'lesson_number': 1, 'chunk_index': 0}],
            distances=[0.1]
        )
        mock_store.search.return_value = mock_search_result
        
        # Create tools and manager
        search_tool = CourseSearchTool(mock_store)
        tool_manager = ToolManager()
        tool_manager.register_tool(search_tool)
        
        # Test tool definitions
        definitions = tool_manager.get_tool_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
        
        print("✓ Tool registration working")
        
        # Test tool execution
        result = tool_manager.execute_tool("search_course_content", query="test")
        assert isinstance(result, str)
        
        print("✓ Tool execution working")
        
        # Test source management
        sources = tool_manager.get_last_sources()
        assert len(sources) > 0
        
        tool_manager.reset_sources()
        sources_after_reset = tool_manager.get_last_sources()
        assert len(sources_after_reset) == 0
        
        print("✓ Source management working")
        
        return True
        
    except Exception as e:
        print(f"✗ Tool manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_with_tools_integration():
    """Test AIGenerator with tools integration"""
    try:
        from ai_generator import AIGenerator
        from search_tools import CourseSearchTool, ToolManager
        from vector_store import SearchResults
        from config import Config
        
        config = Config()
        
        # Create mock vector store with realistic response
        mock_store = Mock()
        mock_search_result = SearchResults(
            documents=["Machine learning is a subset of AI that involves training algorithms on data to make predictions."],
            metadata=[{'course_title': 'AI Fundamentals', 'lesson_number': 2, 'chunk_index': 5}],
            distances=[0.15]
        )
        mock_store.search.return_value = mock_search_result
        
        # Setup course catalog mock
        mock_catalog = Mock()
        mock_catalog.query.return_value = {
            'documents': [['AI Fundamentals']],
            'metadatas': [[{
                'title': 'AI Fundamentals',
                'instructor': 'Dr. Smith',
                'lessons_json': '[{"lesson_number": 2, "lesson_title": "ML Basics", "lesson_link": "https://example.com/lesson2"}]'
            }]]
        }
        mock_store.course_catalog = mock_catalog
        
        # Create tools and AI generator
        search_tool = CourseSearchTool(mock_store)
        tool_manager = ToolManager()
        tool_manager.register_tool(search_tool)
        
        ai_gen = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
        
        # Test with tools - make a real API call that should use tools
        response = ai_gen.generate_response(
            "What does the course say about machine learning?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        print(f"✓ AI with tools integration successful")
        print(f"✓ Response: {response}")
        
        # Check if the response suggests the AI used the search (may or may not based on Claude's decision)
        if "machine learning" in response.lower():
            print("✓ Response contains relevant content")
        else:
            print(f"⚠ Response may not have used search: {response}")
        
        return True
        
    except Exception as e:
        print(f"✗ AI with tools integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Testing Search Tools Functionality ===")
    
    tests = [
        test_mock_search_tool,
        test_tool_manager, 
        test_ai_with_tools_integration
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
    
    if passed == total:
        print("🎉 All search tools tests passed!")
    else:
        print("\n=== Issues Found ===")
        for i, (test, result) in enumerate(zip(tests, results)):
            if not result:
                print(f"- {test.__name__} failed")