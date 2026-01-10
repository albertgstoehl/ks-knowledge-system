from pathlib import Path

from src.utils.paths import find_shared_dir


def test_find_shared_dir_from_repo():
    """Shared directory should be discoverable from repo layout."""
    shared_dir = find_shared_dir(Path(__file__).resolve())
    assert shared_dir.name == "shared"
    assert (shared_dir / "templates" / "components.html").exists()
    assert (shared_dir / "css").exists()
