from __future__ import annotations

from io import BytesIO
import base64
import hmac
import hashlib
import json
import os
import re
import time

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .notion import NotionError, fetch_page, operation_from_page, set_page_url
from .pdf_form import fill_galicia, values_from_form


app = FastAPI(title="Infinito · Generador de prendas", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html"]))


def _authorize(token: str | None) -> None:
    expected = os.getenv("FORM_TOKEN")
    if expected and (not token or not hmac.compare_digest(token, expected)):
        raise HTTPException(status_code=401, detail="Enlace de formulario inválido")


def _session_token(page_id: str, *, now: int | None = None) -> str:
    secret = os.getenv("FORM_TOKEN")
    if not secret:
        raise HTTPException(status_code=500, detail="Falta configurar FORM_TOKEN")
    ttl = int(os.getenv("FORM_LINK_TTL_SECONDS", "86400"))
    payload = {"page_id": page_id, "exp": (now or int(time.time())) + ttl}
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _authorize_session(session: str | None, page_id: str, *, now: int | None = None) -> None:
    secret = os.getenv("FORM_TOKEN")
    if not secret or not session or "." not in session:
        raise HTTPException(status_code=401, detail="Enlace de formulario inválido")
    encoded, received_signature = session.rsplit(".", 1)
    expected_signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Enlace de formulario inválido")
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Enlace de formulario inválido")
    current_time = now or int(time.time())
    if payload.get("page_id") != page_id or int(payload.get("exp", 0)) < current_time:
        raise HTTPException(status_code=401, detail="El enlace del formulario venció")


def _page_id_from_webhook(payload: object) -> str:
    if isinstance(payload, list):
        if len(payload) != 1:
            raise HTTPException(status_code=422, detail="Se esperaba una única operación")
        payload = payload[0]
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="El webhook no contiene una operación")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    page_id = data.get("id") if isinstance(data, dict) else None
    if not page_id:
        raise HTTPException(status_code=422, detail="El webhook no contiene data.id")
    return str(page_id)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request) -> dict[str, str]:
    _authorize(request.query_params.get("token"))
    page_id = _page_id_from_webhook(await request.json())
    try:
        operation = operation_from_page(await fetch_page(page_id))
        banks = {_bank.upper() for _bank in operation["bancos"]}
        if "GALICIA" not in banks:
            raise HTTPException(status_code=422, detail="La operación no corresponde a Banco Galicia")
        session = _session_token(page_id)
        base_url = os.getenv("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
        form_url = f"{base_url}/prenda/{page_id}?session={session}"
        property_name = os.getenv("FORM_URL_PROPERTY", "Formulario prenda")
        await set_page_url(page_id=page_id, property_name=property_name, url=form_url)
    except NotionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok", "page_id": page_id, "form_url": form_url}


@app.get("/prenda/{page_id}", response_class=HTMLResponse)
async def form(request: Request, page_id: str) -> HTMLResponse:
    session = request.query_params.get("session")
    token = request.query_params.get("token")
    if session:
        _authorize_session(session, page_id)
    else:
        _authorize(token)
    try:
        operation = operation_from_page(await fetch_page(page_id))
    except NotionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    banks = {_bank.upper() for _bank in operation["bancos"]}
    if "GALICIA" not in banks:
        raise HTTPException(status_code=422, detail="Esta primera versión admite solamente Banco Galicia")
    return HTMLResponse(templates.get_template("form.html").render(
        request=request,
        operation=operation,
        token=token or "",
        session=session or "",
    ))


@app.post("/prenda/{page_id}/generar")
async def generate(page_id: str, request: Request) -> StreamingResponse:
    form_data = dict(await request.form())
    session = str(form_data.pop("session", ""))
    if session:
        _authorize_session(session, page_id)
    else:
        _authorize(str(form_data.pop("token", "")))
    form_data["page_id"] = page_id
    try:
        pdf = fill_galicia(values_from_form(form_data))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", form_data.get("nombre", "prenda")).strip("-")
    headers = {"Content-Disposition": f'attachment; filename="Prenda-Galicia-{safe_name}.pdf"'}
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf", headers=headers)
