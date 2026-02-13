from pathlib import Path

from pydantic_settings import BaseSettings

# .env 파일 탐색: backend/.env → 프로젝트 루트/.env
_backend_dir = Path(__file__).resolve().parent.parent
_env_candidates = [_backend_dir / ".env", _backend_dir.parent / ".env"]
_env_file = next((p for p in _env_candidates if p.exists()), ".env")


class Settings(BaseSettings):
    model_config = {"env_file": str(_env_file), "env_file_encoding": "utf-8"}

    # Application
    app_env: str = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./auction.db"

    # Anthropic
    anthropic_api_key: str = ""

    # 국토교통부 API
    molit_api_key: str = ""

    # Naver News API
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # File Upload
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    max_total_size_mb: int = 200

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
