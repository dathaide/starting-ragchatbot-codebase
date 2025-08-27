import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from rag_system import RAGSystem
from vector_store import SearchResults

class TestRAGSystem:
    """Test suite for RAGSystem end-to-end functionality"""
    
    def test_init(self, test_config):
        """Test RAGSystem initialization"""
        rag = RAGSystem(test_config)
        
        assert rag.config == test_config
        assert rag.document_processor is not None
        assert rag.vector_store is not None
        assert rag.ai_generator is not None
        assert rag.session_manager is not None
        assert rag.tool_manager is not None
        assert rag.search_tool is not None
        assert rag.outline_tool is not None
        
        # Verify tools are registered
        definitions = rag.tool_manager.get_tool_definitions()
        tool_names = [tool["name"] for tool in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
    
    def test_add_course_document_success(self, test_config, tmp_path):
        """Test successful addition of a course document"""
        rag = RAGSystem(test_config)
        
        # Create a test course file
        course_content = """Course Title: Test Course
Course Link: https://example.com/course
Course Instructor: Test Instructor

Lesson 1: Introduction
This is the introduction lesson content.

Lesson 2: Advanced Topics  
This is the advanced topics content."""
        
        test_file = tmp_path / "test_course.txt"
        test_file.write_text(course_content)
        
        course, chunk_count = rag.add_course_document(str(test_file))
        
        assert course is not None
        assert course.title == "Test Course"
        assert course.instructor == "Test Instructor"
        assert len(course.lessons) == 2
        assert chunk_count > 0
        
        # Verify course is in vector store
        titles = rag.vector_store.get_existing_course_titles()
        assert "Test Course" in titles
    
    def test_add_course_document_failure(self, test_config):
        """Test handling of document processing failure"""
        rag = RAGSystem(test_config)
        
        # Try to add non-existent file
        course, chunk_count = rag.add_course_document("nonexistent_file.txt")
        
        assert course is None
        assert chunk_count == 0
    
    def test_add_course_folder_success(self, test_config, tmp_path):
        """Test adding multiple courses from a folder"""
        rag = RAGSystem(test_config)
        
        # Create test course files
        course1_content = """Course Title: Course One
Course Instructor: Instructor One

Lesson 1: Basics
Basic content here."""
        
        course2_content = """Course Title: Course Two  
Course Instructor: Instructor Two

Lesson 1: Advanced
Advanced content here."""
        
        (tmp_path / "course1.txt").write_text(course1_content)
        (tmp_path / "course2.txt").write_text(course2_content)
        
        courses_added, chunks_added = rag.add_course_folder(str(tmp_path))
        
        assert courses_added == 2
        assert chunks_added > 0
        
        # Verify both courses are in vector store
        titles = rag.vector_store.get_existing_course_titles()
        assert "Course One" in titles
        assert "Course Two" in titles
    
    def test_add_course_folder_skip_existing(self, test_config, tmp_path):
        """Test that existing courses are skipped when adding from folder"""
        rag = RAGSystem(test_config)
        
        course_content = """Course Title: Existing Course
Course Instructor: Test Instructor

Lesson 1: Content
Some lesson content."""
        
        test_file = tmp_path / "course.txt"
        test_file.write_text(course_content)
        
        # Add course first time
        courses_added1, chunks_added1 = rag.add_course_folder(str(tmp_path))
        assert courses_added1 == 1
        
        # Add same folder again - should skip existing
        courses_added2, chunks_added2 = rag.add_course_folder(str(tmp_path))
        assert courses_added2 == 0
        assert chunks_added2 == 0
    
    def test_add_course_folder_nonexistent(self, test_config):
        """Test adding courses from non-existent folder"""
        rag = RAGSystem(test_config)
        
        courses_added, chunks_added = rag.add_course_folder("/nonexistent/path")
        
        assert courses_added == 0
        assert chunks_added == 0
    
    @patch('rag_system.AIGenerator')
    def test_query_simple(self, mock_ai_generator_class, test_config):
        """Test simple query without conversation history"""
        # Mock AI generator
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.return_value = "This is a test response."
        mock_ai_generator_class.return_value = mock_ai_generator
        
        rag = RAGSystem(test_config)
        rag.ai_generator = mock_ai_generator
        
        response, sources = rag.query("What is AI?")
        
        assert response == "This is a test response."
        assert isinstance(sources, list)
        
        # Verify AI generator was called correctly
        mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_ai_generator.generate_response.call_args
        
        assert "What is AI?" in call_args[1]["query"]
        assert call_args[1]["conversation_history"] is None
        assert call_args[1]["tools"] is not None
        assert call_args[1]["tool_manager"] is not None
    
    @patch('rag_system.AIGenerator')
    def test_query_with_session(self, mock_ai_generator_class, test_config):
        """Test query with conversation history"""
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.return_value = "Response with history."
        mock_ai_generator_class.return_value = mock_ai_generator
        
        rag = RAGSystem(test_config)
        rag.ai_generator = mock_ai_generator
        
        # Create a session with history
        session_id = rag.session_manager.create_session()
        rag.session_manager.add_exchange(session_id, "Previous question", "Previous answer")
        
        response, sources = rag.query("Follow-up question", session_id=session_id)
        
        assert response == "Response with history."
        
        # Verify conversation history was passed
        call_args = mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] is not None
        assert "Previous question" in call_args[1]["conversation_history"]
        assert "Previous answer" in call_args[1]["conversation_history"]
        
        # Verify new exchange was added to history
        history = rag.session_manager.get_conversation_history(session_id)
        assert "Follow-up question" in history
        assert "Response with history." in history
    
    def test_query_with_tool_sources(self, test_config):
        """Test query that returns sources from tool usage"""
        rag = RAGSystem(test_config)
        
        # Mock the tool manager to return sources
        mock_sources = [
            {"text": "AI Fundamentals - Lesson 1", "url": "https://example.com/lesson1"},
            {"text": "AI Fundamentals - Lesson 2", "url": "https://example.com/lesson2"}
        ]
        rag.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        rag.tool_manager.reset_sources = Mock()
        
        # Mock AI generator
        rag.ai_generator.generate_response = Mock(return_value="AI response with sources")
        
        response, sources = rag.query("Tell me about AI")
        
        assert response == "AI response with sources"
        assert sources == mock_sources
        
        # Verify sources were retrieved and reset
        rag.tool_manager.get_last_sources.assert_called_once()
        rag.tool_manager.reset_sources.assert_called_once()
    
    def test_get_course_analytics(self, test_config):
        """Test getting course analytics"""
        rag = RAGSystem(test_config)
        
        # Mock vector store methods
        rag.vector_store.get_course_count = Mock(return_value=3)
        rag.vector_store.get_existing_course_titles = Mock(return_value=["Course A", "Course B", "Course C"])
        
        analytics = rag.get_course_analytics()
        
        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Course A" in analytics["course_titles"]

class TestRAGSystemIntegration:
    """Integration tests with real components"""
    
    def test_end_to_end_with_real_vector_store(self, test_config, tmp_path, sample_course, sample_course_chunks):
        """Test end-to-end functionality with real vector store"""
        # Create RAG system with real vector store
        rag = RAGSystem(test_config)
        
        # Add test data
        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)
        
        # Mock AI generator to simulate tool usage
        with patch.object(rag.ai_generator, 'generate_response') as mock_generate:
            # Mock response that indicates tool was used
            mock_generate.return_value = "Based on the course materials, AI involves machine learning concepts."
            
            # Mock tool manager to simulate search results
            mock_sources = [{"text": "AI Fundamentals - Lesson 1", "url": "https://example.com/lesson1"}]
            rag.tool_manager.get_last_sources = Mock(return_value=mock_sources)
            
            response, sources = rag.query("What is covered in the AI course?")
            
            assert response == "Based on the course materials, AI involves machine learning concepts."
            assert len(sources) == 1
            assert sources[0]["text"] == "AI Fundamentals - Lesson 1"
            
            # Verify AI generator was called with tools
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args[1]["tools"] is not None
            assert call_args[1]["tool_manager"] is not None
    
    def test_course_outline_tool_integration(self, test_config, sample_course):
        """Test integration with course outline tool"""
        rag = RAGSystem(test_config)
        
        # Add course metadata
        rag.vector_store.add_course_metadata(sample_course)
        
        # Test course outline tool directly
        result = rag.outline_tool.execute("AI Fundamentals")
        
        assert "Course: AI Fundamentals" in result
        assert "Instructor: Dr. Smith" in result
        assert "Total Lessons: 2" in result
        assert "Lesson 1: Introduction to AI" in result
        assert "Lesson 2: Machine Learning Basics" in result
    
    def test_search_tool_integration(self, test_config, sample_course, sample_course_chunks):
        """Test integration with search tool"""
        rag = RAGSystem(test_config)
        
        # Add test data
        rag.vector_store.add_course_metadata(sample_course)
        rag.vector_store.add_course_content(sample_course_chunks)
        
        # Test search tool directly
        result = rag.search_tool.execute("machine learning")
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should contain course and lesson context
        assert "AI Fundamentals" in result
        
        # Should have sources
        assert len(rag.search_tool.last_sources) > 0
    
    def test_session_management_integration(self, test_config):
        """Test session management integration"""
        rag = RAGSystem(test_config)
        
        # Create session and add exchanges
        session_id = rag.session_manager.create_session()
        rag.session_manager.add_exchange(session_id, "First question", "First answer")
        
        # Mock AI generator
        with patch.object(rag.ai_generator, 'generate_response') as mock_generate:
            mock_generate.return_value = "Second response"
            
            response, sources = rag.query("Second question", session_id=session_id)
            
            # Verify history was passed to AI generator
            call_args = mock_generate.call_args
            history = call_args[1]["conversation_history"]
            assert "First question" in history
            assert "First answer" in history
            
            # Verify new exchange was added
            updated_history = rag.session_manager.get_conversation_history(session_id)
            assert "Second question" in updated_history
            assert "Second response" in updated_history