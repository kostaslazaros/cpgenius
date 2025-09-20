from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["HTML"])
templates = Jinja2Templates(directory="templates")


@router.get("/bval", response_class=HTMLResponse)
async def bval(request: Request):
    return templates.TemplateResponse("bval.html", {"request": request})


@router.get("/enrichment", response_class=HTMLResponse)
async def enrichment(request: Request):
    return templates.TemplateResponse("enrich.html", {"request": request})


@router.get("/fsel", response_class=HTMLResponse)
async def fsel(request: Request):
    return templates.TemplateResponse("feature_selection.html", {"request": request})


@router.get("/gsel", response_class=HTMLResponse)
async def gsel(request: Request):
    return templates.TemplateResponse("genesel.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/hash", response_class=HTMLResponse)
async def hashtest(request: Request):
    return templates.TemplateResponse("sha_1_file_tester.html", {"request": request})


@router.get("/help", response_class=HTMLResponse)
async def help(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})


@router.get("/dmp", response_class=HTMLResponse)
async def under_development(request: Request):
    return templates.TemplateResponse("dmp.html", {"request": request})


@router.get("/documentation", response_class=HTMLResponse)
async def documentation(request: Request):
    return templates.TemplateResponse("doc.html", {"request": request})
