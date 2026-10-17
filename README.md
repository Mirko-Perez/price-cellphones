# pricecomp

Compara el costo de tu proveedor (lista en PDF) contra los precios de mercado (Personal y Movistar; MercadoLibre desactivada por ahora) y arma una tabla con precio sugerido y margen por equipo. Se usa desde una interfaz web local o desde la consola, y el resultado puede subirse a Google Drive.

```
PDF proveedor → equipos/precios → scraping de tiendas → tabla comparativa → Excel → Drive
```

## Instalación
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium     # lo usa el scraper de Movistar
cp .env.example .env            # completar DRIVE_FOLDER_ID (opcional: USD_TO_ARS)
```

### Conectar Google Drive (una sola vez)
1. En console.cloud.google.com creá un proyecto y habilitá la **Google Drive API**.
2. *Pantalla de consentimiento OAuth*: tipo Externo y agregá tu mail como usuario de prueba.
3. *Credenciales* → Crear ID de cliente OAuth → **Aplicación de escritorio** → descargá el JSON y guardalo como `client_secret.json` en la raíz del proyecto.
4. Iniciá sesión con `pricecomp drive-login` (o con el botón **Conectar con Google** de la interfaz). Queda guardado `token.json`.

`client_secret.json`, `token.json` y `.env` están en `.gitignore`; no los subas al repo.

## Uso: interfaz web
```bash
cd price-cellphones && source .venv/bin/activate && pricecomp ui
```
Abre `http://127.0.0.1:8000` (solo accesible desde tu equipo). Cerrar con `Ctrl+C`. Opciones: `--port 8001`, `--no-browser`.

1. Arrastrá el PDF del proveedor (o hacé clic para elegirlo). Muestra cuántos celulares detectó.
2. Opcional, en *Ajustes*: margen mínimo, cuánto por debajo de la mediana apuntar, dólar manual y actualizar precios ignorando la caché.
3. **Comparar precios** (la primera vez tarda cerca de un minuto).
4. En los resultados: resumen, tabla con búsqueda, filtros por estado y orden por columna, **Descargar Excel** y **Subir a Drive**.

La tabla en pantalla oculta algunas columnas por espacio; el Excel las trae todas.

## Uso: consola
```bash
pricecomp parse data/input/lista.pdf              # ver qué equipos y precios lee del PDF
pricecomp run data/input/lista.pdf --no-upload    # genera data/output/comparativa_YYYYMMDD.xlsx
pricecomp run data/input/lista.pdf                # lo anterior + sube a Drive
pricecomp run data/input/lista.pdf -s personal    # limitar a una fuente
pricecomp drive-login                             # login con Google
```
`parse` y `run` aceptan `--parser <nombre>` (por defecto `lista_dolares`).

## Configuración
- **`config/settings.yaml`**: fuentes activas (`sources`), margen mínimo (`margin_min`, 8%), cuánto bajar de la mediana (`undercut`, 2%), umbrales de "caro/barato", score de matching, concurrencia y duración de la caché (`cache_ttl_h`, 12 h).
- **`.env`**: `DRIVE_FOLDER_ID`, `USD_TO_ARS` (opcional), `GOOGLE_CLIENT_SECRET_PATH`, `MELI_CLIENT_ID` / `MELI_CLIENT_SECRET` (solo MercadoLibre).
- **Dólar**: se usa `USD_TO_ARS` si está definido; si no, se consulta dolarapi.com según `fx_rate_type` (por defecto `blue`).

### Cómo se calcula cada fila
- Costo en pesos = costo del PDF × dólar.
- Referencia de mercado = mediana de las ofertas que coinciden con el equipo (misma marca/modelo/almacenamiento).
- Precio sugerido = el mayor entre `costo × (1 + margen mínimo)` y `mediana × (1 − undercut)`.
- Estado: **Competitivo**, **Caro**, **Barato (margen de sobra)**, **Mercado bajo el margen mínimo** o **Sin datos de mercado**.

## Estado de las fuentes
| Fuente | Método | Estado |
|---|---|---|
| Lista del proveedor (PDF en USD) | `CategoryColumnPdfParser`: 2 columnas, solo categorías `CELULARES*` | OK (51 equipos) |
| Personal | HTTP, JSON embebido en el listado paginado (catálogo completo, 98 equipos) | OK |
| Movistar | Playwright, una página por marca con scroll lazy (~1 min) | OK |
| MercadoLibre | API oficial con token | Desactivada: la API da 403 sin token y el sitio bloquea navegadores automatizados |
| Google Drive | OAuth con tu cuenta | Requiere `client_secret.json` y login |

Personal y Movistar son precios de operadoras, con descuentos y financiación propios: sirven de referencia pero suelen estar bien por encima del mercado abierto. Cerca de la mitad de los equipos de la lista no se venden en esas tiendas y quedan "Sin datos de mercado"; MercadoLibre cubriría esa brecha.

Los precios de las tiendas se guardan 12 horas en `data/raw/`. Para forzar datos nuevos, usá la opción de la interfaz o borrá esos archivos.

## Estructura
```
src/pricecomp/
  ingestion/       PDF → SupplierItem (parsers por proveedor, registry.py)
  normalization/   marca/modelo/almacenamiento y matching de ofertas
  scrapers/        una clase por fuente (registry.py); CatalogScraper baja el catálogo completo una vez
  analysis/        precio sugerido, margen, estado y tabla comparativa
  export/          Excel y Google Drive
  web/             interfaz web (FastAPI + una página HTML)
  pipeline.py      parse_items → compare_items → export_excel → upload_excel
  cli.py           comandos de consola
tests/             pytest (matcher, precios, scrapers, API web)
```

## Extender
- **Nueva fuente web**: subclase de `scrapers/base.Scraper` (búsqueda por equipo) o `CatalogScraper` (catálogo completo) y alta en `scrapers/registry.py` + `sources` en `settings.yaml`.
- **Nuevo formato de proveedor**: clase con `parse(path)` en `ingestion/` y alta en `ingestion/registry.py`.
- **Nuevo destino**: módulo en `export/` y llamarlo desde `pipeline.py`.

## Tests
```bash
pytest
```
