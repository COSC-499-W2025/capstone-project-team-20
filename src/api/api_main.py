from fastapi import FastAPI
from src.api.routes import router
"""Creating an api_main for now. once we get a front end (Or once it becomes API
only, we can delete this and have this in main.) Requirement 31"""

app = FastAPI(title="Project Analyzer API")
app.include_router(router)

