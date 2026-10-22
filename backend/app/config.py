from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    football_data_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    xai_api_key: str = ""
    anthropic_api_key: str = ""
    # Model names can change or be retired: override in .env without touching code
    openai_model: str = "gpt-4o-mini"
    xai_model: str = "grok-3-mini"
    gemini_model: str = "gemini-3.8-flash"
    anthropic_model: str = "claude-haiku-5-5"
    database_url: str = "sqlite:///./data/app.db"
    # The Odds API (the-odds-api.com): market odds for the comparison card. Free plan = 500 credits a month.
    odds_api_key: str = ""
    # Signs login tokens. Leave blank to use a random secret saved in data/.auth_secret.
    auth_secret: str = ""
    # fetch_and_predict only predicts matches kicking off within this many hours (each LLM call costs money)
    predict_hours_ahead: int = 48
    # Free AI tiers have per-minute and per-day quotas: pause between calls, cap calls per run
    llm_pause_seconds: int = 7
    llm_max_per_run: int = 10
    # football-data.org free tier allows 10 requests/minute, so each refresh is a single call.
    # Live polling only runs while a stored match could be on.
    standings_cache_seconds: int = 1800  # league tables: one request per league per refresh
    live_cache_seconds: int = 60
    upcoming_cache_seconds: int = 3600


settings = Settings()
