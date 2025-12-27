# Shared Component Library

Reusable UI components for all knowledge-system services.

## Files

```
shared/
├── css/
│   ├── variables.css   # Design tokens (colors, spacing, fonts)
│   ├── base.css        # Reset, typography
│   ├── components.css  # Buttons, tabs, cards, modals, etc.
│   └── utilities.css   # Spacing, layout helpers
│
├── templates/
│   └── components.html # Jinja2 macros
│
├── styleguide.html     # Visual preview (open in browser)
└── README.md           # This file
```

## Quick Start

```html
{% import "components.html" as ui %}

{{ ui.header("Balance", [("Timer", "/"), ("Log", "/log")], active="Timer") }}
{{ ui.button("Save", primary=true) }}
{{ ui.input("email", placeholder="you@example.com") }}
```

## Full Documentation

See `docs/COMPONENT-LIBRARY.md` for complete API reference.

## Preview

Open `styleguide.html` directly in your browser to see all components.
