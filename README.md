# Handoff

Handoff is a live event-operations web app for coordinating volunteers, tasks, urgent help, resources, and shift handoffs without requiring accounts.

## Stack
- Python
- FastAPI
- Jinja2
- SQLAlchemy
- PostgreSQL
- HTML/CSS

## Run locally

1. Create a PostgreSQL database.
2. Copy `.env.example` to `.env`.
3. Put your PostgreSQL connection string in `.env`.
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Start:

```bash
uvicorn app.main:app --reload
```

6. Open http://127.0.0.1:8000

## Important
`.env` is intentionally excluded from Git. Never commit database credentials.
