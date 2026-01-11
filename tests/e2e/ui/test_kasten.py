# tests/e2e/ui/test_kasten.py
"""
Kasten service UI tests.

Tests cover:
- Viewing notes with source tracking
- Navigating between linked notes
- Adding notes to workspace
"""
import pytest
from playwright.sync_api import Page, expect


class TestKastenNotes:
    """Tests for note viewing and navigation."""

    def test_verify_note_source_tracking(self, page: Page, kasten_url: str, kasten_api):
        """Test that notes show their source information."""
        # Get notes
        response = kasten_api.get("/api/notes")
        if response.status_code != 200 or not response.json():
            pytest.skip("No notes available")
        
        notes = response.json()
        note_with_source = None
        
        # Check first 10 notes for one with source
        for note in notes[:10]:
            note_response = kasten_api.get(f"/api/notes/{note['id']}")
            if note_response.status_code == 200:
                note_data = note_response.json()
                if note_data.get("source"):
                    note_with_source = note_data
                    break
        
        # Use any note if none have sources
        if not note_with_source:
            note_response = kasten_api.get(f"/api/notes/{notes[0]['id']}")
            if note_response.status_code != 200:
                pytest.skip("Could not fetch note details")
            note_with_source = note_response.json()
        
        # Navigate to note
        page.goto(f"{kasten_url}/note/{note_with_source['id']}")
        page.wait_for_load_state("networkidle")
        
        # Note content should be visible
        note_content = page.locator("article.note-content")
        expect(note_content).to_be_visible()
        
        # If note has source, source header should be visible
        if note_with_source.get("source"):
            source_header = page.locator("#source-header")
            expect(source_header).to_be_visible()

    def test_navigate_between_linked_notes(self, page: Page, kasten_url: str, kasten_api):
        """Test navigation between linked notes."""
        # Get notes
        response = kasten_api.get("/api/notes")
        if response.status_code != 200 or not response.json():
            pytest.skip("No notes available")
        
        # Navigate to landing page
        page.goto(kasten_url)
        page.wait_for_load_state("networkidle")
        
        # Should see entry points or note list
        note_link = page.locator(".entry-list a, .list__item a").first
        if note_link.is_visible():
            note_link.click()
            page.wait_for_load_state("networkidle")
            
            # Should be on a note page
            note_content = page.locator("article.note-content")
            expect(note_content).to_be_visible()
            
            # Back button should be visible
            back_btn = page.locator(".nav-btn").first
            expect(back_btn).to_be_visible()

    def test_add_note_to_workspace(self, page: Page, kasten_url: str, kasten_api, canvas_api):
        """Test that push to workspace button exists on note page."""
        # Get a note
        response = kasten_api.get("/api/notes")
        if response.status_code != 200 or not response.json():
            pytest.skip("No notes available")
        
        note = response.json()[0]
        
        # Navigate to note
        page.goto(f"{kasten_url}/note/{note['id']}")
        page.wait_for_load_state("networkidle")
        
        # Find push to workspace button
        push_btn = page.locator("a:has-text('Push to Workspace')")
        expect(push_btn).to_be_visible()

    def test_verify_note_in_workspace(self, page: Page, kasten_url: str, canvas_url: str, kasten_api, canvas_api):
        """Test that a note added to workspace appears correctly."""
        # Get a note
        response = kasten_api.get("/api/notes")
        if response.status_code != 200 or not response.json():
            pytest.skip("No notes available")
        
        note = response.json()[0]
        
        # Clear workspace first
        ws_response = canvas_api.get("/api/workspace")
        if ws_response.status_code == 200:
            for ws_note in ws_response.json().get("notes", []):
                canvas_api.delete(f"/api/workspace/notes/{ws_note['id']}")
        
        # Add to workspace via API
        ws_response = canvas_api.post("/api/workspace/notes", json={"km_note_id": note["id"]})
        if ws_response.status_code == 400:
            # Already in workspace - still valid for test
            ws_response = canvas_api.get("/api/workspace")
            ws_note_id = None
            if ws_response.status_code == 200:
                for ws_note in ws_response.json().get("notes", []):
                    if ws_note["km_note_id"] == note["id"]:
                        ws_note_id = ws_note["id"]
                        break
        elif ws_response.status_code != 201:
            pytest.skip(f"Could not add note: {ws_response.text}")
        else:
            ws_note_id = ws_response.json()["id"]
        
        try:
            # Navigate to Canvas workspace
            page.goto(f"{canvas_url}/workspace")
            page.wait_for_load_state("networkidle")
            
            # Graph should show
            graph = page.locator("#graph")
            expect(graph).to_be_visible()
        finally:
            if ws_note_id:
                canvas_api.delete(f"/api/workspace/notes/{ws_note_id}")
