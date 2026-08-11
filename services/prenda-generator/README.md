# Prenda Generator

Servicio independiente para precargar datos de una operación desde Notion y completar la plantilla PDF oficial de cada entidad.

## Primera entidad: Banco Galicia

- Lee la operación mediante `GET /prenda/{page_id}`.
- Precarga `tasa` (Tradicional/UVA) y `CUIL CUIT`, además de los campos comunes.
- Pide solamente los datos documentales que no están en Notion.
- Completa los 51 campos AcroForm del PDF oficial.
- Imprime `Bruto` en `monto uva` únicamente cuando `tasa` contiene `UVA`.
- Descarga un PDF editable para hacer la primera validación de impresión.

## Variables

Copiar `.env.example` y configurar:

- `NOTION_TOKEN`: integración con acceso a la base de operaciones.
- `FORM_TOKEN`: secreto incluido en el enlace del formulario. Si se omite, la validación queda desactivada para desarrollo local.

## Desarrollo

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La URL de prueba es:

```text
http://localhost:8000/prenda/PAGE_ID?token=FORM_TOKEN
```

## Próximas etapas

1. Validar una impresión Galicia con datos reales.
2. Guardar el PDF en Drive y escribir su URL en Notion.
3. Incorporar ICBC reutilizando el mismo formulario común y su propia plantilla.
