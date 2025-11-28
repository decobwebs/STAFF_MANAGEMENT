from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class AnnouncementCreate(BaseModel):
    title: str
    content: str

class AnnouncementResponse(BaseModel):
    id: int
    admin_id: int
    title: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}

class MessageCreate(BaseModel):
    recipient_ids: List[int]  # Staff user IDs
    title: str
    content: str

class MessageReplyCreate(BaseModel):
    content: str
    is_private: bool = False

class MessageReplyResponse(BaseModel):
    id: int
    user_id: int
    content: str
    is_private: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class MessageResponse(BaseModel):
    id: int
    admin_id: int
    recipient_ids: List[int]
    title: str
    content: str
    created_at: datetime
    replies: List[MessageReplyResponse]

    model_config = {"from_attributes": True}




class ConversationCreate(BaseModel):
    title: str
    initial_participant_ids: List[int]  # Staff user IDs (admin is auto-added)

class ConversationResponse(BaseModel):
    id: int
    title: str
    admin_id: int
    participants: List[int]
    created_at: datetime

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}