# YouTube Explaininator

Ask questions about any YouTube video in any of the 22 official Indian languages. Paste a link, ask in your language, get an answer in your language.

## How It Works

```
User Question (any language)
        │
        ▼
┌─────────────────┐
│  Ollama (local)  │ ← Detects language
│  Llama 3.1 8B   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   bge-m3 (local) │ ← Embeds question (multilingual)
│   Embeddings     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Qdrant (Docker)│ ← Finds relevant video chunks
│   Vector Search  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Claude API     │ ← Generates answer in user's language
│   (Sonnet)       │
└────────┬────────┘
         │
         ▼
    Answer in Hindi / Tamil / Bengali / ...
```

**Key design**: Claude API is only used for the final answer (1 call per question). Everything else runs locally — no rate limit concerns for embeddings, language detection, or vector search.

## Supported Languages

Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri, Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu, English.

## Prerequisites

- **Python 3.14+**
- **Docker Desktop** — for Qdrant vector database
- **Ollama** — for local Llama model
- **Redis** — for caching (optional but recommended)
- **Claude API key** — from [console.anthropic.com](https://console.anthropic.com)

## Setup

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd youtube-explaininator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Docker and Qdrant

Open Docker Desktop (or start the daemon), then:

```bash
docker compose up -d
```

This starts Qdrant on `localhost:6333`. Verify it's running:

```bash
curl http://localhost:6333/healthz
# Should return: {"title":"qdrant - vectorass engine","version":"..."}
```

### 3. Start Ollama and pull Llama 3.1

If you don't have Ollama installed:

```bash
# macOS
brew install ollama
```

Start the Ollama server:

```bash
ollama serve
```

In a new terminal, pull the Llama 3.1 model (~5GB download):

```bash
ollama pull llama3.1
```

Verify it works:

```bash
ollama run llama3.1 "Say hello in Tamil"
# Should respond with: வணக்கம் (Vanakkam)
```

### 4. Start Redis (optional)

Redis caches answers so repeated questions don't burn Claude API calls. If you skip this, the app still works — caching is just disabled.

```bash
# macOS
brew install redis
redis-server --daemonize yes

# Verify
redis-cli ping
# Should return: PONG
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Claude API key:

```
CLAUDE_API_KEY=sk-ant-your-key-here
```

All other defaults are fine for local development.

### 6. First run — model download

The first time the app starts, it downloads the `BAAI/bge-m3` multilingual embedding model (~2.2GB). This is a one-time download cached in `~/.cache/huggingface/`.

### 7. Start the server

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

You should see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Usage

### Ingest a video

Pre-load a video's transcript into the vector store:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

Response:

```json
{
  "video_id": "VIDEO_ID",
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "status": "ingested",
  "chunks": 42
}
```

### Ask a question

Ask in any supported language — the system auto-detects the language and responds in kind:

```bash
# Hindi
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "question": "इस वीडियो का मुख्य विषय क्या है?"
  }'

# Tamil
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "question": "இந்த வீடியோவின் முக்கிய கருத்து என்ன?"
  }'

# English
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "question": "What is the main topic of this video?"
  }'
```

Response:

```json
{
  "answer": "The answer in the detected language...",
  "language": "hindi",
  "sources": [
    {"video_url": "https://...", "start_time": 45.2, "score": 0.87}
  ],
  "cached": false
}
```

The `/ask` endpoint auto-ingests the video if it hasn't been ingested yet, so you can skip the `/ingest` step.

### Health check

```bash
curl http://localhost:8000/health
```

### API docs

FastAPI auto-generates interactive docs:

```
http://localhost:8000/docs
```

## Architecture

| Component | Role | Runs |
|---|---|---|
| **Llama 3.1** (Ollama) | Language detection | Locally |
| **bge-m3** (sentence-transformers) | Multilingual embeddings | Locally |
| **Qdrant** (Docker) | Vector similarity search | Locally |
| **Redis** | Response caching | Locally |
| **Claude Sonnet** (API) | Final answer generation | API (5 req/min free tier) |

## Rate Limits

The app is designed for Claude's free tier (5 requests/min, 4K output tokens/min):

- Embeddings and language detection run locally — no API limits
- Only the final answer generation calls Claude (1 call per question)
- Redis caching prevents duplicate API calls for repeated questions
- Built-in rate limiter queues requests if you exceed 5/min

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker compose up` fails | Make sure Docker Desktop is running |
| `ollama` model not found | Run `ollama pull llama3.1` |
| `Connection refused` on port 6333 | Qdrant container isn't running — `docker compose up -d` |
| `Connection refused` on port 11434 | Ollama server isn't running — `ollama serve` |
| First request is slow | bge-m3 model loading into memory (~10s first time) |
| `No transcript available` | Video has no captions/subtitles |
