# Docker Deployment Guide

This project provides two Docker Compose configurations for different use cases.

## Production Deployment (docker-compose.yml)

Uses the pre-built image from Forgejo Container Registry.

### Setup

```bash
# Pull latest image and start
docker-compose pull
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Image Updates

The workflow automatically builds and pushes a new image on every push to `main`. To update your deployment:

```bash
docker-compose pull
docker-compose up -d
```

### Registry Authentication (if needed for private registry)

```bash
docker login git.fml128.ch
# Enter your username and personal access token
```

## Development Setup (docker-compose.dev.yml)

Builds the image locally from source.

### Setup

```bash
# Build and start
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Rebuild after code changes
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Development Features

- Builds image from local Dockerfile
- Source code mounted at `/app/src` for live development (requires FastAPI reload)
- Uses separate container name to avoid conflicts with production setup

## Configuration

Both setups use the same environment variables from `.env`:

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
- `CLAUDE_CODE_OAUTH_TOKEN` - For AI summarization (run `claude setup-token`)
- `JINA_API_KEY` - Optional, for higher rate limits on content extraction

## Data Persistence

Both configurations mount `./data` for database and backups:
- Database: `./data/bookmarks.db`
- Backups: `./data/backups/`

## Available Images

### Latest (Production)
```
git.fml128.ch/albert/bookmark-manager:latest
```

Always points to the most recent build from `main` branch.

### Specific Commit
```
git.fml128.ch/albert/bookmark-manager:<commit-sha>
```

Pin to a specific git commit for stability.

## Switching Between Setups

You can run both simultaneously (different container names):

```bash
# Production on port 8000
docker-compose up -d

# Development on port 8001
docker-compose -f docker-compose.dev.yml up -d
# (Remember to change port in docker-compose.dev.yml)
```

Or switch between them:

```bash
# Stop current setup
docker-compose down
# Or: docker-compose -f docker-compose.dev.yml down

# Start different setup
docker-compose up -d
# Or: docker-compose -f docker-compose.dev.yml up -d
```

## Troubleshooting

### Image pull fails
- Ensure you're logged into the registry: `docker login git.fml128.ch`
- Check image exists: `docker pull git.fml128.ch/albert/bookmark-manager:latest`

### Build fails in dev setup
- Check Dockerfile syntax
- Ensure all dependencies in requirements.txt are valid
- Check build logs: `docker-compose -f docker-compose.dev.yml build --no-cache`

### Container won't start
- Check logs: `docker-compose logs api`
- Verify .env file exists and has required variables
- Check data directory permissions
