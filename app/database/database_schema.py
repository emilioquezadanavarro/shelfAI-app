"""
app/database/database_schema.py

This module defines the Pydantic schemas (data models) for our FastAPI application.

Pydantic is used to strictly enforce what data is allowed into our API endpoints. 
By defining these schemas, we guarantee that the frontend must provide exactly 
the data we require (in the right format) before the application even attempts 
to communicate with the Supabase database.

"""
from pydantic import BaseModel, Field


class CreateProfile(BaseModel):
    """
    Schema for creating a new user profile / field worker.
    
    This class inherits from BaseModel, allowing FastAPI to automatically parse
    incoming JSON requests into this Python object. The Field validation ensures 
    clear documentation for OpenAPI (Swagger) and enforces data presence.

    """
    
    # 'first_name' must exactly match the column name in our Supabase `profiles` table.
    # The '...' inside Field(...) means this field is strictly required.
    first_name: str = Field(..., description="First name of the employee using the app")
    
    # 'last_name' must exactly match the column name in our Supabase `profiles` table.
    last_name: str = Field(..., description="Last name of the employee using the app")
