# Prenda Generator

Servicio independiente para precargar datos de una operación desde Notion y completar la plantilla PDF oficial de cada entidad.

## Primera entidad: Banco Galicia

- Recibe el botón de Notion mediante `POST /webhook?token=FORM_TOKEN`.
- Crea un enlace firmado y temporal y lo guarda solamente en la operación solicitada.
- Lee la operación mediante `GET /prenda/{page_id}?session=...`.
- Precarga `tasa` (Tradicional/UVA) y `CUIL CUIT`, además de los campos comunes.
- Pide solamente los datos documentales que no están en Notion.
- Completa los 51 campos AcroForm del PDF oficial.
- Imprime `Bruto` en `monto uva` únicamente cuando `tasa` contiene `UVA`.
- Descarga un PDF editable para hacer la primera validación de impresión.

## Variables

Copiar `.env.example` y configurar:

- `NOTION_TOKEN`: integración con acceso a la base de operaciones.
- `FORM_TOKEN`: secreto maestro usado para autenticar el webhook y firmar enlaces temporales. No se guarda en Notion.
- `PUBLIC_BASE_URL`: URL pública de Cloud Run, sin `/` final.
- `FORM_URL_PROPERTY`: propiedad URL de Notion donde se guarda el enlace. Por defecto, `Formulario prenda`.
- `FORM_LINK_TTL_SECONDS`: duración del enlace temporal. Por defecto, 86400 segundos (24 horas).

## Desarrollo

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

El webhook que debe usar el botón de Notion es:

```text
https://SERVICIO/webhook?token=FORM_TOKEN
```

## Próximas etapas

1. Validar una impresión Galicia con datos reales.
2. Guardar el PDF en Drive y escribir su URL en Notion.
3. Incorporar ICBC reutilizando el mismo formulario común y su propia plantilla.
