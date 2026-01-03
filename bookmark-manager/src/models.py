from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.sql import func
import enum
from src.database import Base

class BookmarkState(str, enum.Enum):
    inbox = "inbox"
    read = "read"

class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Full markdown from Jina
    state = Column(SQLEnum(BookmarkState), default=BookmarkState.inbox, nullable=False, index=True)
    archive_url = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    read_at = Column(DateTime, nullable=True)
    video_id = Column(String, nullable=True)  # YouTube video ID
    video_timestamp = Column(Integer, default=0)  # Saved position in seconds
    is_thesis = Column(Boolean, default=False, index=True)  # Renamed from is_paper
    pinned = Column(Boolean, default=False, index=True)
    zotero_key = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires

class Feed(Base):
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=True)
    last_fetched_at = Column(DateTime, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class FeedItem(Base):
    __tablename__ = "feed_items"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("feeds.id", ondelete="CASCADE"), nullable=False, index=True)
    guid = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('feed_id', 'guid', name='uq_feed_item_guid'),
    )


class Event(Base):
    """Analytics events for tracking usage."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # 'funnel' or 'feature'
    name = Column(String, nullable=False, index=True)
    event_metadata = Column("metadata", Text, nullable=True)  # JSON string
