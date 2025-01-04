from flask import Flask
from openai import OpenAI
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()


def create_app():
    open_ia = OpenAI()
    app = Flask(__name__, template_folder='templates')
    turso_database_url = os.environ.get("TURSO_DATABASE_URL")
    turso_auth_token = os.environ.get("TURSO_AUTH_TOKEN")
    db_url = f"sqlite+{turso_database_url}/?authToken={turso_auth_token}&secure=true"
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url

    app.secret_key = 'secret_key'

    bootstrap = Bootstrap5(app)

    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(uid):
        from models import User
        return User.query.get(int(uid))

    @login_manager.unauthorized_handler
    def unauthorized():
        return 'Unauthorized'

    bcrypt = Bcrypt(app)

    from routes import register_routes
    register_routes(app, db, bcrypt, open_ia)

    Migrate(app, db)

    return app
