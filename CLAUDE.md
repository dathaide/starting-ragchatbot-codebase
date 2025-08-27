# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start Commands

**Development Setup:**
```bash
# Install dependencies (preferred method)
uv sync

# Alternative if uv has compatibility issues
python3 -m pip install chromadb==1.0.15 anthropic==0.58.2 sentence-transformers==5.0.0 fastapi==0.116.1 uvicorn==0.35.0 python-multipart==0.0.20 python-dotenv==1.1.1

# Create environment file
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

**Running the Application:**
```bash
# Quick start (may need uv path fix)
chmod +x run.sh && ./run.sh

# Manual start (most reliable)
cd backend && python3 -m uvicorn app:app --reload --port 8000

# Alternative with uv
cd backend && ~/.local/bin/uv run uvicorn app:app --reload --port 8000
```

**Testing:**
```bash
# Test API endpoint directly
curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"query": "What courses are available?"}'

# Check course loading
curl http://localhost:8000/api/courses
```

## Architecture Overview

### Core System Design
This is a **tool-based RAG (Retrieval-Augmented Generation) system** where Claude autonomously decides whether to search the knowledge base or answer from general knowledge. The system processes course documents into semantic chunks and provides an AI-powered chat interface.

### Key Components Flow

**1. RAGSystem (rag_system.py)** - Central orchestrator that coordinates all components:
- Initializes document processor, vector store, AI generator, session manager, and tool manager
- Handles query processing by delegating to AI generator with tool access
- Manages conversation history and source tracking

**2. Tool-Based AI Architecture (ai_generator.py + search_tools.py)**:
- **AIGenerator** interfaces with Anthropic Claude API and manages tool execution
- **ToolManager** registers and executes search tools
- **CourseSearchTool** performs semantic search with optional course/lesson filtering
- Claude decides autonomously when to search vs answer directly

**3. Document Processing Pipeline (document_processor.py)**:
- Parses structured course documents with format: Course Title/Link/Instructor + Lesson sections
- Performs sentence-based chunking with configurable size and overlap
- Adds contextual metadata to chunks (course title, lesson number)

**4. Vector Storage (vector_store.py)**:
- ChromaDB integration for semantic search using sentence transformers
- Stores course metadata separately from content chunks
- Supports filtering by course title and lesson number

**5. Frontend Integration (app.py + frontend/)**:
- FastAPI serves both API endpoints and static frontend files
- Pydantic models for request/response validation
- CORS enabled for development

### Data Flow
1. **Startup**: Documents from `docs/` folder automatically processed into vector database
2. **Query**: User query → FastAPI → RAGSystem → AIGenerator (Claude) 
3. **Decision**: Claude determines if search needed or can answer directly
4. **Tool Use**: If needed, Claude calls CourseSearchTool → VectorStore → ChromaDB
5. **Response**: Search results fed back to Claude → synthesized answer → user

### Configuration
- **config.py** centralizes all settings (API keys, chunk sizes, model names, paths)
- **Environment**: `.env` file in root directory for ANTHROPIC_API_KEY
- **Models**: Currently uses Claude Sonnet and all-MiniLM-L6-v2 embeddings

### Document Format Expected
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: Introduction
Lesson Link: [optional_url]
[lesson content...]

Lesson 1: Next Topic  
[lesson content...]
```

## Common Issues

**API Key Problems:**
- Ensure ANTHROPIC_API_KEY is set in `.env` file in root directory
- Verify billing/credits are set up in Anthropic console
- Error "credit balance too low" indicates billing issue, not code problem

**Dependency Issues:**
- `uv` may have macOS compatibility issues with onnxruntime on older versions
- Fallback to pip installation usually resolves compatibility problems
- Use manual uvicorn startup if run.sh fails

**Path Issues:**
- Server runs from `backend/` directory, so `.env` needs to be in parent directory
- ChromaDB creates `chroma_db/` folder in backend directory during startup
- Frontend files served from `frontend/` directory via FastAPI static files

**Vector Database:**
- ChromaDB automatically initialized on first run
- Course documents only processed once (skipped on subsequent runs if already exist)
- Delete `backend/chroma_db/` folder to force reprocessing of all documents