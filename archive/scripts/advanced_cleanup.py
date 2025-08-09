#!/usr/bin/env python3
"""
Advanced cleanup script for removing unused imports and adding docstrings.
"""

import ast
import os
import sys
from pathlib import Path

def find_unused_imports(file_path):
    """Find unused imports in a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Collect all imports
        imports = {}
        import_lines = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split('.')[0]
                    imports[name] = alias.name
                    import_lines[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = f"{module}.{alias.name}"
                    import_lines[name] = node.lineno
        
        # Collect all used names
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)
        
        # Find unused imports
        unused_imports = []
        for name in imports:
            if name not in used_names and name != '*':
                unused_imports.append((name, import_lines[name]))
        
        return unused_imports
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return []

def remove_unused_imports(file_path):
    """Remove unused imports from a file"""
    try:
        unused_imports = find_unused_imports(file_path)
        if not unused_imports:
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Sort by line number in reverse order to avoid index issues
        unused_imports.sort(key=lambda x: x[1], reverse=True)
        
        removed_count = 0
        for name, line_no in unused_imports:
            # Check if the line actually contains an import
            if line_no <= len(lines):
                line = lines[line_no - 1].strip()
                if ('import ' in line and (name in line or name.split('.')[0] in line)):
                    print(f"  Removing unused import: {line}")
                    lines.pop(line_no - 1)
                    removed_count += 1
        
        if removed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error removing unused imports from {file_path}: {e}")
        return False

def add_missing_docstrings(file_path):
    """Add basic docstrings to functions and classes that don't have them"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        lines = content.split('\n')
        
        # Find functions and classes without docstrings
        additions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                # Check if it already has a docstring
                has_docstring = (node.body and 
                               isinstance(node.body[0], ast.Expr) and 
                               isinstance(node.body[0].value, (ast.Str, ast.Constant)))
                
                if not has_docstring and node.lineno > 0:
                    # Calculate indentation
                    line_content = lines[node.lineno - 1]
                    indent = len(line_content) - len(line_content.lstrip())
                    docstring_indent = ' ' * (indent + 4)
                    
                    if isinstance(node, ast.ClassDef):
                        docstring = f'{docstring_indent}"""Class for {node.name}."""'
                    else:
                        docstring = f'{docstring_indent}"""Function {node.name}."""'
                    
                    additions.append((node.lineno, docstring))
        
        # Add docstrings (in reverse order to maintain line numbers)
        if additions:
            additions.sort(reverse=True)
            for line_no, docstring in additions:
                lines.insert(line_no, docstring)
                print(f"  Added docstring to {file_path} at line {line_no}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return True
        
        return False
        
    except Exception as e:
        print(f"Error adding docstrings to {file_path}: {e}")
        return False

def main():
    """Main function"""
    project_root = "/home/eladbenhaim/dev/stanley-opensource/opencode-slack"
    
    print("🔧 Starting advanced cleanup...")
    
    # Find all Python files in src/ directory (focus on main source code)
    python_files = []
    src_dir = os.path.join(project_root, "src")
    
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files in src/")
    
    unused_imports_removed = 0
    docstrings_added = 0
    
    for file_path in python_files:
        print(f"Processing {file_path}")
        
        # Remove unused imports
        if remove_unused_imports(file_path):
            unused_imports_removed += 1
        
        # Add missing docstrings (only for smaller files to avoid clutter)
        try:
            with open(file_path, 'r') as f:
                line_count = len(f.readlines())
            
            if line_count < 200:  # Only add to smaller files
                if add_missing_docstrings(file_path):
                    docstrings_added += 1
        except:
            pass
    
    print(f"\n✅ Advanced cleanup completed!")
    print(f"Files with unused imports removed: {unused_imports_removed}")
    print(f"Files with docstrings added: {docstrings_added}")

if __name__ == "__main__":
    main()