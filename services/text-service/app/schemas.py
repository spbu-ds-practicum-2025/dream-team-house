"""
Pydantic schemas for request/response validation
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class DocumentResponse(BaseModel):
    """Response model for document"""
    version: int
    text: str
    timestamp: datetime

    class Config:
        from_attributes = True


class DocumentInitRequest(BaseModel):
    """Request to initialize a new document"""
    topic: str
    initial_text: str
    mode: Optional[str] = "light"  # light or pro
    max_edits: Optional[int] = 3
    token_budget: Optional[int] = 50000


class DocumentInitResponse(BaseModel):
    """Response for document initialization"""
    document_id: str
    status: str


class EditRequest(BaseModel):
    """Request to submit an edit"""
    agent_id: str
    operation: str  # insert, replace, delete
    anchor: Optional[str] = None
    position: Optional[str] = None  # for insert: before/after
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    tokens_used: int = 0


class EditResponse(BaseModel):
    """Response for edit submission"""
    edit_id: str
    status: str  # accepted, rejected
    version: int


class EditListItem(BaseModel):
    """Edit item in list"""
    edit_id: UUID
    agent_id: str
    operation: str
    status: str
    tokens_used: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReplicationSyncRequest(BaseModel):
    """Replication sync message"""
    version: int
    text: str
    timestamp: datetime
    edit_id: Optional[str] = None
    source_node: str


class ReplicationSyncResponse(BaseModel):
    """Replication sync response"""
    status: str
    version: int


class CatchUpResponse(BaseModel):
    """Catch-up response with missing versions"""
    versions: List[dict]


class AnalyticsEventRequest(BaseModel):
    """Analytics event to send"""
    event_type: str
    agent_id: Optional[str] = None
    version: Optional[int] = None
    tokens: Optional[int] = None
    timestamp: datetime
    metadata: Optional[dict] = None
