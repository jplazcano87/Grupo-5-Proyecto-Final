import pytest
from movies import get_provider_names

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
    # Scenario: 'flatrate' key is present, but its value is an empty dictionary {} instead of a list.
    # Current function behavior: The list comprehension `provider['provider_name'] for provider in {}` will be empty.
    # So, ", ".join([]) results in an empty string "". This test captures that current behavior.
    data = {'flatrate': {}}
    assert get_provider_names(data) == ""

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
