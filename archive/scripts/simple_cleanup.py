#!/usr/bin/env python3
"""
Simple and reliable code cleanup script for OpenCode-Slack project.
"""

from pathlib import Path
import os
import re
import sys

def clean_file(file_path):
    """Clean a single Python file"""
    try:
        with open(file_path, 'r', encoding  = 'utf-8') as f:
            content   =  f.read()

        original_content   =  content
        lines   =  content.split('\n')
        new_lines   =  []

        # Track changes
        changes_made   =  False

        i   =  0
        while i < len(lines):
            line   =  lines[i]
            stripped   =  line.strip()

            # Remove debug print statements
            if (stripped.startswith('print(') and
                any(debug_word in stripped.lower() for debug_word in ['debug', 'test', 'todo', 'fixme'])):
                changes_made   =  True
                i +  =  1
                continue

            if (stripped.startswith('#') and
                any(word in stripped.lower() for word in ['todo', 'fixme', 'xxx', 'hack']) and
                not any(keep_word in stripped.lower() for keep_word in ['implement', 'add', 'fix', 'improve'])):
                changes_made   =  True
                i +  =  1
                continue

            # Fix spacing around operators
            if '  = ' in line and not line.strip().startswith('#'):
                # Fix spacing around = operator
                fixed_line   =  re.sub(r'([^  = !<>])  = ([^  = ])', r'\1   =  \2', line)
                fixed_line   =  re.sub(r'([^  = ])  =  ([^  = ])', r'\1   =  \2', fixed_line)
                if fixed_line ! = line:
                    line   =  fixed_line
                    changes_made   =  True

            # Fix spacing around commas
            if ', ' in line and not line.strip().startswith('#'):
                fixed_line   =  re.sub(r', ([^\s])', r', \1', line)
                if fixed_line ! = line:
                    line   =  fixed_line
                    changes_made   =  True

            # Remove trailing whitespace
            stripped_line   =  line.rstrip()
            if stripped_line ! = line:
                line   =  stripped_line
                changes_made   =  True

            new_lines.append(line)
            i +  =  1

        # Remove multiple consecutive empty lines
        final_lines   =  []
        empty_count   =  0

        for line in new_lines:
            if line.strip() == '':
                empty_count +  =  1
                if empty_count < = 2:  # Allow max 2 consecutive empty lines
                    final_lines.append(line)
            else:
                empty_count   =  0
                final_lines.append(line)

        # Write back if changes were made
        if changes_made:
            new_content   =  '\n'.join(final_lines)
            with open(file_path, 'w', encoding  = 'utf-8') as f:
                f.write(new_content)
            return True

        return False

    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False

def organize_imports(file_path):
    """Organize imports in a Python file"""
    try:
        with open(file_path, 'r', encoding  = 'utf-8') as f:
            content   =  f.read()

        lines   =  content.split('\n')

        # Find import section
        import_start   =  -1
        import_end   =  -1

        for i, line in enumerate(lines):
            stripped   =  line.strip()
            if stripped.startswith(('import ', 'from ')) and import_start == -1:
                import_start   =  i
            elif import_start ! = -1 and not stripped.startswith(('import ', 'from ')) and stripped and not stripped.startswith('#'):
                import_end   =  i
                break

        if import_start == -1:
            return False

        if import_end == -1:
            import_end   =  len(lines)

        # Extract and categorize imports
        import_lines   =  []
        for i in range(import_start, import_end):
            line   =  lines[i].strip()
            if line and not line.startswith('#'):
                import_lines.append(line)

        # Simple categorization
        stdlib_imports   =  []
        third_party_imports   =  []
        local_imports   =  []

        stdlib_modules   =  {
            'os', 'sys', 'json', 'time', 'datetime', 'logging', 'threading', 'asyncio',
            'pathlib', 'sqlite3', 'tempfile', 'unittest', 'argparse', 'subprocess',
            'signal', 'collections', 'functools', 'itertools', 'typing', 'concurrent',
            'urllib', 'http', 'socket', 'ssl', 'hashlib', 'hmac', 'base64', 'uuid',
            'random', 'statistics', 'math', 're', 'shlex', 'copy', 'pickle'
        }

        for line in import_lines:
            if line.startswith('from '):
                module   =  line.split()[1].split('.')[0]
            else:
                module   =  line.split()[1].split('.')[0]

            if module in stdlib_modules:
                stdlib_imports.append(line)
            elif module.startswith('src.') or line.startswith('from .'):
                local_imports.append(line)
            else:
                third_party_imports.append(line)

        # Sort imports
        stdlib_imports.sort()
        third_party_imports.sort()
        local_imports.sort()

        # Rebuild import section
        new_imports   =  []
        if stdlib_imports:
            new_imports.extend(stdlib_imports)
            new_imports.append('')
        if third_party_imports:
            new_imports.extend(third_party_imports)
            new_imports.append('')
        if local_imports:
            new_imports.extend(local_imports)

        # Remove trailing empty line
        while new_imports and new_imports[-1] == '':
            new_imports.pop()

        # Reconstruct file
        new_content   =  '\n'.join(lines[:import_start] + new_imports + [''] + lines[import_end:])

        if new_content ! = content:
            with open(file_path, 'w', encoding  = 'utf-8') as f:
                f.write(new_content)
            return True

        return False

    except Exception as e:
        print(f"Error organizing imports in {file_path}: {e}")
        return False

def main():
    """Main cleanup function"""
    project_root   =  "/home/eladbenhaim/dev/stanley-opensource/opencode-slack"

    print("🧹 Starting simple code cleanup...")

    # Find all Python files
    python_files   =  []
    for root, dirs, files in os.walk(project_root):
        # Skip certain directories
        dirs[:]   =  [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"Found {len(python_files)} Python files")

    files_cleaned   =  0
    imports_organized   =  0

    for file_path in python_files:
        print(f"Processing {file_path}")

        # Clean the file
        if clean_file(file_path):
            files_cleaned +  =  1

        # Organize imports
        if organize_imports(file_path):
            imports_organized +  =  1

    print(f"\n✅ Cleanup completed!")
    print(f"Files cleaned: {files_cleaned}")
    print(f"Import sections organized: {imports_organized}")

if __name__ == "__main__":
    main()