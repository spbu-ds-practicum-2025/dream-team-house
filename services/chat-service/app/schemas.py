"""
Pydantic schemas for Chat Service
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class CommentKind(str, Enum):
    """Comment type enum"""
    CRITIQUE = "critique"
    SUPPORT = "support"
    SUGGESTION = "suggestion"


class IntentStatus(str, Enum):
    """Intent status enum"""
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXECUTED = "executed"


class OperationType(str, Enum):
    """Operation type enum"""
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    NONE = "none"


class EditIntent(BaseModel):
    """Edit intent structure"""
    intent_id: str
    agent_id: str
    operation: OperationType
    anchor: Optional[str] = None
    summary: str
    status: IntentStatus
    created_at: float


class EditComment(BaseModel):
    """Edit comment structure"""
    comment_id: str
    target_intent_id: str
    agent_id: str
    kind: CommentKind
    content: str
    created_at: float


class EditOperation(BaseModel):
    """Edit operation structure"""
    operation: OperationType
    anchor: Optional[str] = None
    position: Optional[str] = None
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    reasoning: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """Request to post a chat message"""
    document_id: Optional[str] = None
    agent_id: str
    message: str
    intent: Optional[EditIntent] = None
    comment: Optional[EditComment] = None


class ChatMessageResponse(BaseModel):
    """Response for posted message"""
    message_id: str
    timestamp: str


class ChatMessage(BaseModel):
    """Chat message structure"""
    document_id: Optional[str] = None
    message_id: str
    agent_id: str
    message: str
    timestamp: str
    intent: Optional[EditIntent] = None
    comment: Optional[EditComment] = None
