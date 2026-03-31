"""
app/routes/routes.py

Defines the HTTP endpoints for the application UI.
It sets up a FastAPI APIRouter and configures Jinja2 templates to render
the graphical interface, mapping the root ("/") path to the index.html template.

"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import os

# Initialize the router
router = APIRouter(
    tags=["Index"]
)

# Templates instance
index_template = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

@router.get("/")
async def index(request: Request):

    return index_template.TemplateResponse(request=request, name="index.html")






