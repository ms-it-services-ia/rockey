from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    database_url: str = "postgresql://rockey:changeme@localhost:5432/rockeydb"
    redis_host: str = "localhost"
    redis_port: int = 6379
    java_services_url: str = "http://localhost:8080"
    internal_service_token: str = "changeme_internal_token"

    google_service_account_json: str = ""
    vinted_drive_folder_id: str = ""

    slack_mcp_token: str = ""
    gmail_mcp_token: str = ""

    # Constitution I.4 / VI.2 timeouts (seconds)
    timeout_llm: int = 30
    timeout_java: int = 10
    timeout_mcp: int = 15
    timeout_pgvector: int = 5
    max_retries: int = 2

    # Constitution I.2 / III.4
    session_ttl_seconds: int = 30 * 60
    max_identification_attempts: int = 2
    max_reformulations: int = 3


settings = Settings()
