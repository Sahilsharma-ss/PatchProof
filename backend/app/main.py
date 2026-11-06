from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.repositories import router as repositories_router

app = FastAPI(
    title="PR Sentinel API",
    description="AI-powered automated pull request verification",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(repositories_router)


@app.get("/")
def home():
    return {"message": "PR Sentinel API is running"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}