#!/usr/bin/env python3
"""
Migration script to add is_paper, pinned, and zotero_key columns to bookmarks table.
This is a one-time migration to update the schema.
"""
import sqlite3
import sys

def migrate_database(db_path):
    """Add missing columns to bookmarks table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = {row[1] for row in cursor.fetchall()}

        migrations_needed = []
        if 'is_paper' not in columns:
            migrations_needed.append("is_paper")
        if 'pinned' not in columns:
            migrations_needed.append("pinned")
        if 'zotero_key' not in columns:
            migrations_needed.append("zotero_key")

        if not migrations_needed:
            print("All columns already exist. No migration needed.")
            return True

        print(f"Adding columns: {', '.join(migrations_needed)}")

        # Add missing columns
        if 'is_paper' in migrations_needed:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN is_paper BOOLEAN DEFAULT 0")
            print("Added is_paper column")

        if 'pinned' in migrations_needed:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN pinned BOOLEAN DEFAULT 0")
            print("Added pinned column")

        if 'zotero_key' in migrations_needed:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN zotero_key VARCHAR")
            print("Added zotero_key column")

        # Create indexes
        if 'is_paper' in migrations_needed:
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_bookmarks_is_paper ON bookmarks (is_paper)")
            print("Created index on is_paper")

        if 'pinned' in migrations_needed:
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_bookmarks_pinned ON bookmarks (pinned)")
            print("Created index on pinned")

        conn.commit()

        # Verify migration
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns_after = {row[1] for row in cursor.fetchall()}

        print(f"\nMigration successful! Database now has columns:")
        for col in sorted(columns_after):
            print(f"  - {col}")

        return True

    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "/app/data/bookmarks.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    print(f"Migrating database: {db_path}")
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
