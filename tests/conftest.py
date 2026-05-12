import os

import pytest

# Set environment variables BEFORE importing any app modules
os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-testing-only"
os.environ["OPENAI_MODEL"] = "gpt-4o"
os.environ["OPENAI_EMBEDDING_MODEL"] = "text-embedding-3-small"
os.environ["DATABASE_URL"] = "postgresql://mock:mock@localhost/mock"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["CHROMA_HOST"] = "localhost"
os.environ["CHROMA_PORT"] = "8001"
os.environ["ALLOWED_ORIGINS"] = '["http://localhost:3000"]'
os.environ["ENVIRONMENT"] = "development"
# Force empty API keys for test mode - override any CI secrets
os.environ["API_SECRET_KEY"] = ""
os.environ["API_SECONDARY_KEY"] = ""


@pytest.fixture(autouse=True)
def initialize_prompts():
    """Initialize prompt registry for all tests."""
    from app.prompts.registry import prompt_registry

    if not prompt_registry._templates:
        prompt_registry.initialize()
    yield
