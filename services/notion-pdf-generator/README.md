# Generador de PDF desde Notion

Primer servicio del repositorio `infinito-automatizaciones`. Recibe el payload completo de una automatización de Notion, normaliza sus propiedades y selecciona una única variante documental.

## Estado

- Parseo del payload real de Notion.
- Plantilla estándar y variante de seguro externo.
- Respuesta HTML de vista previa y render PDF con Chromium.
- Alta o actualización idempotente del archivo en Google Drive.
- Escritura del enlace en una propiedad URL de Notion.
- Protección opcional mediante `WEBHOOK_TOKEN` y `X-Webhook-Token`.
- Pendiente: plantillas UVA y validación con credenciales reales en Cloud Run.

## Configuración

El servicio usa Application Default Credentials para Google Drive. La cuenta de servicio de Cloud Run debe tener acceso de edición a las carpetas de destino.

Para una primera prueba segura conviene configurar solo `DRIVE_DEFAULT_FOLDER_ID` con una carpeta separada. Cuando el flujo esté validado, se incorpora el mapa de carpetas definitivo por entidad.

| Variable | Uso |
|---|---|
| `WEBHOOK_TOKEN` | Protege `/preview` y `/generate`; se acepta por encabezado o `?token=`. |
| `NOTION_TOKEN` | Token de la integración autorizada a editar la base. |
| `NOTION_PDF_PROPERTY` | Propiedad URL a actualizar; por defecto `PDF nuevo`. |
| `DRIVE_FOLDER_BY_BANK_JSON` | Mapa JSON de entidad a ID de carpeta. |
| `DRIVE_DEFAULT_FOLDER_ID` | Carpeta alternativa cuando la entidad no está en el mapa. |

Ejemplo del mapa de carpetas:

```json
{"COLUMBIA":"id-carpeta-columbia","CREDITCAR":"id-carpeta-creditcar"}
```

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

La generación definitiva usa el mismo payload:

```bash
curl -X POST 'http://localhost:8000/generate?token=secreto' \
  -H 'Content-Type: application/json' \
  --data-binary @tests/fixtures/notion_webhook.json
```

La respuesta contiene el enlace estable de Drive. Si la operación ya tenía un PDF, se reemplaza el contenido del mismo archivo.
