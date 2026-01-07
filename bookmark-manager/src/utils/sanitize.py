from markupsafe import Markup
import bleach


ALLOWED_TAGS = [
    "p",
    "a",
    "blockquote",
    "small",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "code",
    "pre",
    "br",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
}

ALLOWED_PROTOCOLS = ["http", "https"]


def sanitize_html(raw_html: str) -> str:
    """Sanitize HTML with a strict allowlist for safe rendering."""
    if not raw_html:
        return ""
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def safe_html(raw_html: str) -> Markup:
    """Return sanitized HTML marked safe for Jinja rendering."""
    return Markup(sanitize_html(raw_html))
