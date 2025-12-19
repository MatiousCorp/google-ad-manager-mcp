# Contributing to GAM MCP Server

Thank you for your interest in contributing to the Google Ad Manager MCP Server! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/MatiousCorp/google-ad-manager-mcp/issues) to avoid duplicates
2. Create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the use case and proposed solution
3. Be open to discussion and alternative approaches

### Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following the code style guidelines
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit with clear, descriptive messages
7. Push to your fork and open a Pull Request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/google-ad-manager-mcp.git
cd google-ad-manager-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Or with uv
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Running the Server Locally

```bash
export GAM_CREDENTIALS_PATH=/path/to/credentials.json
export GAM_NETWORK_CODE=your_network_code
gam-mcp
```

## Code Style Guidelines

### General

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose

### Formatting

We recommend using:
- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Line length: 88 characters (Black default)

### Naming Conventions

- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Documentation

- Update README.md if adding new tools or features
- Include docstrings with Args, Returns, and example usage where helpful
- Update CHANGELOG.md for user-facing changes

## Adding New Tools

When adding a new MCP tool:

1. Create or update the appropriate file in `src/gam_mcp/tools/`
2. Register the tool in `src/gam_mcp/server.py`
3. Add comprehensive error handling
4. Use parameterized queries (bind variables) for GAM API calls
5. Return structured dict responses
6. Add tests for the new tool
7. Document the tool in README.md

### Tool Template

```python
@mcp.tool()
def your_new_tool(param1: str, param2: int = 10) -> dict:
    """
    Brief description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        dict with keys:
            - key1: description
            - key2: description
    """
    client = get_client()

    # Implementation

    return {
        "key1": value1,
        "key2": value2,
    }
```

## Security

- Never commit credentials or secrets
- Use environment variables for configuration
- Validate all user inputs
- Use parameterized queries to prevent injection attacks
- Report security vulnerabilities privately to youssef@matious.com

## Pull Request Process

1. Update documentation for any changed functionality
2. Add or update tests as needed
3. Ensure CI passes (when available)
4. Request review from maintainers
5. Address feedback promptly
6. Squash commits if requested

## Questions?

Feel free to open an issue for any questions about contributing.

Thank you for helping improve GAM MCP Server!
