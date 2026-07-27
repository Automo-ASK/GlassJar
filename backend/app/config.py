from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AcaFund"
    env: str = "development"

    secret_key: str
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10

    monnify_api_key: str = ""
    monnify_secret_key: str = ""
    monnify_contract_code: str = ""
    monnify_base_url: str = "https://sandbox.monnify.com"

    nvidia_api_key: str = ""

    # Comma-separated list of allowed browser origins.
    frontend_origin: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


settings = Settings()
