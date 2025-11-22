"""
Database models for Analytics Service
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Event(Base):
    """Events table for analytics"""
    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    agent_id = Column(String(255), nullable=True)
    version = Column(Integer, nullable=True)
    tokens = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    metadata = Column(JSONB, nullable=True)

    __table_args__ = (
        Index('idx_events_timestamp', 'timestamp', postgresql_using='btree'),
        Index('idx_events_type', 'event_type'),
        Index('idx_events_agent', 'agent_id'),
    )
