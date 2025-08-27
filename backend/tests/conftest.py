import pytest
import os
import tempfile
import shutil
from typing import List, Dict, Any
from unittest.mock import Mock, MagicMock

from models import Course, Lesson, CourseChunk
from config import Config
from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from ai_generator import AIGenerator
from rag_system import RAGSystem
from session_manager import SessionManager


@pytest.fixture
def test_config():
    """Create a test configuration"""
    config = Config()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.CHUNK_SIZE = 400
    config.CHUNK_OVERLAP = 50
    config.MAX_RESULTS = 3
    config.MAX_HISTORY = 2
    # Use temp directory for test ChromaDB
    config.CHROMA_PATH = tempfile.mkdtemp()
    return config


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    lesson1 = Lesson(
        lesson_number=1,
        title="Introduction to AI",
        lesson_link="https://example.com/lesson1",
    )
    lesson2 = Lesson(
        lesson_number=2,
        title="Machine Learning Basics",
        lesson_link="https://example.com/lesson2",
    )

    course = Course(
        title="AI Fundamentals",
        course_link="https://example.com/course",
        instructor="Dr. Smith",
        lessons=[lesson1, lesson2],
    )
    return course


@pytest.fixture
def sample_course_chunks(sample_course):
    """Create sample course chunks for testing"""
    chunks = [
        CourseChunk(
            content="Lesson 1 content: This is an introduction to artificial intelligence and machine learning concepts.",
            course_title="AI Fundamentals",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="AI is transforming many industries including healthcare, finance, and transportation.",
            course_title="AI Fundamentals",
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Course AI Fundamentals Lesson 2 content: Machine learning involves training models on data to make predictions.",
            course_title="AI Fundamentals",
            lesson_number=2,
            chunk_index=2,
        ),
        CourseChunk(
            content="Supervised learning uses labeled data while unsupervised learning finds patterns in unlabeled data.",
            course_title="AI Fundamentals",
            lesson_number=2,
            chunk_index=3,
        ),
    ]
    return chunks


@pytest.fixture
def mock_vector_store(sample_course, sample_course_chunks):
    """Create a mock vector store with predictable responses"""
    mock_store = Mock(spec=VectorStore)

    # Mock search method
    def mock_search(query, course_name=None, lesson_number=None, limit=None):
        # Return different results based on query content
        if "introduction" in query.lower():
            return SearchResults(
                documents=[sample_course_chunks[0].content],
                metadata=[
                    {
                        "course_title": "AI Fundamentals",
                        "lesson_number": 1,
                        "chunk_index": 0,
                    }
                ],
                distances=[0.2],
            )
        elif "machine learning" in query.lower():
            return SearchResults(
                documents=[sample_course_chunks[2].content],
                metadata=[
                    {
                        "course_title": "AI Fundamentals",
                        "lesson_number": 2,
                        "chunk_index": 2,
                    }
                ],
                distances=[0.15],
            )
        elif course_name and course_name.lower() == "nonexistent":
            return SearchResults.empty("No course found matching 'nonexistent'")
        else:
            # General search returns multiple results
            return SearchResults(
                documents=[chunk.content for chunk in sample_course_chunks[:2]],
                metadata=[
                    {
                        "course_title": chunk.course_title,
                        "lesson_number": chunk.lesson_number,
                        "chunk_index": chunk.chunk_index,
                    }
                    for chunk in sample_course_chunks[:2]
                ],
                distances=[0.3, 0.4],
            )

    mock_store.search.side_effect = mock_search

    # Mock course catalog
    mock_catalog = Mock()
    mock_catalog.query.return_value = {
        "documents": [["AI Fundamentals"]],
        "metadatas": [
            [
                {
                    "title": "AI Fundamentals",
                    "instructor": "Dr. Smith",
                    "course_link": "https://example.com/course",
                    "lessons_json": '[{"lesson_number": 1, "lesson_title": "Introduction to AI", "lesson_link": "https://example.com/lesson1"}, {"lesson_number": 2, "lesson_title": "Machine Learning Basics", "lesson_link": "https://example.com/lesson2"}]',
                    "lesson_count": 2,
                }
            ]
        ],
    }
    mock_store.course_catalog = mock_catalog

    return mock_store


@pytest.fixture
def mock_anthropic_response():
    """Create mock Anthropic API response"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "This is a test response from the AI model."
    mock_response.content[0].type = "text"
    mock_response.stop_reason = "end_turn"
    return mock_response


@pytest.fixture
def mock_anthropic_tool_response():
    """Create mock Anthropic API response with tool use"""
    mock_response = Mock()

    # Mock tool use content block
    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = "search_course_content"
    tool_block.id = "tool_123"
    tool_block.input = {"query": "machine learning"}

    mock_response.content = [tool_block]
    mock_response.stop_reason = "tool_use"
    return mock_response


@pytest.fixture
def mock_anthropic_final_response():
    """Create mock final response after tool execution"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = (
        "Based on the search results, machine learning involves training models on data to make predictions."
    )
    mock_response.content[0].type = "text"
    mock_response.stop_reason = "end_turn"
    return mock_response


@pytest.fixture
def mock_ai_generator(mock_anthropic_response):
    """Create a mock AIGenerator"""
    mock_ai = Mock(spec=AIGenerator)
    mock_ai.generate_response.return_value = mock_anthropic_response.content[0].text
    return mock_ai


@pytest.fixture
def course_search_tool(mock_vector_store):
    """Create a CourseSearchTool with mock vector store"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def tool_manager(course_search_tool):
    """Create a ToolManager with CourseSearchTool registered"""
    manager = ToolManager()
    manager.register_tool(course_search_tool)
    return manager


@pytest.fixture
def session_manager():
    """Create a SessionManager for testing"""
    return SessionManager(max_history=2)


@pytest.fixture(autouse=True)
def cleanup_temp_dirs():
    """Clean up temporary directories after tests"""
    yield
    # Cleanup is handled by pytest's tempfile fixtures


@pytest.fixture
def real_vector_store(test_config, sample_course, sample_course_chunks):
    """Create a real VectorStore with test data for integration tests"""
    store = VectorStore(
        test_config.CHROMA_PATH, test_config.EMBEDDING_MODEL, test_config.MAX_RESULTS
    )

    # Add test data
    store.add_course_metadata(sample_course)
    store.add_course_content(sample_course_chunks)

    yield store

    # Cleanup
    try:
        shutil.rmtree(test_config.CHROMA_PATH)
    except OSError:
        pass
