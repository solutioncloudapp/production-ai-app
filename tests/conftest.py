import os

import pytest


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing."""
    os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-testing-only"
    os.environ["OPENAI_MODEL"] = "gpt-4o"
    os.environ["OPENAI_EMBEDDING_MODEL"] = "text-embedding-3-small"
    os.environ["DATABASE_URL"] = "postgresql://mock:mock@localhost/mock"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["CHROMA_HOST"] = "localhost"
    os.environ["CHROMA_PORT"] = "8001"
    os.environ["ALLOWED_ORIGINS"] = '["http://localhost:3000"]'
    yield
    # Clean up might not be necessary if using pytest-env, but we do it manually if needed.
