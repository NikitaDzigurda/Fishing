from time import sleep
from backend.celery_app import celery_app


@celery_app.task(name="backend.tasks.add")
def add(x, y):
    sleep(1)
    return x + y


@celery_app.task(name="backend.tasks.sample_long_task")
def sample_long_task(n: int = 5):
    for i in range(n):
        sleep(1)
    return f"done: {n}"
