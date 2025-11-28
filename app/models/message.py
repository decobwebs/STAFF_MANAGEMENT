from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, func, ARRAY
from app.database import Base
from sqlalchemy.dialects.postgresql import ARRAY


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())





class MessageReply(Base):
    __tablename__ = "message_replies"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Staff or admin
    content = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False)  # True = only admin sees it
    created_at = Column(DateTime(timezone=True), server_default=func.now())




class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Admin who started it
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)  # Can be archived

class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    removed_at = Column(DateTime(timezone=True), nullable=True)  # NULL = still in chat
    removed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who removed them

    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_conversation_user"),)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who sent it
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())