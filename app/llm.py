import anthropic
import ollama
from app.config import settings, INDIAN_LANGUAGES
from app.rate_limiter import RateLimiter

# Shared rate limiter for Claude API
claude_limiter = RateLimiter(max_requests=5, window_seconds=60)


SYSTEM_PROMPT = """You are a helpful assistant that answers questions about YouTube videos.
You will be given context extracted from a video's transcript, and a user's question.

Rules:
1. Answer ONLY based on the provided context. Do not use outside knowledge.
2. If the context does not contain enough information to answer, say "I could not find an answer to this in the video."
3. Keep answers concise and informative (under 500 words).
4. Cite the approximate timestamp when referencing specific parts of the video.
5. You MUST respond in the language specified below. This is critical.

Response language: {language}
"""


async def ask_claude(context_chunks: list[dict], question: str, language: str) -> str:
    """Send a RAG query to Claude and return the answer."""
    await claude_limiter.acquire()

    # Build context block from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        minutes = int(chunk["start_time"] // 60)
        seconds = int(chunk["start_time"] % 60)
        timestamp = f"{minutes}:{seconds:02d}"
        context_parts.append(f"[Chunk {i} | ~{timestamp}]\n{chunk['text']}")

    context_block = "\n\n".join(context_parts)

    system = SYSTEM_PROMPT.format(language=language)
    user_message = f"## Video Context\n\n{context_block}\n\n## Question\n\n{question}"

    client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


def detect_language(text: str) -> str:
    """Use local Ollama to detect the language of the user's input.

    Returns a language name like 'Hindi', 'Tamil', 'English', etc.
    """
    valid_languages = ", ".join(lang.title() for lang in INDIAN_LANGUAGES)

    client = ollama.Client(host=settings.ollama_base_url)
    response = client.chat(
        model=settings.ollama_model,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Detect the language of this text. Respond with ONLY the "
                    f"language name — one of: {valid_languages}. "
                    f"Nothing else.\n\nText: {text}"
                ),
            }
        ],
    )

    detected = response.message.content.strip().lower()

    # Fuzzy match against known languages
    for lang_name in INDIAN_LANGUAGES:
        if lang_name in detected:
            return lang_name

    return "english"  # default fallback
