#!/bin/bash
# Daily backup script

BACKUP_DIR="/app/data/backups"
MAX_DAILY=7
MAX_WEEKLY=4

# Create backup
curl -X POST http://localhost:8000/backup/create

# Cleanup old backups
# Keep last 7 daily backups
cd "$BACKUP_DIR"
ls -t backup_*.db.gz | tail -n +$((MAX_DAILY + 1)) | xargs -r rm

# Keep weekly backups (first backup of each week)
# This is simplified - in production, use proper date logic
