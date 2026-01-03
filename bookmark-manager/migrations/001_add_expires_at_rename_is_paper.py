#!/usr/bin/env python3
"""
Migration: Add expires_at column and rename is_paper to is_thesis

This migration:
1. Adds an 'expires_at' DATETIME column to the bookmarks table (nullable)
2. Renames 'is_paper' column to 'is_thesis'

SQLite 3.25.0+ supports ALTER TABLE ... RENAME COLUMN.
For older versions, we'd need to recreate the table.
"""
import sqlite3
import os
import sys
from datetime import datetime, timedelta


def get_db_path():
    """Get the database path from environment or default"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/bookmarks.db")
    # Extract path from URL
    if db_url.startswith("sqlite"):
        path = db_url.split("///")[-1]
        return path
    return "./data/bookmarks.db"


def check_column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate(db_path=None):
    """Run the migration"""
    if db_path is None:
        db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping migration")
        return True

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check SQLite version
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"SQLite version: {version}")

        major, minor, _ = map(int, version.split('.'))
        supports_rename = (major, minor) >= (3, 25)

        # 1. Add expires_at column if it doesn't exist
        if not check_column_exists(cursor, "bookmarks", "expires_at"):
            print("Adding expires_at column...")
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN expires_at DATETIME")

            # Set expires_at for existing non-protected bookmarks (7 days from now)
            cursor.execute("""
                UPDATE bookmarks
                SET expires_at = datetime('now', '+7 days')
                WHERE pinned = 0 AND is_paper = 0 AND state = 'inbox'
            """)
            print(f"Set expires_at for {cursor.rowcount} existing inbox items")
        else:
            print("expires_at column already exists")

        # 2. Rename is_paper to is_thesis if needed
        has_is_paper = check_column_exists(cursor, "bookmarks", "is_paper")
        has_is_thesis = check_column_exists(cursor, "bookmarks", "is_thesis")

        if has_is_paper and not has_is_thesis:
            if supports_rename:
                print("Renaming is_paper to is_thesis...")
                cursor.execute("ALTER TABLE bookmarks RENAME COLUMN is_paper TO is_thesis")
            else:
                # Fallback for older SQLite: recreate table
                print("SQLite version doesn't support RENAME COLUMN, using table recreation...")

                # Get existing table schema
                cursor.execute("PRAGMA table_info(bookmarks)")
                columns = cursor.fetchall()

                # Build new column definitions
                new_cols = []
                for col in columns:
                    name = col[1]
                    col_type = col[2]
                    not_null = "NOT NULL" if col[3] else ""
                    default = f"DEFAULT {col[4]}" if col[4] else ""

                    if name == "is_paper":
                        name = "is_thesis"

                    new_cols.append(f"{name} {col_type} {not_null} {default}".strip())

                # Create new table
                cursor.execute(f"""
                    CREATE TABLE bookmarks_new ({', '.join(new_cols)})
                """)

                # Copy data
                old_col_names = [c[1] for c in columns]
                new_col_names = ["is_thesis" if c == "is_paper" else c for c in old_col_names]

                cursor.execute(f"""
                    INSERT INTO bookmarks_new ({', '.join(new_col_names)})
                    SELECT {', '.join(old_col_names)} FROM bookmarks
                """)

                # Swap tables
                cursor.execute("DROP TABLE bookmarks")
                cursor.execute("ALTER TABLE bookmarks_new RENAME TO bookmarks")

                print("Table recreated with renamed column")
        elif has_is_thesis:
            print("is_thesis column already exists (already migrated)")
        else:
            print("Neither is_paper nor is_thesis found - schema may differ")

        conn.commit()
        print("Migration completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False

    finally:
        conn.close()


def rollback(db_path=None):
    """Rollback the migration (rename is_thesis back to is_paper, drop expires_at)"""
    if db_path is None:
        db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check SQLite version
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        major, minor, _ = map(int, version.split('.'))
        supports_rename = (major, minor) >= (3, 25)

        if supports_rename:
            if check_column_exists(cursor, "bookmarks", "is_thesis"):
                cursor.execute("ALTER TABLE bookmarks RENAME COLUMN is_thesis TO is_paper")
                print("Renamed is_thesis back to is_paper")

        # Note: SQLite doesn't support DROP COLUMN before 3.35.0
        # For now, just leave expires_at column (it won't hurt)

        conn.commit()
        print("Rollback completed")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Rollback failed: {e}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        db = sys.argv[2] if len(sys.argv) > 2 else None
        rollback(db)
    else:
        db = sys.argv[1] if len(sys.argv) > 1 else None
        migrate(db)
