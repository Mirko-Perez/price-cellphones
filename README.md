# pricecomp

Compara el costo del proveedor (PDF de WhatsApp) contra precios de mercado (MercadoLibre, Personal, Movistar) y genera una tabla con precio sugerido y margen, subida a Google Drive.

```
PDF proveedor → equipos/precios → scraping → tabla comparativa → Excel → Drive
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env   # DRIVE_FOLDER_ID, opcional USD_TO_ARS
```

### Login con Google (una sola vez)
1. console.cloud.google.com → crear proyecto → *APIs y servicios* → habilitar **Google Drive API**.
2. *Pantalla de consentimiento OAuth*: tipo Externo, agregar tu mail como usuario de prueba.
3. *Credenciales* → Crear ID de cliente OAuth → **Aplicación de escritorio** → descargar JSON y guardarlo como `client_secret.json` en la raíz.
4. `pricecomp drive-login` abre el navegador, iniciás sesión y queda `token.json` (ambos en .gitignore).

## Uso
```bash
pricecomp parse data/input/lista.pdf                 # validar qué extrae del PDF
pricecomp run data/input/lista.pdf --no-upload       # genera data/output/comparativa_YYYYMMDD.xlsx
pricecomp run data/input/lista.pdf -s mercadolibre   # solo una fuente
pricecomp run data/input/lista.pdf                   # + sube a Drive
```
Reglas de márgenes/umbrales: `config/settings.yaml`.

## Extender
- **Nueva fuente web**: subclase de `scrapers/base.Scraper` (o `PlaywrightScraper` con selectores) y alta en `scrapers/registry.py` + `settings.yaml`.
- **Nuevo formato de proveedor**: clase con `parse(path)` en `ingestion/` y alta en `ingestion/registry.py`; usar `--parser`.
- **Nuevo destino**: módulo en `export/` y llamarlo desde `pipeline.py`.

## Estado de las fuentes
| Fuente | Método | Estado |
|---|---|---|
| Lista proveedor (PDF en USD) | `CategoryColumnPdfParser`, 2 columnas, solo categorías `CELULARES*` | OK (51 equipos) |
| Personal | HTTP, JSON embebido en el listado paginado (catálogo completo, 98 equipos) | OK |
| Movistar | Playwright, una página por marca con scroll lazy | OK |
| MercadoLibre | API oficial con token (`MELI_CLIENT_ID/SECRET`) | Desactivada por ahora (fuera de `sources`): la API da 403 sin token y el sitio bloquea navegadores automatizados |
| Drive | OAuth con tu cuenta | Requiere `client_secret.json` y `pricecomp drive-login` |

Personal y Movistar son precios de operadoras (con descuentos/financiación propios): sirven de referencia pero suelen estar bien arriba del mercado abierto. MercadoLibre aporta el precio "calle".

Dólar: se usa `USD_TO_ARS` si está definido; si no, se consulta dolarapi.com según `fx_rate_type` (default `blue`).
