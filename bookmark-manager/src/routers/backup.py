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
