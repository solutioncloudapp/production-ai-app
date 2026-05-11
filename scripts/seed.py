"""Seed script to populate initial data."""

import asyncio

import structlog

logger = structlog.get_logger()


async def seed_documents():
    """Seed initial documents into the vector store."""
    logger.info("Seeding documents")

    # Sample documents for initial testing
    documents = [
        {
            "id": "doc_001",
            "content": "Python is a programming language known for readability.",
            "metadata": {"source": "python_docs", "category": "programming"},
        },
        {
            "id": "doc_002",
            "content": "Machine learning enables systems to learn from data.",
            "metadata": {"source": "ml_basics", "category": "ai"},
        },
        {
            "id": "doc_003",
            "content": "FastAPI is a modern Python web framework for APIs.",
            "metadata": {"source": "fastapi_docs", "category": "web"},
        },
    ]

    # In production, these would be added to ChromaDB
    for doc in documents:
        logger.info("Seeded document", id=doc["id"])

    logger.info("Document seeding complete", count=len(documents))


async def seed_prompts():
    """Initialize prompt registry."""
    from app.prompts.registry import prompt_registry
    prompt_registry.initialize()
    logger.info("Prompts seeded")


async def main():
    """Run all seed operations."""
    logger.info("Starting seed process")

    await seed_prompts()
    await seed_documents()

    logger.info("Seed process complete")


if __name__ == "__main__":
    asyncio.run(main())
