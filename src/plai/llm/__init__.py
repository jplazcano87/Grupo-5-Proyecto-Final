import anthropic
from flask import Flask

from ..tmdb import TMDBClient
from .client import AssistantError, ChatAssistant
from .tools import Toolbox

__all__ = ["AssistantError", "ChatAssistant", "get_assistant"]


def get_assistant(app: Flask) -> ChatAssistant:
    """Return the app's assistant, building it on first use.

    Built lazily so the app (and its tests) can start without API keys. Tests can
    replace ``app.extensions["plai_assistant"]`` with a fake.
    """
    if "plai_assistant" not in app.extensions:
        tmdb = TMDBClient(app.config["TMDB_API_KEY"], region=app.config["TMDB_REGION"])
        app.extensions["plai_assistant"] = ChatAssistant(
            anthropic.Anthropic(),
            Toolbox(tmdb),
            model=app.config["ANTHROPIC_MODEL"],
            effort=app.config["ANTHROPIC_EFFORT"],
            max_tokens=app.config["ANTHROPIC_MAX_TOKENS"],
            max_iterations=app.config["MAX_TOOL_ITERATIONS"],
        )
    return app.extensions["plai_assistant"]
