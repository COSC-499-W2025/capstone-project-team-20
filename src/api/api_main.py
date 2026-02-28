from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

app = FastAPI(title="Project Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5175",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)