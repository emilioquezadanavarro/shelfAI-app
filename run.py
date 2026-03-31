"""
run.py

Entry point for the ShelfAI application.
This file is responsible for launching the FastAPI server using Uvicorn.
It reads the port number from the environment and starts the app factory.

"""
import uvicorn
import os
from app import create_app

# Create app instance
app = create_app()

# FastAPI Run Block
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("run:app", host="127.0.0.1", port=port, reload=False)
