"""
app/__init__.py

Implements the FastAPI Application Factory Pattern.
This module is responsible for initializing the core FastAPI instance,
loading environment variables, and configuring/registering the application's routers.

"""
from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes.routes import router

# Load .env file (For API keys!)
load_dotenv()

def create_app():

    # Initialize FastAPI
    app = FastAPI(
        title="ShelfAI App",
        description="Core backend for retail companies shelf comparison"
    )

    print(" === ShelfAI has been started === ")

    # # Configure Database
    # basedir = os.path.abspath(os.path.dirname(__file__))
    # db_path = os.path.join(basedir, '../resonate.db')
    #
    # app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app.config['SECRET_KEY'] = 'a_very_secret_key_for_flashing_messages'

    # # Link the database and the app.
    # db.init_app(app)

    # Register routes
    app.include_router(router)

    return app