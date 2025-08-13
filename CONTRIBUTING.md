# Contributing to OpenCode Async Agents

## Development Process

- Sign commits with DCO (`-s` flag): `git commit -s -m "message"`
- Run lint/tests before PR; add/refresh unit tests
- No secrets or proprietary data in issues/PRs
- Semantic Versioning; maintainers cut releases

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `pytest tests/`
6. Run linting: `python -m flake8 src/`
7. Commit with DCO: `git commit -s -m "Add new feature"`
8. Push and create a pull request

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for public functions
- Keep functions focused and small
- Use meaningful variable names

## Testing

- Write unit tests for new functionality
- Include integration tests for complex features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

## Pull Request Process

1. Update documentation if needed
2. Add entry to CHANGELOG.md
3. Ensure CI passes
4. Request review from maintainers
5. Address feedback promptly

## Code of Conduct

This project follows the Contributor Covenant. Be respectful and inclusive.

## Questions?

Feel free to open an issue for questions or reach out to maintainers.