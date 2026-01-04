#!/usr/bin/env python3
"""
Script to convert README.md to HTML documentation.
Run this script whenever README.md is updated to regenerate the HTML documentation.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import markdown
    from markdown.extensions import codehilite, fenced_code, tables, toc
except ImportError:
    print("Error: markdown library not found.")
    print("Please install it with: pip install markdown")
    sys.exit(1)

def generate_html_from_readme():
    """Convert README.md to HTML with styling."""
    
    # Paths
    project_root = Path(__file__).parent
    readme_path = project_root / "README.md"
    doc_dir = project_root / "doc"
    html_path = doc_dir / "index.html"
    
    # Create doc directory if it doesn't exist
    doc_dir.mkdir(exist_ok=True)
    
    # Read README.md
    if not readme_path.exists():
        print(f"Error: {readme_path} not found!")
        sys.exit(1)
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Configure markdown extensions
    md = markdown.Markdown(
        extensions=[
            'codehilite',
            'fenced_code',
            'tables',
            'toc',
            'nl2br',
            'sane_lists',
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': True,
            },
            'toc': {
                'permalink': True,
                'baselevel': 2,
            }
        }
    )
    
    # Convert markdown to HTML
    html_content = md.convert(markdown_content)
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create full HTML document with styling
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="RAG Course Chatbot Documentation">
    <title>RAG Course Chatbot - Documentation</title>
    <style>
        /* Reset and base styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 0;
            margin: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: #ffffff;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            min-height: 100vh;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        header p {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 2rem;
        }}
        
        /* Typography */
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        
        h1 {{
            font-size: 2rem;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.5rem;
        }}
        
        h2 {{
            font-size: 1.75rem;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 0.3rem;
            margin-top: 2.5rem;
        }}
        
        h3 {{
            font-size: 1.5rem;
            margin-top: 2rem;
        }}
        
        h4 {{
            font-size: 1.25rem;
            margin-top: 1.5rem;
        }}
        
        /* Links */
        a {{
            color: #667eea;
            text-decoration: none;
            transition: color 0.2s;
        }}
        
        a:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}
        
        /* Lists */
        ul, ol {{
            margin-left: 2rem;
            margin-bottom: 1rem;
        }}
        
        li {{
            margin-bottom: 0.5rem;
        }}
        
        /* Code blocks */
        pre {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 1rem;
            overflow-x: auto;
            margin: 1rem 0;
        }}
        
        code {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
            font-size: 0.9em;
            background-color: #f8f9fa;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            color: #e83e8c;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #333;
        }}
        
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        
        th {{
            background-color: #667eea;
            color: white;
            font-weight: 600;
        }}
        
        tr:hover {{
            background-color: #f8f9fa;
        }}
        
        /* Blockquotes */
        blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 1rem;
            margin: 1rem 0;
            color: #666;
            font-style: italic;
        }}
        
        /* Horizontal rules */
        hr {{
            border: none;
            border-top: 2px solid #e9ecef;
            margin: 2rem 0;
        }}
        
        /* Checkboxes */
        input[type="checkbox"] {{
            margin-right: 0.5rem;
        }}
        
        /* Footer */
        footer {{
            background-color: #2c3e50;
            color: white;
            padding: 1.5rem;
            text-align: center;
            margin-top: 3rem;
        }}
        
        footer p {{
            margin: 0.5rem 0;
        }}
        
        .timestamp {{
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        /* Table of Contents */
        .toc {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 1.5rem;
            margin: 2rem 0;
        }}
        
        .toc ul {{
            list-style-type: none;
            margin-left: 0;
        }}
        
        .toc li {{
            margin-bottom: 0.5rem;
        }}
        
        .toc a {{
            color: #667eea;
        }}
        
        /* Responsive design */
        @media (max-width: 768px) {{
            .container {{
                margin: 0;
            }}
            
            header h1 {{
                font-size: 1.8rem;
            }}
            
            .content {{
                padding: 1rem;
            }}
            
            pre {{
                font-size: 0.85em;
            }}
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background-color: white;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            header {{
                background: #667eea !important;
                -webkit-print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>RAG Course Chatbot</h1>
            <p>Documentation</p>
        </header>
        
        <div class="content">
            {html_content}
        </div>
        
        <footer>
            <p><strong>RAG Course Chatbot Documentation</strong></p>
            <p class="timestamp">Last updated: {timestamp}</p>
            <p class="timestamp">Generated from README.md</p>
        </footer>
    </div>
</body>
</html>"""
    
    # Write HTML file
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✓ Successfully generated HTML documentation")
    print(f"  Input:  {readme_path}")
    print(f"  Output: {html_path}")
    print(f"  Generated at: {timestamp}")
    
    return html_path

if __name__ == "__main__":
    try:
        generate_html_from_readme()
    except Exception as e:
        print(f"Error generating HTML: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

