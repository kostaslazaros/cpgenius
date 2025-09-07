from fastapi import APIRouter

router = APIRouter(tags=["util"])


@router.get("/ping")
def ping():
    """Ping the server to check if it's alive"""
    return {"response": "pong"}
