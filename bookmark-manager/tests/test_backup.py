import pytest
from src.services.backup_service import BackupService
from httpx import AsyncClient
from src.main import app
import os
import sqlite3
import shutil


@pytest.mark.asyncio
async def test_create_backup():
    """Test creating a database backup"""
    service = BackupService(
        db_path="test_bookmarks.db",
        backup_dir="test_backups"
    )

    # Create test database
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
        shutil.rmtree("test_backups")


@pytest.mark.asyncio
async def test_list_backups():
    """Test listing available backups"""
    service = BackupService(
        db_path="test_bookmarks.db",
        backup_dir="test_backups"
    )

    # Create test database
    conn = sqlite3.connect("test_bookmarks.db")
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.close()

    # Create a backup
    await service.create_backup()

    # List backups
    backups = await service.list_backups()

    assert len(backups) > 0
    assert "filename" in backups[0]
    assert "size" in backups[0]
    assert "created_at" in backups[0]

    # Cleanup
    os.remove("test_bookmarks.db")
    if os.path.exists("test_backups"):
        shutil.rmtree("test_backups")


@pytest.mark.asyncio
async def test_restore_backup():
    """Test restoring from a backup"""
    service = BackupService(
        db_path="test_bookmarks.db",
        backup_dir="test_backups"
    )

    # Create test database with data
    conn = sqlite3.connect("test_bookmarks.db")
    conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'original')")
    conn.commit()
    conn.close()

    # Create backup
    backup_path = await service.create_backup()
    backup_filename = os.path.basename(backup_path)

    # Modify database
    conn = sqlite3.connect("test_bookmarks.db")
    conn.execute("UPDATE test SET name = 'modified'")
    conn.commit()
    conn.close()

    # Restore backup
    await service.restore_backup(backup_filename)

    # Verify data is restored
    conn = sqlite3.connect("test_bookmarks.db")
    cursor = conn.execute("SELECT name FROM test WHERE id = 1")
    result = cursor.fetchone()
    conn.close()

    assert result[0] == "original"

    # Cleanup
    os.remove("test_bookmarks.db")
    if os.path.exists("test_backups"):
        shutil.rmtree("test_backups")


@pytest.mark.asyncio
async def test_backup_api_endpoints():
    """Test backup API endpoints"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create backup via API
        response = await client.post("/backup/create")
        assert response.status_code == 201
        data = response.json()
        assert "path" in data
        assert "message" in data

        # List backups
        response = await client.get("/backup/list")
        assert response.status_code == 200
        backups = response.json()
        assert isinstance(backups, list)
