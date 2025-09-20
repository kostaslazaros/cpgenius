from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.check_before_run import check
from app.routers.bval_router import router as bval_router
from app.routers.dmp_router import router as dmp_router
from app.routers.docs import router as docs_router
from app.routers.fs_router import router as fs_router
from app.routers.html import router as htmlrouter
from app.routers.util import router as utilrouter

check()


app = FastAPI(
    title="cpgenius API",
    description="API for varius bioinformatics tasks",
    version="1.0.1",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(utilrouter)
app.include_router(htmlrouter)
app.include_router(docs_router)
app.include_router(bval_router)
app.include_router(fs_router)
app.include_router(dmp_router)
