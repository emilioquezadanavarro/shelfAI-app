"""
app/routes/routes.py

Defines the core HTTP endpoints for the FastAPI application.

This module acts as the "Traffic Controller" for the backend. It receives HTTP 
requests from the frontend or API clients, processes them (often by interacting 
with Supabase), and returns JSON responses.

Current capabilities:
1. Serving the Jinja2 HTML Frontend.
2. Providing a Database Health check (`/health/db`).
3. Handling User Profile Creation (`/api/profiles`).

"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

# Import the initialized Supabase client to talk to the database
from app.database.database_setup import supabase

# Import our strict Pydantic schemas to validate incoming JSON data
from app.database.database_schema import CreateProfile

import os

# Initialize the router instance (this groups our endpoints together)
router = APIRouter(
    tags=["Index"]
)

# Tell FastAPI where our HTML template files are stored
index_template = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))


# ==========================================
# FRONTEND ROUTE
# ==========================================
@router.get("/")
async def index(request: Request):
    """
    Root Endpoint - Serves the main HTML interface of the application.
    When a user goes to localhost:8000/, this function returns the index.html file.
    """
    return index_template.TemplateResponse(request=request, name="index.html")


# ==========================================
# 🩺 DIAGNOSTIC ROUTES
# ==========================================
@router.get("/health/db")
async def health_route():
    """
    Database Health Check - Validates the connection to Supabase.
    Attempts to fetch the entire 'profiles' table to prove credentials are valid.
    """
    try:
        # Perform a basic SELECT query on the profiles table
        response = (
            supabase.table("profiles")
            .select("*")
            .execute()
        )
        # Supabase returns an APIResponse object.
        # We need to extract the raw JSON data using '.data' so FastAPI can serialize it.
        return {"status": "success", "data": response.data}
    except Exception as e:
        # If the database is unreachable or keys are wrong, catch it and return gracefully
        return {"status": "error", "message": str(e)}


# ==========================================
# USER PROFILE ROUTES
# ==========================================
@router.post("/api/profiles")
async def create_profile(profile: CreateProfile):
    """
    Creates a new user profile in the database.
    
    Expects a JSON body structured exactly like the `CreateProfile` Pydantic class:
    { "first_name": "name", "last_name": "last name" }
    """
    try:
        # Try to insert the incoming Pydantic object's data into the Supabase table
        new_profile = (
            supabase.table("profiles")
            .insert({
                # Map the Pydantic properties to the database columns
                'first_name': profile.first_name,
                'last_name' : profile.last_name
            })
            .execute() # Fire the query across the internet!
        )

        # Log the success strictly *after* the execute() block survives without errors
        print(f"✅ SUCCESS: Created profile for {profile.first_name} {profile.last_name}")

        # Return a structured JSON confirmation to the frontend, including the generated ID
        return {
            "status": "success",
            "message": f"Welcome {profile.first_name}! Your profile was securely created.",
            "data": new_profile.data
        }

    except Exception as e:
        # If the database rejects the insert (e.g. invalid columns, connection lost), it lands here
        print(f"⛔ Error: There was an error: {e}")
        return {"status": "error", "message": str(e)}
