# Development Tools & Code Quality

This document describes the code quality tools and scripts available for the RAG chatbot project.

## Quick Commands

### Format Code
```bash
# Make script executable (first time only)
chmod +x format.sh

# Run code formatting
./format.sh
```

### Run Quality Checks
```bash
# Make script executable (first time only)  
chmod +x quality-check.sh

# Run complete quality check suite
./quality-check.sh
```

### Manual Commands
```bash
# Format all Python files
export PATH="/Users/deirdreathaide/Library/Python/3.9/bin:$PATH"
black backend/ main.py

# Check formatting without making changes
black --check --diff backend/ main.py

# Check Python syntax
python3 -m py_compile backend/*.py main.py

# Run tests
cd backend && python3 -m pytest tests/ -v
```

## Code Quality Configuration

The project now includes:

### Black Code Formatter
- **Line length**: 88 characters
- **Target Python**: 3.13+
- **Excludes**: chroma_db, .env, .git, __pycache__, build, dist
- **Configuration**: Located in `pyproject.toml`

### Development Dependencies
- **black>=24.0.0**: Code formatting
- **ruff>=0.1.0**: Fast linting (future use)
- **pytest>=7.4.0**: Testing framework
- **pytest-asyncio>=0.21.0**: Async test support
- **httpx>=0.25.0**: HTTP client for API testing

## What Black Fixed

The formatting improvements applied to the codebase include:

1. **Consistent spacing**: Standardized spaces around operators and after commas
2. **Line breaks**: Proper line breaks for long function calls and parameter lists
3. **Import organization**: Cleaned up import statements
4. **Trailing whitespace**: Removed unnecessary trailing spaces
5. **Blank lines**: Consistent spacing between classes and functions
6. **String formatting**: Consistent quote style and formatting

## Files Formatted

Black successfully reformatted the following files:
- `backend/config.py`
- `backend/models.py` 
- `backend/app.py`
- `backend/rag_system.py`
- `backend/ai_generator.py`
- `backend/session_manager.py`
- `backend/document_processor.py`
- `backend/search_tools.py`
- `backend/vector_store.py`
- All test files in `backend/tests/`

## Integration with Existing Workflow

### With uv (when available)
```bash
# Install dev dependencies
uv sync --extra dev

# Run formatting
uv run black backend/ main.py
```

### Fallback (system Python)
```bash
# Install tools
python3 -m pip install black>=24.0.0 --user

# Add to PATH and run
export PATH="/Users/deirdreathaide/Library/Python/3.9/bin:$PATH"
black backend/ main.py
```

## Pre-commit Integration (Optional)

For teams wanting automatic formatting on commit:

1. Install pre-commit: `pip install pre-commit`
2. Create `.pre-commit-config.yaml` (example in planning docs)
3. Install hooks: `pre-commit install`

## Benefits Achieved

✅ **Consistency**: All Python files now follow Black's opinionated formatting  
✅ **Readability**: Improved spacing and line breaks in complex AI/ML code  
✅ **Developer Experience**: Simple `./format.sh` command for formatting  
✅ **Quality Assurance**: `./quality-check.sh` validates formatting and runs tests  
✅ **Low Maintenance**: Black requires zero configuration decisions  

The codebase now has professional-grade code formatting that will improve maintainability and collaboration.