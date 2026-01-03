# kasten/src/scanner.py
import re
import os
from pathlib import Path

LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')
NOTE_ID_PATTERN = re.compile(r'^(\d{4,6}[a-z]+)\.md$')

def extract_links(content: str) -> list[str]:
    """Extract all [[id]] links from content."""
    return LINK_PATTERN.findall(content)

def parse_note(filename: str, content: str) -> tuple[str, str, str, list[str]]:
    """Parse a note file, return (id, title, parent_id, links)."""
    match = NOTE_ID_PATTERN.match(filename)
    if not match:
        return None, None, None, []

    note_id = match.group(1)
    lines = content.strip().split('\n')

    # Parse YAML frontmatter if present
    title_index = 0
    parent_id = None
    if lines and lines[0].strip() == "---":
        # Find closing --- delimiter and extract parent
        for i in range(1, len(lines)):
            line = lines[i].strip()
            if line == "---":
                title_index = i + 1
                break
            # Extract parent: field
            if line.startswith("parent:"):
                parent_id = line.split(":", 1)[1].strip()

    title = lines[title_index].strip() if title_index < len(lines) else ""
    links = extract_links(content)

    return note_id, title, parent_id, links

def scan_notes_directory(directory: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """Scan directory for markdown notes, return notes and links."""
    notes = []
    links = []

    for filename in os.listdir(directory):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        note_id, title, parent_id, note_links = parse_note(filename, content)
        if note_id is None:
            continue

        notes.append({
            "id": note_id,
            "title": title,
            "parent_id": parent_id,
            "file_path": filename
        })

        for target_id in note_links:
            links.append((note_id, target_id))

    # Sort by id
    notes.sort(key=lambda n: n["id"])
    return notes, links
