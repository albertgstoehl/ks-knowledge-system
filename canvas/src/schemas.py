from pydantic import BaseModel, Field
from datetime import datetime

class CanvasContent(BaseModel):
    content: str

class CanvasResponse(BaseModel):
    content: str
    updated_at: datetime | None

class QuoteRequest(BaseModel):
    quote: str = Field(alias="text")
    source_url: str
    source_title: str

    class Config:
        populate_by_name = True

class WorkspaceNoteCreate(BaseModel):
    km_note_id: str

class WorkspaceNoteResponse(BaseModel):
    id: int
    km_note_id: str
    x: float
    y: float

class ConnectionCreate(BaseModel):
    from_note_id: int
    to_note_id: int
    label: str

class ConnectionUpdate(BaseModel):
    label: str

class ConnectionResponse(BaseModel):
    id: int
    from_note_id: int
    to_note_id: int
    label: str

class WorkspaceResponse(BaseModel):
    notes: list[WorkspaceNoteResponse]
    connections: list[ConnectionResponse]
