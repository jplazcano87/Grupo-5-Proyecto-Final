import secrets

from dotenv import load_dotenv
from flask import Flask
from flask_bootstrap import Bootstrap5

from .config import load_config
from .extensions import bcrypt, csrf, db, login_manager, migrate


def create_app(config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(load_config())
    if config:
        app.config.update(config)

    if not app.config["SECRET_KEY"]:
        if not (app.debug or app.testing):
            raise RuntimeError("SECRET_KEY must be set (see .env.example)")
        app.config["SECRET_KEY"] = secrets.token_hex(32)
    app.config.setdefault("SESSION_COOKIE_SECURE", not (app.debug or app.testing))

    Bootstrap5(app)
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .auth import bp as auth_bp
    from .chat import bp as chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    return app
