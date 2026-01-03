import pytest
import asyncio
from src import database
import os
import tempfile

# Initialize database immediately when conftest is imported (before test collection)
# Use a temporary file to ensure proper permissions
test_db = os.path.join(tempfile.gettempdir(), "test_session_bookmarks.db")
if os.path.exists(test_db):
    os.remove(test_db)

# Run async init synchronously
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(database.init_db(f"sqlite+aiosqlite:///{test_db}"))

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    """Cleanup test database after all tests"""
    yield

    # Cleanup
    async def cleanup():
        if database.engine:
            await database.engine.dispose()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cleanup())

    if os.path.exists(test_db):
        os.remove(test_db)
