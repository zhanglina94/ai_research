"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Research OS"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8002
    cors_origins: str = "http://localhost:2008,http://127.0.0.1:2008,http://localhost:3000"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "research"
    postgres_password: str = "research"
    postgres_db: str = "research_os"

    redis_host: str = "localhost"
    redis_port: int = 6379

    milvus_host: str = "localhost"
    milvus_port: int = 19530

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "research"

    arxiv_max_results: int = 10
    storage_path: str = "storage"

    mlflow_tracking_uri: str = "http://localhost:5000"

    autoresearch_max_iterations: int = 12
    autoresearch_train_budget_seconds: int = 300

    # Experiment training: mock | nanochat
    experiment_training_mode: str = "mock"
    experiment_use_gpu: bool = False
    experiment_use_docker: bool = False
    experiment_docker_image: str = "research-ai-experiment-sandbox:latest"
    experiment_docker_memory: str = "4g"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        key = self.openai_api_key.strip()
        return bool(key) and not key.startswith("sk-place")


@lru_cache
def get_settings() -> Settings:
    return Settings()
