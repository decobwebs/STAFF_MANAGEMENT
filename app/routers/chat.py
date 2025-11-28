# app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime, timezone
from typing import List

from app.database import get_db
from app.core.auth import get_current_user
from app.models.message import Conversation, ConversationParticipant, Message
from app.schemas.message import ConversationResponse, MessageResponse, MessageCreate

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all conversations the current user is (or was) part of.
    """
    # Get all conversation IDs where user is/was a participant
    participations = await db.execute(
        select(ConversationParticipant.conversation_id)
        .where(ConversationParticipant.user_id == current_user.id)
    )
    conv_ids = [row[0] for row in participations.fetchall()]
    
    if not conv_ids:
        return []

    # Fetch conversation details
    conversations = await db.execute(
        select(Conversation).where(Conversation.id.in_(conv_ids))
    )
    
    result = []
    for conv in conversations.scalars():
        # Get current active participants
        active_participants = await db.execute(
            select(ConversationParticipant.user_id)
            .where(ConversationParticipant.conversation_id == conv.id)
            .where(ConversationParticipant.removed_at.is_(None))
        )
        participant_ids = [p[0] for p in active_participants.fetchall()]
        
        result.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                admin_id=conv.admin_id,
                participants=participant_ids,
                created_at=conv.created_at
            )
        )
    return result


@router.post("/conversations/{conv_id}/messages", response_model=MessageResponse)
async def send_message(
    conv_id: int,
    message_in: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Send a message in a conversation.
    Only active participants can send messages.
    """
    # Verify user is an active participant
    participant = await db.execute(
        select(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == current_user.id)
        .where(ConversationParticipant.removed_at.is_(None))
    )
    if not participant.scalar_one_or_none():
        raise HTTPException(403, "Not an active participant in this conversation")

    message = Message(
        conversation_id=conv_id,
        sender_id=current_user.id,
        content=message_in.content
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


@router.get("/conversations/{conv_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get messages in a conversation.
    If user was removed, only show messages up to removal time.
    """
    # Verify user was ever a participant
    participant_record = await db.execute(
        select(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == current_user.id)
    )
    participant = participant_record.scalar_one_or_none()
    if not participant:
        raise HTTPException(403, "Not a participant in this conversation")

    # Build query
    query = select(Message).where(Message.conversation_id == conv_id)
    
    # If removed, cap at removal time
    if participant.removed_at:
        query = query.where(Message.created_at <= participant.removed_at)
    
    query = query.order_by(Message.created_at)
    messages = await db.execute(query)
    return messages.scalars().all()