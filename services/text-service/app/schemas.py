"""
Pydantic schemas for request/response validation
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from uuid import UUID


class DocumentResponse(BaseModel):
    """Response model for document"""
    document_id: str
    version: int
    text: str
    timestamp: datetime
    topic: Optional[str] = None
    mode: Optional[str] = None
    status: Optional[str] = None
    max_edits: Optional[int] = None
    token_budget: Optional[int] = None
    token_used: Optional[int] = None
    finished_at: Optional[datetime] = None
    final_version: Optional[int] = None
    total_versions: Optional[int] = None

    class Config:
        from_attributes = True


class DocumentInitRequest(BaseModel):
    """Request to initialize a new document"""
    topic: str
    initial_text: str
    mode: Optional[Literal["light", "pro"]] = "light"
    max_edits: Optional[int] = 3
    token_budget: Optional[int] = 50000


class DocumentInitResponse(BaseModel):
    """Response for document initialization"""
    document_id: str
    status: str


class EditRequest(BaseModel):
    """Request to submit an edit"""
    document_id: Optional[str] = None
    agent_id: str
    operation: str  # insert, replace, delete
    anchor: Optional[str] = None
    position: Optional[str] = None  # for insert: before/after
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    tokens_used: int = 0


class EditResponse(BaseModel):
    """Response for edit submission"""
    document_id: str
    edit_id: str
    status: str  # accepted, rejected
    version: int


class EditListItem(BaseModel):
    """Edit item in list"""
    document_id: str
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
    document_id: str
    version: int
    text: str
    timestamp: datetime
    edit_id: Optional[str] = None
    source_node: str
    topic: Optional[str] = None
    mode: Optional[str] = None
    status: Optional[str] = None
    max_edits: Optional[int] = None
    token_budget: Optional[int] = None
    token_used: Optional[int] = None
    final_version: Optional[int] = None


class ReplicationSyncResponse(BaseModel):
    """Replication sync response"""
    status: str
    version: int


class CatchUpResponse(BaseModel):
    """Catch-up response with missing versions"""
    versions: List[dict]


class DocumentListItem(BaseModel):
    """Summary of a document session"""
    document_id: str
    topic: str
    mode: Optional[str] = None
    status: str
    current_version: int
    final_version: Optional[int] = None
    updated_at: datetime
    finished_at: Optional[datetime] = None


class VersionItem(BaseModel):
    """Single document version item"""
    version: int
    timestamp: datetime


class DiffSegment(BaseModel):
    """Diff segment for highlighting"""
    type: Literal["equal", "insert", "delete", "replace"]
    text: str


class VersionDiffResponse(BaseModel):
    """Diff between two document versions"""
    document_id: str
    target_version: int
    base_version: Optional[int] = None
    timestamp: datetime
    segments: List[DiffSegment]
    target_text: str


class DocumentActionResponse(BaseModel):
    """Response for stop/finalize actions"""
    document_id: str
    status: str
    finished_at: Optional[datetime] = None
    final_version: Optional[int] = None


class AnalyticsEventRequest(BaseModel):
    """Analytics event to send"""
    event_type: str
    agent_id: Optional[str] = None
    version: Optional[int] = None
    tokens: Optional[int] = None
    timestamp: datetime
    metadata: Optional[dict] = None
