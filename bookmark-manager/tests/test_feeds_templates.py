from pathlib import Path


def test_feeds_template_includes_script_once():
    """Prevent duplicate feed scripts that double-submit POST /feeds."""
    templates_dir = Path(__file__).resolve().parents[1] / "src" / "templates"
    content = (templates_dir / "feeds.html").read_text(encoding="utf-8")
    assert '{% include "_scripts_feeds.html" %}' not in content
