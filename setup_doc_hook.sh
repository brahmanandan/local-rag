#!/bin/bash
# Setup script to create a git pre-commit hook that auto-updates HTML docs

HOOK_FILE=".git/hooks/pre-commit"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if .git directory exists
if [ ! -d ".git" ]; then
    echo "Error: This is not a git repository."
    echo "Initialize git first with: git init"
    exit 1
fi

# Create pre-commit hook
cat > "$HOOK_FILE" << 'HOOK_EOF'
#!/bin/bash
# Auto-update HTML documentation if README.md changed

# Get the directory where the hook is running
SCRIPT_DIR="$(git rev-parse --show-toplevel)"
cd "$SCRIPT_DIR"

# Check if README.md is in the staged changes
if git diff --cached --name-only | grep -q "^README.md$"; then
    echo "README.md changed, updating HTML documentation..."
    
    # Run the documentation generator
    if python generate_docs.py; then
        # Stage the updated HTML file
        git add doc/index.html
        echo "✓ HTML documentation updated and staged"
    else
        echo "⚠ Warning: Failed to update HTML documentation"
        echo "  You can update it manually with: python generate_docs.py"
    fi
fi

exit 0
HOOK_EOF

# Make the hook executable
chmod +x "$HOOK_FILE"

echo "✓ Git pre-commit hook installed successfully!"
echo ""
echo "The HTML documentation will now be automatically updated"
echo "whenever you commit changes to README.md"
echo ""
echo "To test it, try:"
echo "  1. Make a small change to README.md"
echo "  2. git add README.md"
echo "  3. git commit -m 'test'"
echo ""
echo "The hook will automatically run generate_docs.py and stage doc/index.html"

