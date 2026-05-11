# Testing Rules

## Test Structure

- Place tests in `tests/` directory
- Mirror source file structure in test files
- Use `test_<module>.py` naming convention

## Test Types

### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Fast execution (< 1 second per test)

### Integration Tests
- Test component interactions
- Use test databases and services
- Slower execution acceptable

### End-to-End Tests
- Test full request flows
- Use the FastAPI test client
- Slowest execution, use sparingly

## Test Patterns

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_function_happy_path():
    # Arrange
    mock_service = AsyncMock()
    mock_service.return_value = expected_result

    # Act
    result = await function_under_test(mock_service)

    # Assert
    assert result == expected_result
    mock_service.assert_called_once()

@pytest.mark.asyncio
async def test_function_error_case():
    # Arrange
    mock_service = AsyncMock()
    mock_service.side_effect = ValueError("test error")

    # Act & Assert
    with pytest.raises(ValueError, match="test error"):
        await function_under_test(mock_service)
```

## Fixtures

Use pytest fixtures for common setup:

```python
@pytest.fixture
def mock_llm():
    return AsyncMock()

@pytest.fixture
def sample_query():
    return "What is the capital of France?"
```

## Coverage

- Aim for > 80% code coverage
- Run with: `pytest --cov=app --cov-report=html`
- Critical paths must have 100% coverage

## CI Integration

Tests run automatically on:
- Pull requests
- Merges to main branch
- Scheduled nightly runs
