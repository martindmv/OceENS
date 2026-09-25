# Manual smoke test

The repository has no automated test suite and no CI yet (the first tests are #85, CI is #78). This procedure runs entirely **outside the process**: start from a fresh clone, launch the application, and observe what it answers and with which exit code.

Run it before proposing a change that touches startup, configuration, dependencies or the container.

## Per-system conventions

Commands are given for **Windows (PowerShell)**, then for **macOS / Linux (bash)**. Only four things change:

| | Windows (PowerShell) | macOS / Linux (bash) |
|---|---|---|
| Virtual environment's interpreter | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Set a variable for one command | `$env:VAR = "x"`, then `Remove-Item Env:VAR` | `VAR=x command` |
| Read the exit code | `$LASTEXITCODE` | `echo $?` |
| Copy / rename a file | `Copy-Item`, `Rename-Item` | `cp`, `mv` |

The commands call the interpreter **by its path** (`.venv\Scripts\python.exe`) instead of activating the environment: on Windows, PowerShell's default execution policy blocks `Activate.ps1`, and that is not what this test is about.

## Static checks

The same on both systems (one line, no continuation):

```
python -m compileall -q main.py sondage_loader.py survey_loader_from_xlsx.py summaries_generator_daemon.py core models routers services
git diff --check
```

## 1. Local start, no credentials

In a fresh clone of the branch, with an empty virtual environment.

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\uvicorn.exe main:app --port 8000
```

**macOS / Linux (bash)**

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8000
```

Expected, with no Entra credential and no LLM key:

| Route | Response |
|---|---|
| `GET /` | 200 |
| `GET /dev/login` | 200 |
| `GET /nope` | 303 to `/` (404 middleware → `/`) |

The startup logs create the tables, insert the demonstration data set, and contain no error and no traceback.

## 2. Start with Docker

This needs a **running Docker daemon**: Docker Desktop on Windows (with the WSL 2 backend) and on macOS, the native daemon on Linux. The command is the same everywhere:

```
docker compose up --build
```

Expected: the image builds, the container starts without restarting in a loop, and `/`, `/dev/login` and `/nope` answer as in step 1.

Without `.env`, `docker compose` fails with `env file .env not found`. That is intended: a fork's first command is copying `.env.example`.

To stop and clean up:

```
docker compose down
```

## 3. Exit codes on invalid configuration

An invalid startup configuration must exit with **code 1**, so that a supervisor or a CI sees the failure.

`.env` must be moved aside for the last two cases: `load_dotenv()` would read `AUTH_MODE=dev` back from it and the application would start normally, with code 0.

**Windows (PowerShell)**

```powershell
# Invalid AUTH_MODE
$env:AUTH_MODE = "bogus"
.venv\Scripts\python.exe -c "import main"; $LASTEXITCODE   # 1
Remove-Item Env:AUTH_MODE

# Missing ENTRA_*, without .env
Rename-Item .env .env.bak
'AUTH_MODE','ENTRA_CLIENT_ID','ENTRA_CLIENT_SECRET','ENTRA_TENANT_ID' |
  ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
.venv\Scripts\python.exe -c "import main"; $LASTEXITCODE   # 1

# Missing SECRET_KEY in entra, without .env
$env:ENTRA_CLIENT_ID = "x"; $env:ENTRA_CLIENT_SECRET = "x"; $env:ENTRA_TENANT_ID = "x"
Remove-Item Env:SECRET_KEY -ErrorAction SilentlyContinue
.venv\Scripts\python.exe -c "import main"; $LASTEXITCODE   # 1
'ENTRA_CLIENT_ID','ENTRA_CLIENT_SECRET','ENTRA_TENANT_ID' |
  ForEach-Object { Remove-Item "Env:$_" }
Rename-Item .env.bak .env
```

**macOS / Linux (bash)**

```bash
# Invalid AUTH_MODE
AUTH_MODE=bogus .venv/bin/python -c "import main"; echo $?   # 1

# Missing ENTRA_*, without .env
mv .env .env.bak
env -u AUTH_MODE -u ENTRA_CLIENT_ID -u ENTRA_CLIENT_SECRET -u ENTRA_TENANT_ID \
  .venv/bin/python -c "import main"; echo $?   # 1

# Missing SECRET_KEY in entra, without .env
env -u AUTH_MODE -u SECRET_KEY ENTRA_CLIENT_ID=x ENTRA_CLIENT_SECRET=x ENTRA_TENANT_ID=x \
  .venv/bin/python -c "import main"; echo $?   # 1
mv .env.bak .env
```

Expected: the log line `INVALID AUTH_MODE 'bogus'` for the first case, `MISSING ENTRA INFO. Please check .env` for the second, `MISSING SECRET_KEY. Required with AUTH_MODE=entra, please check .env` for the third. As a control, `AUTH_MODE=dev` exits with 0, even without `SECRET_KEY`.

## 4. No LLM key

`.env.example` ships `LLM_API_KEY` **empty**: the application starts normally, and only summaries are unavailable. With the `summaries_generator_daemon.py` daemon running, a summary request is marked as a configuration error (`http_status` 500, "variable d'environnement absente ou vide") and no call is made to the provider.

## 5. With an LLM key

Each student gets their own key at <https://locallm.mde.epf.fr> by signing in with their EPF account, then puts it in their `.env`:

```
LLM_API_KEY=<your key>
```

Quick check, without the interface. **The key must be in this command's environment, not only in `.env`**: `load_dotenv()` is called by the application, by the daemon and by the authentication module, but not by `services/llm_client.py`, the only module imported here. Without the prefix below, the command raises `LLMConfigError` whatever `.env` holds.

The `python -c` line fits on one line and is the same on both systems; only the interpreter's path and the way to set the variable change.

**Windows (PowerShell)**

```powershell
$env:LLM_API_KEY = "<your key>"
.venv\Scripts\python.exe -c "from types import SimpleNamespace; from services import llm_client as c; p = SimpleNamespace(name='Ollama EPF', api_type='ollama', base_url='https://locallm.mde.epf.fr/ollama', api_key_env='LLM_API_KEY', default_model='gemma4:26b'); print(c.check_model(p, 'gemma4:26b')); print(c.ping_generation(p, 'gemma4:26b'))"
Remove-Item Env:LLM_API_KEY
```

**macOS / Linux (bash)**

```bash
LLM_API_KEY=<your key> .venv/bin/python -c "from types import SimpleNamespace; from services import llm_client as c; p = SimpleNamespace(name='Ollama EPF', api_type='ollama', base_url='https://locallm.mde.epf.fr/ollama', api_key_env='LLM_API_KEY', default_model='gemma4:26b'); print(c.check_model(p, 'gemma4:26b')); print(c.ping_generation(p, 'gemma4:26b'))"
```

Expected: `True`, then `(True, None, None)`. `check_model` alone is not enough: the model list still answers normally for an account with no credit, and only a generation call reveals it. With an empty value, or without the variable, the same command raises `LLMConfigError`: that is step 4's behaviour.

Then, end to end: request a survey's summaries with `summaries_generator_daemon.py` running. That half does not need the prefix: the daemon reads `.env` itself. Rows go from `http_status` 0 to 200, one at a time (the daemon is sequential), and the summary shows as HTML. Never commit the key: `.env` is ignored by Git.

## Next

Test the routes your change touches by hand, on a throwaway SQLite database (never a copy of production), with the relevant roles and survey statuses.
