from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

try:
    import markdown
except Exception:
    markdown = None

from app.routers.html import templates

router = APIRouter(tags=["Documentation"])

DOCS_DIR = Path("docs")


@router.get("/documentation", response_class=HTMLResponse)
async def docs_index(request: Request):
    # default page
    return await docs_page(request, "overview")


@router.get("/documentation/{page_name}", response_class=HTMLResponse)
async def docs_page(request: Request, page_name: str):
    if markdown is None:
        raise HTTPException(
            500,
            detail="Python 'markdown' package is required to render docs. Please install it.",
        )

    md_path = DOCS_DIR / f"{page_name}.md"
    if not md_path.exists():
        raise HTTPException(404, detail="Documentation page not found")

    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to read documentation file: {e}")

    # Use Markdown object to extract generated TOC HTML from the 'toc' extension
    # Configure Markdown: disable the toc permalink so headings don't get a pilcrow (¶)
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "codehilite"],
        extension_configs={"toc": {"permalink": False}},
    )
    html = md.convert(text)
    toc_html = getattr(md, "toc", "")
    # Build pages list from files in DOCS_DIR to populate sidebar
    pages = []
    try:
        for p in sorted(DOCS_DIR.glob("*.md")):
            # slug is filename without suffix
            slug = p.stem
            title = slug.replace("-", " ").replace("_", " ").title()
            # try to read first H1 heading for nicer title
            try:
                with p.open(encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line.startswith("# "):
                            title = line.lstrip("# ").strip()
                            break
            except Exception:
                pass
            pages.append({"slug": slug, "title": title})
    except Exception:
        pages = []

    return templates.TemplateResponse(
        "doc.html",
        {
            "request": request,
            "content": html,
            "toc": toc_html,
            "pages": pages,
            "current_page": page_name,
            "title": page_name.replace("-", " ").title(),
        },
    )
