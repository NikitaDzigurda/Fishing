from celery import Celery
from backend.settings import settings


def make_celery() -> Celery:
    celery = Celery(
        "backend",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )
    # Optional: configure Celery here (task serialization, timezone etc.)
    celery.conf.update(task_track_started=True, accept_content=["json"], task_serializer="json")
    return celery


celery_app = make_celery()
