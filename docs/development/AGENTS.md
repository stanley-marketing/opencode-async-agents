# AGENTS.md - Development Guidelines

## Build/Test Commands
- **Run all tests**: `python3 -m pytest`
- **Run single test**: `python3 -m pytest tests/test_filename.py::TestClass::test_method`
- **Run tests with coverage**: `python3 -m pytest --cov=src`
- **Install dependencies**: `pip install -r requirements.txt`
- **Start server**: `python3 src/server.py` or `python3 src/main.py`

## Code Style Guidelines
- **Python version**: Use Python 3.x
- **Imports**: Use absolute imports from `src.` modules, group standard/third-party/local imports
- **Type hints**: Use typing annotations for function parameters and return types
- **Docstrings**: Use triple-quoted docstrings for modules, classes, and functions
- **Logging**: Use `logging.getLogger(__name__)` pattern, import logger at module level
- **Error handling**: Use try/except blocks with specific exception types
- **Naming**: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **File structure**: Follow existing patterns - tests in `tests/`, source in `src/` with submodules
- **Optional imports**: Use try/except for optional dependencies with fallback behavior
- **Path handling**: Use `pathlib.Path` for file operations
- **Testing**: Use pytest with unittest.TestCase, mock external dependencies
- **Comments**: Minimal inline comments, focus on clear code and docstrings