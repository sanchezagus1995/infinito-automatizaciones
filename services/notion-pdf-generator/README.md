# Generador de PDF desde Notion

Primer servicio del repositorio `infinito-automatizaciones`. Recibe el payload completo de una automatización de Notion, normaliza sus propiedades y selecciona una única variante documental.

## Estado

- Parseo del payload real de Notion.
- Plantilla estándar y variante de seguro externo.
- Respuesta HTML de vista previa.
- Protección opcional mediante `WEBHOOK_TOKEN` y `X-Webhook-Token`.
- Pendiente: render con Playwright, persistencia en Drive y escritura de la URL `PDF nuevo` en Notion.

## Desarrollo

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

La vista previa recibe el mismo JSON que el webhook actual:

```bash
curl -X POST http://localhost:8000/preview \
  -H 'Content-Type: application/json' \
  --data-binary @tests/fixtures/notion_webhook.json \
  --output preview.html
```
