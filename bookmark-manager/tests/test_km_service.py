import pytest
from unittest.mock import patch, MagicMock
from src.services.km_service import KmService

def test_km_service_format_note():
    """KmService should create a properly formatted note"""
    service = KmService(notes_dir="/tmp/test_notes")

    note_content = service.format_note(
        title="My Insight",
        quote="This is a key passage from the source",
        addition="I think this means X because Y",
        source_title="Article Title",
        source_url="https://example.com/article",
        connection_type="continues",
        connected_to="20251218120000"
    )

    expected = '''# My Insight

> "This is a key passage from the source"

I think this means X because Y

---
Source: [Article Title](https://example.com/article)
Connected to: [[20251218120000]] (continues)
'''
    assert note_content == expected

def test_km_service_creates_stump_note():
    """Stump notes should have no connection"""
    service = KmService(notes_dir="/tmp/test_notes")

    note_content = service.format_note(
        title="New Thought",
        quote="Starting point",
        addition="This begins a new chain",
        source_title="Source",
        source_url="https://example.com",
        connection_type="stump",
        connected_to=None
    )

    assert "Connected to:" not in note_content

@pytest.mark.asyncio
async def test_km_service_create_note():
    """KmService should create a note file with timestamp-based filename"""
    import tempfile
    import os

    # Use a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        service = KmService(notes_dir=tmpdir)

        km_id = await service.create_note(
            title="Test Note",
            quote="Quote",
            addition="Addition",
            source_title="Source",
            source_url="https://example.com",
            connection_type="stump",
            connected_to=None
        )

        assert km_id is not None
        # Verify file exists
        filepath = os.path.join(tmpdir, f"{km_id}.md")
        assert os.path.exists(filepath)

        # Verify content
        with open(filepath, 'r') as f:
            content = f.read()
        assert "# Test Note" in content
        assert '> "Quote"' in content
        assert "Addition" in content
        assert "Source: [Source](https://example.com)" in content
        assert "Connected to:" not in content
