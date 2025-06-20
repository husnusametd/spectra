import logging
import os
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict

import yaml
from dotenv import load_dotenv
from logging.handlers import TimedRotatingFileHandler

BASE_DIR = Path(__file__).resolve().parent


def setup_logging(path: str, retention_days: int):
    log_path = BASE_DIR / path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(log_path, when="midnight", backupCount=retention_days, encoding="utf-8")
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    logging.basicConfig(level=logging.INFO, handlers=[handler], format=fmt)


@lru_cache(maxsize=None)
def load_config() -> Dict[str, Any]:
    """YAML config + .env değişkenlerini yükler."""
    load_dotenv()
    cfg_path = BASE_DIR / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    # env değişkenlerini yerleştir
    expanded = yaml.safe_load(os.path.expandvars(yaml.dump(raw)))
    return expanded


@lru_cache(maxsize=None)
def load_yaml_spec() -> Dict[str, Any]:
    spec_path = BASE_DIR / "spec.yaml"
    with open(spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def round_to_tick(price: float, symbol: str, tick: float = 0.0001) -> float:
    """Basit tick işlevi – ileride exchange info API ile genişletilebilir."""
    from math import floor

    return floor(price / tick) * tick


def save_config(cfg: Dict[str, Any], path: str | Path) -> None:
    """YAML konfigürasyonunu dosyaya kaydeder.

    Parametreler
    -----------
    cfg : dict
        Kaydedilecek yapı.
    path : str | Path
        Çıktı dosya yolu.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, sort_keys=False)

