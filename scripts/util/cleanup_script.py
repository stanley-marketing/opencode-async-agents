#!/usr/bin/env python3
"""
Comprehensive code cleanup script for OpenCode-Slack project.
Performs systematic cleanup and standardization of all Python files.
"""

from pathlib import Path
from typing import List, Set, Dict, Tuple
import os
import re
import subprocess
import sys

import ast

class CodeCleanupTool:
    """Tool for comprehensive Python code cleanup and standardization"""

    def __init__(self, project_root: str):
        self.project_root     =   Path(project_root)
        self.python_files     =   []
        self.cleanup_stats     =   {
            'files_processed': 0,
            'unused_imports_removed': 0,
            'dead_code_removed': 0,
            'comments_cleaned': 0,
            'docstrings_added': 0,
            'formatting_fixes': 0
        }

    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project"""
        python_files     =   []
        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[: ]     =   [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        self.python_files     =   python_files
        return python_files

    def analyze_file_imports(self, file_path: Path) -> Tuple[List[str], Set[str]]:
        """Analyze imports and used names in a file"""
        try:
            with open(file_path, 'r', encoding    =  'utf-8') as f:
                content     =   f.read()

            tree     =   ast.parse(content)

            # Collect all imports
            imports     =   []
            imported_names     =   set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_name     =   alias.asname if alias.asname else alias.name
                        imports.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
                        imported_names.add(import_name.split('.')[0])

                elif isinstance(node, ast.ImportFrom):
                    module     =   node.module or ''
                    for alias in node.names:
                        import_name     =   alias.asname if alias.asname else alias.name
                        imports.append(f"from {module} import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
                        imported_names.add(import_name)

            # Collect all used names
            used_names     =   set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    # For attribute access like os.path, we care about 'os'
                    if isinstance(node.value, ast.Name):
                        used_names.add(node.value.id)

            return imports, imported_names, used_names

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return [], set(), set()

    def clean_imports(self, file_path: Path) -> str:
        """Clean and organize imports in a file"""
        try:
            with open(file_path, 'r', encoding    =  'utf-8') as f:
                content     =   f.read()

            lines     =   content.split('\n')

            # Find import section
            import_start     =   -1
            import_end     =   -1

            for i, line in enumerate(lines):
                stripped     =   line.strip()
                if stripped.startswith(('import ', 'from ')) and import_start == -1:
                    import_start     =   i
                elif import_start ! = -1 and not stripped.startswith(('import ', 'from ')) and stripped and not stripped.startswith('#'):
                    import_end     =   i
                    break

            if import_start == -1:
                return content

            if import_end == -1:
                import_end     =   len(lines)

            # Extract imports
            import_lines     =   lines[import_start: import_end]

            # Categorize imports
            stdlib_imports     =   []
            third_party_imports     =   []
            local_imports     =   []

            stdlib_modules     =   {
                'os', 'sys', 'json', 'time', 'datetime', 'logging', 'threading', 'asyncio',
                'pathlib', 'sqlite3', 'tempfile', 'unittest', 'argparse', 'subprocess',
                'signal', 'collections', 'functools', 'itertools', 'typing', 'concurrent',
                'urllib', 'http', 'socket', 'ssl', 'hashlib', 'hmac', 'base64', 'uuid',
                'random', 'statistics', 'math', 're', 'shlex', 'copy', 'pickle'
            }

            for line in import_lines:
                stripped     =   line.strip()
                if not stripped or stripped.startswith('#'):
                    continue

                # Determine import type
                if stripped.startswith('from '):
                    module     =   stripped.split()[1].split('.')[0]
                else:
                    module     =   stripped.split()[1].split('.')[0]

                if module in stdlib_modules:
                    stdlib_imports.append(stripped)
                elif module.startswith('src.') or module.startswith('.'):
                    local_imports.append(stripped)
                else:
                    third_party_imports.append(stripped)

            # Sort imports within each category
            stdlib_imports.sort()
            third_party_imports.sort()
            local_imports.sort()

            # Rebuild import section
            new_imports     =   []
            if stdlib_imports:
                new_imports.extend(stdlib_imports)
                new_imports.append('')
            if third_party_imports:
                new_imports.extend(third_party_imports)
                new_imports.append('')
            if local_imports:
                new_imports.extend(local_imports)
                new_imports.append('')

            # Remove trailing empty line
            if new_imports and new_imports[-1] == '':
                new_imports.pop()

            # Reconstruct file
            new_content     =   '\n'.join(lines[: import_start] + new_imports + lines[import_end: ])

            return new_content

        except Exception as e:
            print(f"Error cleaning imports in {file_path}: {e}")
            return content

    def remove_unused_imports(self, file_path: Path) -> str:
        """Remove unused imports from a file"""
        try:
            with open(file_path, 'r', encoding    =  'utf-8') as f:
                content     =   f.read()

            # Parse the file
            tree     =   ast.parse(content)

            # Collect imports and their line numbers
            imports_info     =   []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports_info.append((node.lineno, node))

            # Collect all used names
            used_names     =   set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        used_names.add(node.value.id)

            # Determine which imports to keep
            lines     =   content.split('\n')
            lines_to_remove     =   set()

            for line_no, import_node in imports_info:
                should_remove     =   True

                if isinstance(import_node, ast.Import):
                    for alias in import_node.names:
                        name     =   alias.asname if alias.asname else alias.name.split('.')[0]
                        if name in used_names:
                            should_remove     =   False
                            break
                elif isinstance(import_node, ast.ImportFrom):
                    for alias in import_node.names:
                        name     =   alias.asname if alias.asname else alias.name
                        if name in used_names or alias.name == '*':
                            should_remove     =   False
                            break

                # Keep imports that might be used in special ways
                line_content     =   lines[line_no - 1].strip()
                if any(keyword in line_content.lower() for keyword in ['optional', 'try: ', 'except', 'import']):
                    should_remove     =   False

                if should_remove:
                    lines_to_remove.add(line_no - 1)
                    self.cleanup_stats['unused_imports_removed'] +    =   1

            # Remove unused import lines
            new_lines     =   [line for i, line in enumerate(lines) if i not in lines_to_remove]

            return '\n'.join(new_lines)

        except Exception as e:
            print(f"Error removing unused imports in {file_path}: {e}")
            return content

    def clean_dead_code(self, content: str) -> str:
        """Remove dead code and commented-out code blocks"""
        lines     =   content.split('\n')
        new_lines     =   []

        i     =   0
        while i < len(lines):
            line     =   lines[i]
            stripped     =   line.strip()

            # Remove commented-out code blocks (multiple consecutive commented lines that look like code)
            if stripped.startswith('#') and len(stripped) > 1:
                # Check if this looks like commented-out code
                uncommented     =   stripped[1: ].strip()
                if (uncommented.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try: ', 'except', 'import ', 'from ')) or
                    '    =  ' in uncommented or uncommented.endswith(': ')):

                    # Look ahead to see if this is a block of commented code
                    j     =   i + 1
                    consecutive_commented_code     =   1
                    while j < len(lines) and lines[j].strip().startswith('#'):
                        next_uncommented     =   lines[j].strip()[1: ].strip()
                        if (next_uncommented and
                            (next_uncommented.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try: ', 'except', 'import ', 'from ')) or
                             '    =  ' in next_uncommented or next_uncommented.endswith(': ') or
                             next_uncommented.startswith(('print(', 'return ', 'pass', 'break', 'continue')))):
                            consecutive_commented_code +    =   1
                            j +    =   1
                        else:
                            break

                    # If we found multiple lines of commented code, skip them
                    if consecutive_commented_code >   =  3:
                        print(f"Removing {consecutive_commented_code} lines of commented-out code starting at line {i+1}")
                        i     =   j
                        self.cleanup_stats['dead_code_removed'] +    =   consecutive_commented_code
                        continue

            # Remove debug print statements
            if (stripped.startswith('print(') and
                any(debug_word in stripped.lower() for debug_word in ['debug', 'test', 'todo', 'fixme', 'xxx'])):
                self.cleanup_stats['dead_code_removed'] +    =   1
                i +    =   1
                continue

            if stripped.startswith('#') and any(word in stripped.lower() for word in ['todo', 'fixme', 'xxx', 'hack']):
                if not any(keep_word in stripped.lower() for keep_word in ['implement', 'add', 'fix', 'improve', 'optimize']):
                    self.cleanup_stats['dead_code_removed'] +    =   1
                    i +    =   1
                    continue

            new_lines.append(line)
            i +    =   1

        return '\n'.join(new_lines)

    def standardize_formatting(self, content: str) -> str:
        """Standardize code formatting"""
        lines     =   content.split('\n')
        new_lines     =   []

        for line in lines:
            # Fix common formatting issues

            # Standardize spacing around operators
            line     =   re.sub(r'([^    =  !<>])    =  ([^    =  ])', r'\1     =   \2', line)
            line     =   re.sub(r'([^    =  ])    =   ([^    =  ])', r'\1     =   \2', line)

            # Fix spacing around commas
            line     =   re.sub(r', ([^\s])', r', \1', line)

            # Fix spacing around colons in dictionaries
            line     =   re.sub(r': ([^\s])', r': \1', line)

            # Remove trailing whitespace
            line     =   line.rstrip()

            new_lines.append(line)

        # Remove multiple consecutive empty lines
        final_lines     =   []
        empty_count     =   0

        for line in new_lines:
            if line.strip() == '':
                empty_count +    =   1
                if empty_count <   =  2:  # Allow max 2 consecutive empty lines
                    final_lines.append(line)
            else:
                empty_count     =   0
                final_lines.append(line)

        return '\n'.join(final_lines)

    def add_missing_docstrings(self, content: str) -> str:
        """Add missing docstrings to functions and classes"""
        try:
            tree     =   ast.parse(content)
            lines     =   content.split('\n')

            # Find functions and classes without docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    # Check if it already has a docstring
                    has_docstring     =   (node.body and
                                   isinstance(node.body[0], ast.Expr) and
                                   isinstance(node.body[0].value, ast.Str))

                    if not has_docstring and node.lineno > 0:
                        # Add a basic docstring
                        indent     =   len(lines[node.lineno - 1]) - len(lines[node.lineno - 1].lstrip())
                        docstring_indent     =   ' ' * (indent + 4)

                        if isinstance(node, ast.ClassDef):
                            docstring     =   f'{docstring_indent}"""Class for {node.name}."""'
                        else:
                            docstring     =   f'{docstring_indent}"""Function {node.name}."""'

                        # Insert docstring after the function/class definition
                        lines.insert(node.lineno, docstring)
                        self.cleanup_stats['docstrings_added'] +    =   1

            return '\n'.join(lines)

        except Exception as e:
            print(f"Error adding docstrings: {e}")
            return content

    def clean_file(self, file_path: Path) -> bool:
        """Clean a single Python file"""
        try:
            print(f"Cleaning {file_path}")

            # Read original content
            with open(file_path, 'r', encoding    =  'utf-8') as f:
                original_content     =   f.read()

            # Apply cleanup steps
            content     =   original_content

            # 1. Remove unused imports
            content     =   self.remove_unused_imports(file_path)

            # 2. Clean and organize imports
            content     =   self.clean_imports(file_path)

            # 3. Remove dead code
            content     =   self.clean_dead_code(content)

            # 4. Standardize formatting
            content     =   self.standardize_formatting(content)

            # 5. Add missing docstrings (only for files that don't have many)
            if content.count('"""') < 5:  # Don't add to files that already have many docstrings
                content     =   self.add_missing_docstrings(content)

            # Write cleaned content back
            if content !   =  original_content:
                with open(file_path, 'w', encoding    =  'utf-8') as f:
                    f.write(content)
                self.cleanup_stats['files_processed'] +    =   1
                self.cleanup_stats['formatting_fixes'] +    =   1
                return True

            return False

        except Exception as e:
            print(f"Error cleaning {file_path}: {e}")
            return False

    def run_cleanup(self):
        """Run the complete cleanup process"""
        print("🧹 Starting comprehensive code cleanup...")

        # Find all Python files
        python_files     =   self.find_python_files()
        print(f"Found {len(python_files)} Python files to clean")

        # Clean each file
        for file_path in python_files:
            try:
                self.clean_file(file_path)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        # Print summary
        print("\n✅ Cleanup completed!")
        print("📊 Cleanup Statistics: ")
        for key, value in self.cleanup_stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")

def main():
    """Main function"""
    project_root     =   "/home/eladbenhaim/dev/stanley-opensource/opencode-slack"

    cleaner     =   CodeCleanupTool(project_root)
    cleaner.run_cleanup()

if __name__ == "__main__":
    main()