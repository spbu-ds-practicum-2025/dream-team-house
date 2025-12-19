"""
Database models for Text Service
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Enum, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class EditStatus(str, PyEnum):
    """Edit status enum"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class OperationType(str, PyEnum):
    """Operation type for edits"""
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"


class DocumentStatus(str, PyEnum):
    """Document lifecycle status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FINALIZED = "finalized"


class DocumentSession(Base):
    """Document session metadata"""
    __tablename__ = "document_sessions"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic = Column(String(255), nullable=False)
    mode = Column(String(50), nullable=True)
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.ACTIVE)
    max_edits = Column(Integer, nullable=False, default=3)
    token_budget = Column(BigInteger, nullable=False, default=50000)
    token_used = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    final_version = Column(Integer, nullable=True)


class Document(Base):
    """Document version table"""
    __tablename__ = "documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    edit_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index('idx_documents_version', 'document_id', 'version', postgresql_using='btree'),
        UniqueConstraint('document_id', 'version', name='uq_document_version'),
    )


class Edit(Base):
    """Edit records table"""
    __tablename__ = "edits"

    edit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    agent_id = Column(String(255), nullable=False)
    operation = Column(String(50), nullable=False)
    anchor = Column(Text, nullable=True)
    position = Column(String(50), nullable=True)  # for insert: before/after
    old_text = Column(Text, nullable=True)
    new_text = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=False, default=0)
    status = Column(Enum(EditStatus), nullable=False, default=EditStatus.PENDING)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_edits_status', 'status'),
        Index('idx_edits_document', 'document_id'),
        Index('idx_edits_created_at', 'created_at'),
    )


class TokenBudget(Base):
    """Token budget tracking table"""
    __tablename__ = "token_budget"

    document_id = Column(UUID(as_uuid=True), primary_key=True)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    limit_tokens = Column(BigInteger, nullable=False, default=15000000)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
