from datetime import date

import pytest

from plai import create_app
from plai.extensions import bcrypt, db
from plai.models import Message, User


class FakeAssistant:
    """Stands in for ChatAssistant in route tests."""

    def __init__(self):
        self.calls = []
        self.answer = "Te recomiendo Dune."
        self.error = None

    def reply(self, system, history):
        self.calls.append((system, history))
        if self.error:
            raise self.error
        return self.answer


@pytest.fixture
def assistant():
    return FakeAssistant()


@pytest.fixture
def app(assistant):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
        }
    )
    app.extensions["plai_assistant"] = assistant
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    user = User(
        username="ana",
        email="ana@example.com",
        password=bcrypt.generate_password_hash("secret-pass").decode(),
        birthdate=date(1990, 5, 17),
        gender="Mujer",
    )
    user.messages.append(Message(content="Hola!", author="assistant"))
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in(client, user):
    client.post("/login", data={"email": "ana@example.com", "password": "secret-pass"})
    return client
