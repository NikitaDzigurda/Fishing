from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.settings import settings
from backend.celery_app import celery_app


app = FastAPI(title="Academic Profile Backend", version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.ALLOWED_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


class TestResponse(BaseModel):
	msg: str
	env: str | None = None


@app.get("/api/v1/health", response_model=TestResponse)
async def healthcheck():
	return TestResponse(msg="ok", env="development" if settings.DEBUG else "production")


@app.get("/api/v1/test", response_model=TestResponse)
async def test():
	return TestResponse(msg="Hello from Academic Profile Backend!", env=settings.HOST)


@app.post("/api/v1/task")
def trigger_task():
	res = celery_app.send_task("backend.tasks.add", args=(2, 3))
	return {"task_id": res.id}


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
