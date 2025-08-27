#!/bin/bash
set -e

echo "🚀 Running complete code quality checks..."
echo "=============================================="

# Ensure we have the correct PATH for tools
export PATH="/Users/deirdreathaide/Library/Python/3.9/bin:$PATH"

# Step 1: Format code with Black
echo ""
echo "🎨 Step 1: Formatting code with Black..."
black --check --diff backend/ main.py

if [ $? -eq 0 ]; then
    echo "✅ Code formatting: PASSED"
else
    echo "❌ Code formatting: FAILED - Run ./format.sh to fix"
    echo "   Or run: black backend/ main.py"
fi

# Step 2: Check for basic Python syntax errors
echo ""
echo "🔍 Step 2: Checking Python syntax..."
python3 -m py_compile backend/*.py main.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Python syntax: PASSED"
else
    echo "❌ Python syntax: FAILED - Fix syntax errors"
fi

# Step 3: Run tests if they exist
echo ""
echo "🧪 Step 3: Running tests..."
if [ -d "backend/tests" ]; then
    cd backend
    python3 -m pytest tests/ -v --tb=short
    if [ $? -eq 0 ]; then
        echo "✅ Tests: PASSED"
    else
        echo "❌ Tests: FAILED"
    fi
    cd ..
else
    echo "ℹ️  No tests directory found - skipping test run"
fi

echo ""
echo "✅ Quality check complete!"
echo ""
echo "🛠️  Development Tips:"
echo "  - Run './format.sh' to auto-format your code"
echo "  - Ensure tests pass before committing changes"
echo "  - Follow the existing code patterns and naming conventions"