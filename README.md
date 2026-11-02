# plAI

PlaIA is a movie and TV recommender chatbot (Spanish UI). It is a Flask app that uses
**Claude tool use** (function calling) with [TMDB](https://www.themoviedb.org/) as the data
source: the model decides when to look up where a title streams, find a trailer, or list what
is in theatres, and answers in natural language.

Built by Barbara Castillo, Andres Ruggieri Lusso and Juan Pablo Lazcano.

- [How it works](#how-it-works)
- [Project layout](#project-layout)
- [Setup](#setup)
- [Configuration](#configuration)
- [Database](#database)
- [Development](#development)
- [Deployment](#deployment)
- [Security notes](#security-notes)
- [What changed in the 0.2 modernization](#what-changed-in-the-02-modernization)
- [Resumen (español)](#resumen-español)

## How it works

A user message goes through `POST /chat` and ends up in the tool-calling loop in
`src/plai/llm/client.py`:

1. The last `HISTORY_LIMIT` stored messages (starting with a user turn) and the tool schemas
   are sent to Claude, together with a system prompt built from the user's age and gender.
2. If Claude stops with `tool_use`, **every** requested tool is executed and all results are
   returned in a single `tool_result` message. A failing tool is reported with
   `is_error: true`, so the model can recover instead of the request failing.
3. The model is called again, and the loop repeats until Claude answers in text. At most
   `MAX_TOOL_ITERATIONS` round trips are allowed per user message.
4. Only the final text is stored in the chat history.

Refusals, truncated answers, and API errors (rate limit, connection, server) produce a
friendly Spanish message instead of a 500. If the model cannot be reached, the user's message
is kept but no assistant reply is stored.

### Tools

Defined in `src/plai/llm/tools.py` as strict schemas (`strict: true`, no extra properties).

| Tool | Argument | What it returns |
|---|---|---|
| `where_to_watch_tv_show` | `tv_show_name` | Streaming platforms for a TV show in `TMDB_REGION` |
| `where_to_watch_movie` | `movie_name` | Streaming platforms for a movie in `TMDB_REGION` |
| `get_movie_or_show_trailer` | `movie_or_show_name` | YouTube trailer link (movie or TV) |
| `get_current_movies_in_theatres` | none | Movies now playing in `TMDB_REGION` |

Tools return plain text; the model composes the reply. The chat page only turns YouTube URLs
into links, everything else is escaped.

To add a tool: add its schema to `Toolbox.definitions` and a handler to `Toolbox._handlers` in
`tools.py`, and add a test in `tests/test_llm_client.py`.

## Project layout

```
pyproject.toml            dependencies, ruff and pytest config
.env.example              environment variable template
.github/                  CI workflow and Dependabot config
migrations/               Alembic migrations (Flask-Migrate)
src/plai/
  __init__.py             create_app() factory
  config.py               environment-driven defaults
  extensions.py           db, login manager, bcrypt, CSRF, migrate
  models.py               User and Message (SQLAlchemy 2.0)
  validation.py           sign-up and profile validation
  tmdb.py                 TMDB client
  auth/                   sign-up, login, logout
  chat/                   chat, profile, user_data
  llm/
    client.py             the Claude tool-calling loop
    tools.py              tool schemas and dispatch
    prompts.py            system prompt and history builder
  templates/, static/
tests/                    pytest suite (Claude and TMDB are mocked)
```

## Setup

Requires Python 3.12+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then fill in the keys
flask --app plai db upgrade
flask --app plai run --debug
```

Then open <http://127.0.0.1:5000>, create an account, and start chatting.

## Configuration

Settings are read from the environment (a `.env` file is loaded automatically).

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | none, **required** | Claude API key |
| `TMDB_API_KEY` | none, **required** | TMDB read access token |
| `SECRET_KEY` | none | Flask session key. **Required** unless running with `--debug` |
| `DATABASE_URL` | `sqlite:///plai.db` | Database (SQLite file in `instance/` by default) |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | Model ID; `claude-sonnet-5-5` is a cheaper option |
| `ANTHROPIC_EFFORT` | `low` | `low` to `max`; higher thinks harder and costs more |
| `ANTHROPIC_MAX_TOKENS` | `4096` | Max tokens per model response |
| `TMDB_REGION` | `CL` | Watch-provider and now-playing region |
| `HISTORY_LIMIT` | `30` | Stored messages sent to the model per request |
| `MAX_TOOL_ITERATIONS` | `5` | Max model/tool round trips per user message |

Generate a secret key with `python -c "import secrets; print(secrets.token_hex(32))"`.

## Database

SQLite is the default and needs no setup. To use a remote Turso (libSQL) database instead:

```bash
pip install ".[turso]"
# .env
DATABASE_URL="sqlite+libsql://<db>.turso.io?authToken=<token>&secure=true"
```

Any other SQLAlchemy URL (for example PostgreSQL) also works if you install its driver.

Migrations:

```bash
flask --app plai db upgrade                      # apply
flask --app plai db migrate -m "describe change" # generate after editing models
```

**Upgrading an existing database:** the `7c2d9e4f1a10` migration adds a unique index on
`users.email`. It fails if two users share an email, so remove duplicates first and back up
the database. On SQLite the `birthdate` column is intentionally left as text (it already holds
ISO dates, and rebuilding the column as `DATE` would truncate them); on other databases it is
converted to `DATE`. Because of that, `flask db check` may report a Text/Date difference on
SQLite. This is expected.

## Development

```bash
pytest -q        # no API keys needed
ruff check .
```

The test suite covers the tool loop (single and parallel tool calls, tool errors, unknown
tools, iteration cap, refusals, truncation, API errors), the TMDB client, the prompt and
history builder, and the routes (validation, login failure, CSRF, XSS escaping, auth).
CI runs the same checks on Python 3.12 and 3.13.

## Deployment

```bash
gunicorn "plai:create_app()"
```

Set `SECRET_KEY`, `ANTHROPIC_API_KEY`, `TMDB_API_KEY` and `DATABASE_URL`, and serve behind
HTTPS: session cookies are marked `Secure` outside debug mode. Do not run with `--debug` on a
public host.

## Security notes

- Session secret comes from `SECRET_KEY`; the app refuses to start without it outside debug.
- CSRF protection on all forms and on the JSON login request; logout is POST-only.
- Failed logins return 401. Passwords are bcrypt-hashed (minimum length 8).
- Chat output is HTML-escaped; only YouTube links are linkified.
- The system prompt receives only the user's **age** and a gender from a fixed list, not the
  full birthdate. User input is never interpolated into the prompt as instructions.
- Rate limiting and brute-force protection are not implemented yet.

## What changed in the 0.2 modernization

- **LLM:** moved from OpenAI (`gpt-4o`, SDK 1.57) to Claude. Replaced the single-shot call
  (only the first tool call, raw tool output saved as the reply) with a real tool-calling
  loop. Fixed the tool schemas (misnamed `description` keys, missing parameters) and renamed
  `where_to_watch` to `where_to_watch_tv_show`.
- **TMDB:** queries are passed as parameters instead of string-built URLs, results are filtered
  by movie/TV, TV trailers use the right endpoint, HTTP errors are handled, and the region is
  configurable. Tools no longer return HTML.
- **Security:** fixed the hardcoded secret key, the login redirect that succeeded on bad
  credentials, the stored XSS (`| safe`), missing CSRF, and GET logout. Added input validation
  and a unique email constraint.
- **Structure:** flat modules became the `src/plai` package with an app factory and
  blueprints; SQLAlchemy 2.0 models; `pyproject.toml` replaced the pip-freeze
  `requirements.txt` (which also dropped Sphinx, aiohttp and other unused packages).
- **Removed:** `bot.py` (not importable), its tests, `run.py`, the unused templates and script,
  and about 7 MB of unreferenced images.
- **Tooling:** pytest suite with mocks, ruff, GitHub Actions CI, Dependabot.
- **Behavior notes:** old assistant messages that contain HTML trailer links now display as
  plain text; the open Dependabot PRs for `urllib3` and `Werkzeug` are obsolete.

---

## Resumen (español)

plAI es un chatbot recomendador de películas y series hecho con Flask. Usa Claude con
*function calling* para consultar TMDB: dónde ver un título, trailers y cartelera.

Instalación:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env     # completa ANTHROPIC_API_KEY, TMDB_API_KEY y SECRET_KEY
flask --app plai db upgrade
flask --app plai run --debug
```

Las pruebas se ejecutan con `pytest -q` y no necesitan claves. La base de datos por defecto es
SQLite; para Turso instala `pip install ".[turso]"` y define `DATABASE_URL`.
