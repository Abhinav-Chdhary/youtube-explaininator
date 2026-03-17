from pydantic_settings import BaseSettings


INDIAN_LANGUAGES = {
    "assamese": "as", "bengali": "bn", "bodo": "brx", "dogri": "doi",
    "gujarati": "gu", "hindi": "hi", "kannada": "kn", "kashmiri": "ks",
    "konkani": "kok", "maithili": "mai", "malayalam": "ml", "manipuri": "mni",
    "marathi": "mr", "nepali": "ne", "odia": "or", "punjabi": "pa",
    "sanskrit": "sa", "santali": "sat", "sindhi": "sd", "tamil": "ta",
    "telugu": "te", "urdu": "ur", "english": "en",
}


class Settings(BaseSettings):
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6-20250514"
    claude_max_tokens: int = 1024
    ollama_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    collection_name: str = "youtube_videos"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1 hour

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
