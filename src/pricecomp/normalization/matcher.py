from __future__ import annotations

import re

from rapidfuzz import fuzz

from pricecomp.domain.models import Phone

BRANDS = ["samsung", "apple", "iphone", "motorola", "xiaomi", "redmi", "poco", "realme", "zte", "tcl", "nokia", "oppo", "honor", "infinix", "tecno"]

_RAM_STORAGE = re.compile(r"(\d{1,2})\s*/\s*(\d{2,4})\s*(gb|tb)?", re.I)
_STORAGE = re.compile(r"(\d{1,4})\s*(gb|tb)\b", re.I)
_MODEL_TOKENS = re.compile(r"[a-z]*\d+[a-z]*|ultra|plus|pro|max|fe|lite|mini|\+")
_GLUED_SUFFIX = re.compile(r"(\d)(fe|ultra|plus|pro|max)\b", re.I)
_NOISE = re.compile(r"\b(celular|smartphone|libre|dual sim|5g|4g|lte|nuevo|sellado|liberado|nacional)\b", re.I)


def _to_gb(value: int, unit: str | None) -> int:
    return value * 1024 if unit and unit.lower() == "tb" else value


def parse_phone(name: str) -> Phone:
    """Extrae marca/modelo/almacenamiento/RAM de un nombre libre ("Galaxy S24 8/256GB")."""
    text = re.sub(r"[()]", " ", name).strip()
    text = _GLUED_SUFFIX.sub(r"\1 \2", text)  # "S25FE" -> "S25 FE"
    ram = storage = None

    if m := _RAM_STORAGE.search(text):
        ram, storage = int(m.group(1)), _to_gb(int(m.group(2)), m.group(3))
        text = text.replace(m.group(0), " ")
    elif m := _STORAGE.search(text):
        storage = _to_gb(int(m.group(1)), m.group(2))
        text = text.replace(m.group(0), " ")

    text = _NOISE.sub(" ", text)
    words = text.split()
    brand = next((w.lower() for w in words if w.lower() in BRANDS), None)
    if brand == "iphone":  # "iPhone 15" -> marca apple, modelo "iPhone 15"
        brand = "apple"
    elif brand:
        words = [w for w in words if w.lower() != brand]
    model = " ".join(words).strip(" -,/") or name.strip()
    return Phone(brand=brand, model=model, storage_gb=storage, ram_gb=ram)


def offer_matches(phone: Phone, title: str, min_score: int = 80) -> bool:
    """True si el título de una oferta corresponde al equipo buscado."""
    other = parse_phone(title)
    if phone.storage_gb and other.storage_gb and phone.storage_gb != other.storage_gb:
        return False
    target = phone.model.lower()
    return fuzz.token_set_ratio(target, other.model.lower()) >= min_score and _same_model_numbers(target, other.model.lower())


def _same_model_numbers(a: str, b: str) -> bool:
    """Evita mezclar "S24" con "S24 Ultra"/"S23": los tokens con dígitos y sufijos deben coincidir."""
    ka, kb = set(_MODEL_TOKENS.findall(a)), set(_MODEL_TOKENS.findall(b))
    return ka == kb
