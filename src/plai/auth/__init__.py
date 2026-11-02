from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import bcrypt, db
from ..models import Message, User
from ..validation import validate_signup

bp = Blueprint("auth", __name__)

GREETING = "Hola! Soy plaIA, un recomendador de películas. ¿En qué te puedo ayudar?"


@bp.get("/")
def index():
    return redirect(url_for("auth.login"))


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("sign_up.html")

    data, errors = validate_signup(request.form)
    if not errors and db.session.scalar(select(User).filter_by(email=data["email"])):
        errors.append("Ya existe una cuenta con ese email.")
    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template("sign_up.html"), 400

    user = User(
        username=data["username"],
        email=data["email"],
        password=bcrypt.generate_password_hash(data["password"]).decode("utf-8"),
        birthdate=data["birthdate"],
        gender=data["gender"],
    )
    user.messages.append(Message(content=GREETING, author="assistant"))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:  # lost a race with another sign-up for the same email
        db.session.rollback()
        flash("Ya existe una cuenta con ese email.", "danger")
        return render_template("sign_up.html"), 400

    flash("Cuenta creada. Ya puedes ingresar.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    credentials = request.get_json(silent=True) or request.form
    email = (credentials.get("email") or "").strip().lower()
    password = credentials.get("password") or ""
    user = db.session.scalar(select(User).filter_by(email=email))

    if user is None or not bcrypt.check_password_hash(user.password, password):
        if request.is_json:
            return jsonify(error="Email o contraseña incorrectos."), 401
        flash("Email o contraseña incorrectos.", "danger")
        return render_template("login.html"), 401

    login_user(user)
    if request.is_json:
        return jsonify(redirect=url_for("chat.chat"))
    return redirect(url_for("chat.chat"))


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
