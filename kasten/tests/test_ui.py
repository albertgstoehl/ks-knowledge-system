# kasten/tests/test_ui.py
import pytest
import subprocess
import time
import tempfile
import os
import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_db

# Playwright tests require playwright to be installed
try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


async def setup_test_env():
    """Initialize database and create temp dir with test notes."""
    await init_db("sqlite+aiosqlite:///:memory:")
    tmpdir = tempfile.mkdtemp()
    with open(os.path.join(tmpdir, "1219a.md"), "w") as f:
        f.write("Note A title\n\nLinks to [[1219b]]")
    with open(os.path.join(tmpdir, "1219b.md"), "w") as f:
        f.write("Note B title\n\nNo outgoing links")
    os.environ["NOTES_PATH"] = tmpdir
    return tmpdir


@pytest.mark.asyncio
async def test_note_view_with_source():
    """Test note view includes source in template context"""
    await setup_test_env()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/reindex")
        response = await client.get("/note/1219a")
        assert response.status_code == 200
        # Source will be None for existing notes, but page should render
        assert b"note-content" in response.content


@pytest.fixture(scope="module")
def server():
    """Start the server for testing"""
    tmpdir = tempfile.mkdtemp()
    # Create test notes
    with open(os.path.join(tmpdir, "1219a.md"), "w") as f:
        f.write("Test Note A\n\nLinks to [[1219b]]")
    with open(os.path.join(tmpdir, "1219b.md"), "w") as f:
        f.write("Test Note B\n\nNo links")

    os.environ["NOTES_PATH"] = tmpdir
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    proc = subprocess.Popen(
        ["uvicorn", "src.main:app", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    yield "http://localhost:8765"
    proc.terminate()
    proc.wait()

@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_landing_page(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(server)
        title = await page.title()
        assert "Kasten" in title

        # Check feeling lucky button exists
        lucky = page.locator('a:has-text("Feeling Lucky")')
        assert await lucky.is_visible()

        await browser.close()

@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_note_navigation(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Reindex first
        await page.goto(f"{server}/api/reindex", wait_until="networkidle")

        # Go to note
        await page.goto(f"{server}/note/1219a")

        # Check content visible
        content = page.locator(".note-content")
        assert await content.is_visible()

        # Check graph visible
        graph = page.locator("#note-graph")
        assert await graph.is_visible()

        await browser.close()

@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_graph_click_navigation(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(f"{server}/api/reindex", wait_until="networkidle")
        await page.goto(f"{server}/note/1219a")

        # Click on a graph node (forward link)
        circles = page.locator("#note-graph circle[fill='#fff']")
        if await circles.count() > 0:
            await circles.first.click()
            await page.wait_for_url("**/note/**")

        await browser.close()
