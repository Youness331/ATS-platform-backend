from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app = FastAPI(title="Matchline ATS")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

N8N_WEBHOOK_URL = "http://localhost:5678/webhook/ats-resume-analysis"
analyses: dict[str, dict] = {}


class AnalysisResult(BaseModel):
    score: int = Field(ge=0, le=100)
    verdict: str
    summary: str
    strengths: list[str] = []
    gaps: list[str] = []
    recommendations: list[str] = []
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []


class AnalysisCallback(BaseModel):
    analysis_id: UUID
    status: str = "completed"
    result: AnalysisResult


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


@app.get("/results/{analysis_id}", response_class=HTMLResponse)
async def results_page(request: Request, analysis_id: UUID):
    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={"active_page": "results", "analysis_id": str(analysis_id)},
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


@app.post("/api/analyses")
async def create_analysis(
    job_description: Annotated[str, Form()],
    resume: Annotated[UploadFile, File()],
):
    """Queue a resume and job description in the n8n analysis workflow."""
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="job_description is required")
    if not resume.filename:
        raise HTTPException(status_code=422, detail="resume is required")

    allowed_types = {"application/pdf"}
    if resume.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Upload a PDF resume")

    analysis_id = uuid4()
    resume_bytes = await resume.read()
    analyses[str(analysis_id)] = {
        "analysis_id": str(analysis_id),
        "status": "queued",
        "filename": resume.filename,
        "result": None,
    }

    form_data = {
        "analysis_id": str(analysis_id),
        "job_description": job_description,
    }
    files = {
        "resume": (
            resume.filename,
            resume_bytes,
            resume.content_type or "application/octet-stream",
        )
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(N8N_WEBHOOK_URL, data=form_data, files=files)
            response.raise_for_status()
    except httpx.HTTPError as error:
        analyses[str(analysis_id)]["status"] = "failed"
        raise HTTPException(status_code=502, detail="Could not queue analysis in n8n") from error

    analyses[str(analysis_id)]["status"] = "processing"
    return JSONResponse(
        status_code=202,
        content={
            "analysis_id": str(analysis_id),
            "status": "processing",
            "status_url": f"/api/analyses/{analysis_id}",
        },
    )


@app.post("/api/analyses/{analysis_id}/result")
async def receive_analysis_result(analysis_id: UUID, callback: AnalysisCallback):
    """Receive the normalized result from the n8n callback node."""
    analysis = analyses.get(str(analysis_id))
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if callback.analysis_id != analysis_id:
        raise HTTPException(status_code=400, detail="analysis_id does not match callback URL")

    analysis["status"] = callback.status
    analysis["result"] = callback.result.model_dump()
    return {"ok": True, "analysis_id": str(analysis_id), "status": analysis["status"]}


@app.get("/api/analyses/{analysis_id}")
async def get_analysis(analysis_id: UUID):
    """Poll the current analysis status or retrieve its completed result."""
    analysis = analyses.get(str(analysis_id))
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis
