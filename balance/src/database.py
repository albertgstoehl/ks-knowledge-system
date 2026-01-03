import aiosqlite
import os
from contextlib import asynccontextmanager

# Default database URL - can be overridden for testing
DATABASE_URL = os.getenv("DATABASE_URL", "./data/balance.db")


def get_database_url():
    """Get current database URL (allows runtime override)."""
    return DATABASE_URL


async def init_db(db_url: str = None):
    """Initialize database with schema."""
    url = db_url or get_database_url()
    async with aiosqlite.connect(url) as db:
        await db.executescript("""
            -- Sessions (Pomodoro)
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ('expected', 'personal', 'youtube')),
                intention TEXT,
                priority_id INTEGER,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                distractions TEXT CHECK (distractions IN ('none', 'some', 'many')),
                did_the_thing BOOLEAN,
                rabbit_hole BOOLEAN,
                claude_used BOOLEAN DEFAULT FALSE,
                duration_minutes INTEGER,
                FOREIGN KEY (priority_id) REFERENCES priorities(id)
            );

            -- Meditation
            CREATE TABLE IF NOT EXISTS meditation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                occurred_at TIMESTAMP,
                time_of_day TEXT CHECK (time_of_day IN ('morning', 'afternoon', 'evening')),
                duration_minutes INTEGER NOT NULL
            );

            -- Exercise
            CREATE TABLE IF NOT EXISTS exercise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                type TEXT NOT NULL CHECK (type IN ('cardio', 'strength')),
                duration_minutes INTEGER NOT NULL,
                intensity TEXT NOT NULL CHECK (intensity IN ('light', 'medium', 'hard'))
            );

            -- Daily Pulse
            CREATE TABLE IF NOT EXISTS daily_pulse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                feeling TEXT NOT NULL CHECK (feeling IN ('heavy', 'okay', 'light')),
                had_connection BOOLEAN NOT NULL,
                connection_type TEXT CHECK (connection_type IN ('friend', 'family', 'partner'))
            );

            -- Nudge Events
            CREATE TABLE IF NOT EXISTS nudge_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                type TEXT NOT NULL,
                response TEXT NOT NULL CHECK (response IN ('stopped', 'continued'))
            );

            -- Limit Changes
            CREATE TABLE IF NOT EXISTS limit_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                setting TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT NOT NULL
            );

            -- Insight Events
            CREATE TABLE IF NOT EXISTS insight_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shown_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                insight_type TEXT NOT NULL,
                insight_text TEXT NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE,
                followed BOOLEAN
            );

            -- Priorities (for Expected sessions)
            CREATE TABLE IF NOT EXISTS priorities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rank INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                archived_at TEXT
            );

            -- Next Up (quick task capture)
            CREATE TABLE IF NOT EXISTS next_up (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                due_date DATE,
                priority_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                position INTEGER DEFAULT 0,
                FOREIGN KEY (priority_id) REFERENCES priorities(id)
            );

            -- Session Analyses (Claude Code transcript analysis)
            CREATE TABLE IF NOT EXISTS session_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                analyzed_at TEXT NOT NULL,

                -- What happened
                projects_used TEXT,
                prompt_count INTEGER,

                -- Analysis results
                intention_alignment TEXT,
                alignment_detail TEXT,
                scope_behavior TEXT,
                scope_detail TEXT,
                project_switches INTEGER,
                tool_appropriate_count INTEGER,
                tool_questionable_count INTEGER,
                tool_questionable_examples TEXT,
                red_flags TEXT,
                one_line_summary TEXT,
                severity TEXT,

                -- Raw reference
                raw_response TEXT
            );

            -- Settings
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                daily_cap INTEGER NOT NULL DEFAULT 10,
                hard_max INTEGER NOT NULL DEFAULT 16,
                evening_cutoff TEXT NOT NULL DEFAULT '19:00',
                rabbit_hole_check INTEGER NOT NULL DEFAULT 3,
                weekly_rest_min INTEGER NOT NULL DEFAULT 1,
                session_duration INTEGER NOT NULL DEFAULT 25,
                short_break INTEGER NOT NULL DEFAULT 5,
                long_break INTEGER NOT NULL DEFAULT 15
            );

            -- App State
            CREATE TABLE IF NOT EXISTS app_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                break_until TIMESTAMP,
                check_in_mode BOOLEAN DEFAULT FALSE,
                north_star TEXT DEFAULT 'Quality time with family and healthy relationships. Community. Being present. Not taking myself too seriously. Exploring the unexplored. Learning, solving problems, and having fun.'
            );

            -- Initialize settings if not exists
            INSERT OR IGNORE INTO settings (id) VALUES (1);
            INSERT OR IGNORE INTO app_state (id) VALUES (1);
        """)

        # Migration: add claude_used if missing (for existing DBs)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN claude_used BOOLEAN DEFAULT FALSE")
        except Exception:
            pass  # Column already exists

        # Migration: add priority_id if missing (for existing DBs)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN priority_id INTEGER")
        except Exception:
            pass  # Column already exists

        # Migration: add next_up_id if missing (for existing DBs)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN next_up_id INTEGER REFERENCES next_up(id)")
        except Exception:
            pass  # Column already exists

        # Migration: add duration_minutes column for youtube sessions
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN duration_minutes INTEGER")
        except Exception:
            pass  # Column already exists

        # Migration: allow youtube session type (recreate table with new CHECK)
        # Check if youtube is already allowed
        try:
            await db.execute("INSERT INTO sessions (type, intention) VALUES ('youtube', 'test')")
            await db.execute("DELETE FROM sessions WHERE intention = 'test' AND type = 'youtube'")
            await db.commit()
        except Exception:
            # Need to migrate - youtube not allowed yet
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('expected', 'personal', 'youtube')),
                    intention TEXT,
                    priority_id INTEGER,
                    next_up_id INTEGER,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    distractions TEXT CHECK (distractions IN ('none', 'some', 'many')),
                    did_the_thing BOOLEAN,
                    rabbit_hole BOOLEAN,
                    claude_used BOOLEAN DEFAULT FALSE,
                    duration_minutes INTEGER,
                    FOREIGN KEY (priority_id) REFERENCES priorities(id),
                    FOREIGN KEY (next_up_id) REFERENCES next_up(id)
                )
            """)
            await db.execute("""
                INSERT INTO sessions_new
                SELECT id, type, intention, priority_id, next_up_id, started_at, ended_at,
                       distractions, did_the_thing, rabbit_hole, claude_used, duration_minutes
                FROM sessions
            """)
            await db.execute("DROP TABLE sessions")
            await db.execute("ALTER TABLE sessions_new RENAME TO sessions")
            await db.commit()

        await db.commit()


@asynccontextmanager
async def get_db(db_url: str = None):
    """Get database connection."""
    url = db_url or get_database_url()
    db = await aiosqlite.connect(url)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
