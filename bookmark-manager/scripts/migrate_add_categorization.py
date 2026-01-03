#!/usr/bin/env python3
"""
Migration script to add categorization fields to bookmarks table.
Adds: is_paper, pinned, zotero_key columns.
"""
import sqlite3
import os
import sys

def migrate(db_path: str):
    """Add new categorization columns to bookmarks table."""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(bookmarks)")
    columns = {row[1] for row in cursor.fetchall()}

    migrations = []

    if "is_paper" not in columns:
        migrations.append(("is_paper", "ALTER TABLE bookmarks ADD COLUMN is_paper BOOLEAN DEFAULT 0"))

    if "pinned" not in columns:
        migrations.append(("pinned", "ALTER TABLE bookmarks ADD COLUMN pinned BOOLEAN DEFAULT 0"))

    if "zotero_key" not in columns:
        migrations.append(("zotero_key", "ALTER TABLE bookmarks ADD COLUMN zotero_key VARCHAR"))

    if not migrations:
        print("All columns already exist. Nothing to migrate.")
        conn.close()
        return

    for name, sql in migrations:
        print(f"Adding column: {name}")
        cursor.execute(sql)

    conn.commit()
    conn.close()
    print(f"Migration complete. Added {len(migrations)} column(s).")

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/bookmarks.db"
    migrate(db_path)
