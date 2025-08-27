from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults


class Tool(ABC):
    """Abstract base class for all tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "What to search for in the course content"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
        """
        Execute the search tool with given parameters.
        
        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter
            
        Returns:
            Formatted search results or error message
        """
        
        # Use the vector store's unified search interface
        results = self.store.search(
            query=query,
            course_name=course_name,
            lesson_number=lesson_number
        )
        
        # Handle errors
        if results.error:
            return results.error
        
        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."
        
        # Format and return results
        return self._format_results(results)
    
    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI with links
        
        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')
            
            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"
            
            # Get lesson link if available
            lesson_link = self._get_lesson_link(course_title, lesson_num) if lesson_num is not None else None
            
            # Create structured source with link
            source_text = course_title
            if lesson_num is not None:
                source_text += f" - Lesson {lesson_num}"
            
            # Store as structured data for frontend
            source_data = {
                "text": source_text,
                "url": lesson_link
            }
            sources.append(source_data)
            
            formatted.append(f"{header}\n{doc}")
        
        # Store sources for retrieval
        self.last_sources = sources
        
        return "\n\n".join(formatted)
    
    def _get_lesson_link(self, course_title: str, lesson_number: int) -> str:
        """Retrieve lesson link from course catalog"""
        try:
            # Query course catalog for this course
            results = self.store.course_catalog.query(
                query_texts=[course_title],
                where={"title": course_title},
                n_results=1
            )
            
            if results['documents'] and results['metadatas']:
                metadata = results['metadatas'][0][0]
                lessons_json = metadata.get('lessons_json', '[]')
                
                # Parse lessons JSON and find the specific lesson
                import json
                lessons = json.loads(lessons_json)
                for lesson in lessons:
                    if lesson.get('lesson_number') == lesson_number:
                        return lesson.get('lesson_link')
                        
        except Exception as e:
            print(f"Error retrieving lesson link: {e}")
        
        return None


class CourseOutlineTool(Tool):
    """Tool for retrieving course outlines with lesson lists"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "get_course_outline",
            "description": "Get complete course outline with lesson list for a specific course",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_title": {
                        "type": "string",
                        "description": "Course title to get outline for (partial matches work)"
                    }
                },
                "required": ["course_title"]
            }
        }
    
    def execute(self, course_title: str) -> str:
        """
        Execute the course outline tool to get course information and lesson list.
        
        Args:
            course_title: The course title to search for
            
        Returns:
            Formatted course outline or error message
        """
        try:
            # Search course catalog for the specified course
            results = self.store.course_catalog.query(
                query_texts=[course_title],
                n_results=1
            )
            
            if not results['documents'] or not results['documents'][0]:
                return f"No course found matching '{course_title}'"
            
            if not results['metadatas'] or not results['metadatas'][0]:
                return f"Course found but missing metadata for '{course_title}'"
            
            # Extract course metadata
            metadata = results['metadatas'][0][0]
            course_name = metadata.get('title', 'Unknown Course')
            instructor = metadata.get('instructor', 'Unknown Instructor')
            course_link = metadata.get('course_link', '')
            lessons_json = metadata.get('lessons_json', '[]')
            
            # Parse lessons data
            import json
            try:
                lessons = json.loads(lessons_json)
            except json.JSONDecodeError:
                lessons = []
            
            # Format the response
            outline_parts = []
            outline_parts.append(f"Course: {course_name}")
            if course_link:
                outline_parts.append(f"Course Link: {course_link}")
            outline_parts.append(f"Instructor: {instructor}")
            outline_parts.append(f"Total Lessons: {len(lessons)}")
            outline_parts.append("")
            outline_parts.append("Lesson Outline:")
            
            if lessons:
                for lesson in lessons:
                    lesson_num = lesson.get('lesson_number', 'N/A')
                    lesson_title = lesson.get('lesson_title', 'Untitled')
                    outline_parts.append(f"Lesson {lesson_num}: {lesson_title}")
            else:
                outline_parts.append("No lessons available")
            
            return "\n".join(outline_parts)
            
        except Exception as e:
            return f"Error retrieving course outline: {str(e)}"


class ToolManager:
    """Manages available tools for the AI"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    
    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        return self.tools[tool_name].execute(**kwargs)
    
    def get_last_sources(self) -> list:
        """Get sources from the last search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources') and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []