"""
App entry point for uvicorn.
This file imports the FastAPI app from main.py to allow using 'uvicorn app:app --reload'
"""

from main import app

# Export the app so uvicorn can find it
__all__ = ['app']
