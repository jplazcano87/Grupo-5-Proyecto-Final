import pytest

from plai.tmdb import get_provider_names


def test_get_provider_names_multiple_providers():
    data = {
        'flatrate': [
            {'provider_name': 'Netflix'},
            {'provider_name': 'Amazon Prime Video'},
            {'provider_name': 'Disney Plus'}
        ]
    }
    assert get_provider_names(data) == "Netflix, Amazon Prime Video, Disney Plus"

def test_get_provider_names_single_provider():
    data = {
        'flatrate': [
            {'provider_name': 'HBO Max'}
        ]
    }
    assert get_provider_names(data) == "HBO Max"

def test_get_provider_names_empty_provider_list():
    # Scenario: 'flatrate' key is present, but its list of providers is empty.
    # This covers "no provider information" where 'flatrate' is an empty list.
    data = {
        'flatrate': []
    }
    assert get_provider_names(data) == "No estoy seguro de dónde puedes ver esta película o serie :("

def test_get_provider_names_flatrate_key_value_is_none():
    # Scenario: 'flatrate' key is present, but its value is None.
    # This covers "no provider information" where 'flatrate' is None.
    data = {
        'flatrate': None
    }
    assert get_provider_names(data) == "No estoy seguro de dónde puedes ver esta película o serie :("

def test_get_provider_names_missing_flatrate_key():
    # Scenario: 'flatrate' key is missing from the input data.
    data = {'other_key': 'some_value'} # 'flatrate' key is absent
    assert get_provider_names(data) == "No estoy seguro de dónde puedes ver esta película o serie :("

def test_get_provider_names_input_data_is_none():
    # Scenario: The entire input data is None.
    assert get_provider_names(None) == "No estoy seguro de dónde puedes ver esta película o serie :("

def test_get_provider_names_input_data_is_empty_dict():
    # Scenario: The entire input data is an empty dictionary.
    # This also behaves like a missing 'flatrate' key.
    assert get_provider_names({}) == "No estoy seguro de dónde puedes ver esta película o serie :("

def test_get_provider_names_flatrate_is_empty_dict_not_list():
    # Scenario: 'flatrate' is present but empty (here an empty dict): nothing to show.
    data = {'flatrate': {}}
    assert get_provider_names(data) == "No estoy seguro de dónde puedes ver esta película o serie :("

# The following tests check behavior for malformed items *within* the 'flatrate' list.
# They assert that the function currently raises exceptions in these cases,
# which is important for understanding the function's robustness.

def test_get_provider_names_flatrate_list_contains_empty_dict_item_raises_keyerror():
    # Scenario: 'flatrate' is a list containing an empty dictionary.
    # Current behavior: Accessing provider['provider_name'] on an empty dict {} raises KeyError.
    data = {'flatrate': [{}]}
    with pytest.raises(KeyError):
        get_provider_names(data)

def test_get_provider_names_flatrate_list_contains_none_item_raises_typeerror():
    # Scenario: 'flatrate' is a list containing a None item.
    # Current behavior: Accessing provider['provider_name'] on None raises TypeError.
    data = {'flatrate': [None]}
    with pytest.raises(TypeError):
        get_provider_names(data)

def test_get_provider_names_flatrate_list_mixed_valid_and_malformed_items_raise_errors():
    # Scenario: 'flatrate' list has a mix of valid and malformed items.
    # Test with None item first in the list
    data_none_first = {'flatrate': [None, {'provider_name': 'Netflix'}]}
    with pytest.raises(TypeError): # Expected to fail on the None item
        get_provider_names(data_none_first)

    # Test with empty dict item after a valid one
    data_empty_dict_after_valid = {'flatrate': [{'provider_name': 'Netflix'}, {}]}
    with pytest.raises(KeyError): # Expected to fail on the empty dict {} item
        get_provider_names(data_empty_dict_after_valid)

def test_get_provider_names_flatrate_list_item_missing_provider_name_key_raises_keyerror():
    # Scenario: 'flatrate' list has an item (a dictionary) that is missing the 'provider_name' key.
    data = {'flatrate': [{'id': 123, 'some_other_key': 'Some Provider But Wrong Key'}]}
    with pytest.raises(KeyError): # Expects KeyError because 'provider_name' is missing
        get_provider_names(data)


# --- TMDBClient ---------------------------------------------------------------------------

from unittest.mock import MagicMock  # noqa: E402

import requests  # noqa: E402

from plai.tmdb import NO_TRAILER, NOT_FOUND, TMDBClient, TMDBError  # noqa: E402


def make_client(*payloads, region="CL"):
    """TMDBClient whose session returns ``payloads`` in order."""
    session = MagicMock()
    session.headers = {}
    responses = []
    for payload in payloads:
        resp = MagicMock()
        resp.json.return_value = payload
        responses.append(resp)
    session.get.side_effect = responses
    return TMDBClient("key", region=region, session=session), session


def test_missing_api_key_fails_clearly():
    with pytest.raises(TMDBError):
        TMDBClient(None)


def test_search_skips_people_and_wrong_media_type():
    client, session = make_client(
        {"results": [
            {"id": 1, "media_type": "person", "name": "Actor"},
            {"id": 2, "media_type": "movie", "title": "Dune"},
            {"id": 3, "media_type": "tv", "name": "Dune: Prophecy"},
        ]}
    )
    assert client.search("dune", "tv")["id"] == 3
    # the query goes in params (URL-encoded by requests), never in the path
    assert session.get.call_args.kwargs["params"]["query"] == "dune"


def test_where_to_watch_uses_media_type_and_region():
    client, session = make_client(
        {"results": [{"id": 7, "media_type": "tv", "name": "Dark", "first_air_date": "2017-12-01"}]},
        {"results": {"CL": {"flatrate": [{"provider_name": "Netflix"}]}, "US": {}}},
    )
    assert client.where_to_watch("dark", "tv") == "Dark (2017): Netflix"
    assert session.get.call_args.args[0].endswith("/tv/7/watch/providers")


def test_where_to_watch_without_results():
    client, _ = make_client({"results": []})
    assert client.where_to_watch("zzz", "movie") == NOT_FOUND


def test_trailer_for_tv_show_hits_tv_endpoint():
    client, session = make_client(
        {"results": [{"id": 9, "media_type": "tv", "name": "Dark"}]},
        {"results": [
            {"type": "Teaser", "site": "YouTube", "key": "nope"},
            {"type": "Trailer", "site": "YouTube", "key": "abc123"},
        ]},
    )
    assert client.trailer("dark") == "Trailer de Dark: https://www.youtube.com/watch?v=abc123"
    assert session.get.call_args.args[0].endswith("/tv/9/videos")


def test_trailer_not_found():
    client, _ = make_client(
        {"results": [{"id": 9, "media_type": "movie", "title": "X"}]}, {"results": []}
    )
    assert client.trailer("x") == NO_TRAILER


def test_now_playing_lists_titles():
    client, _ = make_client({"results": [{"title": "A"}, {"title": "B"}]})
    assert client.now_playing() == "A, B"


def test_http_failures_raise_tmdb_error():
    client, session = make_client()
    session.get.side_effect = requests.ConnectionError("down")
    with pytest.raises(TMDBError):
        client.now_playing()
