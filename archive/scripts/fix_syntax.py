#!/usr/bin/env python3
"""
Fix syntax errors introduced during cleanup.
"""

import ast
import os
import sys
from pathlib import Path

def check_and_fix_syntax(file_path):
    """Check and fix basic syntax errors in a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file
        try:
            ast.parse(content)
            return False  # No syntax errors
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            
            # Common fixes
            lines = content.split('\n')
            fixed = False
            
            # Fix common spacing issues around operators
            for i, line in enumerate(lines):
                original_line = line
                
                # Fix spaced operators that were incorrectly modified
                line = line.replace(' ! = ', ' != ')
                line = line.replace(' = = ', ' == ')
                line = line.replace(' < = ', ' <= ')
                line = line.replace(' > = ', ' >= ')
                line = line.replace(' + = ', ' += ')
                line = line.replace(' - = ', ' -= ')
                line = line.replace(' * = ', ' *= ')
                line = line.replace(' / = ', ' /= ')
                
                # Fix function calls that got broken
                line = line.replace('( ', '(')
                line = line.replace(' )', ')')
                
                if line != original_line:
                    lines[i] = line
                    fixed = True
            
            if fixed:
                new_content = '\n'.join(lines)
                
                # Test if the fix worked
                try:
                    ast.parse(new_content)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"  Fixed syntax errors in {file_path}")
                    return True
                except SyntaxError:
                    print(f"  Could not automatically fix {file_path}")
                    return False
            
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function"""
    project_root = "/home/eladbenhaim/dev/stanley-opensource/opencode-slack"
    
    print("🔧 Fixing syntax errors...")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip certain directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Checking {len(python_files)} Python files for syntax errors...")
    
    files_fixed = 0
    files_with_errors = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                ast.parse(content)
            except SyntaxError:
                files_with_errors += 1
                if check_and_fix_syntax(file_path):
                    files_fixed += 1
                    
        except Exception as e:
            print(f"Error checking {file_path}: {e}")
    
    print(f"\n✅ Syntax check completed!")
    print(f"Files with syntax errors: {files_with_errors}")
    print(f"Files fixed: {files_fixed}")

if __name__ == "__main__":
    main()