import os

from celery import Celery
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend_url = os.getenv("CELERY_BACKEND_URL", broker_url)

app = Celery(
    "celery_tasks",
    broker=broker_url,
    backend=backend_url,
    include=[
        "app.celery_tasks.bval_tasks",
        "app.celery_tasks.fs_tasks",
        "app.celery_tasks.dmp_tasks",
        "app.celery_tasks.task_analyze_bvals_csv",
    ],
)

app.conf.update(
    timezone="Europe/Athens",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
