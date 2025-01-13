import requests


print(cl_data)
def get_cl_data(movie_name):
    headers = {
        "Authorization": "Bearer <YOUR_TOKEN>",
        "accept": "application/json"
    }
    search_url = f"https://api.themoviedb.org/3/search/multi?query={movie_name}&include_adult=false&page=1"
    resp = requests.get(search_url, headers=headers)
    first_result = resp.json()["results"][0]
    show_id = first_result["id"]
    providers_url = f"https://api.themoviedb.org/3/tv/{show_id}/watch/providers"
    cl_data = requests.get(providers_url, headers=headers).json()["results"]["CL"]
    return cl_data