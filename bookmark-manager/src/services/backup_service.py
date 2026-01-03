import os
import gzip
import shutil
import sqlite3
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self, db_path: str = "data/bookmarks.db", backup_dir: str = "data/backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir

        # Ensure backup directory exists
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

    async def create_backup(self) -> str:
        """Create a compressed backup of the database"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        compressed_path = f"{backup_path}.gz"

        try:
            # Use SQLite backup API for consistency
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(backup_path)

            source_conn.backup(backup_conn)

            source_conn.close()
            backup_conn.close()

            # Compress the backup
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed backup
            os.remove(backup_path)

            # Get file size
            size = os.path.getsize(compressed_path)
            logger.info(f"Created backup: {compressed_path} ({size} bytes)")

            return compressed_path

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise

    async def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []

        if not os.path.exists(self.backup_dir):
            return backups

        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".db.gz"):
                filepath = os.path.join(self.backup_dir, filename)
                stat = os.stat(filepath)

                backups.append({
                    "filename": filename,
                    "path": filepath,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })

        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups

    async def restore_backup(self, backup_filename: str) -> bool:
        """Restore database from a backup"""
        backup_path = os.path.join(self.backup_dir, backup_filename)

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_filename}")

        try:
            # Decompress
            temp_path = backup_path.replace(".gz", "")
            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Replace current database
            shutil.copy2(temp_path, self.db_path)
            os.remove(temp_path)

            logger.info(f"Restored backup: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
