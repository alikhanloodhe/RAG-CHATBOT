import io
import json
import logging
import time
import uuid
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pypdf import PdfReader

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, is_password_hash, verify_password
from app.db.session import get_session, get_engine
from app.models.models import UserDocument, User
from app.core.config import settings
from app.services.cache import cache_service
from app.services.chunker import text_chunker
from app.services.embeddings import embedding_service
from app.services.rag import rag_service
from app.services.llm import llm_service
from app.services.query_cache import build_query_cache_key, invalidate_user_query_cache
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

def extract_text_sync(content_type: str, file_bytes: bytes) -> str:
    """Synchronously extracts text from the document byte array."""
    if content_type == "application/pdf":
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        text_content = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_content += extracted + "\n"
        return text_content
    else:
        # Treat any other file format (txt, md, log, csv, json) as raw text decoding
        return file_bytes.decode("utf-8", errors="ignore")

async def process_document_task(doc_id: int, file_bytes: bytes, filename: str, content_type: str, user_id: int):
    """Processes document in the background: parses PDF/txt, chunks text, embeds, and uploads to Qdrant.

    Offloads CPU-bound parsing and embedding computations to threads to keep the main event loop responsive.

    Args:
        doc_id: The ID of the UserDocument record.
        file_bytes: The raw document binary bytes.
        filename: Name of the uploaded file.
        content_type: Content MIME type (e.g. application/pdf).
        user_id: ID of the user owning the document.
    """
    import asyncio
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.orm import sessionmaker

    # Create a fresh isolated session for the background execution
    async_session = sessionmaker(
        get_engine(), class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Fetch document
            doc = await session.get(UserDocument, doc_id)
            if not doc:
                return

            doc.status = "processing"
            session.add(doc)
            await session.commit()
            await session.refresh(doc)

            # Extract Text in a background thread to prevent event loop blocking
            text = await asyncio.to_thread(extract_text_sync, content_type, file_bytes)

            if not text.strip():
                raise ValueError("Extracted text is empty or could not be parsed.")

            # Segment into token-based sentence-preserving chunks in a background thread
            chunks = await asyncio.to_thread(text_chunker.chunk_text, text)
            if not chunks:
                raise ValueError("Document yielded 0 chunks.")

            # Compute BAAI/bge-small-en-v1.5 embeddings in a background thread
            embeddings = await asyncio.to_thread(embedding_service.get_embeddings, chunks)

            # Upload Dense Vectors + Metadata payloads to Qdrant
            ids = [str(uuid.uuid4()) for _ in chunks]
            payloads = [
                {
                    "document_id": doc_id,
                    "user_id": user_id,
                    "filename": filename,
                    "chunk_index": i,
                    "text": chunk
                }
                for i, chunk in enumerate(chunks)
            ]

            # Upsert vectors (network/disk-bound call, offloaded or run directly)
            await asyncio.to_thread(
                rag_service.upsert_vectors,
                collection_name="rag_documents",
                ids=ids,
                vectors=embeddings,
                payloads=payloads
            )

            # Update Document metadata table
            doc.status = "completed"
            doc.vector_count = len(chunks)
            session.add(doc)
            await session.commit()
            invalidate_user_query_cache(user_id)
            logger.info(
                "Document processed",
                extra={"document_id": doc_id, "filename": filename, "chunk_count": len(chunks)},
            )

        except Exception as e:
            logger.exception(
                "Document ingest failed",
                extra={"document_id": doc_id, "filename": filename},
            )
            try:
                # Re-fetch in case session was closed/rolled back
                doc = await session.get(UserDocument, doc_id)
                if doc:
                    doc.status = "failed"
                    session.add(doc)
                    await session.commit()
            except Exception:
                logger.exception("Failed to mark document ingest as failed", extra={"document_id": doc_id})

@router.post("/upload", status_code=201)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Uploads documents, saving metadata to PostgreSQL and parsing vectors in the background.

    Args:
        background_tasks: FastAPI background tasks queue executor.
        files: List of uploaded files (PDFs, TXT, MD, etc.).
        session: Active DB session dependency.
        current_user: Currently authenticated User.

    Returns:
        JSON response with the list of queued document metadata.
    """
    uploaded_docs = []
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Invalid authenticated user")

    for file in files:
        content = await file.read()
        
        # Create initial Database metadata entry
        db_doc = UserDocument(
            user_id=current_user.id,
            filename=file.filename or "unknown_file",
            content_type=file.content_type or "text/plain",
            size_bytes=len(content),
            status="pending",
            vector_count=0
        )
        session.add(db_doc)
        await session.commit()
        await session.refresh(db_doc)

        # Trigger background processing
        background_tasks.add_task(
            process_document_task,
            doc_id=db_doc.id,
            file_bytes=content,
            filename=db_doc.filename,
            content_type=db_doc.contentType if hasattr(db_doc, 'contentType') else db_doc.content_type,
            user_id=current_user.id
        )
        uploaded_docs.append(db_doc)

    invalidate_user_query_cache(current_user.id)
    return {"message": f"Queued {len(files)} file(s) for ingestion.", "documents": uploaded_docs}

@router.get("/")
async def list_documents(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Lists all document metadata entries belonging to the current user.

    Args:
        session: Active DB session dependency.
        current_user: Currently authenticated User.

    Returns:
        List of UserDocument metadata records.
    """
    statement = select(UserDocument).where(UserDocument.user_id == current_user.id).order_by(UserDocument.id.desc())
    results = await session.execute(statement)
    documents = results.scalars().all()
    return documents

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Deletes a document's metadata from the DB and its vectors from Qdrant.

    Args:
        document_id: Database ID of the document to delete.
        session: Active DB session dependency.
        current_user: Currently authenticated User.

    Returns:
        JSON status message confirming deletion.
    """
    db_doc = await session.get(UserDocument, document_id)
    if not db_doc or db_doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Clean vectors from Qdrant
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        rag_service.client.delete(
            collection_name="rag_documents",
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
        )
    except Exception:
        logger.warning("Failed to delete document vectors from Qdrant", extra={"document_id": document_id}, exc_info=True)

    await session.delete(db_doc)
    await session.commit()
    invalidate_user_query_cache(current_user.id)
    return {"message": f"Document #{document_id} and its associated vectors deleted."}

@router.get("/search")
async def search_rag(query: str, limit: int = 3, current_user: User = Depends(get_current_user)):
    """Runs a hybrid search over the Qdrant database, scoped to the current user.

    Args:
        query: The raw string query.
        limit: Number of results to fetch (defaults to 3).
        current_user: Currently authenticated User.

    Returns:
        A list of matching records.
    """
    results = rag_service.search(query, collection_name="rag_documents", limit=limit, user_id=current_user.id)
    return results

class QueryRequest(BaseModel):
    query: str

class Citation(BaseModel):
    source_id: str
    score: float | None = None
    filename: str
    chunk_index: int
    text: str

class QueryTimings(BaseModel):
    retrieval_ms: int
    generation_ms: int
    total_ms: int

class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    timings: QueryTimings
    cache_hit: bool = False

def build_citations(search_results: list[dict]) -> list[Citation]:
    """Builds structured Citation objects from raw search results.

    Args:
        search_results: List of search result dictionaries containing IDs, scores, and payloads.

    Returns:
        List of formatted Citation objects.
    """
    citations = []
    for result in search_results:
        payload = result.get("payload") or {}
        citations.append(
            Citation(
                source_id=str(result.get("id", "")),
                score=result.get("score"),
                filename=payload.get("filename", "unknown"),
                chunk_index=payload.get("chunk_index", 0),
                text=payload.get("text", ""),
            )
        )
    return citations


@router.post("/query")
async def query_pipeline(request: QueryRequest, current_user: User = Depends(get_current_user)) -> QueryResponse:
    """Orchestrates the RAG pipeline: check cache, retrieve context, synthesize answer, cache result.

    Args:
        request: Schema with raw user search query string.
        current_user: Currently authenticated User.

    Returns:
        QueryResponse containing answer text, citations, and execution latency details.
    """
    started_at = time.perf_counter()
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Invalid authenticated user")

    cache_key = build_query_cache_key(current_user.id, request.query)
    cached_payload = cache_service.get(cache_key)
    if cached_payload:
        try:
            cached_response = QueryResponse.model_validate_json(cached_payload)
            cached_response.cache_hit = True
            cached_response.timings.retrieval_ms = 0
            cached_response.timings.generation_ms = 0
            cached_response.timings.total_ms = round((time.perf_counter() - started_at) * 1000)
            logger.info("Query cache hit", extra={"user_id": current_user.id, "cache_key": cache_key})
            return cached_response
        except (ValueError, json.JSONDecodeError):
            logger.warning("Ignoring invalid cached query payload", extra={"cache_key": cache_key})
    else:
        logger.info("Query cache miss", extra={"user_id": current_user.id, "cache_key": cache_key})

    retrieval_started_at = time.perf_counter()
    search_results = rag_service.search(request.query, collection_name="rag_documents", limit=5, user_id=current_user.id)
    retrieval_ms = round((time.perf_counter() - retrieval_started_at) * 1000)

    context_items = [res["payload"] for res in search_results if res.get("payload")]
    citations = build_citations(search_results)

    generation_started_at = time.perf_counter()
    answer = llm_service.generate_answer(request.query, context_items)
    generation_ms = round((time.perf_counter() - generation_started_at) * 1000)

    total_ms = round((time.perf_counter() - started_at) * 1000)
    response = QueryResponse(
        answer=answer,
        citations=citations,
        timings=QueryTimings(
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,
        ),
        cache_hit=False,
    )
    cache_service.set(cache_key, response.model_dump_json(), expire_seconds=settings.QUERY_CACHE_TTL_SECONDS)
    return response

class RegisterRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

@router.post("/auth/register")
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """Registers a new user account and generates a JWT access token.

    Args:
        request: Register request with username and password.
        session: Active DB session dependency.

    Returns:
        AuthResponse containing JWT access token and user metadata.
    """
    # Check if username already exists
    statement = select(User).where(User.username == request.username)
    results = await session.execute(statement)
    existing_user = results.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(username=request.username, password_hash=hash_password(request.password))
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    access_token = create_access_token(subject=new_user.id)
    return AuthResponse(
        access_token=access_token,
        user=UserResponse(id=new_user.id, username=new_user.username),
    )

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/auth/login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Authenticates a user, upgrades password hashes if legacy, and issues a JWT token.

    Args:
        request: Login request with username and password.
        session: Active DB session dependency.

    Returns:
        AuthResponse containing JWT access token and user metadata.
    """
    statement = select(User).where(User.username == request.username)
    results = await session.execute(statement)
    user = results.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    stored_password = user.password_hash
    legacy_plaintext_match = not is_password_hash(stored_password) and stored_password == request.password
    if not legacy_plaintext_match and not verify_password(request.password, stored_password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if legacy_plaintext_match:
        user.password_hash = hash_password(request.password)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    access_token = create_access_token(subject=user.id)
    return AuthResponse(
        access_token=access_token,
        user=UserResponse(id=user.id, username=user.username),
    )
