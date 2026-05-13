# Contributing to Spotify Playlist Downloader

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Features

Feature requests are welcome! Please:
- Check existing issues first
- Describe the feature and its use case
- Explain why it would be valuable
- Consider implementation complexity

### Submitting Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/spotify-playlist-downloader.git
   cd spotify-playlist-downloader
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the code style guidelines
   - Add tests for new functionality
   - Update documentation as needed

4. **Test your changes**
   ```bash
   # Run tests
   pytest tests/
   
   # Check code style
   black src/
   flake8 src/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## 📝 Code Style Guidelines

### Python Style

We follow PEP 8 with some modifications:

- **Line length**: 100 characters (not 79)
- **Imports**: Group by standard library, third-party, local
- **Type hints**: Use for function signatures
- **Docstrings**: Google style for all public functions/classes

Example:
```python
from typing import List, Optional

def download_track(
    track_id: str,
    output_dir: str,
    quality: int = 320
) -> Optional[str]:
    """Download a single track from Spotify.
    
    Args:
        track_id: Spotify track ID
        output_dir: Directory to save the file
        quality: Audio quality in kbps (default: 320)
        
    Returns:
        Path to downloaded file, or None if failed
        
    Raises:
        ValueError: If track_id is invalid
        IOError: If output_dir is not writable
    """
    pass
```

### Architecture Principles

This project follows **Feature-Sliced Design (FSD)**:

```
src/
├── app/           # Application initialization
├── features/      # Business features (download, metadata, spotify)
├── shared/        # Shared utilities and UI components
└── widgets/       # Complex UI components
```

**Key principles:**
- Each feature is self-contained
- Dependencies flow downward (features → shared)
- Use dependency injection for loose coupling
- Separate domain logic from infrastructure

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add FLAC format support
fix: resolve YouTube matching timeout issue
docs: update installation instructions
refactor: improve error handling in downloader
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_downloader.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_download_track_with_invalid_id`
- Use fixtures for common setup
- Mock external dependencies (Spotify API, YouTube)

Example:
```python
import pytest
from unittest.mock import Mock, patch

def test_download_track_success(tmp_path):
    """Test successful track download."""
    # Arrange
    downloader = Downloader(output_dir=str(tmp_path))
    track_id = "test123"
    
    # Act
    result = downloader.download(track_id)
    
    # Assert
    assert result is not None
    assert result.exists()
```

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use type hints for better IDE support
- Include examples in docstrings for complex functions

### README Updates

When adding features:
- Update the Features section
- Add usage examples
- Update command-line options table
- Add troubleshooting tips if needed

## 🔍 Code Review Process

Pull requests will be reviewed for:

1. **Functionality** - Does it work as intended?
2. **Code Quality** - Is it clean, readable, maintainable?
3. **Tests** - Are there adequate tests?
4. **Documentation** - Is it properly documented?
5. **Architecture** - Does it fit the project structure?

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass and coverage is maintained
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Commit messages follow conventions
- [ ] No merge conflicts

## 🐛 Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

1. **Import errors** - Check your Python path and virtual environment
2. **Test failures** - Ensure all dependencies are installed
3. **Linting errors** - Run `black` and `flake8` before committing

## 📞 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an Issue with the bug template
- **Features**: Create an Issue with the feature template
- **Chat**: Join our community (if available)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Every contribution, no matter how small, is valuable. Thank you for helping make this project better!

---

**Happy Coding! 🎵**