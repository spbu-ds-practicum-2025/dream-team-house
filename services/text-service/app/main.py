"""
Text Service - Distributed document management service
FastAPI application entry point
"""
import os
import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, update
from sqlalchemy.orm import selectinload

from app.database import get_db, init_db
from app.models import Document, Edit, TokenBudget, EditStatus
from app.schemas import (
    DocumentResponse,
    DocumentInitRequest,
    DocumentInitResponse,
    EditRequest,
    EditResponse,
    EditListItem,
    ReplicationSyncRequest,
    ReplicationSyncResponse,
    CatchUpResponse,
)
from app.operations import apply_operation_to_text, validate_edit_request
from app.replication import replicate_to_peers, send_analytics_event, NODE_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Text Service starting - Node: {NODE_ID}")
    await init_db()
    logger.info("Database initialized")
    
    # Initialize token budget if not exists
    async with get_db().__anext__() as db:
        result = await db.execute(select(TokenBudget).where(TokenBudget.id == 1))
        budget = result.scalar_one_or_none()
        if not budget:
            budget = TokenBudget(id=1, total_tokens=0, limit_tokens=15000000)
            db.add(budget)
            await db.commit()
            logger.info("Token budget initialized")
    
    yield
    
    # Shutdown
    logger.info("Text Service shutting down")


app = FastAPI(
    title="Text Service",
    description="Distributed document management service",
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
    """Health check endpoint for Load Balancer"""
    return {"status": "healthy", "node_id": NODE_ID}


@app.get("/api/document/current", response_model=DocumentResponse)
async def get_current_document(db: AsyncSession = Depends(get_db)):
    """Get current document version"""
    result = await db.execute(
        select(Document).order_by(desc(Document.version)).limit(1)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="No document found")
    
    return DocumentResponse(
        version=doc.version,
        text=doc.text,
        timestamp=doc.timestamp,
    )


@app.post("/api/document/init", response_model=DocumentInitResponse)
async def init_document(
    request: DocumentInitRequest,
    db: AsyncSession = Depends(get_db)
):
    """Initialize new document"""
    # Check if document already exists
    result = await db.execute(select(func.count(Document.version)))
    count = result.scalar()
    
    if count > 0:
        # Delete existing documents (as per spec: only one document at a time)
        await db.execute(Document.__table__.delete())
        await db.execute(Edit.__table__.delete())
        await db.execute(
            TokenBudget.__table__.update()
            .where(TokenBudget.id == 1)
            .values(total_tokens=0)
        )
        await db.commit()
        logger.info("Cleared existing documents")
    
    # Create initial document
    doc = Document(
        version=1,
        text=request.initial_text,
        timestamp=datetime.utcnow(),
        edit_id=None,
    )
    db.add(doc)
    await db.commit()
    
    logger.info(f"Initialized document with topic: {request.topic}")
    
    # Send analytics event
    await send_analytics_event({
        "event_type": "document_initialized",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "topic": request.topic,
            "node_id": NODE_ID,
        }
    })
    
    # Replicate to peers
    await replicate_to_peers(doc.version, doc.text, doc.timestamp, None)
    
    return DocumentInitResponse(document_id="1", status="initialized")


@app.post("/api/edits", response_model=EditResponse)
async def submit_edit(
    edit_request: EditRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit an edit from agent"""
    # Validate edit request
    is_valid, error_msg = validate_edit_request(edit_request)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Start transaction
    try:
        # Check token budget
        result = await db.execute(select(TokenBudget).where(TokenBudget.id == 1))
        budget = result.scalar_one_or_none()
        
        if not budget:
            raise HTTPException(status_code=500, detail="Token budget not initialized")
        
        if budget.total_tokens + edit_request.tokens_used > budget.limit_tokens:
            logger.warning(f"Budget exceeded: {budget.total_tokens + edit_request.tokens_used} > {budget.limit_tokens}")
            
            # Send analytics event
            await send_analytics_event({
                "event_type": "budget_exceeded",
                "agent_id": edit_request.agent_id,
                "tokens": edit_request.tokens_used,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "total_tokens": budget.total_tokens,
                    "limit_tokens": budget.limit_tokens,
                }
            })
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Token budget exceeded"
            )
        
        # Get current document
        result = await db.execute(
            select(Document).order_by(desc(Document.version)).limit(1)
        )
        current_doc = result.scalar_one_or_none()
        
        if not current_doc:
            raise HTTPException(status_code=404, detail="No document found")
        
        # Create edit record
        edit = Edit(
            agent_id=edit_request.agent_id,
            operation=edit_request.operation,
            anchor=edit_request.anchor,
            position=edit_request.position,
            old_text=edit_request.old_text,
            new_text=edit_request.new_text,
            tokens_used=edit_request.tokens_used,
            status=EditStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db.add(edit)
        await db.flush()
        
        # Apply operation to text
        new_text, applied = apply_operation_to_text(current_doc.text, edit_request)
        
        if not applied:
            edit.status = EditStatus.REJECTED
            await db.commit()
            
            logger.warning(f"Edit {edit.edit_id} rejected: could not apply operation")
            return EditResponse(
                edit_id=str(edit.edit_id),
                status="rejected",
                version=current_doc.version,
            )
        
        # Create new document version
        new_version = current_doc.version + 1
        new_doc = Document(
            version=new_version,
            text=new_text,
            timestamp=datetime.utcnow(),
            edit_id=edit.edit_id,
        )
        db.add(new_doc)
        
        # Update edit status
        edit.status = EditStatus.ACCEPTED
        edit.applied_at = datetime.utcnow()
        
        # Update token budget
        await db.execute(
            update(TokenBudget)
            .where(TokenBudget.id == 1)
            .values(
                total_tokens=TokenBudget.total_tokens + edit_request.tokens_used,
                updated_at=datetime.utcnow(),
            )
        )
        
        await db.commit()
        
        logger.info(f"Edit {edit.edit_id} accepted, new version: {new_version}")
        
        # Send analytics event
        await send_analytics_event({
            "event_type": "edit_applied",
            "agent_id": edit_request.agent_id,
            "version": new_version,
            "tokens": edit_request.tokens_used,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "edit_id": str(edit.edit_id),
                "operation": edit_request.operation,
                "node_id": NODE_ID,
            }
        })
        
        # Replicate to peers (async, don't wait)
        await replicate_to_peers(
            new_doc.version,
            new_doc.text,
            new_doc.timestamp,
            str(edit.edit_id)
        )
        
        return EditResponse(
            edit_id=str(edit.edit_id),
            status="accepted",
            version=new_version,
        )
    
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing edit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/edits", response_model=List[EditListItem])
async def get_edits(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get list of edits with pagination"""
    result = await db.execute(
        select(Edit)
        .order_by(desc(Edit.created_at))
        .limit(limit)
        .offset(offset)
    )
    edits = result.scalars().all()
    
    return [
        EditListItem(
            edit_id=edit.edit_id,
            agent_id=edit.agent_id,
            operation=edit.operation,
            status=edit.status.value,
            tokens_used=edit.tokens_used,
            created_at=edit.created_at,
        )
        for edit in edits
    ]


@app.post("/api/replication/sync", response_model=ReplicationSyncResponse)
async def replication_sync(
    request: ReplicationSyncRequest,
    db: AsyncSession = Depends(get_db)
):
    """Accept replication message from another node"""
    try:
        # Check if version already exists
        result = await db.execute(
            select(Document).where(Document.version == request.version)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Version {request.version} already exists, skipping replication")
            return ReplicationSyncResponse(status="already_synced", version=request.version)
        
        # Get current highest version
        result = await db.execute(
            select(func.max(Document.version))
        )
        max_version = result.scalar() or 0
        
        if request.version <= max_version:
            logger.warning(f"Received old version {request.version}, current max: {max_version}")
            return ReplicationSyncResponse(status="outdated", version=max_version)
        
        # Apply replication
        new_doc = Document(
            version=request.version,
            text=request.text,
            timestamp=request.timestamp,
            edit_id=request.edit_id,
        )
        db.add(new_doc)
        await db.commit()
        
        logger.info(f"Replicated version {request.version} from {request.source_node}")
        
        return ReplicationSyncResponse(status="synced", version=request.version)
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Replication error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/replication/catch-up", response_model=CatchUpResponse)
async def replication_catchup(
    since_version: int,
    db: AsyncSession = Depends(get_db)
):
    """Get versions for node recovery"""
    result = await db.execute(
        select(Document)
        .where(Document.version > since_version)
        .order_by(Document.version)
    )
    documents = result.scalars().all()
    
    versions = [
        {
            "version": doc.version,
            "text": doc.text,
            "timestamp": doc.timestamp.isoformat(),
            "edit_id": str(doc.edit_id) if doc.edit_id else None,
        }
        for doc in documents
    ]
    
    logger.info(f"Catch-up request for versions > {since_version}, returning {len(versions)} versions")
    
    return CatchUpResponse(versions=versions)
