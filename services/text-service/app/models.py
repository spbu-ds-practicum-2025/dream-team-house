"""
Database models for Text Service
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Enum, Index
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


class Document(Base):
    """Document version table"""
    __tablename__ = "documents"

    version = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    edit_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index('idx_documents_version', 'version', postgresql_using='btree'),
    )


class Edit(Base):
    """Edit records table"""
    __tablename__ = "edits"

    edit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
        Index('idx_edits_created_at', 'created_at'),
    )


class TokenBudget(Base):
    """Token budget tracking table"""
    __tablename__ = "token_budget"

    id = Column(Integer, primary_key=True, default=1)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    limit_tokens = Column(BigInteger, nullable=False, default=15000000)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
