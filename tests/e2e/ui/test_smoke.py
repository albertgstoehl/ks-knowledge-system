"""
Basic UI smoke tests for all services in the knowledge system.

Tests:
- Homepage loads successfully (200 status)
- No JavaScript console errors
- Basic page elements present
"""

import pytest
from playwright.sync_api import Page, expect


class TestBalanceUI:
    """Smoke tests for Balance service UI."""

    def test_homepage_loads(self, page: Page, balance_url: str):
        """Test that Balance homepage loads successfully."""
        page.goto(balance_url)
        # Title includes current view (e.g., "Balance - Timer")
        import re
        expect(page).to_have_title(re.compile(r"^Balance"))
        
    def test_no_console_errors(self, page: Page, balance_url: str):
        """Test that Balance has no JavaScript console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(balance_url)
        page.wait_for_load_state("networkidle")
        assert len(errors) == 0, f"Console errors found: {[e.text for e in errors]}"


class TestBookmarkManagerUI:
    """Smoke tests for Bookmark Manager service UI."""

    def test_homepage_loads(self, page: Page, bookmark_manager_url: str):
        """Test that Bookmark Manager homepage loads successfully."""
        page.goto(bookmark_manager_url)
        # Should have bookmarks or inbox view
        expect(page.locator("body")).to_be_visible()
        
    def test_no_console_errors(self, page: Page, bookmark_manager_url: str):
        """Test that Bookmark Manager has no JavaScript console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(bookmark_manager_url)
        page.wait_for_load_state("networkidle")
        assert len(errors) == 0, f"Console errors found: {[e.text for e in errors]}"


class TestCanvasUI:
    """Smoke tests for Canvas service UI."""

    def test_homepage_loads(self, page: Page, canvas_url: str):
        """Test that Canvas homepage loads successfully."""
        page.goto(canvas_url)
        # Canvas should have main content area
        expect(page.locator("body")).to_be_visible()
        
    def test_no_console_errors(self, page: Page, canvas_url: str):
        """Test that Canvas has no JavaScript console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(canvas_url)
        page.wait_for_load_state("networkidle")
        assert len(errors) == 0, f"Console errors found: {[e.text for e in errors]}"


class TestKastenUI:
    """Smoke tests for Kasten service UI."""

    def test_homepage_loads(self, page: Page, kasten_url: str):
        """Test that Kasten homepage loads successfully."""
        page.goto(kasten_url)
        # Kasten should have notes browser
        expect(page.locator("body")).to_be_visible()
        
    def test_no_console_errors(self, page: Page, kasten_url: str):
        """Test that Kasten has no JavaScript console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(kasten_url)
        page.wait_for_load_state("networkidle")
        assert len(errors) == 0, f"Console errors found: {[e.text for e in errors]}"
