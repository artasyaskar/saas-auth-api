"""File Storage API Routes"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.services.file_storage import FileStorageService, StorageProvider, AccessLevel
from app.core.security import get_current_user

router = APIRouter(prefix="/files", tags=["files"])


class UploadResult(BaseModel):
    file_id: str
    url: str
    filename: str
    size: int


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    access_level: str = "private",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = FileStorageService(db)
    result = service.upload_file(
        file_obj=file.file,
        filename=file.filename,
        content_type=file.content_type,
        user_id=current_user.id,
        access_level=AccessLevel(access_level)
    )
    return {
        "file_id": result.file_id,
        "url": result.url,
        "filename": result.original_filename,
        "size": result.file_size
    }


@router.get("/{file_id}")
async def get_file_info(file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FileStorageService(db)
    info = service.get_file_info(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")
    return info


@router.get("/{file_id}/download")
async def download_file(file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FileStorageService(db)
    url = service.get_download_url(file_id, current_user.id)
    if not url:
        raise HTTPException(status_code=404, detail="File not found or access denied")
    return {"download_url": url}


@router.delete("/{file_id}")
async def delete_file(file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FileStorageService(db)
    success = service.delete_file(file_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted successfully"}


@router.get("/")
async def list_files(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = FileStorageService(db)
    return service.list_user_files(current_user.id, limit, offset)


@router.post("/{file_id}/versions")
async def create_version(file_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FileStorageService(db)
    result = service.create_version(
        file_id=file_id,
        file_obj=file.file,
        filename=file.filename,
        content_type=file.content_type,
        user_id=current_user.id
    )
    return {"version_id": result.new_file_id, "version_number": result.version_number}


@router.get("/{file_id}/versions")
async def list_versions(file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = FileStorageService(db)
    return service.list_versions(file_id)
