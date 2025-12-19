"""
Text Service - Distributed document management service
FastAPI application entry point
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, update

from app.database import get_db, init_db, AsyncSessionLocal
from app.models import (
    Document,
    Edit,
    TokenBudget,
    EditStatus,
    DocumentSession,
    DocumentStatus,
    DocumentSettings,
)
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
    DocumentListItem,
    VersionItem,
    VersionDiffResponse,
    DocumentActionResponse,
    DiffSegment,
    AgentRole,
)
from app.operations import apply_operation_to_text, validate_edit_request, build_diff_segments
from app.replication import replicate_to_peers, send_analytics_event, NODE_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_ROLE_PRESETS = [
    {
        "role_key": "researcher",
        "name": "Исследователь",
        "prompt": "Добавляй факты, контекст и данные. Раскрывай тему глубже за счет примеров и ссылок на источники.",
    },
    {
        "role_key": "narrator",
        "name": "Нарративный писатель",
        "prompt": "Увеличивай объем текста связными абзацами и плавными переходами между идеями, делая рассказ цельным.",
    },
    {
        "role_key": "analyst",
        "name": "Аналитик",
        "prompt": "Расширяй аргументацию: добавляй выводы, сравнения и структурированные рассуждения без воды и повторов.",
    },
    {
        "role_key": "strategist",
        "name": "Стратег",
        "prompt": "Предлагай практические шаги и планы. Раскрывай идеи через детальные рекомендации и сценарии применения.",
    },
    {
        "role_key": "quality_guard",
        "name": "Редактор качества",
        "prompt": "Укрепляй стиль и чистоту текста, убирай явные повторы, добавляй уточнения и разъяснения для ясности.",
    },
    {
        "role_key": "storyfinder",
        "name": "Охотник за примерами",
        "prompt": "Расширяй разделы конкретикой: кейсы, мини-истории, жизненные ситуации, которые иллюстрируют тезисы.",
    },
    {
        "role_key": "visionary",
        "name": "Визионер",
        "prompt": "Добавляй содержательные идеи о будущем, трендах и последствиях, избегая пафоса и бессодержательных повторов.",
    },
    {
        "role_key": "connector",
        "name": "Связующий",
        "prompt": "Добавляй мостики между разделами, показывай как части текста поддерживают друг друга, укрепляй логику.",
    },
    {
        "role_key": "localizer",
        "name": "Локализатор",
        "prompt": "Адаптируй под аудиторию, добавляй отраслевые и культурные нюансы, расширяй примеры под контекст читателя.",
    },
    {
        "role_key": "mentor",
        "name": "Ментор",
        "prompt": "Давай развёрнутые объяснения и советы, добавляй пошаговые инструкции, избегая пустых извинений и просьб.",
    },
]

DEFAULT_ROLE_SETS = {
    "light": ["researcher", "narrator", "analyst"],
    "pro": [
        "researcher",
        "narrator",
        "analyst",
        "strategist",
        "quality_guard",
        "storyfinder",
        "visionary",
        "connector",
        "localizer",
        "mentor",
    ],
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info(f"Text Service starting - Node: {NODE_ID}")
    await init_db()
    logger.info("Database initialized")
    yield
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


async def resolve_document_session(
    db: AsyncSession,
    document_id: Optional[str],
    include_inactive: bool = False,
) -> Optional[DocumentSession]:
    """Get document session either by id or latest (optionally active only)."""
    query = select(DocumentSession)
    if document_id:
        query = query.where(DocumentSession.document_id == uuid.UUID(document_id))
    else:
        query = query.order_by(desc(DocumentSession.created_at))
        if not include_inactive:
            query = query.where(DocumentSession.status == DocumentStatus.ACTIVE)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none()


async def get_budget(db: AsyncSession, document_id: uuid.UUID) -> Optional[TokenBudget]:
    """Fetch token budget for a document."""
    result = await db.execute(
        select(TokenBudget).where(TokenBudget.document_id == document_id)
    )
    return result.scalar_one_or_none()


async def get_document_settings(db: AsyncSession, document_id: uuid.UUID) -> Optional[DocumentSettings]:
    """Fetch document settings (roles, limits)."""
    result = await db.execute(
        select(DocumentSettings).where(DocumentSettings.document_id == document_id)
    )
    return result.scalar_one_or_none()


def resolve_default_roles(mode: Optional[str], agent_count: int) -> List[dict]:
    """Select default roles for mode and ensure list has requested length."""
    preset_map = {role["role_key"]: role for role in DEFAULT_ROLE_PRESETS}
    keys = DEFAULT_ROLE_SETS.get(mode or "light", DEFAULT_ROLE_SETS["light"])
    roles: List[dict] = []
    while len(roles) < agent_count:
        key = keys[len(roles) % len(keys)]
        roles.append(preset_map.get(key, DEFAULT_ROLE_PRESETS[0]))
    return roles[:agent_count]


def safe_div_int(value: Optional[int], divisor: Optional[int]) -> Optional[int]:
    """Safely divide integers returning int or None on invalid input."""
    if value is None or divisor is None or divisor <= 0:
        return None
    return int(value / divisor)


async def get_latest_document(db: AsyncSession, document_id: uuid.UUID) -> Optional[Document]:
    """Fetch latest document version for session."""
    result = await db.execute(
        select(Document)
        .where(Document.document_id == document_id)
        .order_by(desc(Document.version))
        .limit(1)
    )
    return result.scalar_one_or_none()


def build_document_response(
    session: DocumentSession,
    doc: Document,
    budget: Optional[TokenBudget],
    settings: Optional[DocumentSettings],
) -> DocumentResponse:
    """Compose document response with metadata."""
    default_agent_count = 3 if session.mode == "light" else 10
    agent_count = settings.agent_count if settings else default_agent_count
    if not agent_count or agent_count <= 0:
        agent_count = default_agent_count
    max_edits_per_agent = settings.max_edits_per_agent if settings and settings.max_edits_per_agent else safe_div_int(session.max_edits, agent_count)
    agent_roles = settings.agent_roles if settings and settings.agent_roles else resolve_default_roles(session.mode, agent_count)

    return DocumentResponse(
        document_id=str(session.document_id),
        version=doc.version,
        text=doc.text,
        timestamp=doc.timestamp,
        topic=session.topic,
        mode=session.mode,
        status=session.status.value,
        max_edits=session.max_edits,
        token_budget=session.token_budget,
        token_used=budget.total_tokens if budget else session.token_used,
        finished_at=session.finished_at,
        final_version=session.final_version,
        total_versions=doc.version,
        agent_count=agent_count,
        max_edits_per_agent=max_edits_per_agent,
        agent_roles=agent_roles,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for Load Balancer"""
    return {"status": "healthy", "node_id": NODE_ID}


@app.get("/api/document/current", response_model=DocumentResponse)
async def get_current_document(
    document_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get current document version (optionally by id)"""
    session_obj = await resolve_document_session(
        db, document_id, include_inactive=bool(document_id)
    )
    if not session_obj:
        raise HTTPException(status_code=404, detail="No document found")

    doc = await get_latest_document(db, session_obj.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No document versions found")

    budget = await get_budget(db, session_obj.document_id)
    settings = await get_document_settings(db, session_obj.document_id)
    return build_document_response(session_obj, doc, budget, settings)


@app.get("/api/documents", response_model=List[DocumentListItem])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List document sessions with current version info."""
    versions_subquery = (
        select(Document.document_id, func.max(Document.version).label("current_version"))
        .group_by(Document.document_id)
        .subquery()
    )

    result = await db.execute(
        select(DocumentSession, versions_subquery.c.current_version)
        .outerjoin(
            versions_subquery,
            DocumentSession.document_id == versions_subquery.c.document_id,
        )
        .order_by(desc(DocumentSession.updated_at))
    )

    items: List[DocumentListItem] = []
    for session_obj, current_version in result.all():
        items.append(
            DocumentListItem(
                document_id=str(session_obj.document_id),
                topic=session_obj.topic,
                mode=session_obj.mode,
                status=session_obj.status.value,
                current_version=int(current_version or 0),
                final_version=session_obj.final_version,
                updated_at=session_obj.updated_at,
                finished_at=session_obj.finished_at,
            )
        )
    return items


@app.get("/api/document/{document_id}/versions", response_model=List[VersionItem])
async def get_document_versions(
    document_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get list of document versions (latest first)."""
    doc_uuid = uuid.UUID(document_id)
    result = await db.execute(
        select(Document)
        .where(Document.document_id == doc_uuid)
        .order_by(desc(Document.version))
        .limit(limit)
    )
    versions = result.scalars().all()
    return [
        VersionItem(version=doc.version, timestamp=doc.timestamp)
        for doc in versions
    ]


@app.get(
    "/api/document/{document_id}/versions/{version}/diff",
    response_model=VersionDiffResponse,
)
async def get_version_diff(
    document_id: str,
    version: int,
    base_version: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return diff between requested version and previous (or provided) version."""
    doc_uuid = uuid.UUID(document_id)
    target_result = await db.execute(
        select(Document).where(
            Document.document_id == doc_uuid, Document.version == version
        )
    )
    target_doc = target_result.scalar_one_or_none()
    if not target_doc:
        raise HTTPException(status_code=404, detail="Target version not found")

    if base_version is None:
        base_version = max(0, version - 1)

    base_doc = None
    if base_version > 0:
        base_result = await db.execute(
            select(Document).where(
                Document.document_id == doc_uuid, Document.version == base_version
            )
        )
        base_doc = base_result.scalar_one_or_none()

    base_text = base_doc.text if base_doc else ""
    segments = build_diff_segments(base_text, target_doc.text)
    if not segments and target_doc.text:
        segments = [DiffSegment(type="insert", text=target_doc.text).model_dump()]

    return VersionDiffResponse(
        document_id=str(doc_uuid),
        target_version=version,
        base_version=base_version if base_version > 0 else None,
        timestamp=target_doc.timestamp,
        segments=segments,
        target_text=target_doc.text,
    )


@app.post("/api/document/{document_id}/stop", response_model=DocumentActionResponse)
async def stop_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stop agents work for a document (irreversible)."""
    session_obj = await resolve_document_session(db, document_id, include_inactive=True)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = await get_latest_document(db, session_obj.document_id)
    if session_obj.status not in (DocumentStatus.STOPPED, DocumentStatus.FINALIZED):
        session_obj.status = DocumentStatus.STOPPED
        session_obj.finished_at = datetime.utcnow()
        session_obj.final_version = doc.version if doc else session_obj.final_version
        await db.commit()

    return DocumentActionResponse(
        document_id=str(session_obj.document_id),
        status=session_obj.status.value,
        finished_at=session_obj.finished_at,
        final_version=session_obj.final_version,
    )


@app.post("/api/document/{document_id}/finalize", response_model=DocumentActionResponse)
async def finalize_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark document as finalized (final version)."""
    session_obj = await resolve_document_session(db, document_id, include_inactive=True)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = await get_latest_document(db, session_obj.document_id)
    now = datetime.utcnow()
    session_obj.status = DocumentStatus.FINALIZED
    session_obj.finished_at = session_obj.finished_at or now
    session_obj.final_version = doc.version if doc else session_obj.final_version
    await db.commit()

    return DocumentActionResponse(
        document_id=str(session_obj.document_id),
        status=session_obj.status.value,
        finished_at=session_obj.finished_at,
        final_version=session_obj.final_version,
    )


@app.post("/api/document/init", response_model=DocumentInitResponse)
async def init_document(
    request: DocumentInitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initialize new document (multiple sessions supported)"""
    agent_count = request.agent_count or len(request.agent_roles or []) or (3 if request.mode == "light" else 10)
    per_agent_edits = (
        request.max_edits_per_agent
        or request.max_edits
        or (3 if request.mode == "light" else 10)
    )

    roles_payload = request.agent_roles or []
    if not roles_payload:
        roles_payload = [AgentRole(**role) for role in resolve_default_roles(request.mode, agent_count)]
    elif len(roles_payload) < agent_count:
        defaults = resolve_default_roles(request.mode, agent_count)
        roles_payload = list(roles_payload) + [AgentRole(**defaults[i]) for i in range(len(roles_payload), agent_count)]
    elif len(roles_payload) > agent_count:
        roles_payload = roles_payload[:agent_count]

    total_edits_limit = agent_count * per_agent_edits

    doc_session = DocumentSession(
        topic=request.topic,
        mode=request.mode,
        status=DocumentStatus.ACTIVE,
        max_edits=total_edits_limit,
        token_budget=request.token_budget or 50000,
        token_used=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(doc_session)
    await db.flush()

    # Set token budget per document
    budget = TokenBudget(
        document_id=doc_session.document_id,
        total_tokens=0,
        limit_tokens=request.token_budget or 50000,
    )
    db.add(budget)

    # Create initial document version
    doc = Document(
        document_id=doc_session.document_id,
        version=1,
        text=request.initial_text or "",
        timestamp=datetime.utcnow(),
        edit_id=None,
    )
    db.add(doc)

    settings = DocumentSettings(
        document_id=doc_session.document_id,
        agent_count=agent_count,
        max_edits_per_agent=per_agent_edits,
        agent_roles=[role.model_dump() if isinstance(role, AgentRole) else role for role in roles_payload],
    )
    db.add(settings)
    await db.commit()
    await db.refresh(doc_session)

    logger.info(
        f"Initialized document {doc_session.document_id} with topic: {request.topic}, mode: {request.mode}"
    )

    # Send analytics event
    await send_analytics_event(
        {
            "event_type": "document_initialized",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "topic": request.topic,
                "node_id": NODE_ID,
                "mode": request.mode,
                "token_budget": request.token_budget,
                "agent_count": agent_count,
                "max_edits_per_agent": per_agent_edits,
                "document_id": str(doc_session.document_id),
            },
        }
    )

    # Replicate to peers
    session_metadata = {
        "topic": doc_session.topic,
        "mode": doc_session.mode,
        "status": doc_session.status.value,
        "max_edits": doc_session.max_edits,
        "max_edits_per_agent": per_agent_edits,
        "agent_count": agent_count,
        "agent_roles": settings.agent_roles,
        "token_budget": doc_session.token_budget,
        "final_version": doc_session.final_version,
    }
    await replicate_to_peers(
        str(doc_session.document_id),
        doc.version,
        doc.text,
        doc.timestamp,
        None,
        session_metadata,
        budget.total_tokens,
    )

    return DocumentInitResponse(
        document_id=str(doc_session.document_id), status=doc_session.status.value
    )


@app.post("/api/edits", response_model=EditResponse)
async def submit_edit(
    edit_request: EditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit an edit from agent"""
    # Validate edit request
    is_valid, error_msg = validate_edit_request(edit_request)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Resolve target document
    session_obj = await resolve_document_session(db, edit_request.document_id, include_inactive=False)
    if not session_obj:
        raise HTTPException(status_code=404, detail="No active document found")
    if session_obj.status != DocumentStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Document is not active")

    # Start transaction
    try:
        # Check token budget
        budget = await get_budget(db, session_obj.document_id)
        if not budget:
            raise HTTPException(status_code=500, detail="Token budget not initialized")

        new_total_tokens = budget.total_tokens + edit_request.tokens_used
        if new_total_tokens > budget.limit_tokens:
            logger.warning(
                f"Budget exceeded for {session_obj.document_id}: {new_total_tokens} > {budget.limit_tokens}"
            )

            await send_analytics_event(
                {
                    "event_type": "budget_exceeded",
                    "agent_id": edit_request.agent_id,
                    "tokens": edit_request.tokens_used,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "total_tokens": budget.total_tokens,
                        "limit_tokens": budget.limit_tokens,
                        "document_id": str(session_obj.document_id),
                    },
                }
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Token budget exceeded",
            )

        # Get current document
        current_doc = await get_latest_document(db, session_obj.document_id)
        if not current_doc:
            raise HTTPException(status_code=404, detail="No document found")

        # Create edit record
        edit = Edit(
            document_id=session_obj.document_id,
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
                document_id=str(session_obj.document_id),
                edit_id=str(edit.edit_id),
                status="rejected",
                version=current_doc.version,
            )

        # Create new document version
        new_version = current_doc.version + 1
        new_doc = Document(
            document_id=session_obj.document_id,
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
            .where(TokenBudget.document_id == session_obj.document_id)
            .values(
                total_tokens=new_total_tokens,
                updated_at=datetime.utcnow(),
            )
        )
        session_obj.token_used = new_total_tokens
        session_obj.updated_at = datetime.utcnow()

        # Mark as completed when max edits reached
        edits_applied = new_version - 1
        if session_obj.max_edits and edits_applied >= session_obj.max_edits:
            session_obj.status = DocumentStatus.COMPLETED
            session_obj.finished_at = datetime.utcnow()
            session_obj.final_version = new_version

        await db.commit()

        logger.info(
            f"Edit {edit.edit_id} accepted for {session_obj.document_id}, new version: {new_version}"
        )

        # Send analytics event
        await send_analytics_event(
            {
                "event_type": "edit_applied",
                "agent_id": edit_request.agent_id,
                "version": new_version,
                "tokens": edit_request.tokens_used,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "edit_id": str(edit.edit_id),
                    "operation": edit_request.operation,
                    "node_id": NODE_ID,
                    "document_id": str(session_obj.document_id),
                },
            }
        )

        if session_obj.status == DocumentStatus.COMPLETED:
            await send_analytics_event(
                {
                    "event_type": "document_completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "document_id": str(session_obj.document_id),
                        "final_version": new_version,
                        "node_id": NODE_ID,
                    },
                }
            )

        # Replicate to peers (async, don't wait)
        settings = await get_document_settings(db, session_obj.document_id)

        session_metadata = {
            "topic": session_obj.topic,
            "mode": session_obj.mode,
            "status": session_obj.status.value,
            "max_edits": session_obj.max_edits,
            "max_edits_per_agent": settings.max_edits_per_agent if settings else None,
            "agent_count": settings.agent_count if settings else None,
            "agent_roles": settings.agent_roles if settings else None,
            "token_budget": session_obj.token_budget,
            "final_version": session_obj.final_version,
        }
        await replicate_to_peers(
            str(session_obj.document_id),
            new_doc.version,
            new_doc.text,
            new_doc.timestamp,
            str(edit.edit_id),
            session_metadata,
            new_total_tokens,
        )

        return EditResponse(
            document_id=str(session_obj.document_id),
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
    document_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get list of edits with pagination"""
    query = select(Edit).order_by(desc(Edit.created_at))
    if document_id:
        query = query.where(Edit.document_id == uuid.UUID(document_id))

    result = await db.execute(query.limit(limit).offset(offset))
    edits = result.scalars().all()

    return [
        EditListItem(
            document_id=str(edit.document_id),
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
    db: AsyncSession = Depends(get_db),
):
    """Accept replication message from another node"""
    try:
        doc_uuid = uuid.UUID(request.document_id)

        # Ensure session exists
        def safe_status(value: Optional[str]) -> DocumentStatus:
            try:
                return DocumentStatus(value) if value else DocumentStatus.ACTIVE
            except Exception:
                return DocumentStatus.ACTIVE

        session_obj = await resolve_document_session(
            db, str(doc_uuid), include_inactive=True
        )
        if not session_obj:
            session_status = safe_status(request.status)
            incoming_agent_count = request.agent_count or (len(request.agent_roles or []) or (3 if request.mode == "light" else 10))
            if incoming_agent_count <= 0:
                incoming_agent_count = 3 if request.mode == "light" else 10
            incoming_max_per_agent = request.max_edits_per_agent or safe_div_int(request.max_edits, incoming_agent_count)
            session_obj = DocumentSession(
                document_id=doc_uuid,
                topic=request.topic or "replicated",
                mode=request.mode,
                status=session_status,
                max_edits=request.max_edits or (incoming_agent_count * (incoming_max_per_agent or 0)),
                token_budget=request.token_budget or 0,
                token_used=request.token_used or 0,
                final_version=request.final_version,
                created_at=request.timestamp,
                updated_at=request.timestamp,
            )
            db.add(session_obj)

            if request.token_budget is not None:
                db.add(
                    TokenBudget(
                        document_id=doc_uuid,
                        total_tokens=request.token_used or 0,
                        limit_tokens=request.token_budget,
                        updated_at=request.timestamp,
                    )
                )
            db.add(
                DocumentSettings(
                    document_id=doc_uuid,
                    agent_count=incoming_agent_count,
                    max_edits_per_agent=incoming_max_per_agent or 0,
                    agent_roles=request.agent_roles,
                    created_at=request.timestamp,
                    updated_at=request.timestamp,
                )
            )
        else:
            if request.status:
                session_obj.status = safe_status(request.status)
            if request.final_version is not None:
                session_obj.final_version = request.final_version
            if request.max_edits is not None:
                session_obj.max_edits = request.max_edits
            if request.token_used is not None:
                session_obj.token_used = request.token_used
                await db.execute(
                    update(TokenBudget)
                    .where(TokenBudget.document_id == doc_uuid)
                    .values(
                        total_tokens=request.token_used,
                        updated_at=request.timestamp,
                    )
                )
            settings = await get_document_settings(db, doc_uuid)
            incoming_agent_count = request.agent_count or (settings.agent_count if settings else None)
            if settings:
                if request.agent_count:
                    settings.agent_count = request.agent_count
                if request.max_edits_per_agent:
                    settings.max_edits_per_agent = request.max_edits_per_agent
                if request.agent_roles:
                    settings.agent_roles = request.agent_roles
            else:
                inferred_count = incoming_agent_count or (len(request.agent_roles or []) or (3 if request.mode == "light" else 10))
                db.add(
                    DocumentSettings(
                        document_id=doc_uuid,
                        agent_count=inferred_count,
                        max_edits_per_agent=request.max_edits_per_agent or 0,
                        agent_roles=request.agent_roles,
                        created_at=request.timestamp,
                        updated_at=request.timestamp,
                    )
                )

        # Check if version already exists
        result = await db.execute(
            select(Document).where(
                Document.document_id == doc_uuid, Document.version == request.version
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                f"Version {request.version} for {doc_uuid} already exists, skipping replication"
            )
            return ReplicationSyncResponse(
                status="already_synced", version=request.version
            )

        # Get current highest version for document
        result = await db.execute(
            select(func.max(Document.version)).where(Document.document_id == doc_uuid)
        )
        max_version = result.scalar() or 0

        if request.version <= max_version:
            logger.warning(
                f"Received old version {request.version} for {doc_uuid}, current max: {max_version}"
            )
            return ReplicationSyncResponse(status="outdated", version=max_version)

        # Apply replication
        new_doc = Document(
            document_id=doc_uuid,
            version=request.version,
            text=request.text,
            timestamp=request.timestamp,
            edit_id=request.edit_id,
        )
        db.add(new_doc)
        await db.commit()

        logger.info(f"Replicated version {request.version} for {doc_uuid} from {request.source_node}")

        return ReplicationSyncResponse(status="synced", version=request.version)

    except Exception as e:
        await db.rollback()
        logger.error(f"Replication error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/replication/catch-up", response_model=CatchUpResponse)
async def replication_catchup(
    document_id: str,
    since_version: int,
    db: AsyncSession = Depends(get_db),
):
    """Get versions for node recovery"""
    doc_uuid = uuid.UUID(document_id)
    result = await db.execute(
        select(Document)
        .where(Document.document_id == doc_uuid, Document.version > since_version)
        .order_by(Document.version)
    )
    documents = result.scalars().all()

    versions = [
        {
            "version": doc.version,
            "text": doc.text,
            "timestamp": doc.timestamp.isoformat(),
            "edit_id": str(doc.edit_id) if doc.edit_id else None,
            "document_id": str(doc.document_id),
        }
        for doc in documents
    ]

    logger.info(
        f"Catch-up request for document {document_id} versions > {since_version}, returning {len(versions)} versions"
    )

    return CatchUpResponse(versions=versions)
