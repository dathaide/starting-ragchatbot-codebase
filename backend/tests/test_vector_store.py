import pytest
import tempfile
import shutil
import json
from unittest.mock import Mock, patch
from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


class TestVectorStore:
    """Test suite for VectorStore functionality"""

    def test_init(self, test_config):
        """Test VectorStore initialization"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        assert store.max_results == test_config.MAX_RESULTS
        assert store.client is not None
        assert store.embedding_function is not None
        assert store.course_catalog is not None
        assert store.course_content is not None

    def test_add_course_metadata(self, real_vector_store, sample_course):
        """Test adding course metadata to the catalog"""
        # Course metadata should already be added via fixture
        existing_titles = real_vector_store.get_existing_course_titles()
        assert "AI Fundamentals" in existing_titles

        # Test retrieving course metadata
        metadata_list = real_vector_store.get_all_courses_metadata()
        assert len(metadata_list) == 1

        metadata = metadata_list[0]
        assert metadata["title"] == "AI Fundamentals"
        assert metadata["instructor"] == "Dr. Smith"
        assert metadata["course_link"] == "https://example.com/course"
        assert "lessons" in metadata
        assert len(metadata["lessons"]) == 2

    def test_add_course_content(self, test_config):
        """Test adding course content chunks"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        chunks = [
            CourseChunk(
                content="Test content about AI",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
            )
        ]

        store.add_course_content(chunks)

        # Verify content was added by searching for it
        results = store.search("AI")
        assert not results.is_empty()
        assert "Test content about AI" in results.documents[0]

    def test_search_basic(self, real_vector_store):
        """Test basic search functionality"""
        results = real_vector_store.search("artificial intelligence")

        assert not results.is_empty()
        assert len(results.documents) > 0
        assert len(results.metadata) > 0
        assert len(results.distances) > 0

        # Check that results contain expected metadata
        for metadata in results.metadata:
            assert "course_title" in metadata
            assert "chunk_index" in metadata

    def test_search_with_course_filter(self, real_vector_store):
        """Test search with course name filtering"""
        results = real_vector_store.search("learning", course_name="AI Fundamentals")

        assert not results.is_empty()

        # All results should be from the specified course
        for metadata in results.metadata:
            assert metadata["course_title"] == "AI Fundamentals"

    def test_search_with_lesson_filter(self, real_vector_store):
        """Test search with lesson number filtering"""
        results = real_vector_store.search("content", lesson_number=1)

        assert not results.is_empty()

        # All results should be from lesson 1
        for metadata in results.metadata:
            assert metadata.get("lesson_number") == 1

    def test_search_with_both_filters(self, real_vector_store):
        """Test search with both course and lesson filters"""
        results = real_vector_store.search(
            "introduction", course_name="AI Fundamentals", lesson_number=1
        )

        assert not results.is_empty()

        for metadata in results.metadata:
            assert metadata["course_title"] == "AI Fundamentals"
            assert metadata.get("lesson_number") == 1

    def test_search_nonexistent_course(self, real_vector_store):
        """Test search with non-existent course name"""
        results = real_vector_store.search("test", course_name="Nonexistent Course")

        assert results.error is not None
        assert "No course found matching" in results.error
        assert results.is_empty()

    def test_search_with_limit(self, real_vector_store):
        """Test search with custom result limit"""
        results = real_vector_store.search("content", limit=1)

        assert not results.is_empty()
        assert len(results.documents) <= 1

    def test_resolve_course_name_exact_match(self, real_vector_store):
        """Test course name resolution with exact match"""
        resolved = real_vector_store._resolve_course_name("AI Fundamentals")
        assert resolved == "AI Fundamentals"

    def test_resolve_course_name_partial_match(self, real_vector_store):
        """Test course name resolution with partial match"""
        # Should find "AI Fundamentals" when searching for "Fundamentals"
        resolved = real_vector_store._resolve_course_name("Fundamentals")
        assert resolved == "AI Fundamentals"

    def test_resolve_course_name_no_match(self, real_vector_store):
        """Test course name resolution with no match"""
        resolved = real_vector_store._resolve_course_name("Nonexistent Course")
        assert resolved is None

    def test_build_filter_no_filters(self, test_config):
        """Test filter building with no filters"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        filter_dict = store._build_filter(None, None)
        assert filter_dict is None

    def test_build_filter_course_only(self, test_config):
        """Test filter building with course filter only"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        filter_dict = store._build_filter("Test Course", None)
        assert filter_dict == {"course_title": "Test Course"}

    def test_build_filter_lesson_only(self, test_config):
        """Test filter building with lesson filter only"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        filter_dict = store._build_filter(None, 1)
        assert filter_dict == {"lesson_number": 1}

    def test_build_filter_both_filters(self, test_config):
        """Test filter building with both filters"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        filter_dict = store._build_filter("Test Course", 2)
        expected = {"$and": [{"course_title": "Test Course"}, {"lesson_number": 2}]}
        assert filter_dict == expected

    def test_get_course_count(self, real_vector_store):
        """Test getting course count"""
        count = real_vector_store.get_course_count()
        assert count == 1

    def test_get_existing_course_titles(self, real_vector_store):
        """Test getting existing course titles"""
        titles = real_vector_store.get_existing_course_titles()
        assert isinstance(titles, list)
        assert "AI Fundamentals" in titles

    def test_get_course_link(self, real_vector_store):
        """Test getting course link"""
        link = real_vector_store.get_course_link("AI Fundamentals")
        assert link == "https://example.com/course"

        # Test non-existent course
        link = real_vector_store.get_course_link("Nonexistent")
        assert link is None

    def test_get_lesson_link(self, real_vector_store):
        """Test getting lesson link"""
        link = real_vector_store.get_lesson_link("AI Fundamentals", 1)
        assert link == "https://example.com/lesson1"

        # Test non-existent lesson
        link = real_vector_store.get_lesson_link("AI Fundamentals", 999)
        assert link is None

        # Test non-existent course
        link = real_vector_store.get_lesson_link("Nonexistent", 1)
        assert link is None

    def test_clear_all_data(self, test_config):
        """Test clearing all data"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        # Add some data
        course = Course(title="Test Course", instructor="Test Instructor")
        chunks = [
            CourseChunk(
                content="Test content", course_title="Test Course", chunk_index=0
            )
        ]

        store.add_course_metadata(course)
        store.add_course_content(chunks)

        # Verify data exists
        assert store.get_course_count() > 0

        # Clear data
        store.clear_all_data()

        # Verify data is cleared
        assert store.get_course_count() == 0

        # Verify collections still exist and work
        search_results = store.search("test")
        assert search_results.is_empty()

    def test_search_error_handling(self, test_config):
        """Test search error handling"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        # Mock course_content to raise an exception
        store.course_content = Mock()
        store.course_content.query.side_effect = Exception("Database error")

        results = store.search("test query")

        assert results.error is not None
        assert "Search error" in results.error
        assert results.is_empty()


class TestSearchResults:
    """Test suite for SearchResults class"""

    def test_from_chroma_with_results(self):
        """Test creating SearchResults from ChromaDB results"""
        chroma_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key1": "value1"}, {"key2": "value2"}]],
            "distances": [[0.1, 0.2]],
        }

        results = SearchResults.from_chroma(chroma_results)

        assert results.documents == ["doc1", "doc2"]
        assert results.metadata == [{"key1": "value1"}, {"key2": "value2"}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None

    def test_from_chroma_empty(self):
        """Test creating SearchResults from empty ChromaDB results"""
        chroma_results = {"documents": [], "metadatas": [], "distances": []}

        results = SearchResults.from_chroma(chroma_results)

        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error is None

    def test_empty_with_error(self):
        """Test creating empty SearchResults with error message"""
        results = SearchResults.empty("Test error message")

        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error == "Test error message"

    def test_is_empty_true(self):
        """Test is_empty returns True for empty results"""
        results = SearchResults(documents=[], metadata=[], distances=[])
        assert results.is_empty() is True

    def test_is_empty_false(self):
        """Test is_empty returns False for non-empty results"""
        results = SearchResults(
            documents=["doc1"], metadata=[{"key": "value"}], distances=[0.1]
        )
        assert results.is_empty() is False
