# tests/e2e/ui/test_balance.py
"""
Balance service UI tests.

Tests cover:
- Timer-complete idempotency (CRITICAL - original bug)
- Session lifecycle (start, abandon)
- Meditation/exercise logging
- Settings management
- Stats viewing

NOTE: The dev environment has a known issue where the UI at /dev/ fetches
from production API due to relative paths in JS. This means UI tests
may not reflect dev API state. The API-level tests are the reliable
verification of functionality.
"""
import pytest
import time
from playwright.sync_api import Page, expect


def wait_for_break_to_end(balance_api, max_wait_seconds: int = 30) -> bool:
    """
    Wait for any existing break to end.
    Returns True if break ended or no break, False if timeout.
    """
    for _ in range(max_wait_seconds):
        response = balance_api.get("/api/check")
        if response.status_code == 200:
            data = response.json()
            if not data.get("on_break", False):
                return True
            remaining = data.get("remaining_seconds", 0)
            if remaining > max_wait_seconds:
                # Break too long, can't wait
                return False
        time.sleep(1)
    return False


def ensure_clean_state(balance_api, max_wait: int = 30) -> bool:
    """
    Ensure Balance is in a clean state (no session, no break).
    Returns True if clean state achieved.
    """
    # Try to abandon any existing session (may fail if no session)
    balance_api.post("/api/sessions/abandon")
    
    # Wait for any break to end
    return wait_for_break_to_end(balance_api, max_wait)


class TestBalanceTimerComplete:
    """Tests for timer completion and break handling."""

    def test_break_timer_idempotency(self, page: Page, balance_url: str, balance_api):
        """
        CRITICAL: Verify that calling timer-complete multiple times doesn't reset the break.
        
        This was the original bug that motivated the CI/CD pipeline.
        The idempotency guard in sessions.py:249 should prevent double-breaks.
        
        The bug was: when a user refreshed the page during a break, the frontend
        would call timer-complete again, which would reset the break timer.
        
        This test verifies:
        1. Start a session via API
        2. Call timer-complete to start break - get break_until timestamp
        3. Call timer-complete AGAIN (simulating page reload)
        4. Verify break_until is UNCHANGED (idempotency guard works)
        
        NOTE: UI verification is skipped due to known dev environment issue
        where UI fetches from production API instead of dev API.
        """
        # Step 1: Ensure clean state - wait for any existing break
        if not ensure_clean_state(balance_api, max_wait=60):
            pytest.skip("Could not get clean state (break still active)")
        
        # Step 2: Start a session via API
        response = balance_api.post("/api/sessions/start", json={
            "type": "expected",
            "intention": "Test session for idempotency"
        })
        assert response.status_code == 200, f"Failed to start session: {response.text}"
        
        # Step 3: Complete the timer via API (simulates timer ending)
        response = balance_api.post("/api/sessions/timer-complete")
        assert response.status_code == 200, f"Failed to complete timer: {response.text}"
        data = response.json()
        initial_break_until = data.get("break_until")
        assert initial_break_until, "Should have break_until timestamp"
        
        # Store the initial break duration for verification
        initial_break_duration = data.get("break_duration")
        
        # Step 4: Wait a moment to let time pass
        time.sleep(2)
        
        # Step 5: Call timer-complete AGAIN (simulates what happens on page reload)
        # THIS IS THE CRITICAL TEST - the bug was that this would reset the break
        response = balance_api.post("/api/sessions/timer-complete")
        assert response.status_code == 200, f"Second timer-complete failed: {response.text}"
        data = response.json()
        
        # Step 6: CRITICAL CHECK - Verify break_until hasn't changed (idempotency!)
        new_break_until = data.get("break_until")
        assert new_break_until == initial_break_until, (
            f"BUG: Break timer was reset! "
            f"Original: {initial_break_until}, After second call: {new_break_until}. "
            f"The idempotency guard in sessions.py should prevent this."
        )
        
        # Step 7: Verify break duration decreased (proving same break is continuing)
        new_break_duration = data.get("break_duration")
        # Duration should be same or less (since time passed)
        assert new_break_duration <= initial_break_duration, (
            f"Break duration should not increase. "
            f"Initial: {initial_break_duration}, Current: {new_break_duration}"
        )
        
        # Step 8: Verify we can call it multiple more times without resetting
        for i in range(3):
            time.sleep(0.5)
            response = balance_api.post("/api/sessions/timer-complete")
            assert response.status_code == 200
            data = response.json()
            assert data.get("break_until") == initial_break_until, (
                f"Break reset on call {i+3}! This should NEVER happen."
            )
        
        # Step 9: Basic UI verification - just check page loads
        # (UI state may not match due to dev/prod API routing issue)
        page.goto(balance_url)
        page.wait_for_load_state("networkidle")
        
        # The page should at least load without error
        # Use the header title which is unique
        expect(page.locator(".header__title")).to_contain_text("Balance")
        
        # Cleanup is handled by the next test's ensure_clean_state


class TestBalanceSessionLifecycle:
    """Tests for starting and abandoning sessions."""

    def test_start_pomodoro_session(self, page: Page, balance_url: str, balance_api):
        """
        Test starting a new Pomodoro session via UI.
        
        Uses "personal" session type because it doesn't require Priority
        or Next Up selection (unlike "expected" type).
        """
        # Ensure clean state
        if not ensure_clean_state(balance_api, max_wait=60):
            pytest.skip("Could not get clean state (break still active)")
        
        # Navigate to Balance
        page.goto(balance_url)
        page.wait_for_load_state("networkidle")
        
        # Should see home page with start button
        home_page = page.locator("#page-home")
        expect(home_page).to_be_visible()
        
        # Select session type "personal" (doesn't require Next Up or Priority)
        page.locator("button.btn--option[data-type='personal']").click()
        
        # Enter intention
        intention_input = page.locator("#intention-input")
        intention_input.fill("Test Pomodoro session")
        
        # Click start button - should be enabled for personal type
        start_btn = page.locator("#start-btn")
        expect(start_btn).to_be_enabled()
        start_btn.click()
        
        # Should transition to active session page
        active_page = page.locator("#page-active")
        expect(active_page).to_be_visible(timeout=5000)
        
        # Timer should be visible on active page (uses #active-time ID)
        timer = page.locator("#active-time")
        expect(timer).to_be_visible()
        
        # Intention should be displayed (uses #active-intention ID)
        intention_display = page.locator("#active-intention")
        expect(intention_display).to_contain_text("Test Pomodoro session")
        
        # Cleanup
        balance_api.post("/api/sessions/abandon")

    def test_abandon_session(self, page: Page, balance_url: str, balance_api):
        """Test abandoning an active session."""
        # Ensure clean state first
        if not ensure_clean_state(balance_api, max_wait=60):
            pytest.skip("Could not get clean state (break still active)")
        
        # Start a session via API
        response = balance_api.post("/api/sessions/start", json={
            "type": "personal",
            "intention": "Session to abandon"
        })
        assert response.status_code == 200, f"Failed to start session: {response.text}"
        
        # Navigate to Balance
        page.goto(balance_url)
        page.wait_for_load_state("networkidle")
        
        # Should see active session page
        active_page = page.locator("#page-active")
        expect(active_page).to_be_visible(timeout=5000)
        
        # Click abandon button - this triggers a confirmation dialog
        abandon_btn = page.locator("#abandon-btn")
        expect(abandon_btn).to_be_visible()
        
        # Set up dialog handler before clicking
        page.on("dialog", lambda dialog: dialog.accept())
        abandon_btn.click()
        
        # Should return to home page after confirming abandon
        home_page = page.locator("#page-home")
        expect(home_page).to_be_visible(timeout=5000)
        
        # Start button should be available again
        start_btn = page.locator("#start-btn")
        expect(start_btn).to_be_visible()
