from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pricecomp.config import ROOT, Settings, load_settings
from pricecomp.export.drive import get_credentials
from pricecomp.pipeline import compare_items, export_excel, parse_items, upload_excel

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD = 20 * 1024 * 1024

app = FastAPI(title="pricecomp", docs_url=None, redoc_url=None)


@dataclass
class Job:
    status: str = "running"  # running | done | error
    stage: str = "Iniciando"
    done: int = 0
    total: int = 0
    columns: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    usd_to_ars: float | None = None
    excel: Path | None = None
    drive_link: str | None = None
    error: str | None = None


UPLOADS: dict[str, Path] = {}
JOBS: dict[str, Job] = {}


class CompareRequest(BaseModel):
    file_id: str
    margin_min: float | None = None  # porcentaje, ej. 8
    undercut: float | None = None  # porcentaje, ej. 2
    usd_to_ars: float | None = None
    refresh: bool = False


def _settings(req: CompareRequest | None = None) -> Settings:
    s = load_settings()
    if not req:
        return s
    pricing = s.pricing.model_copy(update={
        **({"margin_min": req.margin_min / 100} if req.margin_min is not None else {}),
        **({"undercut": req.undercut / 100} if req.undercut is not None else {}),
    })
    scraping = s.scraping.model_copy(update={"cache_ttl_h": 0} if req.refresh else {})
    return s.model_copy(update={"pricing": pricing, "scraping": scraping, "usd_to_ars": req.usd_to_ars or s.usd_to_ars})


@app.get("/api/defaults")
def defaults() -> dict:
    s = _settings()
    return {"margin_min": s.pricing.margin_min * 100, "undercut": s.pricing.undercut * 100, "fx_rate_type": s.fx_rate_type, "sources": s.sources}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "El archivo supera los 20 MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "El archivo no es un PDF válido.")
    file_id = uuid.uuid4().hex
    path = _settings().cache_dir.parent / "input" / f"{file_id}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    try:
        items = await asyncio.to_thread(parse_items, path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(422, str(exc)) from exc
    UPLOADS[file_id] = path
    return {
        "file_id": file_id,
        "filename": Path(file.filename or "lista.pdf").name,
        "items": [{"name": i.raw_name, "cost": i.cost, "currency": i.currency} for i in items],
    }


@app.post("/api/compare")
async def start_compare(req: CompareRequest) -> dict:
    path = UPLOADS.get(req.file_id)
    if not path:
        raise HTTPException(404, "Archivo no encontrado, volvé a subir el PDF.")
    settings = _settings(req)
    job_id = uuid.uuid4().hex
    job = JOBS[job_id] = Job()

    def progress(stage: str, done: int, total: int) -> None:
        job.stage, job.done, job.total = stage, done, total

    async def run() -> None:
        try:
            items = await asyncio.to_thread(parse_items, path)
            result = await compare_items(items, settings, on_progress=progress)
            job.excel = await asyncio.to_thread(export_excel, result, settings)
            job.columns = list(result.table.columns)
            job.rows = json.loads(result.table.to_json(orient="records"))  # NaN -> null
            job.usd_to_ars = result.usd_to_ars
            job.status = "done"
        except Exception as exc:
            job.status, job.error = "error", str(exc)

    asyncio.create_task(run())
    return {"job_id": job_id}


def _job(job_id: str) -> Job:
    if job_id not in JOBS:
        raise HTTPException(404, "Trabajo no encontrado.")
    return JOBS[job_id]


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    j = _job(job_id)
    out = {"status": j.status, "stage": j.stage, "done": j.done, "total": j.total, "error": j.error}
    if j.status == "done":
        out |= {"columns": j.columns, "rows": j.rows, "usd_to_ars": j.usd_to_ars, "drive_link": j.drive_link}
    return out


@app.get("/api/jobs/{job_id}/excel")
def download_excel(job_id: str) -> FileResponse:
    j = _job(job_id)
    if not j.excel:
        raise HTTPException(409, "El Excel todavía no está listo.")
    return FileResponse(j.excel, filename=j.excel.name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/drive/status")
def drive_status() -> dict:
    s = _settings()
    return {"connected": s.google_token_path.exists(), "has_client_secret": s.google_client_secret_path.exists(), "folder_configured": bool(s.drive_folder_id)}


@app.post("/api/drive/login")
async def drive_login() -> dict:
    s = _settings()
    try:
        await asyncio.to_thread(get_credentials, s.google_client_secret_path, s.google_token_path)  # abre el navegador
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"connected": True}


@app.post("/api/jobs/{job_id}/drive")
async def upload_drive(job_id: str) -> dict:
    j = _job(job_id)
    if not j.excel:
        raise HTTPException(409, "El Excel todavía no está listo.")
    try:
        j.drive_link = await asyncio.to_thread(upload_excel, j.excel, _settings())
    except Exception as exc:
        raise HTTPException(400, f"No se pudo subir a Drive: {exc}") from exc
    return {"drive_link": j.drive_link}


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
