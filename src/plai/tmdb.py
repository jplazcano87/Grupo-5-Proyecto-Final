"""Minimal TMDB (themoviedb.org) client used by the assistant's tools.

Every public method returns a short plain-text (Spanish) string for the model to
read. Network or API failures raise ``TMDBError`` so the tool loop can report
them to the model with ``is_error`` instead of presenting them as answers.
"""

import logging

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.themoviedb.org/3"
NOT_FOUND = "No estoy seguro de dónde puedes ver esta película o serie :("
NO_TRAILER = "No encontré trailer de esa serie o película"


class TMDBError(Exception):
    """TMDB could not be reached or returned an unusable response."""


def get_provider_names(data):
    providers = (data or {}).get("flatrate")
    if not providers:
        return NOT_FOUND
    return ", ".join(provider["provider_name"] for provider in providers)


class TMDBClient:
    def __init__(self, api_key, region="CL", session=None, timeout=5):
        if not api_key:
            raise TMDBError("TMDB_API_KEY no está configurada")
        self.region = region
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "accept": "application/json"}
        )

    def _get(self, path, **params):
        try:
            response = self.session.get(
                f"{BASE_URL}{path}", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("TMDB request to %s failed: %s", path, exc)
            raise TMDBError(f"TMDB request failed: {path}") from exc

    def search(self, query, media_type=None):
        """Return the first movie/tv result for ``query`` (people are ignored)."""
        wanted = {media_type} if media_type else {"movie", "tv"}
        data = self._get("/search/multi", query=query, include_adult="false", page=1)
        for result in data.get("results") or []:
            if result.get("media_type") in wanted:
                return result
        return None

    def where_to_watch(self, title, media_type):
        result = self.search(title, media_type)
        if not result:
            return NOT_FOUND
        data = self._get(f"/{media_type}/{result['id']}/watch/providers")
        region_data = (data.get("results") or {}).get(self.region)
        return f"{_display_title(result)}: {get_provider_names(region_data)}"

    def trailer(self, title):
        result = self.search(title)
        if not result:
            return NO_TRAILER
        data = self._get(f"/{result['media_type']}/{result['id']}/videos")
        for video in data.get("results") or []:
            if video.get("type", "").lower() == "trailer" and video.get("site") == "YouTube":
                return (
                    f"Trailer de {_display_title(result)}: "
                    f"https://www.youtube.com/watch?v={video['key']}"
                )
        return NO_TRAILER

    def now_playing(self):
        data = self._get(
            "/movie/now_playing", language="es-ES", page=1, region=self.region
        )
        titles = [movie["title"] for movie in data.get("results") or [] if movie.get("title")]
        return ", ".join(titles) if titles else "No pude encontrar películas en cartelera"


def _display_title(result):
    title = result.get("title") or result.get("name") or "Sin título"
    year = (result.get("release_date") or result.get("first_air_date") or "")[:4]
    return f"{title} ({year})" if year else title
