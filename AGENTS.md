# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Main Flask application (MongoDB, S3, Pinecone integrations).
- `templates/`: Jinja2 views (dashboard, calendar, admin, uploads).
- `static/`: Front-end assets (CSS/JS/images).
- `uploads/`: Temporary file storage before S3 upload.
- `generar_faqs.py`, `procesar_pdfs.py`, `reset_password.py`: Utility scripts.
- `requirements.txt`, `.env`, `README.md`, `usuarios.json`.

## Build, Test, and Development Commands
- Create env: `python -m venv .venv && source .venv/bin/activate` (Windows: `\.venv\Scripts\activate`).
- Install deps: `pip install -r requirements.txt`.
- Run dev server: `python app.py` (uses `PORT` env; default 10000). Example: `PORT=5000 python app.py` (Windows: `set PORT=5000 && python app.py`).
- Production (example): `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`.

## Coding Style & Naming Conventions
- Python 3.x, PEP 8, 4-space indentation.
- Use `snake_case` for functions/variables, `PascalCase` for classes.
- Keep route handlers small; move helpers to functions.
- Templates: prefer descriptive file names and blocks; static assets under `static/`.
- No formatter enforced; if used, keep diffs minimal and consistent.

## Testing Guidelines
- No test suite yet. If adding tests, use `pytest`.
- Place tests under `tests/` with names like `test_<module>.py`.
- Aim to cover routes, permission decorators, and Mongo queries with fixtures/mocks.

## Commit & Pull Request Guidelines
- Write clear, present-tense messages in Spanish or English.
  - Example: `añade filtros de fechas` or `feat: reset password page`.
- One logical change per commit when possible.
- PRs should include: concise description, linked issue(s), screenshots for UI changes, and steps to reproduce or verify.

## Security & Configuration Tips
- Required env vars: `MONGO_URI`, `SECRET_KEY`, `AWS_S3_BUCKET`, `AWS_S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `PORT`.
- Do not commit `.env` or credentials. Use least-privilege AWS keys and IP-restricted Mongo users.
- Super-admin usernames are hardcoded for sensitive routes; review before deploying.

## Agent-Specific Instructions
- Keep changes minimal and aligned with existing patterns and language.
- Do not rename files or routes without coordination.
- Avoid introducing new dependencies unless justified and documented in `requirements.txt` and `README.md`.
