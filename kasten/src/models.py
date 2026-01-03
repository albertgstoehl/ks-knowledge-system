# kasten/src/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class Source(Base):
    """Archived bookmark sources from Bookmark Manager"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), unique=True, nullable=False)
    title = Column(String(512))
    description = Column(Text)
    content = Column(Text)
    video_id = Column(String(64))
    archived_at = Column(DateTime, server_default=func.now())

    # Relationship
    notes = relationship("Note", back_populates="source")


class Note(Base):
    """Note metadata - content lives in markdown files"""
    __tablename__ = "notes"

    id = Column(String(10), primary_key=True)  # e.g., "1219a"
    title = Column(String(255))
    parent_id = Column(String(10), ForeignKey("notes.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    file_path = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    source = relationship("Source", back_populates="notes")


class Link(Base):
    """Links between notes"""
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note_id = Column(String(10), ForeignKey("notes.id"), nullable=False)
    to_note_id = Column(String(10), ForeignKey("notes.id"), nullable=False)


class Event(Base):
    """Analytics events for tracking usage."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # 'funnel' or 'feature'
    name = Column(String(255), nullable=False, index=True)
    event_metadata = Column("metadata", Text, nullable=True)  # JSON string
