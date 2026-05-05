"""Messaging API Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.services.messaging import MessagingService, MessageType, NotificationChannel
from app.core.security import get_current_user

router = APIRouter(prefix="/messaging", tags=["messaging"])


class SendMessageRequest(BaseModel):
    recipient_id: Optional[int] = None
    thread_id: Optional[str] = None
    content: str
    message_type: str = "direct"


@router.post("/messages")
async def send_message(request: SendMessageRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = MessagingService(db)
    message_id = service.send_message(
        service.MessageData(
            sender_id=current_user.id,
            recipient_id=request.recipient_id,
            thread_id=request.thread_id,
            content=request.content,
            message_type=MessageType(request.message_type)
        )
    )
    return {"message_id": message_id}


@router.get("/threads")
async def get_my_threads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = MessagingService(db)
    return service.get_user_threads(current_user.id)


@router.get("/notifications")
async def get_my_notifications(unread_only: bool = False, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = MessagingService(db)
    return service.get_user_notifications(current_user.id, unread_only, limit)
