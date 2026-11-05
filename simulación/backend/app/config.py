"""Configuración del servicio, leída de variables de entorno o de .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    entorno: Literal["desarrollo", "produccion"] = "desarrollo"
    log_level: str = "INFO"
    database_url: str = Field("sqlite:///./simulaciones.db",
                              description="Base donde se guardan simulaciones y predicciones")
    ruta_base_agregada: Path = APP_DIR / "data" / "base_agregada.csv"
    ruta_modelos: Path = APP_DIR / "ml" / "artifacts"
    tolerancia_equilibrio_mm: float = Field(0.5, gt=0,
                                            description="|brecha| en mil millones que cuenta como equilibrio")
    max_escenarios_montecarlo: int = Field(5000, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Settings se instancia una sola vez y se reutiliza en cada petición."""
    return Settings()
