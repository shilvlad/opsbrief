"""Локальные настройки OpsBrief из .env без дополнительных зависимостей."""
import os
from pathlib import Path

_ENV = Path(__file__).resolve().parents[1] / ".env"


def setting(name, default=""):
    """Переменные окружения имеют приоритет перед локальным .env."""
    if name in os.environ:
        return os.environ[name]
    try:
        lines = _ENV.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return default
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            return value
    return default
