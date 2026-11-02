"""Shared validation for sign-up and profile forms."""

import re
from datetime import date

from .llm.prompts import GENDERS

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MIN_AGE = 13


def parse_birthdate(value: str | None) -> tuple[date | None, str | None]:
    try:
        birthdate = date.fromisoformat((value or "").strip())
    except ValueError:
        return None, "La fecha de nacimiento no es válida."
    today = date.today()
    had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
    age = today.year - birthdate.year - (not had_birthday)
    if birthdate.year < 1900 or age < MIN_AGE:
        return None, f"Debes tener al menos {MIN_AGE} años."
    return birthdate, None


def parse_gender(value: str | None) -> tuple[str | None, str | None]:
    if value in GENDERS:
        return value, None
    return None, "Selecciona un género."


def validate_signup(form) -> tuple[dict, list[str]]:
    errors = []
    username = (form.get("username") or "").strip()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""

    if not 1 <= len(username) <= 50:
        errors.append("El nombre de usuario debe tener entre 1 y 50 caracteres.")
    if not EMAIL_RE.match(email) or len(email) > 254:
        errors.append("El email no es válido.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password != form.get("repeat_password"):
        errors.append("Las contraseñas no coinciden.")
    birthdate, error = parse_birthdate(form.get("birthdate"))
    if error:
        errors.append(error)
    gender, error = parse_gender(form.get("gender"))
    if error:
        errors.append(error)

    return (
        {
            "username": username,
            "email": email,
            "password": password,
            "birthdate": birthdate,
            "gender": gender,
        },
        errors,
    )
