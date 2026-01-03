from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional, Literal

class BookmarkCreate(BaseModel):
    url: HttpUrl

class BookmarkUpdate(BaseModel):
    state: Optional[Literal["inbox", "read"]] = None

class BookmarkDescriptionUpdate(BaseModel):
    description: str

class BookmarkTitleUpdate(BaseModel):
    title: str

class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    state: str
    archive_url: Optional[str]
    added_at: datetime
    read_at: Optional[datetime]
    video_id: Optional[str]
    video_timestamp: int = 0
    is_thesis: bool = False  # Renamed from is_paper
    pinned: bool = False
    zotero_key: Optional[str] = None
    expires_at: Optional[datetime] = None  # Added


class BookmarkTimestampUpdate(BaseModel):
    timestamp: int  # seconds

class BookmarkPinUpdate(BaseModel):
    pinned: bool

class BookmarkThesisUpdate(BaseModel):
    is_thesis: bool

class SearchRequest(BaseModel):
    query: str
    state: Optional[Literal["inbox", "read"]] = None
    limit: int = 20

class SearchResult(BaseModel):
    bookmark: BookmarkResponse
    score: float


class FeedCreate(BaseModel):
    url: HttpUrl


class FeedUpdate(BaseModel):
    title: str


class FeedItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    feed_id: int
    guid: str
    url: str
    title: Optional[str]
    description: Optional[str]
    published_at: Optional[datetime]
    fetched_at: datetime


class FeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    last_fetched_at: Optional[datetime]
    error_count: int
    created_at: datetime


class FeedWithItemsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    last_fetched_at: Optional[datetime]
    error_count: int
    created_at: datetime
    items: list[FeedItemResponse]


class BookmarkContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: Optional[str]
    content: Optional[str]


class BookmarkExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    title: Optional[str]
    description: Optional[str]
    content: Optional[str]
    video_id: Optional[str]


class CanvasQuoteCreate(BaseModel):
    bookmark_id: int
    quote: str


class CanvasQuoteResponse(BaseModel):
    success: bool
    message: str
