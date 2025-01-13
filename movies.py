import requests
import os

from dotenv import load_dotenv

load_dotenv()


def get_provider_names(data):
    if not data or 'flatrate' not in data:
        return "No estoy seguro de dónde puedes ver esta película o serie :("
    return ", ".join(provider['provider_name'] for provider in data['flatrate'])


def where_to_watch(tv_show_name):
    print("tv_show_name", tv_show_name)
    token_tmbd = os.environ.get("TMDB_API_KEY")

    headers = {
        "Authorization": f"Bearer {token_tmbd}",
        "accept": "application/json"
    }
    search_url = f"https://api.themoviedb.org/3/search/multi?query={
        tv_show_name}&include_adult=false&page=1"
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
    token_tmbd = os.environ.get("TMDB_API_KEY")

    headers = {
        "Authorization": f"Bearer {token_tmbd}",
        "accept": "application/json"
    }
    search_url = f"https://api.themoviedb.org/3/search/multi?query={
        movie_name}&include_adult=false&page=1"
    resp = requests.get(search_url, headers=headers, timeout=5)
    data = resp.json()
    results = data.get("results")
    if not results:
        return get_provider_names(None)
    first_result = results[0]

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
