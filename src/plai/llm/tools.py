"""Tool definitions the model can call, and the registry that executes them."""

from collections.abc import Callable

from ..tmdb import TMDBClient


def _tool(name: str, description: str, properties: dict[str, str]) -> dict:
    """Build a strict Anthropic tool definition whose params are all required strings."""
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                key: {"type": "string", "description": text} for key, text in properties.items()
            },
            "required": list(properties),
            "additionalProperties": False,
        },
    }


class Toolbox:
    """Holds the tool schemas sent to the model and dispatches calls by name."""

    def __init__(self, tmdb: TMDBClient):
        self._handlers: dict[str, Callable[..., str]] = {
            "where_to_watch_tv_show": lambda tv_show_name: tmdb.where_to_watch(
                tv_show_name, "tv"
            ),
            "where_to_watch_movie": lambda movie_name: tmdb.where_to_watch(movie_name, "movie"),
            "get_movie_or_show_trailer": lambda movie_or_show_name: tmdb.trailer(
                movie_or_show_name
            ),
            "get_current_movies_in_theatres": lambda: tmdb.now_playing(),
        }
        self.definitions: list[dict] = [
            _tool(
                "where_to_watch_tv_show",
                "Returns the streaming platforms where a TV show can be watched. "
                "Do not use for movies.",
                {"tv_show_name": "The name of the TV show to search for"},
            ),
            _tool(
                "where_to_watch_movie",
                "Returns the streaming platforms where a movie can be watched. "
                "Do not use for TV shows.",
                {"movie_name": "The name of the movie to search for"},
            ),
            _tool(
                "get_movie_or_show_trailer",
                "Returns a YouTube link to the trailer of a movie or TV show.",
                {"movie_or_show_name": "The name of the movie or TV show to search for"},
            ),
            _tool(
                "get_current_movies_in_theatres",
                "Returns the movies that are currently in theatres.",
                {},
            ),
        ]

    def run(self, name: str, arguments: dict) -> str:
        handler = self._handlers.get(name)
        if handler is None:
            raise KeyError(f"unknown tool: {name}")
        return handler(**arguments)
