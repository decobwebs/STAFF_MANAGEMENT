from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.core.auth import get_current_user
from app.models.message import Message, MessageReply
from app.schemas.message import MessageResponse, MessageReplyCreate, MessageReplyResponse
from typing import List

router = APIRouter(prefix="/messages", tags=["messages"])

# 1. Get messages for current staff
@router.get("", response_model=List[MessageResponse])
async def get_my_messages(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    messages = await db.execute(
        select(Message)
        .where(Message.recipient_ids.contains([current_user.id]))
        .order_by(Message.created_at.desc())
    )
    result = []
    for msg in messages.scalars():
        # Only show replies the user is allowed to see
        replies = await db.execute(
            select(MessageReply)
            .where(MessageReply.message_id == msg.id)
            .where(
                (MessageReply.is_private == False) | 
                (MessageReply.user_id == current_user.id) |
                (MessageReply.user_id == msg.admin_id)
            )
            .order_by(MessageReply.created_at)
        )
        result.append(
            MessageResponse(
                id=msg.id,
                admin_id=msg.admin_id,
                recipient_ids=msg.recipient_ids,
                title=msg.title,
                content=msg.content,
                created_at=msg.created_at,
                replies=[MessageReplyResponse.model_validate(r) for r in replies.scalars()]
            )
        )
    return result

# 2. Reply to a message
@router.post("/{message_id}/reply", response_model=MessageReplyResponse)
async def reply_to_message(
    message_id: int,
    reply_in: MessageReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Verify user is a recipient
    message = await db.execute(
        select(Message)
        .where(Message.id == message_id)
        .where(Message.recipient_ids.contains([current_user.id]))
    )
    msg = message.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found or access denied")

    reply = MessageReply(
        message_id=message_id,
        user_id=current_user.id,
        content=reply_in.content,
        is_private=reply_in.is_private
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return reply