import pytest
from bot import build_prompt

class MockUser:
    def __init__(self, favorite_genre=None, disliked_genre=None, messages=None):
        self.favorite_genre = favorite_genre
        self.disliked_genre = disliked_genre
        self.messages = messages if messages is not None else []

def test_build_prompt_with_favorite_genre():
    user = MockUser(favorite_genre="Action")
    prompt = build_prompt(user, "")
    assert "El género favorito del usuario es: Action." in prompt

def test_build_prompt_with_disliked_genre():
    user = MockUser(disliked_genre="Horror")
    prompt = build_prompt(user, "")
    assert "El género a evitar del usuario es: Horror." in prompt

def test_build_prompt_with_both_genres():
    user = MockUser(favorite_genre="Comedy", disliked_genre="Drama")
    prompt = build_prompt(user, "")
    assert "El género favorito del usuario es: Comedy." in prompt
    assert "El género a evitar del usuario es: Drama." in prompt

def test_build_prompt_with_no_genres():
    user = MockUser()
    prompt = build_prompt(user, "")
    assert "El género favorito del usuario es:" not in prompt
    assert "El género a evitar del usuario es:" not in prompt

def test_build_prompt_with_context():
    user = MockUser()
    context = "Looking for a movie released after 2020."
    prompt = build_prompt(user, context)
    assert f"Además considera el siguiente contenido: {context}" in prompt

def test_build_prompt_without_context():
    user = MockUser()
    prompt = build_prompt(user, "")
    assert "Además considera el siguiente contenido:" not in prompt

def test_build_prompt_base_message():
    user = MockUser()
    prompt = build_prompt(user, "")
    expected_base_prompt = """Eres un chatbot que recomienda películas, te llamas 'PlaIA'.
    - Tu rol es responder recomendaciones de manera breve y concisa.
    - No repitas recomendaciones.
    """
    assert expected_base_prompt in prompt
