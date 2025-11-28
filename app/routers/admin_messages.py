from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.core.auth import get_current_admin
from app.models.message import Announcement, Conversation, ConversationParticipant, Message, MessageReply
from app.models.user import User
from typing import List
from datetime import datetime, timezone
from app.schemas.message import (
    AnnouncementCreate, AnnouncementResponse, ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse,
    MessageReplyCreate, MessageReplyResponse
)

router = APIRouter(prefix="/admin/messages", tags=["admin-messages"])

# 1. Create Announcement
@router.post("/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    announcement_in: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    announcement = Announcement(
        admin_id=admin.id,
        title=announcement_in.title,
        content=announcement_in.content
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return announcement

# 2. Send Targeted Message
@router.post("", response_model=MessageResponse)
async def send_message(
    message_in: MessageCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # Validate all recipients are staff
    for user_id in message_in.recipient_ids:
        user = await db.execute(
            select(User).where(User.id == user_id, User.role == "staff")
        )
        if not user.scalar_one_or_none():
            raise HTTPException(400, f"Invalid staff user ID: {user_id}")

    message = Message(
        admin_id=admin.id,
        recipient_ids=message_in.recipient_ids,
        title=message_in.title,
        content=message_in.content
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return MessageResponse(
        id=message.id,
        admin_id=message.admin_id,
        recipient_ids=message.recipient_ids,
        title=message.title,
        content=message.content,
        created_at=message.created_at,
        replies=[]  # No replies yet
    )

@router.get("", response_model=List[MessageResponse])
async def get_messages(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # Join Message → Conversation to get admin_id
    result = await db.execute(
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.admin_id == admin.id)
        .order_by(Message.created_at.desc())
    )
    messages = result.scalars().all()
    
    # Convert to response model
    return [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender_id=msg.sender_id,
            content=msg.content,
            created_at=msg.created_at
        )
        for msg in messages
    ]


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conv_in: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # Create conversation
    conv = Conversation(admin_id=admin.id, title=conv_in.title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    # Add admin + initial participants
    participant_ids = set(conv_in.initial_participant_ids + [admin.id])
    for user_id in participant_ids:
        # Validate staff user
        user = await db.execute(
            select(User).where(User.id == user_id, User.role == "staff")
        )
        if not user.scalar_one_or_none() and user_id != admin.id:
            raise HTTPException(400, f"Invalid staff user: {user_id}")
        
        participant = ConversationParticipant(
            conversation_id=conv.id,
            user_id=user_id
        )
        db.add(participant)
    
    await db.commit()
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        admin_id=conv.admin_id,
        participants=list(participant_ids),
        created_at=conv.created_at
    )



@router.post("/conversations/{conv_id}/participants/{user_id}/add")
async def add_participant(
    conv_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin)  # Or allow any participant
):
    # Verify user is staff
    user = await db.execute(select(User).where(User.id == user_id, User.role == "staff"))
    if not user.scalar_one_or_none():
        raise HTTPException(400, "Invalid staff user")

    # Verify current user is in conversation
    participant = await db.execute(
        select(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == current_user.id)
        .where(ConversationParticipant.removed_at.is_(None))
    )
    if not participant.scalar_one_or_none():
        raise HTTPException(403, "Not a participant in this conversation")

    # Add participant (idempotent)
    new_part = ConversationParticipant(conversation_id=conv_id, user_id=user_id)
    db.add(new_part)
    await db.commit()
    return {"message": "Participant added"}

@router.post("/conversations/{conv_id}/participants/{user_id}/remove")
async def remove_participant(
    conv_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin)  # Or allow any participant
):
    # Prevent removing admin
    conv = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conversation = conv.scalar_one()
    if user_id == conversation.admin_id:
        raise HTTPException(403, "Cannot remove admin")

    # Verify current user is in conversation
    participant = await db.execute(
        select(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == current_user.id)
        .where(ConversationParticipant.removed_at.is_(None))
    )
    if not participant.scalar_one_or_none():
        raise HTTPException(403, "Not a participant")

    # Mark as removed
    stmt = (
        update(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == user_id)
        .where(ConversationParticipant.removed_at.is_(None))
        .values(removed_at=datetime.now(timezone.utc), removed_by=current_user.id)
    )
    await db.execute(stmt)
    await db.commit()
    return {"message": "Participant removed"}



@router.post("/conversations/{conv_id}/participants/{user_id}/add")
async def add_participant(
    conv_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Admin adds a staff member to a conversation.
    """
    # Verify target user is staff
    user = await db.execute(
        select(User).where(User.id == user_id, User.role == "staff")
    )
    if not user.scalar_one_or_none():
        raise HTTPException(400, "Invalid staff user")

    # Verify admin is in the conversation
    admin_part = await db.execute(
        select(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == admin.id)
        .where(ConversationParticipant.removed_at.is_(None))
    )
    if not admin_part.scalar_one_or_none():
        raise HTTPException(403, "Admin not in this conversation")

    # Add participant (idempotent)
    new_part = ConversationParticipant(conversation_id=conv_id, user_id=user_id)
    db.add(new_part)
    await db.commit()
    return {"message": "Participant added"}


@router.post("/conversations/{conv_id}/participants/{user_id}/remove")
async def remove_participant(
    conv_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Admin removes a participant from a conversation.
    Admin cannot be removed.
    """
    # Prevent removing admin
    conv = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conversation = conv.scalar_one_or_none()
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    if user_id == conversation.admin_id:
        raise HTTPException(403, "Cannot remove admin")

    # Verify admin is in the conversation
    admin_part = await db.execute(
        select(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == admin.id)
        .where(ConversationParticipant.removed_at.is_(None))
    )
    if not admin_part.scalar_one_or_none():
        raise HTTPException(403, "Admin not in this conversation")

    # Mark as removed
    stmt = (
        update(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == conv_id)
        .where(ConversationParticipant.user_id == user_id)
        .where(ConversationParticipant.removed_at.is_(None))
        .values(
            removed_at=datetime.now(timezone.utc),
            removed_by=admin.id
        )
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(400, "User not an active participant")
    
    await db.commit()
    return {"message": "Participant removed"}