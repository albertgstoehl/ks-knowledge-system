# YouTube Videos Design

## Overview

Add support for YouTube videos with embedded playback via Piped (privacy frontend) and timestamp saving for resume functionality.

## Features

### 1. YouTube Channel RSS
Subscribe to YouTube channels via their RSS feed:
```
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```
Videos appear in Feeds tab alongside other RSS content.

### 2. YouTube URL Detection
When a YouTube URL is added to Inbox:
- Detect `youtube.com/watch?v=` or `youtu.be/` patterns
- Extract video ID
- Mark as video type for special UI treatment

### 3. Embedded Video Playback
Videos open in detail panel with:
- Piped iframe embed (`piped.video/embed/VIDEO_ID`)
- Timestamp input field
- Save Position button
- Standard actions: Open in Piped | Mark Read | Delete

### 4. Resume Playback
- Store last saved timestamp per video
- Load embed with `?start=SECONDS` parameter
- Manual save via "Save Position" button (most reliable cross-browser)

## Data Model

Extend `Bookmark` model:

```python
# New fields on Bookmark
video_id = Column(String, nullable=True)  # YouTube video ID
video_timestamp = Column(Integer, default=0)  # Seconds
```

Detection logic:
```python
def extract_video_id(url: str) -> Optional[str]:
    # youtube.com/watch?v=VIDEO_ID
    # youtu.be/VIDEO_ID
    # Return VIDEO_ID or None
```

## API Changes

### New Endpoint
```
PATCH /bookmarks/{id}/timestamp
Body: { "timestamp": 330 }  # seconds
```

### Modified Response
`BookmarkResponse` includes:
- `video_id: Optional[str]`
- `video_timestamp: int`
- `is_video: bool` (computed)

## UI Changes

### Detail Panel (Video)
```
┌─────────────────────────────┐
│ ┌─────────────────────────┐ │
│ │                         │ │
│ │    Piped Embed          │ │
│ │    (16:9 ratio)         │ │
│ │                         │ │
│ └─────────────────────────┘ │
│                             │
│ Video Title                 │
│ Channel Name                │
│                             │
│ Position: [__5:30__] [Save] │
│                             │
│ [Open in Piped] [Read] [Del]│
└─────────────────────────────┘
```

### Timestamp Input
- Text input accepting `MM:SS` or `HH:MM:SS` format
- Parse to seconds on save
- Display formatted on load

## Piped Integration

Embed URL format:
```
https://piped.video/embed/VIDEO_ID?start=SECONDS
```

No postMessage communication needed - timestamp is manual input.

## Implementation Tasks

1. Add `video_id` and `video_timestamp` fields to Bookmark model
2. Add video detection in bookmark creation
3. Add `/bookmarks/{id}/timestamp` endpoint
4. Update BookmarkResponse schema
5. Create video detail panel template/JS
6. Add timestamp parsing utilities (MM:SS <-> seconds)
7. Test with YouTube channel RSS feeds
