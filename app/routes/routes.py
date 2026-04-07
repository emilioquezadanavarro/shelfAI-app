"""
app/routes/routes.py

Defines the core HTTP endpoints for the FastAPI application.

This module acts as the "Traffic Controller" for the backend. It receives HTTP 
requests from the frontend or API clients, processes them (often by interacting 
with Supabase), and returns JSON responses.

Current capabilities:
1. Serving the Jinja2 HTML Frontend (Dynamic index).
2. Serving the Personalized Field Worker Dashboard (`/profile_dashboard`).
3. Providing a Database Health check (`/health/db`).
4. Handling User Profile Creation API (`/api/profiles`).

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
    
    Before returning the index.html file, this route actively queries the Supabase
    database for all existing user profiles. It then injects those profiles into the 
    HTML template so they can be rendered dynamically in the dropdown menu.

    """
    try:
        # Step 1: Query Supabase for all profiles
        response = (
            supabase.table("profiles")
            .select("*")
            .execute()
        )

        all_users = response.data

        # Step 2: Bundle the data into a "context" dictionary
        # The frontend Jinja2 engine will look for the key "profiles"
        context_data = {
            "request": request,    # Strictly required by FastAPI
            "profiles": all_users  # The list of dictionaries from Supabase
        }

        # Step 3: Pass everything to the template engine to compile into HTML
        return index_template.TemplateResponse(
            request=request,
            name="index.html",
            context=context_data
        )

    except Exception as e:
        # If the database is unreachable, catch it and return gracefully
        return {"status": "error", "message": str(e)}


@router.get("/profile_dashboard")
async def profile_dashboard(request: Request, profile_id: str):
    """
    Dashboard Endpoint - Serves the personalized user dashboard.
    
    This route acts as a "catcher" for the frontend form. It automatically extracts
    the `profile_id` parameter from the incoming URL (e.g., ?profile_id=123) and 
    uses it to securely fetch that exact user's data from Supabase.

    """
    try:
        # Step 1: Securely query Supabase for the specific user matching the URL ID
        # We use .eq() to filter the table rows exactly like a SQL WHERE clause
        profile_response = (
            supabase.table("profiles")
            .select("*")
            .eq("id", profile_id)
            .execute()
        )

        # Since IDs are unique, we extract the first (and only) dictionary in the list
        actual_profile = profile_response.data[0]

        # Step 2: Box up the profile data so the Jinja engine can read it
        profile_context_data = {
            "request": request,       # Strictly required by FastAPI for templating
            "profile": actual_profile # Injected so HTML can use {{ profile.first_name }}
        }

        # Step 3: Pass everything to the template engine to compile into HTML
        return index_template.TemplateResponse(
            request=request,
            name="profile_dashboard.html",
            context=profile_context_data
        )

    except Exception as e:
        # If the database is unreachable or the ID is invalid, catch it and return gracefully
        return {"status": "error", "message": str(e)}

# ==========================================
# DIAGNOSTIC ROUTES
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
