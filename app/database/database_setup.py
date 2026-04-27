"""
app/database/database_setup.py

This module establishes and configures the connections to the Supabase database.
It securely loads environment credentials and instantiates two global Supabase clients:
1. `supabase`: The standard client and user operations.
2. `supabase_admin`: The elevated "Service Role" client used strictly for admin tasks (like creating worker accounts).
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load the environment variables from your .env file
load_dotenv()

# Securely fetch the credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # FOR ADMIN WORKFLOW

# Sanity check in case there is a problem with the credentials:
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY or not SUPABASE_SECRET_KEY:
    raise ValueError ("🚨Missing Supabase credentials. Check your .env file!")

# Initialize the Admin client (Bypasses all Row Level Security. Never expose this to frontend!)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
print("✅ Successfully connected to Supabase Admin!")

# Initialize the Standard client (Follows Row Level Security, safe for standard operations)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
print("✅ Successfully connected to Supabase Standard Client!")
