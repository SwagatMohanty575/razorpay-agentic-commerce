from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./app.db"

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    llm_provider: str = "ollama"
    llm_model: str = "llama3.1"
    llm_base_url: str = "http://localhost:11434"

    auto_approve_max_inr: int = 2000
    user_confirm_max_inr: int = 10000

    class Config:
        env_file = str(ENV_FILE)


settings = Settings()