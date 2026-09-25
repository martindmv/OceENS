# OcéEns II

Course evaluation platform built for the EPF engineering school.

## Overview

**OcéEns II** lets program managers, facilitators, campus managers and administrators create and run evaluation surveys (*sondages*) for EPF's programs, and lets students answer them. Answers can be exported, visualised, and summarised by an LLM (*synthèses*). The interface uses EPF's official visual identity and is in French.

### Tech stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.12) |
| **Authentication** | Microsoft Entra ID (Azure AD) via OAuth 2.0 / MSAL and Microsoft Graph, or a development sign-in |
| **Database** | SQLite (SQLAlchemy + SQLModel) |
| **Templating** | Jinja2 (server-side rendering) |
| **Frontend** | HTML / CSS / JavaScript, no framework |
| **Server** | Uvicorn |
| **Packaging** | `pyproject.toml`, [uv](https://docs.astral.sh/uv/) with a committed `uv.lock` |
| **Logging** | Python's standard `logging`, through Uvicorn's handlers |
| **Exports** | Pandas (CSV) |
| **Answer summaries** | Separate daemon calling an LLM (`requests-cache`, `markdown-it-py`) |

---

## Getting started

The shortest path from a fresh clone needs no Entra application and no LLM key: `.env.example` ships `AUTH_MODE=dev`, the [development sign-in](#development-sign-in).

1. **Create your `.env`** from the example. Every other command reads it, and `docker compose` refuses to start without it.

   ```bash
   cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
   ```

2. **Start the application**, with Docker or without.

   **With Docker Compose** (needs a running Docker daemon):

   ```bash
   docker compose up --build
   ```

   **Without Docker**, with [uv](https://docs.astral.sh/uv/getting-started/installation/). `uv sync` creates `.venv`, installs the Python version pinned in `.python-version` if it is missing, the dependencies locked in `uv.lock`, and the `oceens` package itself. The same commands work on Windows, macOS and Linux, from any working directory inside the clone:

   ```bash
   uv sync
   uv run uvicorn oceens.main:app --port 8000
   ```

   `uv run oceens` does the same through the installed entry point, listening on `0.0.0.0:8000`.

3. **Open <http://localhost:8000>** and sign in from `/dev/login` as any seeded user.

On first start the application creates the tables and, when the database has no user yet, inserts the demonstration data set (see [Demonstration data](#demonstration-data)). Without an LLM key everything works except summaries.

To check that the application actually works, follow the [smoke test](docs/smoke-test.md).

### The summaries daemon

Summaries are produced by a separate process, `oceens.summaries_generator_daemon`. The web application only queues requests in the `summaries` table; nothing is generated until the daemon runs. Start it next to the application, through its entry point:

```bash
uv run oceens-summaries-daemon
```

or set `RUN_SUMMARIES_DAEMON=1` in `.env` to have the application start it and stop it with itself. It loops, writes to the database and calls an external LLM service, so it only runs when you start it. Without `LLM_API_KEY`, every queued summary is marked as a configuration error and no call is made. It caches LLM responses in `cache_llm.db`, in the working directory it was started from.

### Docker Compose

The image installs the `oceens` package from `uv.lock` (`uv sync --locked`) and runs its `oceens` entry point: Uvicorn on `0.0.0.0:8000`, without `--reload`. After changing the code, rebuild with `docker compose up --build`. `.env` is never copied into the image.

`docker-compose.yaml` builds the image, publishes port 8000, reads `.env` through `env_file` and restarts the container automatically. It mounts two host directories:

- the database directory, `${LOCAL_DATABASE_DIR:-./database}` on `/app/database`, so the SQLite file survives a rebuild. Inside the container, `LOCAL_DATABASE_DIR` is always `/app/database`: the value in `.env` names the host directory;
- `./src/oceens/import` over the installed package's `import/`, for the demonstration answers, which `.dockerignore` keeps out of the image.

To stop and remove the container: `docker compose down`.

### In production

`launch.sh` runs `uv sync --locked`, then the `oceens` and `oceens-summaries-daemon` entry points in two `screen` sessions on the production server. It hardcodes the server's path, `/home/mde-admin/OceENS`, and needs `uv` installed there.

---

## Configuration

The application reads its configuration from environment variables, and loads `.env` from the project root at startup; a variable already set in the environment wins over `.env`. `.env.example` lists every variable with its default; this section is the reference for what each one does.

| Variable | Default | Effect |
|----------|---------|--------|
| `AUTH_MODE` | `entra` | `entra`: Microsoft Entra ID. `dev`: the [development sign-in](#development-sign-in), **never in production**. Case and surrounding spaces are ignored; any other value stops the application at startup (exit code 1). |
| `DEV_LOGIN_KEY` | *(unset)* | `dev` only. When set, every development sign-in must provide it (`key` field), otherwise `401`. When unset, the sign-in is open to anyone. Ignored, with a warning, in `entra`. |
| `ALLOWED_DOMAINS` | `epf.fr,epfedu.fr` in `dev`, *empty* in `entra` | Comma-separated e-mail domains allowed to sign in; any other domain gets `403`. In `entra`, leaving it empty refuses every sign-in. The admin screens that add users or students check against it too, falling back to `epf.fr,epfedu.fr`. |
| <a id="secret_key"></a>`SECRET_KEY` | *(unset)* | Signs the session cookies: anyone who knows it can forge a session, an administrator's included. **Required with `AUTH_MODE=entra`**: missing or empty, the application logs a critical error and exits with code 1. In `dev`, when unset, a random key is drawn at each start (with a warning), and sessions are lost on restart. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_TENANT_ID` | *(unset)* | The Entra ID application's credentials. Required with `AUTH_MODE=entra`: if one is missing the application exits with code 1. Not read in `dev`. |
| `REDIRECT_URI` | `https://localhost/auth/callback` | Where Entra ID redirects after sign-in; must match the application's registration. `entra` only. |
| `LOCAL_DATABASE_DIR` | `database/` at the project root | Directory of the SQLite file `db_oceens.db`, created if missing. A relative path is resolved from the project root. With Docker Compose, it is the host directory mounted on `/app/database`, and the container itself always uses `/app/database`. |
| `LLM_API_KEY` | *(empty)* | API key of the default LLM provider, *Ollama EPF*. Empty: the application runs, and requested summaries are marked as a configuration error. Other providers read their own variable, see [LLM providers](#llm-providers-answer-summaries). |
| `RUN_SUMMARIES_DAEMON` | *(unset)* | `1`, `true`, `yes` or `on`: the application starts the summaries daemon as a child process and stops it on shutdown. Leave unset where `launch.sh` already runs the daemon. |

> [!CAUTION]
> Never commit `.env`. It is listed in `.gitignore`, as are `*.db` files (`database/db_oceens.db`, `cache_llm.db`).

---

## Roles

A role is stored with its scope, one row per role in the `roles` table. A user can hold several.

- `student`, or no role at all: answers the surveys they are enrolled in. A user created at sign-in has no role row; one added from the admin screen gets an explicit `student` row. Both are treated as students.
- `program_manager:<code>`: manages the surveys of their program(s).
- `facilitator:<code>`: runs the surveys of their program(s).
- `campus_manager:<campus>`: scoped to a whole campus.
- `admin`: general administration.

Several scopes are separated by `;` (for example `program_manager:MDAI4;MDAI5`).

### Demonstration data

On an empty database, the seed (`src/oceens/core/seed.py`) inserts four surveys with answers, and users you can sign in as with the development sign-in:

| User | Roles |
|------|-------|
| `arnaud.jousset@epf.fr`, `etienne.gibaud@epf.fr` | `admin` only |
| `antoine.gademer@epf.fr` | `admin`, `program_manager:MDAI5` |
| `yassine.gharbi@epfedu.fr` | `admin`, `campus_manager:Montpellier` |
| `oceens.facilitator@epf.fr` | `facilitator:MDAI5` only |
| `oceens.program-manager@epf.fr` | `program_manager:MDAI5` only |
| `oceens.campus-manager@epf.fr` | `campus_manager:Montpellier` only |
| `bob.leponge@epfedu.fr` and 17 others | none (student) |

Programs are synchronised from `src/oceens/import/Program_list.csv` at every start; the rest is seeded only when the database has no user.

---

## Main pages and routes

| Route | Description |
|-------|-------------|
| `/` | Home, sign-in hub; redirects a signed-in user to their dashboard. |
| `/login`, `/auth/callback`, `/logout` | Microsoft Entra ID sign-in flow. In `dev`, `/login` redirects to `/dev/login` and `/auth/callback` does not exist. |
| `/dev/login` | Development sign-in: user picker on `GET`, sign-in on `POST` (only with `AUTH_MODE=dev`). |
| `/dashboard/student` | Student dashboard. |
| `/dashboard/program-manager` | Program manager dashboard. |
| `/dashboard/facilitator` | Facilitator dashboard. |
| `/dashboard/campus-manager` | Campus manager dashboard. |
| `/dashboard/teachers/analytics` | Satisfaction score per teacher, filterable by year, semester and program. For `campus_manager` and `program_manager`, each within their scope. |
| `/dashboard/admin` | Administrator dashboard. |
| `/dashboard/survey-create` | Survey creation and settings. |
| `/api/surveys/{survey_id}` | The questionnaire (answering a survey). |
| `/api/surveys/{survey_id}/status` | Change a survey's status. |
| `/api/surveys/{survey_id}/students` | Students enrolled in a survey. |
| `/api/surveys/{survey_id}/export` | CSV export of the answers. |
| `/api/surveys/{survey_id}/visualisation` | Answer visualisation. Accepts `?teacher=<name>` to open already filtered on a teacher. |
| `/api/surveys/{survey_id}/generate-summaries` | Queue the LLM summaries of a survey. |
| `/api/surveys/{survey_id}/destroy-summaries` | Delete a survey's summaries. |
| `/api/surveys/{survey_id}/cost` | Cost of a survey's summaries. |
| `/api/users`, `/api/users/{user_id}/role` | Add a user by e-mail; change a user's roles. |
| `/backend/prompts`, `/backend/prompts/new`, `/backend/prompts/{id}/edit` | LLM prompts: list, creation form, edit form (admin only). |
| `/api/prompts` (`POST`), `/api/prompts/{id}` (`PUT`, `DELETE`) | Create, update, delete a prompt. Update and delete are refused while the prompt is referenced by a summary. |
| `/backend/templates` | Survey templates, with their sections and questions (admin only). |
| `/backend/providers` | LLM providers (admin only). |
| `/backend/llm/prices`, `/backend/llm/costs` | LLM price list and costs (admin only). |

Any other path that answers 404 redirects to `/` with a `303`. FastAPI's own `/docs` lists every route.

---

## Development sign-in

To work on a fork without an Azure application, the **development sign-in** (`AUTH_MODE=dev`) signs you in as any user, with no proof of identity. It must **never** be used in production. The variables it reads are in [Configuration](#configuration).

In `dev`, the session cookie is no longer restricted to HTTPS (so `http://localhost` works), `/login` redirects to `/dev/login`, `/auth/callback` does not exist, and `/logout` clears the session and returns to `/`. A warning is logged at startup. A red banner, which cannot be dismissed, shows at the top of every page that includes the shared header: it shows the signed-in address, offers "Changer d'utilisateur" (`/dev/login`), and says the access is open to anyone when `DEV_LOGIN_KEY` is unset.

`POST /dev/login` expects a form with `email`, `name` (optional) and `key` (when `DEV_LOGIN_KEY` is set). The user is fetched or created as on return from Entra: an unknown address becomes a new student. Without `name`, the display name is built from the address (`bob.leponge@epfedu.fr` → "Bob Leponge"). A new sign-in replaces the session: that is how you switch users.

In a browser, `GET /dev/login` lists the database's users, grouped by role name without scope (a user with no role appears under `student`, a user with several roles under each of them). A click signs in as that user; a free field accepts any other address, with an optional name. When `DEV_LOGIN_KEY` is set, a single key field shows and serves every sign-in on the page; the key is never stored in the session.

```bash
AUTH_MODE=dev DEV_LOGIN_KEY=my-key uv run uvicorn oceens.main:app

# Sign in as a seeded admin; -c stores the session cookie
curl -i -c cookies.txt \
  -d email=arnaud.jousset@epf.fr -d key=my-key \
  http://localhost:8000/dev/login

# Reuse the cookie (-b) for the next requests
curl -b cookies.txt -c cookies.txt -L http://localhost:8000/
```

> [!WARNING]
> `dev` does not require `SECRET_KEY`. Unset, the key is random and unknown. But if a known `SECRET_KEY` is set (shared, copied from an example), anyone who knows it can forge a session cookie and bypass `DEV_LOGIN_KEY`. See [`SECRET_KEY`](#secret_key).

## Entra ID sign-in (OAuth 2.0)

With `AUTH_MODE=entra`, sign-in goes through **Microsoft Entra ID** with the MSAL library:

```
1. The user clicks "Se connecter"
   → FastAPI generates a random state (UUID, CSRF protection)
   → Redirect to Microsoft's sign-in page

2. The user authenticates with Microsoft
   → Microsoft redirects to /auth/callback with a code and the state

3. The server exchanges the code for an access token
   → Fetches the user's profile from Microsoft Graph
   → Reads the user's role(s) and scope from the database, creating the user if unknown
   → Creates the session {name, email, roles}
   → Redirects to the matching dashboard

4. On sign-out (/logout)
   → Clears the session and cookies
   → Signs out from Microsoft
   → Returns to the home page
```

Signing in authorises no business action by itself: each route then checks the role and its scope (program or campus) with `require_roles()` and its helpers.

---

## LLM providers (answer summaries)

Summaries of free-text answers are generated by an LLM. The provider is **configured from the interface** (`/backend/providers`, admin only), without touching the code. The default provider is **Ollama EPF** (`https://locallm.mde.epf.fr/ollama`, model `gemma4:26b`, key in `LLM_API_KEY`), created automatically at startup when missing. Each EPF student gets their own key at <https://locallm.mde.epf.fr>, by signing in with their EPF account.

### Supported API types

| `api_type` | Covers |
|------------|--------|
| `ollama`    | Ollama servers (local, EPF, third-party) |
| `openai`    | OpenAI **and any OpenAI-compatible endpoint**: vLLM, Groq, Mistral, LM Studio… |
| `anthropic` | Claude API (Anthropic) |

### Security principle: no key in the database

The SQLite database is not encrypted and ends up in backups, so **no API key is stored in it**. The `llm_providers` table only holds the *name* of the environment variable (`api_key_env`, e.g. `OPENAI_API_KEY`); the value stays in `.env` and is only read when a call is made. That name is checked against an allowlist (`LLM_*` or `*_API_KEY`), so it cannot point at a system secret (`SECRET_KEY`, `ENTRA_CLIENT_SECRET`…).

### Adding a provider

1. **Add the key to `.env`** under a conforming name (`LLM_*` or `*_API_KEY`):

   ```env
   OPENAI_API_KEY=sk-...
   ```

2. **Restart the application and the summaries daemon**: both read `.env` only at startup.

3. **Create the provider** in `/backend/providers` → *+ Nouveau fournisseur*: name, API type, base URL, the environment variable's name (`OPENAI_API_KEY`), and a default model. The **key present / absent** indicator confirms the variable is loaded. The **Tester** button checks that the URL and the key answer, then sends a one-token generation to confirm the account can actually generate (see below).

4. **Link a prompt** to the provider: in `/backend/prompts`, a `<select>` picks a prompt's provider. A prompt with no provider (`provider_id` NULL) falls back to Ollama EPF.

> [!NOTE]
> A provider referenced by at least one prompt cannot be deleted, so as not to break those prompts.

### Exhausted credit and other provider errors

Each provider reports failures in its own format: exhausted credit is a `429 insufficient_quota` at OpenAI, but a `400 "Your credit balance is too low"` at Anthropic. `src/oceens/services/llm_client.py` normalises these responses into categories (`quota`, `rate_limit`, `auth`, `model`, `server`) and derives a readable message from them, in French, which is written to `Summary.metadata_text` instead of the raw JSON, so a failed summary explains itself in the interface. The provider's raw response stays in the daemon's logs.

> [!IMPORTANT]
> The **Tester** button does not stop at listing models: at OpenAI as at Anthropic, `GET /v1/models` still answers normally with a zero balance. A one-token generation (negligible cost) is sent next; it is the only way to spot exhausted credit **before** starting a summary campaign.

---

## Summary costs

The cost of each summary is **measured, not estimated**. When generating, the daemon records the token counts returned by the provider (`Summary.input_tokens`, `output_tokens`, `model_used`): it is the only chance to capture them, as no API returns them afterwards. The amount is those counts crossed with the price list. **All amounts are in euros.**

### Price list: `/backend/llm/prices`

Prices live in the database (`llm_model_prices`) and are editable from the administration, so following a price change, or pricing a provider added locally, needs no release. Each price has two parts that add up:

- a **flat cost per generation**, as a range, for models not billed by the token;
- a **price per million tokens**, input and output, for providers billing by consumption.

Prices published in dollars are converted once, when entered, at the exchange rate set on the same page (0.92 by default); changing the rate later does not rewrite existing prices.

Seeded at startup (`seed_model_prices`, idempotent: a price corrected by hand is never overwritten):

| Model | Flat cost per generation | Input €/M tokens | Output €/M tokens |
| --- | ---: | ---: | ---: |
| `gemma4:26b` (Ollama EPF, self-hosted) | 0.02 – 0.05 | 0.00 | 0.00 |
| `claude-opus-5` | — | 4.60 | 23.00 |
| `claude-sonnet-5` | — | 2.76 | 13.80 |
| `claude-haiku-4-5` | — | 0.92 | 4.60 |

Self-hosted is not free: the flat cost of EPF's server covers GPU, electricity and depreciation. The Anthropic prices are its public dollar prices converted at 0.92. Other providers' prices (OpenAI, Mistral, Groq…) are **to be entered**: they are not guessed. A price specific to a provider wins over a generic price for the same model name.

### Where to see costs

| Where | What |
| --- | --- |
| `/backend/llm/costs` | Overall cost, by survey and by model (admin) |
| 💰 button on a survey row | Cost of that survey's summaries |

### What is not priced

A summary cannot be priced when its counts are missing (generated before this feature, or a provider that does not expose them) or when its model has no recorded price. It is then **counted separately**, never estimated nor set to zero: an invented amount would do more harm than a missing one, since it would show with the authority of a real one. The screens say explicitly when a total is partial.

> [!IMPORTANT]
> Tracking starts when the feature is deployed: summaries generated earlier have no counts in the database and cannot be priced retroactively.

---

## Logging

Application logs use Python's standard `logging` module and the `uvicorn` logger, so messages from the application, `src/oceens/core/auth.py` and `src/oceens/core/seed.py` share the server's format, colours and handlers.

| Level | Use |
|-------|-----|
| `DEBUG` | Details useful in development and while seeding. |
| `INFO` | Startup, shutdown and normal operations. |
| `WARNING` | An expected resource is missing, or a non-blocking situation. |
| `ERROR` / `EXCEPTION` | An operation failed; `logger.exception()` keeps the traceback. |
| `CRITICAL` | Required configuration is missing and the application cannot start. |

```python
import logging

logger = logging.getLogger("uvicorn")

logger.info("Operation done")

try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")
```

New diagnostics use the appropriate logger rather than `print()`. The application level is set to `DEBUG` in `src/oceens/core/dependencies.py`. Logs go through Uvicorn's handler, usually to `stderr`; redirect it (`2> error.log`) to keep them.

---

## Notable features

### Teacher analytics

`/dashboard/teachers/analytics` (`campus_manager`, `program_manager`) aggregates the satisfaction score per `(teacher, survey)` from the `QCU_Satisfaction` answers that carry an `Answer.teacher` (module sections). The teacher list is sorted with `teacher_sort_key()`, ignoring case and accents, and can be filtered by school year, semester, program and teacher.

### Teacher filter in the visualisation

A client-side selector filters the visualisation without reloading: only the chosen teacher's modules stay visible, and the Campus and Program sections are hidden. The page reads `?teacher=<name>` on load to pre-filter; links from the analytics pass it, so a click on a teacher's score opens their view directly.

### Surveys imported from Excel

`oceens.survey_loader_from_xlsx` is a command-line tool that imports a survey from a syllabus and a form export: `uv run python -m oceens.survey_loader_from_xlsx SYLLABUS FORMS PROGRAM SEMESTER YEAR`. The surveys it loads have no `QCU_Attendance` question, so `src/oceens/services/visualisation_data.py` falls back on `satisfaction_responses_count` as the denominator of the teacher score. Teacher names are normalised with `.title()` on import and on aggregation, so case variants merge (`"GADEMER Antoine"` and `"Gademer Antoine"` are one entry). Questions are sorted by `question_id` in the template, which puts charts before free-text answers whatever the insertion order.

### Campus manager scope

The `campus_manager` dashboard only shows closed surveys with at least one respondent. The questionnaire link and QR code are hidden there (`can_view_survey_link=False`): this role reads results without distributing surveys. The `{% if can_view_survey_link | default(true) %}` guard leaves the other dashboards unchanged.

### Cleaning up orphan students

When a survey is deleted, the students no longer attached to **any other** survey are deleted too, so unused accounts do not pile up (`src/oceens/services/helpers.py`, `_delete_orphan_students`). A guard protects users with a privileged role (`admin`, `program_manager`, `facilitator`, `campus_manager`): a teacher or manager who answered a survey is never deleted.

### Adding a user by e-mail

The "Utilisateurs" tab of the administrator dashboard has a **"+ Ajouter un utilisateur"** button: an e-mail address is enough to create the account, with the `student` role (`POST /api/users`, admin only). The address is validated (format and allowed domain) and duplicates are refused.

---

## Project structure

```
OceENS/
├── pyproject.toml                # Package metadata, dependencies, entry points
├── uv.lock                       # Locked dependency versions (committed)
├── .python-version               # Python version used by uv
├── launch.sh                     # Production launch script (no Docker)
├── Dockerfile, docker-compose.yaml, .dockerignore
├── .env.example                  # Configuration reference; copy to .env (never committed)
├── CONTEXT.md                    # Domain glossary
├── Template_2025.md              # The end-of-semester survey template, as text
│
├── src/oceens/                   # The oceens package: all the application's code and files
│   ├── main.py                   #   FastAPI factory, middlewares, router assembly; `oceens` entry point
│   ├── sondage_loader.py         #   Loads a full survey for the CSV export
│   ├── survey_loader_from_xlsx.py #  Command-line import of a survey from Excel files
│   ├── summaries_generator_daemon.py # LLM summaries, in a separate process; `oceens-summaries-daemon`
│   │
│   ├── core/                     #   Low-level access and security
│   │   ├── auth.py               #     Entra ID sign-in (login, logout, callback) and development sign-in
│   │   ├── database.py           #     SQLite engine and the SessionDep dependency
│   │   ├── security.py           #     Roles, scopes, access control
│   │   ├── dependencies.py       #     Shared Jinja templates and logger
│   │   └── seed.py               #     Initial data and program synchronisation
│   │
│   ├── models/                   #   SQLModel schema, one file per table
│   │   ├── __init__.py           #     Re-exports every class (see its docstring)
│   │   └── User.py, Survey.py, ...
│   │
│   ├── routers/                  #   Routes, split by business domain
│   │   ├── pages.py              #     Home and per-role dashboards
│   │   ├── surveys.py            #     Surveys: CRUD, status, export, visualisation
│   │   ├── students.py           #     Enrolling students in a survey
│   │   ├── users.py              #     User roles
│   │   ├── summaries.py          #     Queuing LLM summaries
│   │   ├── prompts.py            #     Prompt administration
│   │   ├── survey_templates.py   #     Survey template administration
│   │   ├── sections_questions.py #     Section and question administration
│   │   └── llm/                  #     LLM administration
│   │       ├── _access.py        #       Shared access control of the LLM screens
│   │       ├── providers.py      #       LLM providers (CRUD and connection test)
│   │       ├── prices.py         #       Price list per model
│   │       └── costs.py          #       Overall and per-survey cost
│   │
│   ├── services/                 #   Business logic
│   │   ├── helpers.py            #     Navigation, statistics, filters, sorting
│   │   ├── visualisation_data.py #     Aggregations and visualisation context
│   │   ├── llm_client.py         #     Multi-provider LLM client (ollama/openai/anthropic)
│   │   ├── llm_costs.py          #     Summary cost (measured tokens × price list)
│   │   ├── settings_store.py     #     Application settings (exchange rate)
│   │   └── export_csv.py         #     CSV export of the answers
│   │
│   ├── templates/                #   Jinja2 templates: index.html, dashboard/, backend/, template_parts/
│   ├── static/                   #   css/, js/, img/
│   └── import/                   #   Program list and demonstration answers read by the seed
│
├── docs/                         # Smoke test, ADRs, agent docs
├── llm-utils/                    # LLM tools outside the application
│
├── database/                     # SQLite database, created at startup (ignored by Git)
└── .venv/                        # Virtual environment created by uv sync (ignored by Git)
```

---

## Deployment checklist

- [ ] `AUTH_MODE` unset or `entra`
- [ ] `.env` holds the real Entra ID credentials and a dedicated [`SECRET_KEY`](#secret_key)
- [ ] `ALLOWED_DOMAINS` set: empty, it refuses every sign-in
- [ ] Valid SSL certificate (Let's Encrypt or equivalent): outside `dev`, the session cookie is HTTPS-only
- [ ] Database present (`database/db_oceens.db` or `LOCAL_DATABASE_DIR`), or the Docker volume mounted
- [ ] Environment variables secured, `LLM_API_KEY` included
- [ ] **Docker Compose**: `.env` loaded through `env_file`, never copied into the image; `LOCAL_DATABASE_DIR` pointing at the right directory
- [ ] Summaries daemon running if LLM summaries are used

---

## Before contributing

There is no automated test suite nor CI yet (#85, #78). Before proposing a change, run the [smoke test](docs/smoke-test.md): its static checks, then the steps your change touches. Then test the affected routes by hand on a throwaway SQLite database (never a copy of production), with the relevant roles and survey statuses.

---

## Resources

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI and Uvicorn logging guide](https://apitally.io/blog/fastapi-logging-guide)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://learn.microsoft.com/en-us/graph/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Pandas](https://pandas.pydata.org/)

---

**OcéEns team** — EPF
