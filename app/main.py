from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.vector_store import vector_store
from app.cache import cache
from app.rag import ingest_video, ask_question


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, clean up on shutdown."""
    # Startup
    vector_store.ensure_collection()
    try:
        await cache.connect()
    except Exception:
        print("⚠ Redis not available — caching disabled")
    yield
    # Shutdown
    await cache.close()


app = FastAPI(
    title="YouTube Explaininator",
    description="Ask questions about YouTube videos in any of 22 Indian languages",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Request / Response models ---

class IngestRequest(BaseModel):
    youtube_url: str

class IngestResponse(BaseModel):
    video_id: str
    url: str
    status: str
    chunks: int = 0

class AskRequest(BaseModel):
    youtube_url: str
    question: str

class AskResponse(BaseModel):
    answer: str
    language: str
    sources: list[dict] = []
    cached: bool = False


# --- Endpoints ---

@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(req: IngestRequest):
    """Pre-ingest a video's transcript into the vector store."""
    try:
        result = await ingest_video(req.youtube_url)
        return IngestResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest):
    """Ask a question about a YouTube video. Auto-detects language and responds in kind."""
    try:
        result = await ask_question(req.youtube_url, req.question)
        return AskResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
