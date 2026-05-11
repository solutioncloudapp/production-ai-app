# Code Style Rules

## Python Style

- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- Use `UPPER_CASE` for constants
- Maximum line length: 120 characters
- Use type hints for all function signatures
- Use Pydantic models for data validation

## Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

Each group should be separated by a blank line and sorted alphabetically.

## Docstrings

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Short description of the function.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.
    """
```

## Error Handling

- Use specific exception types
- Never use bare `except:`
- Log exceptions with context
- Return meaningful error messages

## Testing

- Test files should mirror source file structure
- Use descriptive test function names: `test_<function>_<scenario>`
- Mock external dependencies
- Test both success and failure cases
