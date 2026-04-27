"""
app/routes/routes.py

Defines the core HTTP endpoints for the FastAPI application.

This module acts as the "Traffic Controller" for the backend. It receives HTTP 
requests from the frontend or API clients, processes them (often by interacting 
with Supabase), and returns appropriate responses (HTML templates or JSON).

Current capabilities:
1. Authentication: Secure login with role-based routing (`/api/login`).
2. Category Manager Dashboard: Admin interface for managing workers and campaigns (`/category_manager/...`).
3. Worker Registration: "Two-Step Procedure" using the admin client to create GoTrue users + DB profiles.
4. Worker Dashboard: Personalized workspace for Field Workers (`/worker_dashboard`).
5. Campaign Onboarding: AI-powered rule extraction from marketing PDFs (`/api/onboard_campaign`).
6. Shelf Evaluation: Vision AI comparison of shelf photos against campaign rules.

Uses two Supabase clients:
- `supabase`: Standard client for user-facing operations (login, queries).
- `supabase_admin`: Elevated Service Role client for admin-only actions (creating users).

"""
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app.database.database_schema import CreateWorker

# Import the initialized Supabase client to talk to the database
from app.database.database_setup import supabase
from app.database.database_setup import supabase_admin

from app.ai_agents.evaluation_agent import EvaluationAgent
from app.ai_agents.extraction_rules_agent import ExtractionRulesAgent, extract_text_from_pdf

from typing import Annotated

import base64
import os



# Initialize the router instance (this groups our endpoints together)
router = APIRouter(
    tags=["Index"]
)

# Tell FastAPI where our HTML template files are stored
index_template = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))


# ==========================================
# =            FRONTEND ROUTE              =
# ==========================================

@router.get("/")
async def index(request: Request):
    """
    Root Endpoint - Serves the secure login interface.
    
    This is the first page users see. It renders 'index.html', which now 
    contains the email/password form for our authentication system.
    """
    try:
        # Create a context dictionary to pass data to the HTML template.
        # Even if I don't have user data to send yet, Jinja2/FastAPI
        # requires the 'request' object to be present to render correctly.
        context_data = {
            "request": request,    # Strictly required by FastAPI
        }

        # The TemplateResponse compiles the HTML and the 'context_data'
        # into a final package that the user's browser can display.
        return index_template.TemplateResponse(
            request=request,
            name="index.html",
            context=context_data
        )

    except Exception as e:
        # Standard error handling: if the template fails to load,
        # it catches the error and display it so the app doesn't crash.
        return {"status": "error", "message": str(e)}


@router.post("/api/login")
async def login(email: str = Form(...), password: str = Form(...)):
    """
    Login Endpoint - Authenticates users and routes them to the correct dashboard.
    
    This route receives credentials from the login form, verifies them with 
    Supabase Auth, and fetches the user's role (Manager or Worker) from the 
    database.

    It then:
    1. Sets a secure HttpOnly cookie containing the access token.
    2. Redirects the user to their specific workspace based on their role.

    """


    try:
        # 1. Ask Supabase to log the user in
        auth_response = supabase.auth.sign_in_with_password({"email":email, "password": password})

        #2. Extract the secure "JWT Token" and the user ID from response.
        access_token = auth_response.session.access_token
        user_id = auth_response.user.id

        #3. Query the Supabase profiles table
        profile_response = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .execute()
        )

        #4. Extract the user's role from database response
        user_role = profile_response.data[0]["role"]

        #5. Create the RedirectResponse based on the role
        # Role-based routing: send each user type to their specific dashboard
        if user_role == "category manager":
            print(f"✅️ SUCCESS: You have logged in as a Category Manager!")
            response = RedirectResponse(url=f"/category_manager/dashboard?profile_id={user_id}", status_code=303)
        elif user_role == "worker":
            print(f"✅️ SUCCESS: You have logged in as a Field Worker!")
            response = RedirectResponse(url=f"/worker_dashboard?profile_id={user_id}", status_code=303)
        else:
            raise Exception("Invalid role")

        #6. Plant the secure cookie
        # This attaches the secret token to the browser, so the user stays logged in.
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True, # Security: Prevents hackers from reading the cookie with JavaScript
            secure=False,  # Set to True if using HTTPS in production
            max_age=3600  # Cookie expires in 1 hour
        )

        return response

    except Exception as e:
        # If login fails (wrong password, etc.), redirect back to home with an error parameter (optional)
        print(f"Login failed: {e}")
        return RedirectResponse(url="/?error=InvalidLogin", status_code=303)

# ==========================================
# =     CATEGORY MANAGER ROLE ROUTES       =
# ==========================================

@router.get("/category_manager/dashboard")
async def category_manager_dashboard(request: Request, profile_id: str, success_msg: str = None):
    """
    Category Manager Dashboard Endpoint.
    
    Fetches the category manager's profile data from Supabase using the provided profile_id
    and renders the main dashboard interface. Also handles displaying optional success messages
    after actions like creating a worker.
    """

    try:
        # Step 1: Query Supabase for the manager's profile using their UUID
        category_manager_profile_response = (
            supabase.table("profiles")
            .select("*")
            .eq("id", profile_id)
            .execute()
        )

        # Step 2: Extract the single profile dictionary from the response list
        category_manager_profile = category_manager_profile_response.data[0]

        # Step 3: Bundle all data the HTML template needs into a context dictionary
        category_manager_profile_context_data = {
            "request": request,          # Strictly required by FastAPI for templating
            "profile": category_manager_profile,  # Full profile dict → {{ profile.first_name }}
            "profile_id": profile_id,    # Passed to child routes via URL links
            "success_msg": success_msg   # Optional flash message after worker creation
        }

        # Step 4: Render the dashboard HTML with the manager's data injected
        return index_template.TemplateResponse(
            request=request,
            name="category_manager_dashboard.html",
            context=category_manager_profile_context_data
        )


    except Exception as e:
        # If the database is unreachable or the ID is invalid, catch it and return gracefully
        return {"status": "error", "message": str(e)}

@router.get("/category_manager/create_worker")
async def create_worker_page(request: Request, profile_id: str):
    """
    Create Worker Form Page.

    Serves the HTML form for the Category Manager to register new workers. 
    Passes the `profile_id` through the template context so the form can 
    include it when submitting the POST request.

    """

    # Render the registration form, injecting the manager's ID so the hidden field can capture it
    return index_template.TemplateResponse(
        request=request,
        name="create_worker.html",
        context={
            "request": request,     # Strictly required by FastAPI for templating
            "profile_id": profile_id,  # Injected into hidden field → becomes worker.created_by_id on POST
        }
    )


@router.post("/category_manager/create_worker")
async def create_worker(worker: Annotated[CreateWorker, Form()]):
    """
    Creates a new field worker account in the database.

    This handles the "Two-Steps procedure" for worker registration:
    1. Uses the 'admin' auth client to bypass session-switching and create a GoTrue user.
    2. Inserts the worker's profile data into the `profiles` table using the newly generated UUID.

    Upon success, redirects the Category Manager back to their dashboard with a success message.
    """
    try:
        # Step 1: Create a new GoTrue user via the Admin client (avoids contaminating the Manager's session)
        new_worker_auth_response = supabase_admin.auth.admin.create_user({
            "email": worker.email,                # Worker's login email
            "password": worker.password,            # Temporary password for first login
            "user_metadata": {"first_name": worker.first_name, "last_name": worker.last_name},
            "email_confirm": True                   # Skip email verification (admin-created account)
        })

        # Step 2: Extract the UUID that Supabase Auth generated for this new user
        user_id = new_worker_auth_response.user.id

        # Step 3: Synchronize the worker's data into the profiles table, linking it to the Auth UUID
        (
            supabase.table("profiles")
            .insert({
                'id': user_id,                        # Links this profile to the GoTrue auth record
                'first_name': worker.first_name,
                'last_name': worker.last_name,
                'role': worker.role,                   # Always 'worker' (enforced by frontend dropdown)
                'created_by_id': worker.created_by_id  # Audit trail: which Manager created this account
            })
            .execute()
        )

        # Log the success strictly *after* the execute() block survives without errors
        print(f"✅ SUCCESS: Created profile for the worker: {worker.first_name} {worker.last_name}")

        # Step 5: Redirect the Manager back to THEIR dashboard (using created_by_id, not the worker's ID!)
        return RedirectResponse(
            f"/category_manager/dashboard?profile_id={worker.created_by_id}&success_msg=Worker {worker.first_name} was created successfully!",
            status_code=303  # 303 = "See Other" tells the browser to switch from POST to GET
        )


    except Exception as e:
        # If the database rejects the insert (e.g. invalid columns, connection lost), it lands here
        print(f"⛔ Error: There was an error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/worker_dashboard")
async def worker_dashboard(request: Request, profile_id: str):
    """
    Worker Dashboard Endpoint.
    
    Serves the personalized dashboard for Field Workers. It extracts
    the `profile_id` parameter from the URL to securely fetch and display 
    the worker's specific data and available actions from Supabase.

    """
    try:
        # Step 1: Securely query Supabase for the specific user matching the URL ID
        # Use .eq() to filter the table rows exactly like a SQL WHERE clause
        profile_response = (
            supabase.table("profiles")
            .select("*")
            .eq("id", profile_id)
            .execute()
        )

        # Since IDs are unique, this extracts the first (and only) dictionary in the list
        actual_profile = profile_response.data[0]

        # Step 2: Fetch all available campaigns so the worker can select one
        campaigns_response = supabase.table("campaigns").select("id, campaign_name").execute()
        campaigns_list = campaigns_response.data

        # Step 3: Box up the profile and campaign data so the Jinja engine can read it
        profile_context_data = {
            "request": request,       # Strictly required by FastAPI for templating
            "profile": actual_profile, # Injected so HTML can use {{ profile.first_name }}
            "campaigns": campaigns_list # Injected so HTML can build a dropdown
        }

        # Step 3: Pass everything to the template engine to compile into HTML
        return index_template.TemplateResponse(
            request=request,
            name="worker_dashboard.html",
            context=profile_context_data
        )

    except Exception as e:
        # If the database is unreachable or the ID is invalid, catch it and return gracefully
        return {"status": "error", "message": str(e)}


@router.get("/upload-rules")
async def upload_rules_page(request: Request, profile_id: str = None):
    """
    Upload Rules Page - Serves the campaign document upload form.
    
    If a `profile_id` is supplied in the URL query parameters, this route fetches
    the corresponding user profile from Supabase to provide a personalized greeting.

    """
    profile_data = None

    if profile_id:
        try:
            profile_response = supabase.table("profiles").select("*").eq("id", profile_id).single().execute()
            profile_data = profile_response.data
        except Exception as e:
            print(f"Warning: Could not fetch profile for greeting: {e}")

    return index_template.TemplateResponse(
        request=request,
        name="upload_rules_document.html",
        context={
            "request": request, 
            "profile_id": profile_id,
            "profile": profile_data
        }
    )

@router.post("/api/onboard_campaign")

async def extracting_rules(campaign_document: UploadFile, profile_id: str = Form(...)):
    """
    Campaign Onboarding Endpoint - Extracts structured rules from a marketing PDF.

    This route receives a PDF document uploaded by the marketing team, saves it to 
    the server, extracts its text content using PyMuPDF, and then sends that raw text 
    to the ExtractionRulesAgent (GPT-4o-mini). The AI parses the document and returns 
    a structured JSON object containing brand info, SKU portfolio, KPIs, and audit rules.

    The result is then persisted into the Supabase `campaigns` table as JSONB.

    """

    # Step 1: Read the raw bytes of the uploaded PDF asynchronously
    imported_document_bytes = await campaign_document.read()

    # Step 2: Save the PDF to the campaign_documents folder on disk
    # This is required because our extract_text_from_pdf() helper opens files by path
    base_dir = os.path.dirname(__file__)
    pdf_path = os.path.join(base_dir, "..", "campaign_documents", campaign_document.filename)

    with open(pdf_path, "wb") as f:
        f.write(imported_document_bytes)

    # Step 3: Extract the raw text content from the saved PDF
    pdf_text = extract_text_from_pdf(campaign_document.filename)

    # Step 4: Initialize and invoke the AI Extraction Agent
    print("Initializing Extraction Rules Agent 🤖")
    extraction_rules_agent = ExtractionRulesAgent()

    try:
        print("Invoking Extraction Rules Agent 🤖 (This takes ~5 seconds)...")
        ai_extraction_result = await extraction_rules_agent.create_campaign_rules(pdf_text)

        # Step 5: Print the structured result to the terminal for debugging
        print("\n=== 🎯 EXTRACTED CAMPAIGN RULES ===")
        print(f"Brand: {ai_extraction_result.brand}")
        print(f"Campaign: {ai_extraction_result.campaign_name}")
        print(f"Focus Product: {ai_extraction_result.focus_product}")
        print(f"Target Price: ${ai_extraction_result.target_price}")
        print(f"Min Facings: {ai_extraction_result.min_facings}")
        print(f"Share of Facings: {ai_extraction_result.share_of_facing}%")
        print(f"Price Tag Required: {ai_extraction_result.price_tag_required}")
        print(f"\nPortfolio SKUs:")
        for sku in ai_extraction_result.portfolio_skus:
            print(f"  - {sku}")
        print(f"\nRules:")
        for rule in ai_extraction_result.rules:
            print(f"  - {rule}")
    except Exception as e:
        return {"status": "error", "message": f"AI Engine Failed: {str(e)}"}

    # Step 6: Save the extracted rules as JSONB into the Supabase campaigns table
    # .model_dump() converts the Pydantic object into a Python dictionary for JSONB storage
    try:
        extraction_response = supabase.table("campaigns").insert({
            "campaign_name": ai_extraction_result.campaign_name,
            "evaluation_rules": ai_extraction_result.model_dump(),
            "reference_image_url": "testing_placeholder_url.png", # Later, there will be a real storage bucket
            "created_by": profile_id
        }).execute()

        # Grab the newly generated UUID assigned by the database and campaign name
        new_campaign_id = extraction_response.data[0]["id"]
        extracted_campaign_name = extraction_response.data[0]["campaign_name"]

        print(f"\n✅ Marketing Rules have been saved to Supabase! Campaign Name: {extracted_campaign_name} ")

        # Step 7: Redirect to the Campaign Dashboard
        return RedirectResponse(f"/campaign/{new_campaign_id}?profile_id={profile_id}", status_code=303)
        
    except Exception as e:
        return {"status": "error", "message": f"Database Insertion Failed: {str(e)}"}


@router.get("/campaign/{campaign_id}")
async def campaign_dashboard(request: Request, campaign_id: str, profile_id: str = None):
    """
    Campaign Dashboard - Displays extracted rules and provides the shelf photo upload form.

    This route fetches the campaign record from Supabase using the URL parameter,
    then injects the JSONB evaluation_rules into the HTML template so the user can
    review the AI-extracted rules before uploading a shelf photo for auditing.
    It also propagates the `profile_id` to ensure the final audit remains linked
    to the active field worker.

    """
    try:
        # Step 1: Fetch the campaign record from Supabase
        campaign_response = supabase.table("campaigns").select("*").eq("id", campaign_id).single().execute()
        campaign_data = campaign_response.data

        # Step 2: Extract the JSONB rules for easy access in the template
        rules_data = campaign_data.get("evaluation_rules", {})

        # Step 3: Inject everything into the HTML template
        return index_template.TemplateResponse(
            request=request,
            name="campaign_dashboard.html",
            context={
                "request": request,
                "campaign": campaign_data,
                "campaign_id": campaign_id,
                "rules": rules_data,
                "profile_id": profile_id
            }
        )

    except Exception as e:
        return {"status": "error", "message": f"Failed to load campaign: {str(e)}"}


@router.post("/api/analyze-shelf")
async def analyze_shelf(shelf_photo: UploadFile, profile_id: str = Form(...), campaign_id: str = Form(...)):
    """

    AI Shelf Analysis Endpoint - Evaluates a shelf photo against campaign rules.

    This core endpoint receives a shelf photo from the field worker, encodes it, 
    and passes it to the EvaluationAgent (GPT-4o Vision). The agent acts as an 
    expert auditor, comparing the visual reality against the strict text rules 
    fetched from the specific campaign. It calculates a score and itemized feedback,
    which are then persisted to Supabase, linking the audit to both the campaign 
    and the profile.

    """

    # Step 1: Read the physical bytes of the image asynchronously
    image_bytes = await shelf_photo.read()

    # Step 2: Translated the raw bytes into a giant Base64 string for OpenAI
    print("Encoding image for OpenAI 💻")
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Step 3: Fetch the real campaign rules from Supabase
    print(f"Fetching rules for campaign: {campaign_id}")
    import json
    try:
        campaign_result = supabase.table("campaigns").select("evaluation_rules").eq("id", campaign_id).single().execute()

        # Convert the JSON back into a formatted string so the AI can read it easily
        real_rules = json.dumps(campaign_result.data["evaluation_rules"], indent=2)

    except Exception as e:
        return {"status": "error", "message": f"Could not find campaign rules: {str(e)}"}


    # Step 4: Calling the agent
    print("Initializing Evaluation Agent 🤖")
    evaluation_agent = EvaluationAgent()

    # Step 5: Run the AI Engine
    try:
        print("Invoking Evaluation Agent 🤖 (This takes ~5 seconds)...")
        ai_evaluation_result = await evaluation_agent.analyze_shelf_image(base64_image, real_rules)

        print("\n=== 🎯 EVALUATION RESULT ===")
        print(f"Overall Score: {ai_evaluation_result.ai_score}/100")
        print("\nEvaluation Feedback:")
        for detail in ai_evaluation_result.feedbacks:
            status = "✅ PASS" if detail.is_compliant else "❌ FAIL"
            print(f" - {status}: {detail.feedback_text}")

    except Exception as e:
        return {"status": "error", "message": f"AI Engine Failed: {str(e)}"}

    # Step 6: Save the Parent Record (The Overall Score)
    try:
        eval_response = supabase.table("ai_evaluation").insert({
            "profile_id": profile_id,
            "uploaded_image_url": "testing_placeholder_url.png",  # Later, there will be a real storage bucket
            "ai_score": ai_evaluation_result.ai_score,
            "campaign_id": campaign_id
        }).execute()

        # Grab the newly generated UUID assigned by the database
        new_evaluation_id = eval_response.data[0]["id"]

        # Step 7: Bulk-Save the Children Records (The Itemized Feedback)
        feedbacks_to_insert = []
        for detail in ai_evaluation_result.feedbacks:
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
    """
    Evaluation Scorecard - Displays the final results of an AI shelf audit.

    This route fetches the parent `ai_evaluation` record (the overall score) and 
    all associated `ai_evaluation_feedback` records (the itemized checklist) from 
    Supabase. It renders them in a clean scorecard UI for the field worker to review.

    """

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