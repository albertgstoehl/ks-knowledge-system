import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Initialize database before each test."""
    await init_db("sqlite+aiosqlite:///:memory:")
    yield


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
