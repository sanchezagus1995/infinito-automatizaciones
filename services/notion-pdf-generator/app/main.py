from __future__ import annotations

import asyncio
import base64
import hmac
import os
import re
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import ConfigurationError, drive_folder_for, notion_property_name
from .drive_storage import upsert_pdf
from .notion_payload import PayloadError, operation_from_webhook
from .notion_client import set_pdf_url
from .pdf_renderer import render_pdf
from .template_selector import UnsupportedOperation, select_variant

app = FastAPI(title="Infinito · Generador de PDF", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html"]))
styles = Path("static/styles.css").read_text(encoding="utf-8")
logo_data_uri = "data:image/png;base64," + base64.b64encode(
    Path("static/infinito-creditos.png").read_bytes()
).decode("ascii")


def _authorize(header_token: str | None, query_token: str | None = None) -> None:
    expected = os.getenv("WEBHOOK_TOKEN")
    received = header_token or query_token
    if expected and (not received or not hmac.compare_digest(received, expected)):
        raise HTTPException(status_code=401, detail="Token de webhook inválido")


def _document(payload: object) -> tuple[dict, str, str]:
    operation = operation_from_webhook(payload)
    variant = select_variant(operation["bancos"], str(operation["tasa"]))
    html = templates.get_template("nota_operacion.html").render(
        operation=operation,
        variant=variant,
        styles=styles,
        logo_data_uri=logo_data_uri,
    )
    return operation, variant, html


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/preview", response_class=HTMLResponse)
async def preview(request: Request, x_webhook_token: str | None = Header(default=None)) -> HTMLResponse:
    _authorize(x_webhook_token, request.query_params.get("token"))
    try:
        _, _, html = _document(await request.json())
    except (PayloadError, UnsupportedOperation) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return HTMLResponse(html)


@app.post("/generate", response_class=JSONResponse)
async def generate(request: Request, x_webhook_token: str | None = Header(default=None)) -> JSONResponse:
    _authorize(x_webhook_token, request.query_params.get("token"))
    try:
        operation, variant, html = _document(await request.json())
        pdf = await render_pdf(html)
        folder_id = drive_folder_for(operation["banco"])
        safe_operation = re.sub(r"[^A-Za-z0-9_-]+", "-", str(operation["nro_op"])).strip("-") or operation["page_id"]
        filename = f"Nota Infinito - Operación {safe_operation}.pdf"
        drive_url = await asyncio.to_thread(
            upsert_pdf,
            content=pdf,
            filename=filename,
            folder_id=folder_id,
            notion_page_id=operation["page_id"],
        )
        await set_pdf_url(
            page_id=operation["page_id"],
            property_name=notion_property_name(),
            url=drive_url,
        )
    except (PayloadError, UnsupportedOperation) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "status": "ok",
        "operation": operation["nro_op"],
        "variant": variant,
        "drive_url": drive_url,
    })
