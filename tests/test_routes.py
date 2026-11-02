from datetime import date

from sqlalchemy import select

from plai import create_app
from plai.extensions import db
from plai.llm import AssistantError
from plai.models import Message, User

SIGNUP = {
    "username": "bruno",
    "email": "Bruno@Example.com",
    "password": "a-long-password",
    "repeat_password": "a-long-password",
    "birthdate": "1995-02-03",
    "gender": "Hombre",
}


def test_signup_creates_user_with_greeting(client):
    response = client.post("/signup", data=SIGNUP)

    assert response.status_code == 302
    user = db.session.scalar(select(User).filter_by(email="bruno@example.com"))
    assert user.birthdate == date(1995, 2, 3)
    assert user.password != SIGNUP["password"]
    assert [m.author for m in user.messages] == ["assistant"]


def test_signup_rejects_invalid_input(client):
    bad = {**SIGNUP, "password": "short", "repeat_password": "different", "gender": "1"}
    response = client.post("/signup", data=bad)

    assert response.status_code == 400
    assert db.session.scalar(select(User)) is None


def test_signup_rejects_duplicate_email(client, user):
    response = client.post("/signup", data={**SIGNUP, "email": "ana@example.com"})
    assert response.status_code == 400


def test_login_failure_returns_401_and_does_not_authenticate(client, user):
    response = client.post("/login", json={"email": "ana@example.com", "password": "wrong"})
    assert response.status_code == 401
    assert client.get("/chat").status_code == 302  # still redirected to login


def test_login_success_returns_redirect_target(client, user):
    response = client.post("/login", json={"email": "ana@example.com", "password": "secret-pass"})
    assert response.status_code == 200
    assert response.json["redirect"] == "/chat"
    assert client.get("/chat").status_code == 200


def test_chat_requires_login(client):
    assert client.get("/chat").status_code == 302
    assert client.post("/chat", data={"intent": "Enviar", "message": "hola"}).status_code == 302


def test_send_message_stores_both_turns_and_calls_assistant(logged_in, assistant, user):
    response = logged_in.post("/chat", data={"intent": "Enviar", "message": "algo de terror"})

    assert response.status_code == 302
    assert [(m.author, m.content) for m in user.messages] == [
        ("assistant", "Hola!"),
        ("user", "algo de terror"),
        ("assistant", "Te recomiendo Dune."),
    ]
    system, history = assistant.calls[0]
    assert "edad:" in system
    assert history == [{"role": "user", "content": "algo de terror"}]


def test_quick_intent_sends_canned_message(logged_in, assistant):
    logged_in.post("/chat", data={"intent": "Recomienda algo al azar"})
    assert assistant.calls[0][1][-1]["content"] == "Recomiéndame una película al azar"


def test_unknown_intent_and_empty_message_are_400(logged_in):
    assert logged_in.post("/chat", data={"intent": "nope"}).status_code == 400
    assert logged_in.post("/chat", data={"intent": "Enviar", "message": "  "}).status_code == 400


def test_assistant_failure_keeps_user_message_but_stores_no_reply(logged_in, assistant, user):
    assistant.error = AssistantError("El asistente no está disponible por ahora.")

    response = logged_in.post(
        "/chat", data={"intent": "Enviar", "message": "hola"}, follow_redirects=True
    )

    assert "El asistente no está disponible" in response.text
    assert [m.author for m in user.messages] == ["assistant", "user"]


def test_chat_escapes_html_but_links_youtube(logged_in, user):
    db.session.add(Message(content="<script>alert(1)</script>", author="user", user=user))
    db.session.add(
        Message(
            content="<img src=x onerror=alert(1)> https://www.youtube.com/watch?v=abc123XYZ",
            author="assistant",
            user=user,
        )
    )
    db.session.commit()

    html = logged_in.get("/chat").text

    assert "<script>alert(1)</script>" not in html
    assert "<img src=x" not in html
    assert '<a href="https://www.youtube.com/watch?v=abc123XYZ"' in html


def test_logout_is_post_only(logged_in):
    assert logged_in.get("/logout").status_code == 405
    assert logged_in.post("/logout").status_code == 302
    assert logged_in.get("/chat").status_code == 302


def test_profile_update_validates_and_saves(logged_in, user):
    assert logged_in.post("/profile", data={"birthdate": "nope", "gender": "Mujer"}).status_code == 400

    response = logged_in.post("/profile", data={"birthdate": "1991-01-02", "gender": "Otro"})
    assert response.status_code == 302
    assert (user.birthdate, user.gender) == (date(1991, 1, 2), "Otro")


def test_csrf_is_enforced_when_enabled():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with app.app_context():
        db.create_all()
        response = app.test_client().post("/login", json={"email": "a@b.co", "password": "x"})
    assert response.status_code == 400


def test_secret_key_required_outside_debug_and_tests():
    import pytest

    with pytest.raises(RuntimeError):
        create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "SECRET_KEY": None})
