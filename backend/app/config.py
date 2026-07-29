from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GlassJar"
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
    # The wallet/settlement account disbursements are debited from — from
    # your Monnify dashboard. Required for expense payouts; not needed for
    # collecting payments.
    monnify_wallet_account_number: str = ""

    # Flutterwave v4 (OAuth2 client-credentials) — the active payment rail.
    flutterwave_client_id: str = ""
    flutterwave_client_secret: str = ""
    flutterwave_encryption_key: str = ""
    # Set on the Flutterwave dashboard under Webhooks — used to verify the
    # flutterwave-signature header on incoming webhook deliveries.
    flutterwave_webhook_secret_hash: str = ""
    flutterwave_idp_url: str = (
        "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"
    )
    flutterwave_base_url: str = "https://f4bexperience.flutterwave.com"
    # Optional: pin virtual-account creation to a specific partner bank code
    # instead of letting Flutterwave auto-assign one. Leave blank for
    # auto-assignment. Set this if your auto-assigned bank is having issues
    # (e.g. an outage) and support gives you a working bank code to use.
    flutterwave_preferred_bank_code: str = ""

    nvidia_api_key: str = ""

    # Comma-separated list of allowed browser origins.
    frontend_origin: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


settings = Settings()
