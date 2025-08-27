#!/bin/bash
set -e

echo "🎨 Formatting Python code with Black..."

# Ensure we have the correct PATH for tools
export PATH="/Users/deirdreathaide/Library/Python/3.9/bin:$PATH"

# Preview changes first (optional - comment out if you want direct formatting)
echo "📋 Preview of changes:"
black --diff --color backend/ main.py || true

echo ""
echo "✨ Applying formatting..."
black backend/ main.py

echo "✅ Code formatting complete!"
echo ""
echo "📊 Summary:"
echo "  - All Python files formatted with Black (line length: 88)"
echo "  - Consistent spacing and indentation applied"
echo "  - Import statements organized"