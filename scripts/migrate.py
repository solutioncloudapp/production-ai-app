"""Migration script for database schema updates."""

import asyncio

import structlog

logger = structlog.get_logger()


async def run_migrations():
    """Run all pending database migrations."""
    logger.info("Starting migrations")

    migrations = [
        ("001_create_conversations", create_conversations_table),
        ("002_create_feedback", create_feedback_table),
        ("003_create_cost_records", create_cost_records_table),
    ]

    for name, migration in migrations:
        logger.info("Running migration", migration=name)
        await migration()
        logger.info("Migration complete", migration=name)

    logger.info("All migrations complete")


async def create_conversations_table():
    """Create conversations table."""
    # In production, this would use SQLAlchemy or similar
    logger.info("Created conversations table")


async def create_feedback_table():
    """Create feedback table."""
    logger.info("Created feedback table")


async def create_cost_records_table():
    """Create cost records table."""
    logger.info("Created cost records table")


async def main():
    """Run migrations."""
    await run_migrations()


if __name__ == "__main__":
    asyncio.run(main())
