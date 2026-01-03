from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.database import Base

class CanvasState(Base):
    """Single draft canvas - only one row with id=1"""
    __tablename__ = "canvas_state"

    id = Column(Integer, primary_key=True, default=1)
    content = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class WorkspaceNote(Base):
    """Reference to km note in workspace (content fetched from Kasten)"""
    __tablename__ = "workspace_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    km_note_id = Column(String(255), nullable=False, unique=True)
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)

class WorkspaceConnection(Base):
    """Labeled edge between notes"""
    __tablename__ = "workspace_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note_id = Column(Integer, ForeignKey("workspace_notes.id"), nullable=False)
    to_note_id = Column(Integer, ForeignKey("workspace_notes.id"), nullable=False)
    label = Column(String(255), default="")


class Event(Base):
    """Analytics events for tracking usage."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # 'funnel' or 'feature'
    name = Column(String(255), nullable=False, index=True)
    event_metadata = Column("metadata", Text, nullable=True)  # JSON string
