from src.utils.sanitize import sanitize_html


def test_sanitize_html_allows_basic_tags_and_strips_script():
    raw = (
        '<p>Hello <strong>world</strong></p>'
        '<script>alert(1)</script>'
        '<a href="https://example.com">link</a>'
        '<a href="javascript:alert(1)">bad</a>'
    )

    cleaned = sanitize_html(raw)

    assert '<script>' not in cleaned
    assert '<strong>world</strong>' in cleaned
    assert 'href="https://example.com"' in cleaned
    assert 'javascript:' not in cleaned
