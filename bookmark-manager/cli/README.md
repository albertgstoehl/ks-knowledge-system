# Bookmark Manager CLI

Command-line interface for the Bookmark Manager API.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Make sure the API is running on `http://localhost:8000`.

### Add a bookmark
```bash
./bookmark_cli.py add "https://example.com"
```

### List bookmarks
```bash
./bookmark_cli.py list
./bookmark_cli.py list --state inbox
./bookmark_cli.py list --limit 50
```

### Search
```bash
# Keyword search
./bookmark_cli.py search "python programming"

# Semantic search
./bookmark_cli.py search --semantic "article about consumer experience"

# Filter by state
./bookmark_cli.py search --state inbox "technology"
```

### Mark as read
```bash
./bookmark_cli.py mark 1 read
./bookmark_cli.py mark 1 inbox
```

### Delete bookmark
```bash
./bookmark_cli.py delete 1
```

### Backup
```bash
./bookmark_cli.py backup
```

## Configuration

Set the API URL with environment variable:
```bash
export BOOKMARK_API_URL="http://your-server:8000"
```
