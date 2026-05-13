"""
MarketPlus - Configuración de Base de Datos
Lee las credenciales MySQL desde variables de entorno o un archivo .env

Crea un archivo .env en la raíz del proyecto con este contenido:

    DB_HOST=localhost
    DB_PORT=3306
    DB_NAME=marketplus
    DB_USER=root
    DB_PASSWORD=tu_password
    DB_POOL_SIZE=5
    DB_CONNECT_TIMEOUT=10
"""

import os
from dataclasses import dataclass


def _env(key: str, default: str = "") -> str:
    """Lee una variable de entorno; si no existe intenta cargar .env primero."""
    if key not in os.environ:
        _load_dotenv()
    return os.environ.get(key, default)


def _load_dotenv(path: str = ".env") -> None:
    """
    Cargador mínimo de .env sin dependencias externas.
    Solo soporta KEY=VALUE, ignora comentarios (#) y líneas vacías.
    """
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    pool_size: int
    connect_timeout: int

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            host=_env("DB_HOST", "localhost"),
            port=int(_env("DB_PORT", "3306")),
            database=_env("DB_NAME", "marketplus"),
            user=_env("DB_USER", "root"),
            password=_env("DB_PASSWORD", ""),
            pool_size=int(_env("DB_POOL_SIZE", "5")),
            connect_timeout=int(_env("DB_CONNECT_TIMEOUT", "10")),
        )

    def __repr__(self) -> str:
        return (
            f"DatabaseConfig(host={self.host!r}, port={self.port}, "
            f"database={self.database!r}, user={self.user!r}, "
            f"password='***', pool_size={self.pool_size})"
        )
