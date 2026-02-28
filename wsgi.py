"""
WSGI entry point for Gunicorn server.

Usage: gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
"""

from pdf_annotator.app import create_app

app = create_app("production")
