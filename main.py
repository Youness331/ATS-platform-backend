from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app = FastAPI(title="Matchline ATS")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"active_page": "home"},
    )


@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="analyze.html",
        context={"active_page": "analyze", "submitted": False},
    )


@app.post("/analyze", response_class=HTMLResponse)
async def submit_analysis(
    request: Request,
    job_description: Annotated[str, Form()] = "",
    resume: UploadFile | None = File(default=None),
):
    return templates.TemplateResponse(
        request=request,
        name="analyze.html",
        context={
            "active_page": "analyze",
            "submitted": True,
            "job_description": job_description,
            "resume_name": resume.filename if resume else None,
        },
    )
