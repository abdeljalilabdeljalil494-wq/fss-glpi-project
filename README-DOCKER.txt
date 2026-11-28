FSS GLPI - Docker files only
============================

Copy these files into the ROOT of your existing fss-glpi-project folder,
next to app.py and requirements.txt. Do not put them inside a subfolder.

Files:
  Dockerfile        Docker image with development and production targets
  compose.yaml      Development setup with source bind mount / auto-reload
  compose.prod.yaml Production setup with Gunicorn
  .dockerignore     Excludes secrets, local DB files and caches from image build
  .env.example      Environment variable template (copy to .env)
  wsgi.py           Gunicorn entry point; imports app and initializes its DB

First run (PowerShell, from the project root):
  Copy-Item .env.example .env
  $secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
  $content = Get-Content .env -Raw
  $content = $content -replace '(?m)^APP_SECRET_KEY=.*$', "APP_SECRET_KEY=$secret"
  [System.IO.File]::WriteAllText((Join-Path $PWD ".env"), $content, [System.Text.UTF8Encoding]::new($false))
  docker compose config -q
  docker compose up --build

Open http://localhost:8000

Production:
  Stop development with Ctrl+C, then:
  docker compose down
  docker compose -f compose.prod.yaml up --build -d

IMPORTANT:
- This project's current database implementation is SQLite. These files preserve SQLite;
  they do not add a MySQL/MariaDB service or migrate the schema.
- Copy the files into the project root, not into a nested docker folder.
- Do not commit/share .env. Never run development and production simultaneously
  against the same SQLite database.
- Do not use "docker compose down -v" unless you intentionally want to delete
  persistent production data.
