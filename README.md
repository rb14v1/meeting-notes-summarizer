# Meeting Notes & Action Items Summarizer

A small team tool for pasting in freeform meeting notes and turning them
into a short AI summary plus a tracked list of action items. Every
logged-in user can see every meeting (it's a shared, team-wide log, not
per-user data); only a meeting's creator or an admin can edit or delete it.
React + Vite + TypeScript frontend, Django REST Framework backend, plain
PostgreSQL database - no pgvector, no vector database, no embeddings
anywhere in this app. No Celery/Redis either - there is no background work
to run.

## Data model

- **User** - custom user, `email` as `USERNAME_FIELD`, no `username` field.
  `full_name`, `role` (`member` or `admin`).
- **Meeting** - `title`, `meeting_date`, `raw_notes` (the pasted/typed
  freeform notes), `created_by`, `created_at`.
- **MeetingSummary** - one-to-one with Meeting. `summary`, `generated_at`.
  Created the first time a meeting is summarized; **replaced** (not
  appended to) on every re-summarize.
- **ActionItem** - `meeting` (FK), `description`, `assignee` (free-text name
  or null), `is_done`, `is_ai_generated`, `created_at`. Created from the
  AI's parsed action-items list at summarize time, but a user can also add,
  edit or delete action items manually afterward - they are never
  AI-only/read-only. `is_ai_generated` is what lets re-summarizing replace
  only the AI-generated subset while leaving manually-added items (and
  their done/edited state) untouched.

## AI feature - a single chat-completion call

`apps/common/ai.py::summarize_meeting_notes(raw_notes) -> {"summary": str, "action_items": list[str]}`
is the only AI touchpoint in this app - there is no embeddings model and no
vector database anywhere.

- **Real path** (`OPENAI_API_KEY` set): calls the OpenAI chat completions
  API (`OPENAI_CHAT_MODEL`, default `gpt-5.6-sol`) asking for structured
  JSON, parsed defensively - if the model's response isn't valid JSON with
  the expected shape, the code falls back to a minimal labelled result
  instead of raising.
- **Stub path** (no key - the default for local dev/tests): fully offline
  and deterministic. The summary is the first one or two sentences of the
  notes; the 2-4 action items are synthesized from a sha256 hash of the
  text, so the **same** `raw_notes` always produces the **same** stub
  output - this determinism is what the test suite (and the seed data
  migration) relies on.

The AI call is a normal synchronous function call made before saving - no
vector database to desync, so there's no `transaction.on_commit` dance
needed here.

## REST API

- `/api/auth/` - `register/`, `login/` (JWT), `refresh/`, `logout/`
- `GET /api/users/me/`
- `/api/meetings/` - list/create/retrieve/update/delete. Any authenticated
  user can see every meeting; only the creator or an admin can
  update/delete one (`apps/meetings/permissions.py::IsMeetingCreatorOrAdminForWrite`).
- `POST /api/meetings/{id}/summarize/` - runs the AI call against
  `raw_notes`, creates/replaces the `MeetingSummary`, and replaces only the
  AI-generated `ActionItem`s (manually-added ones are preserved). Open to
  any authenticated user, same as list/retrieve.
- `/api/meetings/{id}/action-items/` - list/create action items for a
  meeting (manual creates are always `is_ai_generated=False`).
- `/api/action-items/{id}/` - PATCH to toggle `is_done` / edit
  `description`/`assignee`, DELETE to remove. Works regardless of
  `is_ai_generated`.

## Demo data

`apps/meetings/migrations/0002_seed_demo_data.py` is a data migration
(`RunPython`) that seeds a fresh database with:

- two logins: **member@example.com** / **demo12345** (role=member) and
  **admin@example.com** / **demo12345** (role=admin)
- 10 meetings covering varied topics (sprint planning, budget review,
  hiring, customer feedback, incident postmortem, roadmap planning, vendor
  review, all-hands, a 1:1 left un-summarized on purpose) - most with a
  generated `MeetingSummary` and a mix of AI-generated and manually-added
  `ActionItem`s, some done and some not.

It calls the real `summarize_meeting_notes()` function to generate the
seeded summaries/action items - since no `OPENAI_API_KEY` is configured at
migrate time, this always runs in the deterministic stub mode, so the seed
data is exactly what anyone gets from a fresh `migrate` run.

It's idempotent - every row is looked up with `get_or_create` (users,
meetings) or an explicit existence check (summaries/action items, which
have no natural unique key) before being created, so running `migrate`
again never duplicates rows.

## Running locally with Docker (Postgres)

```bash
cp .env.example .env
docker compose up --build
```

Backend on http://localhost:8000, frontend on http://localhost:5173.

## Running the backend without Docker (dev-only SQLite override)

No Postgres/Docker needed for this - same `USE_SQLITE` pattern used by the
sibling apps in this workspace. **Never set `USE_SQLITE=True` in
docker-compose or production.**

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash; use venv\Scripts\activate.bat on cmd

pip install -r requirements.txt

export USE_SQLITE=True
export DJANGO_SETTINGS_MODULE=config.settings.dev

python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
python manage.py runserver
```

## Running the frontend

```bash
cd frontend
npm install
npm run dev      # dev server on :5173
npm run build    # production build (tsc -b && vite build)
```

Set `VITE_API_BASE_URL` (see `frontend/.env.example`) if the backend isn't
at `http://localhost:8000/api`.

## Auth trade-off (dev-only)

The access token is kept in memory only; the refresh token is kept in
`localStorage` and the client refreshes on a 401. A real deployment would
instead issue the refresh token as an httpOnly cookie from the backend -
this simplified pattern (same as the sibling apps in this workspace) is a
deliberate trade-off for a small demo app, not a recommendation for
production.
