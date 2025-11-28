from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.settings import settings
from backend.celery_app import celery_app
from backend.handlers.auth import router as auth_router
from backend.handlers.authors import router as profile_router
from backend.handlers.admin import router as admin_router


app = FastAPI(title="Academic Profile Backend", version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.ALLOWED_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)



app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(admin_router)


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
