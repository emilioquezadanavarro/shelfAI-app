"""
app/database/database_setup.py

This module establishes and configures the connection to the Supabase database.
It securely loads the environment credentials (URL and Service Key) and instantiates 
a global Supabase client. This client can be imported throughout the FastAPI application
(by routes, services, or AI agents) to perform CRUD operations without re-initializing 
the connection each time.

"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load the environment variables from your .env file
load_dotenv()

# Securely fetch the credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Sanity check in case there is a problem with the credentials:
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError ("🚨Missing Supabase credentials. Check your .env file!")

# Initialize the official connection client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
print("✅ Successfully connected to Supabase!")
