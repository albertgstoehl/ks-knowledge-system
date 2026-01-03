# kasten/tests/test_scanner.py
import pytest
import tempfile
import os
from src.scanner import parse_note, extract_links, scan_notes_directory

def test_extract_links():
    content = "This links to [[1219a]] and [[1219b]] notes."
    links = extract_links(content)
    assert links == ["1219a", "1219b"]

def test_extract_links_empty():
    content = "No links here."
    links = extract_links(content)
    assert links == []

def test_parse_note():
    content = "First line is title\n\nMore content [[1219b]] here."
    note_id, title, parent_id, links = parse_note("1219a.md", content)
    assert note_id == "1219a"
    assert title == "First line is title"
    assert parent_id is None
    assert links == ["1219b"]

def test_scan_notes_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        with open(os.path.join(tmpdir, "1219a.md"), "w") as f:
            f.write("Note A title\n\nLinks to [[1219b]]")
        with open(os.path.join(tmpdir, "1219b.md"), "w") as f:
            f.write("Note B title\n\nNo links here")

        notes, links = scan_notes_directory(tmpdir)

        assert len(notes) == 2
        assert notes[0]["id"] == "1219a"
        assert notes[0]["title"] == "Note A title"
        assert len(links) == 1
        assert links[0] == ("1219a", "1219b")
