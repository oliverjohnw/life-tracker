# Life Dashboard

A personal dashboard for tracking concerts, movies, sporting events, golf &
disc golf, and books. Django + Postgres on Railway, managed with `uv`.

| Tracker | What's there |
|---|---|
| **Concerts** | Logbook of expandable ticket-stub cards (poster, lineup, setlist.fm links, ratings) + Insights tab, one page |
| **Movies** | Diary, insights, hall of fame/shame, watchlist tab |
| **Sports** | Game log with W/L record, insights |
| **Golf** | Golf *and* disc golf on one page — switch with the toggle at the top |
| **Books** | Bookshelf of covers with a detail sheet, reading stats |

The home page shows a calendar heatmap of everything you've logged (colored by
tracker), a unified recent-activity feed, and quick "log something" buttons.

## Local setup

```bash
uv sync
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Open `http://localhost:8000` and log in. The whole site requires login
(`core/middleware.py`) — it holds personal data and is meant to be reachable
from the internet.

**Logging new entries:** the **Log something** button (sidebar, or any tracker's
header button) slides out a panel. Pick what you're logging from the dropdown and the
right short form appears — venues/courses are matched by name (type "Fiserv Forum" and
city/state fill in), people are chips with autocomplete, festival acts can be added with
"+ Add an act", and optional fields sit under "More details". It also works as a plain
page at `/log/` (a good phone bookmark). Code lives in `quicklog/`; forms are in
`quicklog/forms.py` and the dropdown order in `quicklog/registry.py`.

The Django admin (`/admin/`) is still there for **editing or deleting** past entries —
every expanded card has an "Edit in admin" link. Run the tests with
`uv run python manage.py test`.

## Data model

- **core.Person / core.Location** — shared by every tracker (who you went with;
  venues, stadiums, courses).
- **concerts.Event → Performance** — one outing with many acts. A festival is one
  Event with several Performances, each with its own genre, rating, tour and
  setlist.fm link. Events also hold the poster photo, seats, price, merch spend
  and sound/view/crowd scores.
- **movies.Movie / WatchlistItem**, **sports.SportingEvent** (with `my_team`,
  from which W/L is derived), **golf.Round** (`game` = golf or disc_golf, with
  optional course rating/slope for handicap differential), **books.Book**.

## Importing from Google Sheets

Each importer is idempotent — re-running updates existing rows instead of
duplicating them:

```bash
uv run python manage.py import_concerts --dry-run
uv run python manage.py import_concerts
uv run python manage.py import_movies --watchlist-worksheet "Watchlist"
uv run python manage.py import_sports
```

Sheet IDs go in `.env` (`CONCERTS_SHEET_ID`, `MOVIES_SHEET_ID`,
`SPORTS_SHEET_ID`) — it's the long string in the sheet URL between `/d/` and
`/edit`. Or pass `--sheet-id` / `--worksheet` on the command line.

### One-time Google Cloud setup (you do this part)

1. In [Google Cloud Console](https://console.cloud.google.com), create a project and
   enable the **Google Sheets API**.
2. Create a **service account** and download a JSON key for it.
3. Share each Google Sheet (Viewer is enough) with the service account's
   `client_email`.
4. Locally: save the key as `./google-service-account.json` (gitignored) and set
   `GOOGLE_APPLICATION_CREDENTIALS=./google-service-account.json`. On Railway: paste
   the whole JSON into a `GOOGLE_SERVICE_ACCOUNT_JSON` variable and run
   `railway run python manage.py import_concerts` from your machine.

Notes on the data: "MIlwaukee"-style capitalization typos are repaired on import,
and movies/sports tabs may have extra columns (a `Genre` column on movies, a
`My Team` column on sports) which are picked up automatically if present.

## Deploying to Railway

1. **New Project → Deploy from GitHub repo** → pick this repo.
2. In the project, **+ New → Database → PostgreSQL**.
3. On the web service → **Variables**, add:

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | `${{ secret(64) }}` — Railway generates a random value; the app refuses to boot without one |
   | `DATABASE_URL` | `${{ Postgres.DATABASE_URL }}` (use your database service's name if it isn't "Postgres") |
   | `ADMIN_USERNAME` / `ADMIN_PASSWORD` | your login — created on first deploy by `ensure_admin`, which never overwrites an existing user. Delete `ADMIN_PASSWORD` afterwards if you like. |
   | `MEDIA_ROOT` | `/data/media` (after step 4) |

4. **Uploaded images** (concert posters, book covers) need a persistent disk, because the
   container filesystem is wiped on every deploy: service → **Volumes** → add one mounted
   at `/data`. Images are served by Django behind the login, so they stay private.
5. Service → **Settings → Networking → Generate Domain**. The app trusts that domain
   automatically (`RAILWAY_PUBLIC_DOMAIN`); redeploy once after generating it.
6. `railway.json` does the rest: `collectstatic` at build, then `migrate` + `ensure_admin`
   before each deploy, then gunicorn.

## Extending

- **New tracker:** `uv run python manage.py startapp <name>`, add models + admin
  (reuse `core.Person` / `core.Location`), a view that builds `tiles` and `charts`
  with `core/charts.py`, and a template extending `layouts/tracker.html`. Add one
  line to `core/categories.py` for its color, icon and nav entry.
- **Charts** all go through `core/charts.py` so they share one look.
- **Cache-busting in dev:** templates use `{% asset %}` so edited CSS/JS is never stale.
