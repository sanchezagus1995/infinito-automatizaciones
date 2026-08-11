from __future__ import annotations

from io import BytesIO
import hmac
import os
import re

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .notion import NotionError, fetch_page, operation_from_page
from .pdf_form import fill_galicia, values_from_form


app = FastAPI(title="Infinito · Generador de prendas", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html"]))


def _authorize(token: str | None) -> None:
    expected = os.getenv("FORM_TOKEN")
    if expected and (not token or not hmac.compare_digest(token, expected)):
        raise HTTPException(status_code=401, detail="Enlace de formulario inválido")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/prenda/{page_id}", response_class=HTMLResponse)
async def form(request: Request, page_id: str) -> HTMLResponse:
    token = request.query_params.get("token")
    _authorize(token)
    try:
        operation = operation_from_page(await fetch_page(page_id))
    except NotionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    banks = {_bank.upper() for _bank in operation["bancos"]}
    if "GALICIA" not in banks:
        raise HTTPException(status_code=422, detail="Esta primera versión admite solamente Banco Galicia")
    return HTMLResponse(templates.get_template("form.html").render(request=request, operation=operation, token=token or ""))


@app.post("/prenda/{page_id}/generar")
async def generate(page_id: str, request: Request) -> StreamingResponse:
    form_data = dict(await request.form())
    _authorize(str(form_data.pop("token", "")))
    form_data["page_id"] = page_id
    try:
        pdf = fill_galicia(values_from_form(form_data))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", form_data.get("nombre", "prenda")).strip("-")
    headers = {"Content-Disposition": f'attachment; filename="Prenda-Galicia-{safe_name}.pdf"'}
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf", headers=headers)
