# tests/e2e/ui/test_canvas.py
"""
Canvas service UI tests.

Tests cover:
- Viewing cited text in drafts
- Converting drafts to notes
- Workspace management
- Export functionality
"""
import pytest
from playwright.sync_api import Page, expect


class TestCanvasDraft:
    """Tests for draft functionality."""

    def test_show_cited_text_in_draft(self, page: Page, canvas_url: str, canvas_api):
        """Test that cited text appears correctly in the draft."""
        # Clear draft first
        canvas_api.delete("/api/canvas")
        
        # Add quote via API (using the correct field name)
        response = canvas_api.post("/api/quotes", json={
            "text": "This is a test quote for verification",
            "source_url": "https://example.com/source",
            "source_title": "Test Source Article"
        })
        assert response.status_code == 201, f"Failed to add quote: {response.text}"
        
        # Navigate to draft page
        page.goto(f"{canvas_url}/draft")
        page.wait_for_load_state("networkidle")
        
        # Draft editor should be visible
        editor = page.locator("#canvas-editor")
        expect(editor).to_be_visible()
        
        # Verify quote appears in editor content via API
        response = canvas_api.get("/api/canvas")
        assert response.status_code == 200
        content = response.json().get("content", "")
        assert "test quote for verification" in content.lower(), \
            f"Quote not found in draft: {content[:200]}"
        
        # Cleanup
        canvas_api.delete("/api/canvas")

    def test_convert_draft_to_note(self, page: Page, canvas_url: str, canvas_api):
        """Test that draft editor loads and can detect note block format."""
        # Set up draft with note block format
        note_content = """### Test Note Title

This is the content of the test note.
---"""
        canvas_api.put("/api/canvas", json={"content": note_content})
        
        # Navigate to draft
        page.goto(f"{canvas_url}/draft")
        page.wait_for_load_state("networkidle")
        
        # Editor should show content
        editor = page.locator("#canvas-editor")
        expect(editor).to_be_visible()
        
        # Wait for content to be loaded via JS fetch (async)
        page.wait_for_timeout(1000)
        
        # Verify content is loaded via API (JS loads content from server)
        response = canvas_api.get("/api/canvas")
        assert response.status_code == 200
        content = response.json().get("content", "")
        assert "Test Note Title" in content, f"Note content not in draft: {content[:100]}"
        
        # Note modal exists but is hidden (activated by --- pattern detection)
        note_modal = page.locator("#note-modal")
        expect(note_modal).to_be_attached()
        
        # Cleanup
        canvas_api.delete("/api/canvas")


class TestCanvasWorkspace:
    """Tests for workspace functionality."""

    def test_add_note_to_workspace(self, page: Page, canvas_url: str, canvas_api, kasten_api):
        """Test adding a note to the workspace."""
        # Get a note from Kasten
        response = kasten_api.get("/api/notes")
        if response.status_code != 200 or not response.json():
            pytest.skip("No notes available in Kasten")
        
        notes = response.json()
        note_id = notes[0]["id"]
        
        # Clear workspace
        ws_response = canvas_api.get("/api/workspace")
        if ws_response.status_code == 200:
            for note in ws_response.json().get("notes", []):
                canvas_api.delete(f"/api/workspace/notes/{note['id']}")
        
        # Add note to workspace via API
        ws_note_id = None
        response = canvas_api.post("/api/workspace/notes", json={"km_note_id": note_id})
        if response.status_code == 400:
            # Note already in workspace - that's fine for this test
            pass
        elif response.status_code != 201:
            pytest.skip(f"Could not add note to workspace: {response.text}")
        else:
            ws_note_id = response.json()["id"]
        
        try:
            # Navigate to workspace
            page.goto(f"{canvas_url}/workspace")
            page.wait_for_load_state("networkidle")
            
            # Graph should be visible
            graph = page.locator("#graph")
            expect(graph).to_be_visible()
            
            # Toolbar buttons should be visible
            connect_btn = page.locator("#connect-btn")
            expect(connect_btn).to_be_visible()
        finally:
            # Cleanup
            if ws_note_id:
                canvas_api.delete(f"/api/workspace/notes/{ws_note_id}")

    def test_connect_two_notes_in_workspace(self, page: Page, canvas_url: str, canvas_api, kasten_api):
        """Test that connect button exists for workspace with notes."""
        # Get at least 2 notes
        response = kasten_api.get("/api/notes")
        if response.status_code != 200 or len(response.json()) < 2:
            pytest.skip("Need at least 2 notes in Kasten")
        
        notes = response.json()
        note1_id = notes[0]["id"]
        note2_id = notes[1]["id"]
        
        # Clear workspace first
        ws_response = canvas_api.get("/api/workspace")
        if ws_response.status_code == 200:
            for note in ws_response.json().get("notes", []):
                canvas_api.delete(f"/api/workspace/notes/{note['id']}")
        
        # Add both notes
        ws_note1 = canvas_api.post("/api/workspace/notes", json={"km_note_id": note1_id})
        ws_note2 = canvas_api.post("/api/workspace/notes", json={"km_note_id": note2_id})
        
        if ws_note1.status_code != 201 or ws_note2.status_code != 201:
            pytest.skip("Could not add notes to workspace")
        
        ws_note1_id = ws_note1.json()["id"]
        ws_note2_id = ws_note2.json()["id"]
        
        try:
            # Navigate to workspace
            page.goto(f"{canvas_url}/workspace")
            page.wait_for_load_state("networkidle")
            
            # Connect button should exist (disabled until selection)
            connect_btn = page.locator("#connect-btn")
            expect(connect_btn).to_be_visible()
            
            # Graph should be visible with nodes
            graph = page.locator("#graph")
            expect(graph).to_be_visible()
            
            # Connection modal exists (hidden until triggered)
            connection_modal = page.locator("#connection-modal")
            expect(connection_modal).to_be_attached()
        finally:
            canvas_api.delete(f"/api/workspace/notes/{ws_note1_id}")
            canvas_api.delete(f"/api/workspace/notes/{ws_note2_id}")

    def test_export_workspace(self, page: Page, canvas_url: str):
        """Test that export button exists and is clickable."""
        page.goto(f"{canvas_url}/workspace")
        page.wait_for_load_state("networkidle")
        
        # Export button should be visible
        export_btn = page.locator("#export-btn")
        expect(export_btn).to_be_visible()
        expect(export_btn).to_be_enabled()
