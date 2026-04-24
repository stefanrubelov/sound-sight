from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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

    # ML model
    ml_model_path: str = "../ml/artifacts/soundsight_classifier.joblib"
    ml_unknown_threshold: float = 0.50

    # Per-class severity: critical | warn | info | none
    class_severity: dict[str, str] = {
        "fire_alarm": "critical",
        "glass_breaking": "critical",
        "baby_crying": "warn",
        "doorbell": "warn",
        "dog_barking": "warn",
        "timer_beep": "info",
        "water_running": "info",
        "unknown": "none",
    }

    # Per-class LED hex color (matches firmware color map)
    class_led_color: dict[str, str] = {
        "fire_alarm": "#FF0000",
        "glass_breaking": "#FF0000",
        "baby_crying": "#FFFF00",
        "doorbell": "#0000FF",
        "dog_barking": "#FFFF00",
        "timer_beep": "#00FF00",
        "water_running": "#0000FF",
        "unknown": "#000000",
    }

    # Per-severity vibration pattern (matches firmware pattern names)
    severity_vibration: dict[str, str] = {
        "critical": "continuous",
        "warn": "double_pulse",
        "info": "short_pulse",
        "none": "none",
    }


settings = Settings()
