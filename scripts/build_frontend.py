#!/usr/bin/env python3
"""
Enterprise Frontend Build Script
=================================

This script builds and minifies the frontend assets for production.
It creates optimized CSS and JS bundles.

Usage:
    python scripts/build_frontend.py

Output:
    - static/css/design-system/main.min.css
    - static/js/core.min.js
"""

import re
import os
from pathlib import Path
from datetime import datetime


def minify_css(css: str) -> str:
    """
    Minify CSS content by removing comments, whitespace, and redundancies.
    
    Args:
        css: Original CSS content
    
    Returns:
        Minified CSS string
    """
    # Remove CSS comments (/* ... */)
    css = re.sub(r'/\*[\s\S]*?\*/', '', css)
    
    # Remove single-line comments that might exist
    css = re.sub(r'//.*$', '', css, flags=re.MULTILINE)
    
    # Remove unnecessary whitespace
    css = re.sub(r'\s+', ' ', css)
    
    # Remove spaces around selectors and properties
    css = re.sub(r'\s*{\s*', '{', css)
    css = re.sub(r'\s*}\s*', '}', css)
    css = re.sub(r'\s*;\s*', ';', css)
    css = re.sub(r'\s*:\s*', ':', css)
    css = re.sub(r'\s*,\s*', ',', css)
    
    # Remove last semicolon before closing brace
    css = re.sub(r';}', '}', css)
    
    # Remove leading/trailing whitespace
    css = css.strip()
    
    return css


def minify_js(js: str) -> str:
    """
    Minify JavaScript content (basic minification - for production use a proper tool).
    
    Args:
        js: Original JavaScript content
    
    Returns:
        Minified JavaScript string
    """
    # Remove single-line comments (but preserve URLs)
    lines = js.split('\n')
    result = []
    for line in lines:
        # Check if line has a URL (http:// or https://)
        if 'http://' in line or 'https://' in line:
            result.append(line)
        else:
            # Remove single-line comments
            result.append(re.sub(r'//.*$', '', line))
    
    js = '\n'.join(result)
    
    # Remove multi-line comments (/* ... */)
    js = re.sub(r'/\*[\s\S]*?\*/', '', js)
    
    # Remove JSDoc comments (/** ... */)
    js = re.sub(r'/\*\*[\s\S]*?\*/', '', js)
    
    # Collapse multiple newlines
    js = re.sub(r'\n\s*\n', '\n', js)
    
    # Remove leading whitespace from each line but preserve code structure
    lines = js.split('\n')
    result = [line.strip() for line in lines if line.strip()]
    js = '\n'.join(result)
    
    return js


def resolve_css_imports(css_path: Path, base_dir: Path) -> str:
    """
    Resolve @import statements and combine CSS files.
    
    Args:
        css_path: Path to the main CSS file
        base_dir: Base directory for resolving relative paths
    
    Returns:
        Combined CSS content with imports resolved
    """
    content = css_path.read_text(encoding='utf-8')
    
    # Find all @import statements - handle both @import "..." and @import url("...")
    import_pattern = re.compile(r"@import\s+(?:url\s*\(\s*)?['\"]([^'\"]+)['\"](?:\s*\))?\s*;?")
    
    def replace_import(match):
        import_path = match.group(1)
        # Remove leading ./ if present
        import_path = import_path.lstrip('./')
        # Resolve the path relative to the base directory
        full_path = base_dir / import_path
        if full_path.exists():
            print(f"    Importing: {import_path}")
            # Recursively resolve imports in the imported file
            return resolve_css_imports(full_path, full_path.parent)
        else:
            print(f"    Warning: Could not find import {import_path}")
            return f"/* Missing import: {import_path} */"
    
    return import_pattern.sub(replace_import, content)


def build_css():
    """Build and minify the CSS design system."""
    base_dir = Path(__file__).parent.parent
    design_system_dir = base_dir / 'static' / 'css' / 'design-system'
    main_css_path = design_system_dir / 'main.css'
    output_path = design_system_dir / 'main.min.css'
    
    print("Building CSS...")
    print(f"  Source: {main_css_path}")
    
    if not main_css_path.exists():
        print(f"  Error: main.css not found at {main_css_path}")
        return False
    
    # Resolve all imports and combine
    combined_css = resolve_css_imports(main_css_path, design_system_dir)
    
    # Get original size
    original_size = len(combined_css.encode('utf-8'))
    
    # Minify
    minified_css = minify_css(combined_css)
    
    # Add banner
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    banner = f"/* GsmInfinity Enterprise Design System v3.0 | Built: {timestamp} */\n"
    minified_css = banner + minified_css
    
    # Get minified size
    minified_size = len(minified_css.encode('utf-8'))
    
    # Write output
    output_path.write_text(minified_css, encoding='utf-8')
    
    # Calculate savings
    savings = ((original_size - minified_size) / original_size) * 100
    
    print(f"  Output: {output_path}")
    print(f"  Original: {original_size:,} bytes")
    print(f"  Minified: {minified_size:,} bytes")
    print(f"  Savings: {savings:.1f}%")
    
    return True


def build_js():
    """Build and minify the core JavaScript."""
    base_dir = Path(__file__).parent.parent
    js_dir = base_dir / 'static' / 'js'
    core_js_path = js_dir / 'core.js'
    output_path = js_dir / 'core.min.js'
    
    print("\nBuilding JavaScript...")
    print(f"  Source: {core_js_path}")
    
    if not core_js_path.exists():
        print(f"  Error: core.js not found at {core_js_path}")
        return False
    
    # Read original
    original_js = core_js_path.read_text(encoding='utf-8')
    
    # Get original size
    original_size = len(original_js.encode('utf-8'))
    
    # Minify
    minified_js = minify_js(original_js)
    
    # Add banner
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    banner = f"/* GsmInfinity Core JS v3.0 | Built: {timestamp} */\n"
    minified_js = banner + minified_js
    
    # Get minified size
    minified_size = len(minified_js.encode('utf-8'))
    
    # Write output
    output_path.write_text(minified_js, encoding='utf-8')
    
    # Calculate savings
    savings = ((original_size - minified_size) / original_size) * 100
    
    print(f"  Output: {output_path}")
    print(f"  Original: {original_size:,} bytes")
    print(f"  Minified: {minified_size:,} bytes")
    print(f"  Savings: {savings:.1f}%")
    
    return True


def main():
    """Main build function."""
    print("=" * 60)
    print("GSMINFINITY ENTERPRISE FRONTEND BUILD")
    print("=" * 60)
    print()
    
    css_success = build_css()
    js_success = build_js()
    
    print()
    print("=" * 60)
    
    if css_success and js_success:
        print("BUILD SUCCESSFUL")
        print()
        print("To use minified versions in production:")
        print("  1. Update templates/base.html to use:")
        print("     - css/design-system/main.min.css")
        print("     - js/core.min.js")
        print("  2. Or configure Django's STATICFILES_STORAGE for")
        print("     automatic compression")
    else:
        print("BUILD COMPLETED WITH ERRORS")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
