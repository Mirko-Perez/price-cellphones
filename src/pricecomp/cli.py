from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer

from pricecomp.config import load_settings
from pricecomp.export.drive import get_credentials
from pricecomp.ingestion.registry import get_parser
from pricecomp.pipeline import run_pipeline

app = typer.Typer(help="Comparador de precios de celulares: proveedor vs mercado.", no_args_is_help=True)


@app.command()
def parse(pdf: Path, parser: str = "lista_dolares") -> None:
    """Muestra los equipos/precios que se extraen del PDF (para validar el parser)."""
    for it in get_parser(parser).parse(pdf):
        typer.echo(f"{it.raw_name!r:60} {it.cost:>12,.2f} {it.currency}  -> {it.phone.query}")


@app.command("drive-login")
def drive_login() -> None:
    """Inicia sesión con tu cuenta de Google (una sola vez) y guarda el token."""
    s = load_settings()
    get_credentials(s.google_client_secret_path, s.google_token_path)
    typer.echo(f"Listo, token guardado en {s.google_token_path}")


@app.command()
def run(
    pdf: Path,
    parser: str = "lista_dolares",
    source: Annotated[Optional[list[str]], typer.Option("--source", "-s", help="Limitar fuentes")] = None,
    no_upload: bool = typer.Option(False, "--no-upload", help="No subir a Drive"),
) -> None:
    """Pipeline completo: PDF -> scraping -> tabla -> Excel -> Drive."""
    out, link = asyncio.run(run_pipeline(pdf, load_settings(), parser, not no_upload, source))
    typer.echo(f"Excel: {out}")
    if link:
        typer.echo(f"Drive: {link}")


if __name__ == "__main__":
    app()
