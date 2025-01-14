import requests
import os

from dotenv import load_dotenv

load_dotenv()

token_tmbd = os.environ.get("TMDB_API_KEY")
headers = {
    "Authorization": f"Bearer {token_tmbd}",
    "accept": "application/json"
}


def get_provider_names(data):
    if not data or 'flatrate' not in data:
        return "No estoy seguro de dónde puedes ver esta película o serie :("
    return ", ".join(provider['provider_name'] for provider in data['flatrate'])


def where_to_watch(tv_show_name):
    print("tv_show_name", tv_show_name)
    search_url = f"https://api.themoviedb.org/3/search/multi?query={tv_show_name}&include_adult=false&page=1"
    resp = requests.get(search_url, headers=headers, timeout=5)
    data = resp.json()
    results = data.get("results")
    if not results:
        return get_provider_names(None)
    first_result = results[0]

    show_id = first_result["id"]
    providers_url = f"https://api.themoviedb.org/3/tv/{
        show_id}/watch/providers"
    try:
        response = requests.get(providers_url, headers=headers, timeout=5)
        data_json = response.json()
        cl_data = data_json["results"]["CL"]
    except (requests.RequestException, KeyError, ValueError):
        return get_provider_names(None)

    return get_provider_names(cl_data)


def where_to_watch_movie(movie_name):
    print("tv_show_name", movie_name)

    first_result = get_movie_id(movie_name)
    if not first_result:
        return get_provider_names(None)
    show_id = first_result["id"]
    providers_url = f"https://api.themoviedb.org/3/movie/{
        show_id}/watch/providers"
    try:
        response = requests.get(providers_url, headers=headers, timeout=5)
        data_json = response.json()
        print("data_json", data_json)
        cl_data = data_json["results"]["CL"]
    except (requests.RequestException, KeyError, ValueError):
        return get_provider_names(None)

    return get_provider_names(cl_data)


def get_movie_id(movie_name):
    print("tv_show_name", movie_name)

    search_url = f"https://api.themoviedb.org/3/search/multi?query={
        movie_name}&include_adult=false&page=1"
    resp = requests.get(search_url, headers=headers, timeout=5)
    data = resp.json()
    results = data.get("results")
    if not results:
        return None
    return results[0]


def get_movie_or_show_trailer(movie_or_show_name):
    movie_id = get_movie_id(movie_or_show_name)
    if not movie_id:
        return get_provider_names(None)
    show_id = movie_id["id"]
    videos_url = f"https://api.themoviedb.org/3/movie/{show_id}/videos"

    try:
        response = requests.get(videos_url, headers=headers, timeout=5)
        data = response.json()
        print("data", data)
        # Find first available trailer
        for video in data.get('results', []):
            if video['type'].lower() == 'trailer':
                return f'<a href="https://www.youtube.com/watch?v={video["key"]}">Click aquí para ver el trailer de {movie_or_show_name}</a>'

        return "No encontré trailer de esa serie o pelicula"

    except (requests.RequestException, KeyError, ValueError):
        return "No encontré trailer de esa serie o pelicula"


def get_current_movies_in_theatres():
    url = "https://api.themoviedb.org/3/movie/now_playing?language=es-ES&page=1&region=CL"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        movies = data.get('results', [])
        return ", ".join(movie['title'] for movie in movies)
    except (requests.RequestException, KeyError, ValueError):
        return "No pude encontrar películas en cartelera"
