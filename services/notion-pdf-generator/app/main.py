from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .notion_payload import PayloadError, operation_from_webhook
from .template_selector import UnsupportedOperation, select_variant

app = FastAPI(title="Infinito · Generador de PDF", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html"]))


def _authorize(token: str | None) -> None:
    expected = os.getenv("WEBHOOK_TOKEN")
    if expected and (not token or not hmac.compare_digest(token, expected)):
        raise HTTPException(status_code=401, detail="Token de webhook inválido")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/preview", response_class=HTMLResponse)
async def preview(request: Request, x_webhook_token: str | None = Header(default=None)) -> HTMLResponse:
    _authorize(x_webhook_token)
    try:
        operation = operation_from_webhook(await request.json())
        variant = select_variant(operation["bancos"], str(operation["tasa"]))
    except (PayloadError, UnsupportedOperation) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if variant.startswith("uva_"):
        raise HTTPException(status_code=501, detail=f"La plantilla {variant} todavía no fue incorporada")
    html = templates.get_template("nota_operacion.html").render(operation=operation, variant=variant)
    return HTMLResponse(html)
