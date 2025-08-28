import pytest
import os
import tempfile
import shutil
from typing import List, Dict, Any
from unittest.mock import Mock, MagicMock

from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


# FastAPI Testing Fixtures

@pytest.fixture
def mock_rag_system(mock_vector_store, mock_ai_generator, session_manager, sample_course):
    """Create a mock RAGSystem for API testing"""
    mock_rag = Mock(spec=RAGSystem)
    
    # Mock query method
    def mock_query(query_text, session_id=None):
        if "error" in query_text.lower():
            raise Exception("Test error")
        
        return (
            f"Mock response for: {query_text}",
            [
                {"text": "Source 1: Course content", "url": "https://example.com/lesson1"},
                {"text": "Source 2: Additional material", "url": None}
            ]
        )
    
    mock_rag.query.side_effect = mock_query
    
    # Mock course analytics
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 1,
        "course_titles": ["AI Fundamentals"]
    }
    
    # Mock session manager
    mock_rag.session_manager = session_manager
    
    return mock_rag

@pytest.fixture
def test_app(mock_rag_system):
    """Create FastAPI app without static file mounting for testing"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional
    
    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Pydantic models (replicated from main app)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceData(BaseModel):
        text: str
        url: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceData]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    class ClearSessionRequest(BaseModel):
        session_id: str
    
    # API Endpoints (replicated from main app)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            # Process query using mock RAG system
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            # Convert sources to SourceData objects
            structured_sources = []
            for source in sources:
                if isinstance(source, dict):
                    structured_sources.append(SourceData(
                        text=source.get("text", "Unknown Source"),
                        url=source.get("url")
                    ))
                else:
                    structured_sources.append(SourceData(
                        text=str(source),
                        url=None
                    ))
            
            return QueryResponse(
                answer=answer,
                sources=structured_sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/clear-session")
    async def clear_session(request: ClearSessionRequest):
        try:
            mock_rag_system.session_manager.clear_session(request.session_id)
            return {"status": "success", "message": f"Session {request.session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Root endpoint for static file testing
    @app.get("/")
    async def root():
        return {"message": "RAG System API - Test Mode"}
    
    return app

@pytest.fixture
def test_client(test_app):
    """Create FastAPI test client"""
    return TestClient(test_app)

@pytest.fixture
def api_query_request():
    """Sample API query request data"""
    return {
        "query": "What courses are available?",
        "session_id": None
    }

@pytest.fixture
def api_query_request_with_session():
    """Sample API query request with session ID"""
    return {
        "query": "Tell me more about machine learning",
        "session_id": "test-session-123"
    }

@pytest.fixture
def invalid_query_request():
    """Invalid API request for error testing"""
    return {
        "invalid_field": "This should cause validation error"
    }

@pytest.fixture
def clear_session_request():
    """Sample clear session request"""
    return {
        "session_id": "test-session-123"
    }
