# Bookmark Manager API Implementation Plan

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** Build a minimal bookmark management system with semantic search, Web Archive integration, and automated backups.

**Architecture:** FastAPI REST API with SQLite database (using sqlite-vss for vector search), async background jobs for metadata extraction and archiving, Jina AI Reader for page content extraction, and automated backup system.

**Tech Stack:** FastAPI, SQLite with sqlite-vss extension, sentence-transformers (all-MiniLM-L6-v2), Jina AI Reader API, Docker

---

## Task 1: Project Structure & Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/main.py`
- Create: `tests/__init__.py`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `README.md`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "bookmark-manager"
version = "0.1.0"
description = "Minimal bookmark manager with semantic search"
requires-python = ">=3.11"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

**Step 2: Create requirements.txt**

```txt
fastapi==0.115.0
uvicorn[standard]==0.31.0
pydantic==2.9.2
pydantic-settings==2.5.2
sqlalchemy==2.0.35
aiosqlite==0.20.0
sqlite-vss==0.1.2
sentence-transformers==3.2.0
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
```

**Step 3: Create basic FastAPI app**

File: `src/main.py`
```python
from fastapi import FastAPI

app = FastAPI(
    title="Bookmark Manager API",
    description="Minimal bookmark management with semantic search",
    version="0.1.0"
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**Step 4: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 5: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///app/data/bookmarks.db
      - JINA_API_KEY=${JINA_API_KEY:-}
    restart: unless-stopped
```

**Step 6: Create .env.example**

```
# Optional: Jina AI API key for higher rate limits
JINA_API_KEY=

# Database
DATABASE_URL=sqlite:///app/data/bookmarks.db
```

**Step 7: Create README.md**

```markdown
# Bookmark Manager

Minimal bookmark management system with semantic search.

## Features

- Add bookmarks via REST API
- Semantic search using embeddings
- Keyword search
- Web Archive integration
- Automated backups
- Filter by read/unread status

## Quick Start

1. Copy `.env.example` to `.env`
2. Run: `docker-compose up -d`
3. API available at http://localhost:8000
4. Docs at http://localhost:8000/docs

## API Endpoints

- `POST /bookmarks` - Add bookmark
- `GET /bookmarks` - List bookmarks
- `PATCH /bookmarks/{id}` - Update bookmark
- `DELETE /bookmarks/{id}` - Delete bookmark
- `POST /search/semantic` - Semantic search
- `POST /search/keyword` - Keyword search
- `POST /backup/create` - Create backup
- `GET /backup/list` - List backups
```

**Step 8: Test basic setup**

Run: `python -m pytest tests/ -v` (should pass with no tests)

**Step 9: Commit**

```bash
git add .
git commit -m "feat: initial project structure and dependencies"
```

---

## Task 2: Database Models & Schema

**Files:**
- Create: `src/database.py`
- Create: `src/models.py`
- Create: `src/schemas.py`
- Create: `tests/test_database.py`

**Step 1: Write failing test for database connection**

File: `tests/test_database.py`
```python
import pytest
from src.database import init_db, get_db
import os

@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initializes successfully"""
    test_db = "test_bookmarks.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    await init_db(f"sqlite:///{test_db}")

    # Should create database file
    assert os.path.exists(test_db)

    # Cleanup
    os.remove(test_db)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_database_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.database'"

**Step 3: Create database.py with SQLAlchemy setup**

File: `src/database.py`
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
import os

class Base(DeclarativeBase):
    pass

engine = None
async_session_maker = None

async def init_db(database_url: str = None):
    global engine, async_session_maker

    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bookmarks.db")

    # Convert sync sqlite URL to async
    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session_maker() as session:
        yield session
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_database_initialization -v`
Expected: PASS

**Step 5: Create SQLAlchemy models**

File: `src/models.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime
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
    state = Column(SQLEnum(BookmarkState), default=BookmarkState.inbox, nullable=False, index=True)
    archive_url = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    read_at = Column(DateTime, nullable=True)

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    bookmark_id = Column(Integer, ForeignKey("bookmarks.id", ondelete="CASCADE"), nullable=False)
    embedding_data = Column(Text, nullable=False)  # JSON serialized vector
```

**Step 6: Create Pydantic schemas**

File: `src/schemas.py`
```python
from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional, Literal

class BookmarkCreate(BaseModel):
    url: HttpUrl

class BookmarkUpdate(BaseModel):
    state: Optional[Literal["inbox", "read"]] = None

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

class SearchRequest(BaseModel):
    query: str
    state: Optional[Literal["inbox", "read"]] = None
    limit: int = 20

class SearchResult(BaseModel):
    bookmark: BookmarkResponse
    score: float
```

**Step 7: Write test for bookmark model**

File: `tests/test_database.py` (add to existing)
```python
from src.models import Bookmark, BookmarkState
from sqlalchemy import select

@pytest.mark.asyncio
async def test_bookmark_creation():
    """Test creating a bookmark"""
    test_db = "test_bookmarks.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    await init_db(f"sqlite+aiosqlite:///{test_db}")

    async with async_session_maker() as session:
        bookmark = Bookmark(
            url="https://example.com",
            title="Example",
            state=BookmarkState.inbox
        )
        session.add(bookmark)
        await session.commit()

        result = await session.execute(select(Bookmark))
        saved_bookmark = result.scalar_one()

        assert saved_bookmark.url == "https://example.com"
        assert saved_bookmark.state == BookmarkState.inbox

    os.remove(test_db)
```

**Step 8: Run test**

Run: `pytest tests/test_database.py::test_bookmark_creation -v`
Expected: PASS

**Step 9: Commit**

```bash
git add src/database.py src/models.py src/schemas.py tests/test_database.py
git commit -m "feat: add database models and schemas"
```

---

## Task 3: Jina AI Integration

**Files:**
- Create: `src/services/__init__.py`
- Create: `src/services/jina_client.py`
- Create: `tests/test_jina_client.py`

**Step 1: Write failing test for Jina client**

File: `tests/test_jina_client.py`
```python
import pytest
from src.services.jina_client import JinaClient

@pytest.mark.asyncio
async def test_jina_extract_metadata():
    """Test Jina AI metadata extraction"""
    client = JinaClient()
    result = await client.extract_metadata("https://example.com")

    assert "title" in result
    assert "description" in result
    assert "content" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_jina_client.py -v`
Expected: FAIL

**Step 3: Implement Jina client**

File: `src/services/jina_client.py`
```python
import httpx
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class JinaClient:
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://r.jina.ai"
        self.api_key = api_key
        self.timeout = 30.0

    async def extract_metadata(self, url: str) -> Dict[str, str]:
        """Extract title, description, and content from URL using Jina AI"""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/{url}",
                    headers=headers,
                    follow_redirects=True
                )
                response.raise_for_status()

                # Jina returns markdown content
                content = response.text

                # Extract title (first # heading)
                title = ""
                description = ""
                lines = content.split("\n")

                for line in lines:
                    if line.startswith("# ") and not title:
                        title = line[2:].strip()
                    elif line.strip() and not line.startswith("#") and not description:
                        description = line.strip()
                        break

                return {
                    "title": title or "Untitled",
                    "description": description or "",
                    "content": content
                }

        except httpx.HTTPError as e:
            logger.error(f"Jina API error for {url}: {e}")
            return {
                "title": "Error fetching content",
                "description": "",
                "content": ""
            }
        except Exception as e:
            logger.error(f"Unexpected error extracting metadata for {url}: {e}")
            return {
                "title": "Error",
                "description": "",
                "content": ""
            }
```

**Step 4: Run test**

Run: `pytest tests/test_jina_client.py -v`
Expected: PASS (network test, may be slow)

**Step 5: Commit**

```bash
git add src/services/ tests/test_jina_client.py
git commit -m "feat: add Jina AI client for metadata extraction"
```

---

## Task 4: Embedding Service

**Files:**
- Create: `src/services/embedding_service.py`
- Create: `tests/test_embedding_service.py`

**Step 1: Write failing test for embedding generation**

File: `tests/test_embedding_service.py`
```python
import pytest
from src.services.embedding_service import EmbeddingService

def test_embedding_generation():
    """Test embedding generation from text"""
    service = EmbeddingService()
    text = "This is a test article about technology"

    embedding = service.generate_embedding(text)

    assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
    assert all(isinstance(x, float) for x in embedding)

def test_embedding_similarity():
    """Test embedding similarity calculation"""
    service = EmbeddingService()

    text1 = "Python programming language"
    text2 = "Python coding and development"
    text3 = "Cooking recipes for dinner"

    emb1 = service.generate_embedding(text1)
    emb2 = service.generate_embedding(text2)
    emb3 = service.generate_embedding(text3)

    # Similar texts should have higher similarity
    sim_12 = service.cosine_similarity(emb1, emb2)
    sim_13 = service.cosine_similarity(emb1, emb3)

    assert sim_12 > sim_13
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_embedding_service.py -v`
Expected: FAIL

**Step 3: Implement embedding service**

File: `src/services/embedding_service.py`
```python
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding service with specified model"""
        self.model = SentenceTransformer(model_name)
        logger.info(f"Loaded embedding model: {model_name}")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 384

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        return float(dot_product / (norm_v1 * norm_v2))
```

**Step 4: Run test**

Run: `pytest tests/test_embedding_service.py -v`
Expected: PASS (may take time on first run to download model)

**Step 5: Commit**

```bash
git add src/services/embedding_service.py tests/test_embedding_service.py
git commit -m "feat: add embedding service with sentence-transformers"
```

---

## Task 5: Web Archive Integration

**Files:**
- Create: `src/services/archive_service.py`
- Create: `tests/test_archive_service.py`

**Step 1: Write failing test for archive submission**

File: `tests/test_archive_service.py`
```python
import pytest
from src.services.archive_service import ArchiveService

@pytest.mark.asyncio
async def test_archive_submission():
    """Test submitting URL to Web Archive"""
    service = ArchiveService()
    result = await service.submit_to_archive("https://example.com")

    assert result is not None
    assert "web.archive.org" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_archive_service.py -v`
Expected: FAIL

**Step 3: Implement archive service**

File: `src/services/archive_service.py`
```python
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ArchiveService:
    def __init__(self):
        self.save_url = "https://web.archive.org/save"
        self.timeout = 60.0
        self.max_retries = 3

    async def submit_to_archive(self, url: str) -> Optional[str]:
        """Submit URL to Web Archive and return snapshot URL"""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(f"{self.save_url}/{url}")

                    if response.status_code == 200:
                        # Archive.org redirects to the snapshot URL
                        snapshot_url = str(response.url)
                        logger.info(f"Successfully archived {url}: {snapshot_url}")
                        return snapshot_url
                    else:
                        logger.warning(f"Archive attempt {attempt + 1} failed with status {response.status_code}")

            except httpx.TimeoutException:
                logger.warning(f"Archive timeout for {url} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Archive error for {url}: {e}")

        logger.error(f"Failed to archive {url} after {self.max_retries} attempts")
        return None
```

**Step 4: Run test**

Run: `pytest tests/test_archive_service.py -v`
Expected: PASS (network test, may be slow)

**Step 5: Commit**

```bash
git add src/services/archive_service.py tests/test_archive_service.py
git commit -m "feat: add Web Archive integration service"
```

---

## Task 6: Background Job Processing

**Files:**
- Create: `src/services/background_jobs.py`
- Modify: `src/main.py`

**Step 1: Create background job handler**

File: `src/services/background_jobs.py`
```python
from src.services.jina_client import JinaClient
from src.services.embedding_service import EmbeddingService
from src.services.archive_service import ArchiveService
from src.models import Bookmark, Embedding
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

logger = logging.getLogger(__name__)

class BackgroundJobService:
    def __init__(self, jina_api_key: str = None):
        self.jina_client = JinaClient(api_key=jina_api_key)
        self.embedding_service = None  # Lazy load (heavy)
        self.archive_service = ArchiveService()

    def _get_embedding_service(self) -> EmbeddingService:
        """Lazy load embedding service"""
        if self.embedding_service is None:
            self.embedding_service = EmbeddingService()
        return self.embedding_service

    async def process_new_bookmark(self, bookmark_id: int, session: AsyncSession):
        """Process a new bookmark: fetch metadata, generate embedding, archive"""
        logger.info(f"Processing bookmark {bookmark_id}")

        # Fetch bookmark
        bookmark = await session.get(Bookmark, bookmark_id)
        if not bookmark:
            logger.error(f"Bookmark {bookmark_id} not found")
            return

        # 1. Extract metadata with Jina
        logger.info(f"Extracting metadata for {bookmark.url}")
        metadata = await self.jina_client.extract_metadata(bookmark.url)

        bookmark.title = metadata.get("title", "Untitled")
        bookmark.description = metadata.get("description", "")

        # 2. Generate embedding
        logger.info(f"Generating embedding for bookmark {bookmark_id}")
        embedding_service = self._get_embedding_service()
        text_to_embed = f"{bookmark.title} {bookmark.description}"
        embedding_vector = embedding_service.generate_embedding(text_to_embed)

        # Save embedding
        embedding = Embedding(
            bookmark_id=bookmark_id,
            embedding_data=json.dumps(embedding_vector)
        )
        session.add(embedding)

        # 3. Submit to Web Archive
        logger.info(f"Submitting to Web Archive: {bookmark.url}")
        archive_url = await self.archive_service.submit_to_archive(bookmark.url)
        if archive_url:
            bookmark.archive_url = archive_url

        await session.commit()
        logger.info(f"Completed processing bookmark {bookmark_id}")
```

**Step 2: Update main.py to initialize job service**

File: `src/main.py`
```python
from fastapi import FastAPI
from src.services.background_jobs import BackgroundJobService
import os

app = FastAPI(
    title="Bookmark Manager API",
    description="Minimal bookmark management with semantic search",
    version="0.1.0"
)

# Initialize services
jina_api_key = os.getenv("JINA_API_KEY")
background_job_service = BackgroundJobService(jina_api_key=jina_api_key)

@app.on_event("startup")
async def startup():
    from src.database import init_db
    await init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**Step 3: Commit**

```bash
git add src/services/background_jobs.py src/main.py
git commit -m "feat: add background job processing service"
```

---

## Task 7: Bookmark CRUD Endpoints

**Files:**
- Create: `src/routers/__init__.py`
- Create: `src/routers/bookmarks.py`
- Modify: `src/main.py`
- Create: `tests/test_bookmarks_api.py`

**Step 1: Write failing test for bookmark creation**

File: `tests/test_bookmarks_api.py`
```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_create_bookmark():
    """Test creating a new bookmark"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/bookmarks",
            json={"url": "https://example.com"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com"
        assert data["state"] == "inbox"

@pytest.mark.asyncio
async def test_list_bookmarks():
    """Test listing bookmarks"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create bookmark first
        await client.post("/bookmarks", json={"url": "https://example.com"})

        # List bookmarks
        response = await client.get("/bookmarks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_bookmarks_api.py -v`
Expected: FAIL (endpoints don't exist)

**Step 3: Implement bookmark router**

File: `src/routers/bookmarks.py`
```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Bookmark, BookmarkState
from src.schemas import BookmarkCreate, BookmarkUpdate, BookmarkResponse
from src.main import background_job_service
from typing import List, Optional

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """Create a new bookmark"""
    # Check for duplicate
    result = await session.execute(
        select(Bookmark).where(Bookmark.url == str(bookmark_data.url))
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bookmark with this URL already exists"
        )

    # Create bookmark
    bookmark = Bookmark(
        url=str(bookmark_data.url),
        state=BookmarkState.inbox
    )
    session.add(bookmark)
    await session.commit()
    await session.refresh(bookmark)

    # Queue background processing
    background_tasks.add_task(
        background_job_service.process_new_bookmark,
        bookmark.id,
        session
    )

    return bookmark

@router.get("", response_model=List[BookmarkResponse])
async def list_bookmarks(
    state: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
):
    """List bookmarks with optional state filter"""
    query = select(Bookmark)

    if state:
        try:
            state_enum = BookmarkState(state)
            query = query.where(Bookmark.state == state_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state. Must be 'inbox' or 'read'"
            )

    query = query.order_by(Bookmark.added_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    bookmarks = result.scalars().all()

    return bookmarks

@router.get("/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(
    bookmark_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get a single bookmark by ID"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    return bookmark

@router.patch("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    update_data: BookmarkUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Update bookmark (mark as read/inbox)"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    if update_data.state:
        bookmark.state = BookmarkState(update_data.state)
        if update_data.state == "read":
            from datetime import datetime
            bookmark.read_at = datetime.utcnow()
        else:
            bookmark.read_at = None

    await session.commit()
    await session.refresh(bookmark)

    return bookmark

@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Delete a bookmark"""
    bookmark = await session.get(Bookmark, bookmark_id)

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    await session.delete(bookmark)
    await session.commit()
```

**Step 4: Register router in main.py**

File: `src/main.py` (add after app initialization)
```python
from src.routers import bookmarks

app.include_router(bookmarks.router)
```

**Step 5: Run test**

Run: `pytest tests/test_bookmarks_api.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/routers/ tests/test_bookmarks_api.py src/main.py
git commit -m "feat: add bookmark CRUD endpoints"
```

---

## Task 8: Search Endpoints

**Files:**
- Create: `src/routers/search.py`
- Create: `src/services/search_service.py`
- Modify: `src/main.py`
- Create: `tests/test_search.py`

**Step 1: Write failing test for semantic search**

File: `tests/test_search.py`
```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_semantic_search():
    """Test semantic search"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test bookmarks
        await client.post("/bookmarks", json={"url": "https://python.org"})

        # Wait a moment for background processing
        import asyncio
        await asyncio.sleep(2)

        # Search
        response = await client.post(
            "/search/semantic",
            json={"query": "python programming", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_keyword_search():
    """Test keyword search"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Search
        response = await client.post(
            "/search/keyword",
            json={"query": "python", "limit": 10}
        )

        assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_search.py -v`
Expected: FAIL

**Step 3: Implement search service**

File: `src/services/search_service.py`
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, text
from src.models import Bookmark, Embedding, BookmarkState
from src.services.embedding_service import EmbeddingService
from typing import List, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self.embedding_service = None

    def _get_embedding_service(self) -> EmbeddingService:
        if self.embedding_service is None:
            self.embedding_service = EmbeddingService()
        return self.embedding_service

    async def semantic_search(
        self,
        query: str,
        session: AsyncSession,
        state_filter: Optional[str] = None,
        limit: int = 20
    ) -> List[Tuple[Bookmark, float]]:
        """Semantic search using embeddings"""
        # Generate query embedding
        embedding_service = self._get_embedding_service()
        query_embedding = embedding_service.generate_embedding(query)

        # Fetch all embeddings (for small scale, this is fine)
        stmt = select(Embedding, Bookmark).join(Bookmark)

        if state_filter:
            state_enum = BookmarkState(state_filter)
            stmt = stmt.where(Bookmark.state == state_enum)

        result = await session.execute(stmt)
        rows = result.all()

        # Calculate similarities
        results = []
        for embedding_row, bookmark in rows:
            stored_embedding = json.loads(embedding_row.embedding_data)
            similarity = embedding_service.cosine_similarity(
                query_embedding,
                stored_embedding
            )
            results.append((bookmark, similarity))

        # Sort by similarity and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def keyword_search(
        self,
        query: str,
        session: AsyncSession,
        state_filter: Optional[str] = None,
        limit: int = 20
    ) -> List[Bookmark]:
        """Simple keyword search on title and description"""
        stmt = select(Bookmark).where(
            or_(
                Bookmark.title.ilike(f"%{query}%"),
                Bookmark.description.ilike(f"%{query}%"),
                Bookmark.url.ilike(f"%{query}%")
            )
        )

        if state_filter:
            state_enum = BookmarkState(state_filter)
            stmt = stmt.where(Bookmark.state == state_enum)

        stmt = stmt.order_by(Bookmark.added_at.desc()).limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()
```

**Step 4: Implement search router**

File: `src/routers/search.py`
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas import SearchRequest, SearchResult, BookmarkResponse
from src.services.search_service import SearchService
from typing import List

router = APIRouter(prefix="/search", tags=["search"])
search_service = SearchService()

@router.post("/semantic", response_model=List[SearchResult])
async def semantic_search(
    search_data: SearchRequest,
    session: AsyncSession = Depends(get_db)
):
    """Semantic search using embeddings"""
    results = await search_service.semantic_search(
        query=search_data.query,
        session=session,
        state_filter=search_data.state,
        limit=search_data.limit
    )

    return [
        SearchResult(
            bookmark=BookmarkResponse.model_validate(bookmark),
            score=score
        )
        for bookmark, score in results
    ]

@router.post("/keyword", response_model=List[BookmarkResponse])
async def keyword_search(
    search_data: SearchRequest,
    session: AsyncSession = Depends(get_db)
):
    """Keyword search on title, description, and URL"""
    results = await search_service.keyword_search(
        query=search_data.query,
        session=session,
        state_filter=search_data.state,
        limit=search_data.limit
    )

    return [BookmarkResponse.model_validate(b) for b in results]
```

**Step 5: Register search router**

File: `src/main.py`
```python
from src.routers import bookmarks, search

app.include_router(bookmarks.router)
app.include_router(search.router)
```

**Step 6: Run test**

Run: `pytest tests/test_search.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/routers/search.py src/services/search_service.py src/main.py tests/test_search.py
git commit -m "feat: add semantic and keyword search endpoints"
```

---

## Task 9: Backup System

**Files:**
- Create: `src/routers/backup.py`
- Create: `src/services/backup_service.py`
- Modify: `src/main.py`
- Create: `tests/test_backup.py`

**Step 1: Write failing test for backup**

File: `tests/test_backup.py`
```python
import pytest
from src.services.backup_service import BackupService
import os

@pytest.mark.asyncio
async def test_create_backup():
    """Test creating a database backup"""
    service = BackupService(
        db_path="test_bookmarks.db",
        backup_dir="test_backups"
    )

    # Create test database
    import sqlite3
    conn = sqlite3.connect("test_bookmarks.db")
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.close()

    # Create backup
    backup_path = await service.create_backup()

    assert os.path.exists(backup_path)
    assert backup_path.endswith(".db.gz")

    # Cleanup
    os.remove("test_bookmarks.db")
    if os.path.exists("test_backups"):
        import shutil
        shutil.rmtree("test_backups")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_backup.py -v`
Expected: FAIL

**Step 3: Implement backup service**

File: `src/services/backup_service.py`
```python
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
```

**Step 4: Run test**

Run: `pytest tests/test_backup.py -v`
Expected: PASS

**Step 5: Implement backup router**

File: `src/routers/backup.py`
```python
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from src.services.backup_service import BackupService
from typing import List, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/backup", tags=["backup"])
backup_service = BackupService()

class BackupInfo(BaseModel):
    filename: str
    size: int
    created_at: str

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_backup():
    """Create a new database backup"""
    try:
        backup_path = await backup_service.create_backup()
        return {
            "message": "Backup created successfully",
            "path": backup_path
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup failed: {str(e)}"
        )

@router.get("/list", response_model=List[BackupInfo])
async def list_backups():
    """List all available backups"""
    backups = await backup_service.list_backups()
    return backups

@router.post("/restore/{backup_filename}")
async def restore_backup(backup_filename: str):
    """Restore database from a backup"""
    try:
        await backup_service.restore_backup(backup_filename)
        return {"message": "Backup restored successfully"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {str(e)}"
        )

@router.get("/download/{backup_filename}")
async def download_backup(backup_filename: str):
    """Download a backup file"""
    backups = await backup_service.list_backups()
    backup = next((b for b in backups if b["filename"] == backup_filename), None)

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )

    return FileResponse(
        path=backup["path"],
        filename=backup_filename,
        media_type="application/gzip"
    )
```

**Step 6: Register backup router**

File: `src/main.py`
```python
from src.routers import bookmarks, search, backup

app.include_router(bookmarks.router)
app.include_router(search.router)
app.include_router(backup.router)
```

**Step 7: Run test**

Run: `pytest tests/test_backup.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add src/routers/backup.py src/services/backup_service.py src/main.py tests/test_backup.py
git commit -m "feat: add backup and restore functionality"
```

---

## Task 10: CLI Tool

**Files:**
- Create: `cli/bookmark_cli.py`
- Create: `cli/requirements.txt`
- Create: `cli/README.md`

**Step 1: Create CLI requirements**

File: `cli/requirements.txt`
```txt
httpx==0.27.2
click==8.1.7
rich==13.9.2
```

**Step 2: Implement CLI**

File: `cli/bookmark_cli.py`
```python
#!/usr/bin/env python3
import click
import httpx
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional

console = Console()

API_BASE_URL = "http://localhost:8000"

@click.group()
def cli():
    """Bookmark Manager CLI"""
    pass

@cli.command()
@click.argument('url')
def add(url: str):
    """Add a new bookmark"""
    try:
        response = httpx.post(f"{API_BASE_URL}/bookmarks", json={"url": url})
        response.raise_for_status()

        data = response.json()
        console.print(f"[green]✓[/green] Added bookmark: {data['url']}")
        console.print(f"  ID: {data['id']}")
        console.print(f"  State: {data['state']}")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.option('--state', type=click.Choice(['inbox', 'read']), help='Filter by state')
@click.option('--limit', default=20, help='Number of results')
def list(state: Optional[str], limit: int):
    """List bookmarks"""
    params = {"limit": limit}
    if state:
        params["state"] = state

    try:
        response = httpx.get(f"{API_BASE_URL}/bookmarks", params=params)
        response.raise_for_status()

        bookmarks = response.json()

        if not bookmarks:
            console.print("[yellow]No bookmarks found[/yellow]")
            return

        table = Table(title="Bookmarks")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("State", style="magenta")
        table.add_column("URL", style="blue")

        for bm in bookmarks:
            table.add_row(
                str(bm['id']),
                bm['title'] or "Untitled",
                bm['state'],
                bm['url'][:50] + "..." if len(bm['url']) > 50 else bm['url']
            )

        console.print(table)
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.argument('query')
@click.option('--semantic', is_flag=True, help='Use semantic search')
@click.option('--state', type=click.Choice(['inbox', 'read']), help='Filter by state')
@click.option('--limit', default=10, help='Number of results')
def search(query: str, semantic: bool, state: Optional[str], limit: int):
    """Search bookmarks"""
    endpoint = "semantic" if semantic else "keyword"

    payload = {
        "query": query,
        "limit": limit
    }
    if state:
        payload["state"] = state

    try:
        response = httpx.post(f"{API_BASE_URL}/search/{endpoint}", json=payload)
        response.raise_for_status()

        results = response.json()

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        table = Table(title=f"Search Results: '{query}'")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        if semantic:
            table.add_column("Score", style="green")
        table.add_column("URL", style="blue")

        for result in results:
            bm = result.get('bookmark', result)
            row = [
                str(bm['id']),
                bm['title'] or "Untitled",
            ]
            if semantic:
                row.append(f"{result['score']:.3f}")
            row.append(bm['url'][:40] + "..." if len(bm['url']) > 40 else bm['url'])

            table.add_row(*row)

        console.print(table)
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.argument('bookmark_id', type=int)
@click.argument('state', type=click.Choice(['inbox', 'read']))
def mark(bookmark_id: int, state: str):
    """Mark bookmark as read/inbox"""
    try:
        response = httpx.patch(
            f"{API_BASE_URL}/bookmarks/{bookmark_id}",
            json={"state": state}
        )
        response.raise_for_status()

        console.print(f"[green]✓[/green] Marked bookmark {bookmark_id} as {state}")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.argument('bookmark_id', type=int)
def delete(bookmark_id: int):
    """Delete a bookmark"""
    if click.confirm(f"Delete bookmark {bookmark_id}?"):
        try:
            response = httpx.delete(f"{API_BASE_URL}/bookmarks/{bookmark_id}")
            response.raise_for_status()

            console.print(f"[green]✓[/green] Deleted bookmark {bookmark_id}")
        except httpx.HTTPError as e:
            console.print(f"[red]Error:[/red] {e}")

@cli.command()
def backup():
    """Create a database backup"""
    try:
        response = httpx.post(f"{API_BASE_URL}/backup/create")
        response.raise_for_status()

        data = response.json()
        console.print(f"[green]✓[/green] Backup created: {data['path']}")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

if __name__ == '__main__':
    cli()
```

**Step 3: Make CLI executable**

Run: `chmod +x cli/bookmark_cli.py`

**Step 4: Create CLI README**

File: `cli/README.md`
```markdown
# Bookmark Manager CLI

Command-line interface for the Bookmark Manager API.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Make sure the API is running on `http://localhost:8000`.

### Add a bookmark
```bash
./bookmark_cli.py add "https://example.com"
```

### List bookmarks
```bash
./bookmark_cli.py list
./bookmark_cli.py list --state inbox
./bookmark_cli.py list --limit 50
```

### Search
```bash
# Keyword search
./bookmark_cli.py search "python programming"

# Semantic search
./bookmark_cli.py search --semantic "article about consumer experience"

# Filter by state
./bookmark_cli.py search --state inbox "technology"
```

### Mark as read
```bash
./bookmark_cli.py mark 1 read
./bookmark_cli.py mark 1 inbox
```

### Delete bookmark
```bash
./bookmark_cli.py delete 1
```

### Backup
```bash
./bookmark_cli.py backup
```

## Configuration

Set the API URL with environment variable:
```bash
export BOOKMARK_API_URL="http://your-server:8000"
```
```

**Step 5: Commit**

```bash
chmod +x cli/bookmark_cli.py
git add cli/
git commit -m "feat: add CLI tool for bookmark management"
```

---

## Task 11: Testing & Documentation

**Files:**
- Create: `pytest.ini`
- Create: `.github/workflows/tests.yml` (optional)
- Update: `README.md`

**Step 1: Create pytest configuration**

File: `pytest.ini`
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short
```

**Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 3: Update main README with complete documentation**

File: `README.md` (replace content)
```markdown
# Bookmark Manager

Minimal bookmark management system with semantic search, Web Archive integration, and automated backups.

## Features

- **Easy Input**: Add bookmarks via REST API (CLI, future: Telegram bot, browser extension)
- **Smart Search**:
  - Semantic search using embeddings ("that article about everything getting worse")
  - Keyword search on title, description, and URL
  - Filter by read/unread status
- **Web Archive**: Automatic snapshot creation on archive.org
- **State Management**: Simple inbox/read workflow
- **Automated Backups**: Daily backups with compression
- **CLI Tool**: Command-line interface for quick access

## Tech Stack

- **Backend**: FastAPI + Python 3.11
- **Database**: SQLite with sqlite-vss for vector search
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Content Extraction**: Jina AI Reader API
- **Deployment**: Docker Compose

## Quick Start

### 1. Clone and setup

```bash
git clone https://git.fml128.ch/albert/bookmark-manager.git
cd bookmark-manager
cp .env.example .env
```

### 2. Run with Docker

```bash
docker-compose up -d
```

### 3. Access API

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

### 4. Use CLI

```bash
cd cli
pip install -r requirements.txt
./bookmark_cli.py add "https://example.com"
./bookmark_cli.py search --semantic "python programming"
```

## API Endpoints

### Bookmarks

- `POST /bookmarks` - Add new bookmark
- `GET /bookmarks` - List bookmarks (optional: `?state=inbox|read&limit=20`)
- `GET /bookmarks/{id}` - Get single bookmark
- `PATCH /bookmarks/{id}` - Update bookmark state
- `DELETE /bookmarks/{id}` - Delete bookmark

### Search

- `POST /search/semantic` - Semantic search
- `POST /search/keyword` - Keyword search

Request body:
```json
{
  "query": "article about consumer experience",
  "state": "inbox",  // optional: "inbox" or "read"
  "limit": 20
}
```

### Backup

- `POST /backup/create` - Create backup
- `GET /backup/list` - List available backups
- `POST /backup/restore/{filename}` - Restore from backup
- `GET /backup/download/{filename}` - Download backup file

## Development

### Run tests

```bash
pytest tests/ -v
```

### Local development without Docker

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

uvicorn src.main:app --reload
```

## Configuration

Environment variables in `.env`:

- `DATABASE_URL` - SQLite database path (default: `sqlite:///app/data/bookmarks.db`)
- `JINA_API_KEY` - Optional Jina AI API key for higher rate limits

## Backup Strategy

- **Automatic**: Daily backups (configure cron in container)
- **Manual**: `POST /backup/create` or `./bookmark_cli.py backup`
- **Storage**: `/app/data/backups` (mounted volume)
- **Format**: Compressed SQLite files (`.db.gz`)
- **Retention**: Last 7 daily + 4 weekly backups

## Future Enhancements

- Telegram bot integration
- Email forwarding for bookmark input
- Browser extension
- LLM-enhanced search (hybrid approach)
- Multi-user support
- Tags and collections
- Full-text search on archived content

## License

MIT
```

**Step 4: Commit**

```bash
git add pytest.ini README.md
git commit -m "docs: add testing configuration and comprehensive documentation"
```

---

## Task 12: Deployment & Production Setup

**Files:**
- Create: `scripts/backup_cron.sh`
- Create: `scripts/setup_cron.sh`
- Update: `Dockerfile`
- Update: `docker-compose.yml`

**Step 1: Create backup cron script**

File: `scripts/backup_cron.sh`
```bash
#!/bin/bash
# Daily backup script

BACKUP_DIR="/app/data/backups"
MAX_DAILY=7
MAX_WEEKLY=4

# Create backup
curl -X POST http://localhost:8000/backup/create

# Cleanup old backups
# Keep last 7 daily backups
cd "$BACKUP_DIR"
ls -t backup_*.db.gz | tail -n +$((MAX_DAILY + 1)) | xargs -r rm

# Keep weekly backups (first backup of each week)
# This is simplified - in production, use proper date logic
```

**Step 2: Make script executable**

Run: `chmod +x scripts/backup_cron.sh`

**Step 3: Update Dockerfile for production**

File: `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download embedding model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create data directory
RUN mkdir -p /app/data /app/data/backups

# Setup cron for daily backups
RUN echo "0 2 * * * /app/scripts/backup_cron.sh" | crontab -

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["sh", "-c", "cron && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
```

**Step 4: Update docker-compose for production**

File: `docker-compose.yml`
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: bookmark-manager-api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///app/data/bookmarks.db
      - JINA_API_KEY=${JINA_API_KEY:-}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Nginx reverse proxy for SSL
  # nginx:
  #   image: nginx:alpine
  #   ports:
  #     - "80:80"
  #     - "443:443"
  #   volumes:
  #     - ./nginx.conf:/etc/nginx/nginx.conf:ro
  #     - ./certs:/etc/nginx/certs:ro
  #   depends_on:
  #     - api
  #   restart: unless-stopped
```

**Step 5: Build and test Docker image**

Run:
```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

**Step 6: Test health endpoint**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"healthy"}`

**Step 7: Commit**

```bash
git add scripts/ Dockerfile docker-compose.yml
git commit -m "feat: add production deployment configuration with automated backups"
```

---

## Task 13: Final Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write end-to-end integration test**

File: `tests/test_integration.py`
```python
import pytest
from httpx import AsyncClient
from src.main import app
import asyncio

@pytest.mark.asyncio
async def test_full_bookmark_workflow():
    """Test complete workflow: add → search → mark read → search filtered"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Add bookmark
        response = await client.post(
            "/bookmarks",
            json={"url": "https://python.org"}
        )
        assert response.status_code == 201
        bookmark = response.json()
        bookmark_id = bookmark["id"]
        assert bookmark["state"] == "inbox"

        # 2. Wait for background processing
        await asyncio.sleep(3)

        # 3. Verify bookmark was processed
        response = await client.get(f"/bookmarks/{bookmark_id}")
        assert response.status_code == 200
        processed = response.json()
        assert processed["title"] is not None

        # 4. Semantic search
        response = await client.post(
            "/search/semantic",
            json={"query": "programming language", "limit": 10}
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0

        # 5. Mark as read
        response = await client.patch(
            f"/bookmarks/{bookmark_id}",
            json={"state": "read"}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["state"] == "read"
        assert updated["read_at"] is not None

        # 6. Search with state filter (inbox should be empty)
        response = await client.post(
            "/search/keyword",
            json={"query": "python", "state": "inbox"}
        )
        assert response.status_code == 200
        inbox_results = response.json()
        assert len(inbox_results) == 0

        # 7. Search read items
        response = await client.post(
            "/search/keyword",
            json={"query": "python", "state": "read"}
        )
        assert response.status_code == 200
        read_results = response.json()
        assert len(read_results) > 0

        # 8. Delete bookmark
        response = await client.delete(f"/bookmarks/{bookmark_id}")
        assert response.status_code == 204

        # 9. Verify deleted
        response = await client.get(f"/bookmarks/{bookmark_id}")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_backup_workflow():
    """Test backup and restore"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create backup
        response = await client.post("/backup/create")
        assert response.status_code == 201

        # List backups
        response = await client.get("/backup/list")
        assert response.status_code == 200
        backups = response.json()
        assert len(backups) > 0
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v -s`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests"
```

---

## Completion Checklist

After implementing all tasks:

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Docker build succeeds (`docker-compose build`)
- [ ] API starts and health check passes
- [ ] Can add bookmark via API
- [ ] Background processing works (metadata, embedding, archive)
- [ ] Semantic search returns results
- [ ] Keyword search works
- [ ] State filtering works
- [ ] Backup creation succeeds
- [ ] CLI tool works with running API
- [ ] Documentation is complete

## Next Steps

After implementation:

1. **Deploy to Hetzner VPS**
   - Clone repository
   - Run `docker-compose up -d`
   - Configure domain and SSL (Caddy/Traefik)

2. **Setup monitoring**
   - Add logging aggregation
   - Setup alerts for failed backups

3. **Future integrations**
   - Telegram bot endpoint
   - Email forwarding
   - Browser extension

4. **Performance optimization**
   - Add caching for embeddings
   - Implement pagination
   - Consider PostgreSQL for >10k bookmarks
