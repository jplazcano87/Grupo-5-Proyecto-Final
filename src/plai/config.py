import os


def load_config() -> dict:
    """Build the default app config from environment variables."""
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URL", "sqlite:///plai.db"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "ANTHROPIC_MODEL": os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5"),
        "ANTHROPIC_EFFORT": os.environ.get("ANTHROPIC_EFFORT", "low"),
        "ANTHROPIC_MAX_TOKENS": int(os.environ.get("ANTHROPIC_MAX_TOKENS", "4096")),
        "TMDB_API_KEY": os.environ.get("TMDB_API_KEY"),
        "TMDB_REGION": os.environ.get("TMDB_REGION", "CL"),
        # How many stored messages are sent to the model per request.
        "HISTORY_LIMIT": int(os.environ.get("HISTORY_LIMIT", "30")),
        # Upper bound on model <-> tool round trips per user message.
        "MAX_TOOL_ITERATIONS": int(os.environ.get("MAX_TOOL_ITERATIONS", "5")),
    }
