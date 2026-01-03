# YouTube Videos in Conveyor Belt UI

## Overview

Add YouTube video support to the new conveyor belt inbox layout.

## Design

### Layout
When current item has `video_id`, replace description area with embedded player:
- Title and domain above player
- 16:9 YouTube embed (youtube-nocookie.com for privacy)
- Timestamp status below: "Position: 5:30 · Saved"
- "Next Up" queue remains at bottom

### Action Panel
Same as regular bookmarks, minus "Mark as Paper" (doesn't apply to videos).

### Behavior
- **Auto-save on pause**: YT IFrame API detects pause → PATCH timestamp
- **Video ended prompt**: confirm() → Archive or Delete → reload
- **Resume playback**: Embed loads with `?start=SECONDS` param

## Implementation

Single file change: `src/templates/index.html`

1. Detect `current.video_id` in template
2. Conditionally render player vs description
3. Add YT IFrame API script
4. Add player init + event handlers JS

No backend changes - API already complete.
