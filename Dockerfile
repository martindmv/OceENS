FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/
WORKDIR /app

# UV_LINK_MODE=copy : pas de liens durs depuis le cache de uv (autre système de fichiers)
# UV_PYTHON_DOWNLOADS=0 : utiliser le Python de l'image, jamais en télécharger un
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Dépendances seules d'abord, depuis le lockfile : cette couche reste en cache
# tant que pyproject.toml et uv.lock ne changent pas.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-install-project

# Puis le paquet oceens, installé (pas éditable) dans .venv avec ses templates,
# fichiers statiques et données de seed.
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# Le paquet est installé, pas cloné : database.py ne peut pas déduire la racine
# du projet de son propre emplacement. La base SQLite vit donc dans
# /app/database, à monter comme volume pour la conserver entre les redémarrages.
# Le fichier .env ne doit PAS être copié dans l'image : fournir les secrets via
# --env-file .env au lancement (docker run) ou via les variables d'environnement.
ENV LOCAL_DATABASE_DIR=/app/database

# Point d'entrée installé `oceens` (pyproject.toml) : uvicorn sur 0.0.0.0:8000
CMD ["oceens"]
