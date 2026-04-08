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
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

# Import the initialized Supabase client to talk to the database
from app.database.database_setup import supabase

# Import our strict Pydantic schemas to validate incoming JSON data
from app.database.database_schema import CreateProfile

from app.ai_agents.evaluation_agent import EvaluationAgent

import base64

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


@router.post("/api/analyze-shelf")
async def analyze_shelf(shelf_photo: UploadFile, profile_id: str = Form(...)):

    # Step 1: Read the physical bytes of the image asynchronously
    image_bytes = await shelf_photo.read()

    # Step 2: Translated the raw bytes into a giant Base64 string for OpenAI
    print("Encoding image for OpenAI 💻")
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Step 3: The fake rules for testing
    test_rules = """
        REQUIREMENT 1: Red Coca-Cola products must be clearly visible and present.
        REQUIREMENT 2: Competitor brands (specifically blue bottles) are STRICTLY FORBIDDEN anywhere on the shelves. If even one single blue bottle is visible in the photo, this rule absolutely FAILS.
        REQUIREMENT 3: The shelf MUST NOT have any dark, empty gaps. It must be 100% fully stocked from end to end. If a bottle is missing, this rule FAILS.
        REQUIREMENT 4: Every single bottle must be standing perfectly upright. If any bottle is knocked over horizontally, lying down, or tilted sideways, this rule absolutely FAILS.
        """

    # Step 4: Calling the agent
    print("Initializing Evaluation Agent 🤖")
    evaluation_agent = EvaluationAgent()

    # Step 5: Run the AI Engine
    try:
        print("Invoking Evaluation Agent 🤖 (This takes ~5 seconds)...")
        ai_result = await evaluation_agent.analyze_shelf_image(base64_image, test_rules)

        print("\n=== 🎯 EVALUATION RESULT ===")
        print(f"Overall Score: {ai_result.ai_score}/100")
        print("\nEvaluation Feedback:")
        for detail in ai_result.feedbacks:
            status = "✅ PASS" if detail.is_compliant else "❌ FAIL"
            print(f" - {status}: {detail.feedback_text}")

    except Exception as e:
        return {"status": "error", "message": f"AI Engine Failed: {str(e)}"}

    # Step 6: Save the Parent Record (The Overall Score)
    try:
        eval_response = supabase.table("ai_evaluation").insert({
            "profile_id": profile_id,
            "uploaded_image_url": "testing_placeholder_url.png",  # Later, there will be a real storage bucket
            "ai_score": ai_result.ai_score
        }).execute()

        # Grab the newly generated UUID assigned by the database
        new_evaluation_id = eval_response.data[0]["id"]

        # Step 7: Bulk-Save the Children Records (The Itemized Feedback)
        feedbacks_to_insert = []
        for detail in ai_result.feedbacks:
            feedbacks_to_insert.append({
                "ai_evaluation_id": new_evaluation_id,
                "feedback_text": detail.feedback_text,
                "is_compliant": detail.is_compliant
            })

        supabase.table("ai_evaluation_feedback").insert(feedbacks_to_insert).execute()
        print(f"\n✅ Saved to Supabase! Evaluation ID: {new_evaluation_id} . Thank you for using our service 👋")

        # Step 8: Return success to the Evaluation dashboard!
        return RedirectResponse(f"/evaluation/{new_evaluation_id}", status_code=303)
    except Exception as e:
        return {"status": "error", "message": f"Database Insertion Failed: {str(e)}"}

@router.get("/evaluation/{eval_id}")
async def evaluation_dashboard(request:Request, eval_id: str):

    try:
        # Step 1: Get the main scorecard (the parent row)
        evaluation_response = supabase.table("ai_evaluation").select("*").eq("id", eval_id).single().execute()
        evaluation_data = evaluation_response.data

        # Step 2: Get the itemized feedback checklist (the children rows)
        feedback_response = supabase.table("ai_evaluation_feedback").select("*").eq("ai_evaluation_id", eval_id).execute()
        feedbacks_data = feedback_response.data

        # Step 3: Inject the data into the HTML page
        return index_template.TemplateResponse(
            request=request,
            name="evaluation_dashboard.html",
            context={
                "request": request,
                "evaluation": evaluation_data,
                "feedbacks": feedbacks_data
            }
        )
    except Exception as e:
        return {"status": "error", "message": f"Failed to load dashboard: {str(e)}"}

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
