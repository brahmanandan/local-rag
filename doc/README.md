# Documentation

This folder contains the HTML documentation generated from `README.md`.

## Files

- `index.html` - HTML version of the README.md documentation

## Updating the Documentation

The HTML documentation is generated from the main `README.md` file. To update it:

### Manual Update

```bash
# From the project root directory
python generate_docs.py
```

### Automatic Update (Git Hook)

To automatically update the HTML documentation whenever README.md changes, you can set up a git pre-commit hook:

**Easy setup (recommended):**
```bash
# From the project root directory
./setup_doc_hook.sh
```

**Manual setup:**
```bash
# Create the hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Update HTML documentation if README.md changed
if git diff --cached --name-only | grep -q README.md; then
    echo "README.md changed, updating HTML documentation..."
    python generate_docs.py
    git add doc/index.html
fi
EOF

# Make it executable
chmod +x .git/hooks/pre-commit
```

The hook will automatically:
1. Detect when README.md is being committed
2. Run `generate_docs.py` to update the HTML
3. Stage the updated `doc/index.html` file
4. Include it in your commit

### Watch Mode (Development)

For active development, you can use a file watcher to auto-regenerate:

**Using entr (Linux/macOS):**
```bash
# Install entr: brew install entr (macOS) or apt-get install entr (Linux)
ls README.md | entr python generate_docs.py
```

**Using watchdog (Python):**
```bash
pip install watchdog
# Then run:
python -c "from watchdog.observers import Observer; from watchdog.events import FileSystemEventHandler; import subprocess; class Handler(FileSystemEventHandler): def on_modified(self, e): subprocess.run(['python', 'generate_docs.py']) if e.src_path.endswith('README.md') else None; o = Observer(); o.schedule(Handler(), '.', recursive=False); o.start(); import time; time.sleep(3600)"
```

## Viewing the Documentation

Simply open `doc/index.html` in your web browser:

```bash
# macOS
open doc/index.html

# Linux
xdg-open doc/index.html

# Windows
start doc/index.html
```

Or serve it with a simple HTTP server:

```bash
# Python 3
python -m http.server 8000 --directory doc

# Then open http://localhost:8000 in your browser
```

