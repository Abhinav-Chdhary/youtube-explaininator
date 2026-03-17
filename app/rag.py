import asyncio
from app.transcript import extract_video_id, fetch_transcript, chunk_transcript, get_video_metadata
from app.embeddings import embedding_model
from app.vector_store import vector_store
from app.llm import ask_claude, detect_language
from app.cache import cache
from app.config import settings


async def ingest_video(youtube_url: str) -> dict:
    """Extract, chunk, embed, and store a video's transcript.

    Returns metadata about the ingested video.
    """
    video_id = extract_video_id(youtube_url)
    metadata = get_video_metadata(video_id)

    # Skip if already ingested
    if vector_store.video_exists(video_id):
        return {**metadata, "status": "already_ingested"}

    # Fetch and chunk transcript (CPU-bound, run in thread)
    transcript = await asyncio.to_thread(fetch_transcript, video_id)
    chunks = await asyncio.to_thread(
        chunk_transcript, transcript, settings.chunk_size, settings.chunk_overlap
    )

    if not chunks:
        raise ValueError(f"No transcript content found for video: {video_id}")

    # Embed all chunks
    texts = [c["text"] for c in chunks]
    embeddings = await embedding_model.encode(texts)

    # Store in Qdrant
    await asyncio.to_thread(
        vector_store.upsert_chunks,
        embeddings.tolist(),
        chunks,
        video_id,
        metadata["url"],
    )

    return {**metadata, "status": "ingested", "chunks": len(chunks)}


async def ask_question(youtube_url: str, question: str) -> dict:
    """Full RAG pipeline: ingest (if needed) → detect language → retrieve → generate.

    Returns {answer, language, sources}.
    """
    video_id = extract_video_id(youtube_url)

    # 1. Detect language via local Ollama
    language = await asyncio.to_thread(detect_language, question)

    # 2. Check cache first (saves Claude API calls)
    cached = await cache.get(video_id, question, language)
    if cached:
        return {
            "answer": cached,
            "language": language,
            "sources": [],
            "cached": True,
        }

    # 3. Ingest video if not already done
    await ingest_video(youtube_url)

    # 4. Embed the question and search
    query_embedding = await embedding_model.encode([question])
    results = await asyncio.to_thread(
        vector_store.search,
        query_embedding[0].tolist(),
        video_id,
        settings.top_k,
    )

    if not results:
        answer = "I could not find any relevant information in this video."
        return {"answer": answer, "language": language, "sources": [], "cached": False}

    # 5. Generate answer via Claude
    answer = await ask_claude(results, question, language)

    # 6. Cache the answer
    await cache.set(video_id, question, language, answer)

    # 7. Build source citations
    sources = [
        {
            "video_url": r["video_url"],
            "start_time": r["start_time"],
            "score": round(r["score"], 3),
        }
        for r in results
    ]

    return {
        "answer": answer,
        "language": language,
        "sources": sources,
        "cached": False,
    }
