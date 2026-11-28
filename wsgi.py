"""Production WSGI entry point for Gunicorn."""
from app import app, init_db

# Gunicorn imports this module; app.py only initializes the database when run directly.
init_db()
