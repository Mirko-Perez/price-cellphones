from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class PricingConfig(BaseModel):
    margin_min: float = 0.08
    undercut: float = 0.02
    cheap_threshold: float = 0.10
    expensive_threshold: float = 0.10


class MatchingConfig(BaseModel):
    min_score: int = 80
    max_offers_per_source: int = 10


class ScrapingConfig(BaseModel):
    concurrency: int = 4
    timeout_s: int = 20
    cache_ttl_h: int = 12


class Settings(BaseSettings):
    """Secretos por .env; parámetros de negocio por config/settings.yaml."""

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    google_client_secret_path: Path = ROOT / "client_secret.json"  # cliente OAuth "Aplicación de escritorio"
    google_token_path: Path = ROOT / "token.json"  # se genera con `pricecomp drive-login`
    drive_folder_id: str = ""
    usd_to_ars: float | None = None  # si no se define, se consulta fx_rate_type online
    fx_rate_type: str = "blue"  # blue | oficial | bolsa (MEP) | contadoconliqui

    sources: list[str] = ["personal", "movistar"]
    pricing: PricingConfig = PricingConfig()
    matching: MatchingConfig = MatchingConfig()
    scraping: ScrapingConfig = ScrapingConfig()

    cache_dir: Path = ROOT / "data" / "raw"
    output_dir: Path = ROOT / "data" / "output"


def load_settings(path: Path = ROOT / "config" / "settings.yaml") -> Settings:
    load_dotenv(ROOT / ".env")  # expone también MELI_* a los scrapers
    overrides = yaml.safe_load(path.read_text()) if path.exists() else {}
    return Settings(**(overrides or {}))
