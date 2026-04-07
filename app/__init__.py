"""
app/__init__.py

Implements the FastAPI Application Factory Pattern.

This module acts as the starting point for your backend engine. It is responsible for:
1. Loading secure environment variables (API Keys, Supabase Credentials) from `.env`.
2. Initializing the core FastAPI application instance.
3. Mounting the "static" directory so the browser can download CSS and Images.
4. Registering all the API routing blueprints (from `app/routes/routes.py`).

By using the factory pattern (`create_app`), we ensure that our app can be easily
imported by testing frameworks without immediately starting the server.

"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.routes.routes import router
import os

# 1. Load Environment Variables First
# This ensures that OS level variables like SUPABASE_URL are securely loaded
# before any other files try to import them.
load_dotenv()


def create_app():
    """
    Factory function to initialize and configure the application.
    """
    
    # 2. Instantiate the Core FastAPI Object
    # The title and description will automatically populate your Swagger documentation 
    # at http://127.0.0.1:8000/docs
    app = FastAPI(
        title="ShelfAI App",
        description="Core backend for retail companies shelf comparison"
    )

    print(" === ShelfAI has been started === ")

    # 3. Mount Static Files
    # We must explicitly tell FastAPI where our static assets (like CSS) live.
    # We mount the directory `app/templates/static` to the URL prefix `/static`.
    # When HTML requests `<link href="/static/styles.css">`, FastAPI knows where to find it.
    app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "templates", "static")), name="static")

    # 4. Register Routes
    # We attach the 'router' (which holds all our endpoints from routes.py)
    # directly into this main FastAPI engine.
    app.include_router(router)

    return app