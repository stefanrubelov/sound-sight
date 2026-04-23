from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./soundsight.db"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost",
        "http://127.0.0.1",
    ]

    # Logging
    log_level: str = "INFO"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ChromaDB
    chroma_persist_dir: str = "./rag/chroma_data"


settings = Settings()
