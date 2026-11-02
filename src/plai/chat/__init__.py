import re

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from markupsafe import Markup, escape

from ..extensions import db
from ..llm import AssistantError, get_assistant
from ..llm.prompts import build_history, build_system_prompt
from ..models import Message
from ..validation import parse_birthdate, parse_gender

bp = Blueprint("chat", __name__)

MAX_MESSAGE_LENGTH = 1000

# Quick-reply buttons: button label -> message sent on the user's behalf.
INTENTS = {
    "Recomienda algo al azar": "Recomiéndame una película al azar",
    "Recomienda series de acción": "Recomiéndame series de acción",
    "Recomienda películas de suspenso": "Recomiéndame una película de suspenso",
}

_YOUTUBE_URL = re.compile(r"https://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]{6,20}")


@bp.app_template_filter("chat_text")
def chat_text(text: str) -> Markup:
    """Escape message text, turning only YouTube URLs into links."""
    parts, last = [], 0
    for match in _YOUTUBE_URL.finditer(text):
        parts.append(escape(text[last : match.start()]))
        parts.append(
            Markup('<a href="{0}" target="_blank" rel="noopener noreferrer">{0}</a>').format(
                match.group(0)
            )
        )
        last = match.end()
    parts.append(escape(text[last:]))
    return Markup("").join(parts)


@bp.get("/chat")
@login_required
def chat():
    return render_template(
        "chat.html", messages=current_user.messages, username=current_user.username
    )


@bp.post("/chat")
@login_required
def send_message():
    intent = request.form.get("intent")
    if intent == "Enviar":
        text = (request.form.get("message") or "").strip()
        if not text or len(text) > MAX_MESSAGE_LENGTH:
            abort(400)
    elif intent in INTENTS:
        text = INTENTS[intent]
    else:
        abort(400)

    user = current_user._get_current_object()
    db.session.add(Message(content=text, author="user", user=user))
    db.session.commit()

    try:
        answer = get_assistant(current_app).reply(
            build_system_prompt(age=user.age, gender=user.gender),
            build_history(user.messages, current_app.config["HISTORY_LIMIT"]),
        )
    except AssistantError as exc:
        flash(str(exc), "danger")
    else:
        db.session.add(Message(content=answer, author="assistant", user=user))
        db.session.commit()
    return redirect(url_for("chat.chat"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        birthdate, birthdate_error = parse_birthdate(request.form.get("birthdate"))
        gender, gender_error = parse_gender(request.form.get("gender"))
        errors = [e for e in (birthdate_error, gender_error) if e]
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("edit_user.html", user=current_user), 400
        current_user.birthdate = birthdate
        current_user.gender = gender
        db.session.commit()
        flash("Perfil actualizado.", "success")
        return redirect(url_for("chat.profile"))
    return render_template("edit_user.html", user=current_user)


@bp.get("/user_data")
@login_required
def user_data():
    return jsonify(
        username=current_user.username,
        email=current_user.email,
        birthdate=current_user.birthdate.isoformat(),
        gender=current_user.gender,
    )
