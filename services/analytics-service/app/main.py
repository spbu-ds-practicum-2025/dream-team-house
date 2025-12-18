"""
Analytics Service - Telemetry and metrics aggregation
FastAPI application with PostgreSQL
"""
import logging
from datetime import datetime, timedelta
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, and_

from app.database import get_db, init_db
from app.models import Event
from app.schemas import EventRequest, EventResponse, MetricsResponse, TimeSeriesPoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Analytics Service starting")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Analytics Service shutting down")


app = FastAPI(
    title="Analytics Service",
    description="Telemetry and metrics aggregation service",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/analytics/events", response_model=EventResponse)
async def post_event(
    event: EventRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive event from Text Service
    Store event in PostgreSQL for later aggregation
    """
    try:
        db_event = Event(
            event_type=event.event_type,
            agent_id=event.agent_id,
            version=event.version,
            tokens=event.tokens,
            timestamp=event.timestamp,
            event_metadata=event.metadata,
        )
        db.add(db_event)
        await db.commit()
        
        logger.info(f"Event recorded: {event.event_type} from {event.agent_id}")
        
        return EventResponse(status="ok")
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error storing event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/metrics", response_model=MetricsResponse)
async def get_metrics(
    period: str = "1h",
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated metrics for specified period
    Supports: 1h, 24h, 7d
    """
    try:
        # Parse period
        now = datetime.utcnow()
        if period == "1h":
            since = now - timedelta(hours=1)
            time_bucket = timedelta(minutes=5)
        elif period == "24h":
            since = now - timedelta(hours=24)
            time_bucket = timedelta(hours=1)
        elif period == "7d":
            since = now - timedelta(days=7)
            time_bucket = timedelta(hours=6)
        else:
            raise HTTPException(status_code=400, detail="Invalid period")
        
        # Total edits
        result = await db.execute(
            select(func.count(Event.id))
            .where(
                and_(
                    Event.event_type == "edit_applied",
                    Event.timestamp >= since
                )
            )
        )
        total_edits = result.scalar() or 0
        
        # Total tokens
        result = await db.execute(
            select(func.sum(Event.tokens))
            .where(
                and_(
                    Event.event_type == "edit_applied",
                    Event.timestamp >= since,
                    Event.tokens.isnot(None)
                )
            )
        )
        total_tokens = result.scalar() or 0
        
        # Active agents
        result = await db.execute(
            select(func.count(distinct(Event.agent_id)))
            .where(
                and_(
                    Event.event_type == "edit_applied",
                    Event.timestamp >= since,
                    Event.agent_id.isnot(None)
                )
            )
        )
        active_agents = result.scalar() or 0
        
        # Calculate edits per minute
        time_range_minutes = (now - since).total_seconds() / 60
        edits_per_minute = total_edits / time_range_minutes if time_range_minutes > 0 else 0
        
        # Average latency (if stored in event_metadata)
        result = await db.execute(
            select(Event.event_metadata)
            .where(
                and_(
                    Event.event_type.in_(["replication_success", "replication_failed"]),
                    Event.timestamp >= since,
                    Event.event_metadata.isnot(None)
                )
            )
        )
        latencies = []
        for row in result:
            if row[0] and "latency_ms" in row[0]:
                latencies.append(row[0]["latency_ms"])
        
        avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0
        
        # Token usage by time (time series)
        # Build time buckets
        time_series = []
        current_time = since
        
        while current_time < now:
            bucket_end = current_time + time_bucket
            
            # Get tokens used in this bucket
            result = await db.execute(
                select(func.sum(Event.tokens))
                .where(
                    and_(
                        Event.event_type == "edit_applied",
                        Event.timestamp >= current_time,
                        Event.timestamp < bucket_end,
                        Event.tokens.isnot(None)
                    )
                )
            )
            tokens_in_bucket = result.scalar() or 0
            
            time_series.append(TimeSeriesPoint(
                timestamp=current_time.isoformat(),
                value=int(tokens_in_bucket)
            ))
            
            current_time = bucket_end
        
        logger.info(f"Metrics requested for period {period}: {total_edits} edits, {total_tokens} tokens")
        
        return MetricsResponse(
            total_edits=total_edits,
            total_tokens=int(total_tokens),
            active_agents=active_agents,
            avg_latency_ms=float(avg_latency_ms),
            edits_per_minute=float(edits_per_minute),
            token_usage_by_time=time_series,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
