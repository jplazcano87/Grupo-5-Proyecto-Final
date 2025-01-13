import requests
import os

from dotenv import load_dotenv

load_dotenv()


def get_provider_data(movie_name):

    token_tmbd = os.environ.get("TMDB_API_KEY")

    headers = {
        "Authorization": f"Bearer {token_tmbd}",
        "accept": "application/json"
    }
    search_url = f"https://api.themoviedb.org/3/search/multi?query={
        movie_name}&include_adult=false&page=1"
    resp = requests.get(search_url, headers=headers)
    first_result = resp.json()["results"][0]
    show_id = first_result["id"]
    providers_url = f"https://api.themoviedb.org/3/tv/{
        show_id}/watch/providers"
    cl_data = requests.get(providers_url, headers=headers).json()[
        "results"]["CL"]
    return cl_data
