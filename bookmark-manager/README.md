# Bookmark Manager

Minimal bookmark management system with semantic search, Web Archive integration, and automated backups.

## Features

- **Easy Input**: Add bookmarks via REST API (CLI, future: Telegram bot, browser extension)
- **AI-Powered Summaries**: Claude Haiku generates concise 2-3 sentence descriptions from full page content
- **Smart Search**:
  - Semantic search using embeddings ("that article about everything getting worse")
  - Keyword search on title, description, and URL
  - Filter by read/unread status
- **Web Archive**: Automatic snapshot creation on archive.org
- **State Management**: Simple inbox/read workflow
- **Automated Backups**: Daily backups with compression
- **CLI Tool**: Command-line interface for quick access

## Tech Stack

- **Backend**: FastAPI + Python 3.11
- **Database**: SQLite with sqlite-vss for vector search
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Content Extraction**: Jina AI Reader API
- **LLM**: Claude Haiku via claude-agent-sdk (uses Claude Code subscription)
- **Deployment**: Docker Compose

## Quick Start

### 1. Clone and setup

```bash
git clone https://git.fml128.ch/albert/bookmark-manager.git
cd bookmark-manager
cp .env.example .env
```

### 2. Generate Claude Code OAuth token

```bash
claude setup-token
# Copy the token to .env file as CLAUDE_CODE_OAUTH_TOKEN
```

### 3. Run with Docker

```bash
docker-compose up -d
```

### 4. Access API

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

### 5. Install CLI (Optional)

Install the CLI tool globally using pipx for easy access from anywhere:

```bash
# Install pipx if you don't have it
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install the bookmark CLI
pipx install .[cli]

# Now use it from anywhere
bookmark add "https://example.com"
bookmark list
bookmark search --semantic "python programming"
```

**Alternative: Local development usage**

```bash
cd cli
pip install -r requirements.txt
./bookmark_cli.py add "https://example.com"
```

## API Endpoints

### Bookmarks

- `POST /bookmarks` - Add new bookmark
- `GET /bookmarks` - List bookmarks (optional: `?state=inbox|read&limit=20`)
- `GET /bookmarks/{id}` - Get single bookmark
- `PATCH /bookmarks/{id}` - Update bookmark state
- `DELETE /bookmarks/{id}` - Delete bookmark

### Search

- `POST /search/semantic` - Semantic search
- `POST /search/keyword` - Keyword search

Request body:
```json
{
  "query": "article about consumer experience",
  "state": "inbox",  // optional: "inbox" or "read"
  "limit": 20
}
```

### Backup

- `POST /backup/create` - Create backup
- `GET /backup/list` - List available backups
- `POST /backup/restore/{filename}` - Restore from backup
- `GET /backup/download/{filename}` - Download backup file

## Development

### Run tests

```bash
pytest tests/ -v
```

### Local development without Docker

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

uvicorn src.main:app --reload
```

## Configuration

Environment variables in `.env`:

- `DATABASE_URL` - SQLite database path (default: `sqlite:///app/data/bookmarks.db`)
- `JINA_API_KEY` - Optional Jina AI API key for higher rate limits
- `CLAUDE_CODE_OAUTH_TOKEN` - Claude Code OAuth token for LLM summarization (generate with: `claude setup-token`)

## Backup Strategy

- **Automatic**: Daily backups (configure cron in container)
- **Manual**: `POST /backup/create` or `./bookmark_cli.py backup`
- **Storage**: `/app/data/backups` (mounted volume)
- **Format**: Compressed SQLite files (`.db.gz`)
- **Retention**: Last 7 daily + 4 weekly backups

## Future Enhancements

- Telegram bot integration
- Email forwarding for bookmark input
- Browser extension
- LLM-enhanced search (hybrid approach)
- Multi-user support
- Tags and collections
- Full-text search on archived content

## License

MIT
