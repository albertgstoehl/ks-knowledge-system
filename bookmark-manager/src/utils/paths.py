from pathlib import Path


def find_shared_dir(start_path: Path) -> Path:
    """Locate the shared/ directory by walking up from start_path."""
    path = start_path.resolve()
    if path.is_file():
        path = path.parent

    for parent in [path, *path.parents]:
        candidate = parent / "shared"
        if candidate.is_dir() and (candidate / "templates").is_dir():
            return candidate

    raise RuntimeError(f"shared directory not found from {start_path}")
