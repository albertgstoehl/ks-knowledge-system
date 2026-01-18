import pytest
from playwright.sync_api import Page, expect


def test_today_page_loads(page: Page, train_url: str):
    """Verify Today page shows Start Workout button."""
    page.goto(f"{train_url}/")
    expect(page.locator("text=Start Workout")).to_be_visible()


def test_history_page_loads(page: Page, train_url: str):
    """Verify History page shows exercise dropdown."""
    page.goto(f"{train_url}/history")
    expect(page.locator("#exercise-select")).to_be_visible()


def test_plan_page_loads(page: Page, train_url: str):
    """Verify Plan page shows markdown content container."""
    page.goto(f"{train_url}/plan")
    expect(page.locator(".markdown-content")).to_be_visible()


def test_bottom_nav_works(page: Page, train_url: str):
    """Verify bottom nav navigates between tabs."""
    page.goto(f"{train_url}/")

    # Click History
    page.click(".bottom-nav >> text=History")
    expect(page.locator("#exercise-select")).to_be_visible()

    # Click Plan
    page.click(".bottom-nav >> text=Plan")
    expect(page.locator(".markdown-content")).to_be_visible()

    # Click Today
    page.click(".bottom-nav >> text=Today")
    expect(page.locator("text=Start Workout")).to_be_visible()
