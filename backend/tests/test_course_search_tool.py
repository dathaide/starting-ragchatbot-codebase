import pytest
from unittest.mock import Mock, patch
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool execute method"""

    def test_get_tool_definition(self, course_search_tool):
        """Test that tool definition is properly formatted"""
        definition = course_search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["query"]

        properties = definition["input_schema"]["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties

    def test_execute_basic_search(self, course_search_tool):
        """Test basic search functionality"""
        result = course_search_tool.execute("introduction")

        # Should return formatted results
        assert isinstance(result, str)
        assert "AI Fundamentals" in result
        assert "Lesson 1" in result
        assert "introduction to artificial intelligence" in result

        # Check that sources were stored
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source["text"] == "AI Fundamentals - Lesson 1"
        assert source["url"] is not None  # Should have lesson link

    def test_execute_with_course_filter(self, course_search_tool):
        """Test search with course name filter"""
        result = course_search_tool.execute(
            "machine learning", course_name="AI Fundamentals"
        )

        assert isinstance(result, str)
        assert "AI Fundamentals" in result
        assert "Lesson 2" in result

        # Verify the search was called with correct parameters
        course_search_tool.store.search.assert_called_with(
            query="machine learning", course_name="AI Fundamentals", lesson_number=None
        )

    def test_execute_with_lesson_filter(self, course_search_tool):
        """Test search with lesson number filter"""
        result = course_search_tool.execute("concepts", lesson_number=1)

        # Verify the search was called with correct parameters
        course_search_tool.store.search.assert_called_with(
            query="concepts", course_name=None, lesson_number=1
        )

    def test_execute_with_both_filters(self, course_search_tool):
        """Test search with both course name and lesson number filters"""
        result = course_search_tool.execute(
            "artificial intelligence", course_name="AI Fundamentals", lesson_number=1
        )

        course_search_tool.store.search.assert_called_with(
            query="artificial intelligence",
            course_name="AI Fundamentals",
            lesson_number=1,
        )

    def test_execute_empty_results(self, mock_vector_store):
        """Test handling of empty search results"""
        # Mock empty results
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("nonexistent query")

        assert "No relevant content found" in result
        assert len(tool.last_sources) == 0

    def test_execute_empty_results_with_filters(self, mock_vector_store):
        """Test empty results with filter information in message"""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("query", course_name="Test Course", lesson_number=1)

        assert "No relevant content found in course 'Test Course' in lesson 1" in result

    def test_execute_search_error(self, mock_vector_store):
        """Test handling of search errors"""
        # Mock error result
        mock_vector_store.search.return_value = SearchResults.empty(
            "Database connection failed"
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query")

        assert result == "Database connection failed"
        assert len(tool.last_sources) == 0

    def test_execute_nonexistent_course(self, course_search_tool):
        """Test search with non-existent course name"""
        result = course_search_tool.execute("test", course_name="nonexistent")

        assert "No course found matching 'nonexistent'" in result

    def test_format_results_single_item(self, course_search_tool):
        """Test result formatting with single search result"""
        results = SearchResults(
            documents=["This is test content about AI."],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.2],
        )

        formatted = course_search_tool._format_results(results)

        assert "[Test Course - Lesson 1]" in formatted
        assert "This is test content about AI." in formatted

        # Check sources
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source["text"] == "Test Course - Lesson 1"

    def test_format_results_multiple_items(self, course_search_tool):
        """Test result formatting with multiple search results"""
        results = SearchResults(
            documents=[
                "First result about machine learning.",
                "Second result about neural networks.",
            ],
            metadata=[
                {"course_title": "AI Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "AI Course", "lesson_number": 2, "chunk_index": 1},
            ],
            distances=[0.1, 0.2],
        )

        formatted = course_search_tool._format_results(results)

        assert "[AI Course - Lesson 1]" in formatted
        assert "[AI Course - Lesson 2]" in formatted
        assert "First result about machine learning." in formatted
        assert "Second result about neural networks." in formatted

        # Check that results are separated by double newlines
        assert "\n\n" in formatted

        # Check sources
        assert len(course_search_tool.last_sources) == 2

    def test_format_results_no_lesson_number(self, course_search_tool):
        """Test formatting when lesson number is missing"""
        results = SearchResults(
            documents=["Content without lesson number."],
            metadata=[{"course_title": "Test Course", "chunk_index": 0}],
            distances=[0.3],
        )

        formatted = course_search_tool._format_results(results)

        assert "[Test Course]" in formatted
        assert "Content without lesson number." in formatted

        # Check source format
        source = course_search_tool.last_sources[0]
        assert source["text"] == "Test Course"

    @patch("search_tools.json.loads")
    def test_get_lesson_link_success(self, mock_json_loads, course_search_tool):
        """Test successful lesson link retrieval"""
        # Mock lessons data
        mock_json_loads.return_value = [
            {"lesson_number": 1, "lesson_link": "https://example.com/lesson1"},
            {"lesson_number": 2, "lesson_link": "https://example.com/lesson2"},
        ]

        link = course_search_tool._get_lesson_link("AI Fundamentals", 2)

        assert link == "https://example.com/lesson2"

    def test_get_lesson_link_not_found(self, course_search_tool):
        """Test lesson link retrieval when lesson not found"""
        link = course_search_tool._get_lesson_link("AI Fundamentals", 999)

        assert link is None

    def test_get_lesson_link_exception(self, mock_vector_store):
        """Test lesson link retrieval when exception occurs"""
        # Mock exception during course catalog query
        mock_vector_store.course_catalog.query.side_effect = Exception("Database error")

        tool = CourseSearchTool(mock_vector_store)
        link = tool._get_lesson_link("Test Course", 1)

        assert link is None


class TestToolManager:
    """Test suite for ToolManager integration with CourseSearchTool"""

    def test_register_and_execute_tool(self, tool_manager, course_search_tool):
        """Test tool registration and execution"""
        # Tool should already be registered via fixture
        definitions = tool_manager.get_tool_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

        # Test tool execution
        result = tool_manager.execute_tool(
            "search_course_content", query="machine learning"
        )

        assert isinstance(result, str)
        assert "AI Fundamentals" in result or "machine learning" in result

    def test_execute_nonexistent_tool(self, tool_manager):
        """Test execution of non-existent tool"""
        result = tool_manager.execute_tool("nonexistent_tool", query="test")

        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self, tool_manager, course_search_tool):
        """Test retrieval of sources from last search"""
        # Execute a search to generate sources
        tool_manager.execute_tool("search_course_content", query="introduction")

        sources = tool_manager.get_last_sources()
        assert len(sources) > 0
        assert isinstance(sources[0], dict)
        assert "text" in sources[0]

    def test_reset_sources(self, tool_manager, course_search_tool):
        """Test resetting sources from all tools"""
        # Execute search to generate sources
        tool_manager.execute_tool("search_course_content", query="introduction")
        assert len(tool_manager.get_last_sources()) > 0

        # Reset sources
        tool_manager.reset_sources()
        assert len(tool_manager.get_last_sources()) == 0
        assert len(course_search_tool.last_sources) == 0
