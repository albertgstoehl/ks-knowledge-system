# Backup Configuration

## Automatic Backups

The bookmark manager has **automatic daily backups** configured via cron.

### Schedule
- **Frequency**: Daily at 2:00 AM UTC
- **Cron expression**: `0 2 * * * /app/scripts/backup_cron.sh`

### Retention Policy
- **Daily backups**: Last 7 days retained
- **Weekly backups**: Last 4 weeks retained
- **Location**: `/app/data/backups/` (mounted to `./data/backups/` on host)
- **Format**: Compressed SQLite database (`.db.gz`)

### Backup Contents
Each backup contains:
- All bookmarks with metadata
- Titles and descriptions
- Semantic embeddings (384-dimensional vectors)
- Archive URLs
- Read/unread state and timestamps

### Manual Backup

Create a backup manually via CLI:
```bash
cd cli
./bookmark_cli.py backup
```

Or via API:
```bash
curl -X POST http://localhost:8000/backup/create
```

### Restore from Backup

Via API:
```bash
# List available backups
curl http://localhost:8000/backup/list

# Restore specific backup
curl -X POST http://localhost:8000/backup/restore/backup_20251020_110511.db.gz
```

### Verification

Check that cron is running:
```bash
docker exec bookmark-manager-api service cron status
```

List scheduled jobs:
```bash
docker exec bookmark-manager-api crontab -l
```

Check backup files:
```bash
ls -lh data/backups/
```

### Notes

- Backups run automatically - no user action required
- The backup script cleans up old backups to prevent disk space issues
- Backups are compressed to save space (~100KB per backup with 7 bookmarks)
- The Docker volume ensures backups persist even if container is recreated
