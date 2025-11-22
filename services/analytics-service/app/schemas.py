"""
Pydantic schemas for Analytics Service
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class EventRequest(BaseModel):
    """Event submission request"""
    event_type: str
    agent_id: Optional[str] = None
    version: Optional[int] = None
    tokens: Optional[int] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    """Event submission response"""
    status: str


class TimeSeriesPoint(BaseModel):
    """Time series data point"""
    timestamp: str
    value: int


class MetricsResponse(BaseModel):
    """Aggregated metrics response"""
    total_edits: int
    total_tokens: int
    active_agents: int
    avg_latency_ms: float
    edits_per_minute: float
    token_usage_by_time: List[TimeSeriesPoint]
