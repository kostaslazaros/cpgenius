from fastapi import HTTPException

from app.celery_tasks.celery import app as celery_app
from app.schemas import TaskStatus


def get_celery_task_status(task_id: str):
    try:
        task_result = celery_app.AsyncResult(task_id)

        status_response = TaskStatus(
            task_id=task_id, status=task_result.status, result=task_result.info
        )

        if task_result.ready():
            if task_result.successful():
                status_response.result = task_result.result
            else:
                status_response.error = str(task_result.info)

        return status_response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking task status: {str(e)}"
        )
