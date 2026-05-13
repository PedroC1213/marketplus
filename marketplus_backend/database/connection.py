"""
MarketPlus - Conexión MySQL
Pool de conexiones reutilizables con reconexión automática y context manager.

Dependencia: pip install mysql-connector-python
"""

import logging
import threading
import time
from contextlib import contextmanager
from typing import Generator, Optional

try:
    import mysql.connector
    from mysql.connector import pooling, Error as MySQLError
    from mysql.connector.connection import MySQLConnection
    from mysql.connector.cursor import MySQLCursor
except ImportError as e:
    raise ImportError(
        "Instala el driver MySQL: pip install mysql-connector-python"
    ) from e

from database.config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Gestiona un pool de conexiones MySQL.

    Uso:
        db = DatabaseConnection(DatabaseConfig.from_env())
        with db.cursor() as cur:
            cur.execute("SELECT * FROM reviews WHERE id = %s", (review_id,))
            row = cur.fetchone()
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[pooling.MySQLConnectionPool] = None
        self._lock = threading.Lock()

    # ── Ciclo de vida ──────────────────────────────────────────

    def connect(self) -> None:
        """Inicializa el pool. Llama explícitamente o usa connect()."""
        with self._lock:
            if self._pool is not None:
                return
            try:
                self._pool = pooling.MySQLConnectionPool(
                    pool_name="marketplus_pool",
                    pool_size=self.config.pool_size,
                    pool_reset_session=True,
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password,
                    connect_timeout=self.config.connect_timeout,
                    charset="utf8mb4",
                    use_unicode=True,
                    autocommit=False,
                )
                logger.info(
                    f"Pool MySQL iniciado → {self.config.host}:{self.config.port}"
                    f"/{self.config.database} (pool_size={self.config.pool_size})"
                )
            except MySQLError as e:
                logger.error(f"No se pudo conectar a MySQL: {e}")
                raise

    def disconnect(self) -> None:
        """Cierra todas las conexiones del pool."""
        with self._lock:
            self._pool = None
            logger.info("Pool MySQL cerrado.")

    def ping(self) -> bool:
        """Verifica que la conexión esté activa."""
        try:
            with self.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    # ── Context managers ───────────────────────────────────────

    @contextmanager
    def connection(self) -> Generator[MySQLConnection, None, None]:
        """
        Obtiene una conexión del pool y la devuelve al terminar.
        Hace rollback automático en caso de excepción.
        """
        if self._pool is None:
            self.connect()

        conn: MySQLConnection = self._pool.get_connection()
        try:
            yield conn
            conn.commit()
        except MySQLError as e:
            conn.rollback()
            logger.error(f"Error MySQL, rollback aplicado: {e}")
            raise
        finally:
            conn.close()

    @contextmanager
    def cursor(
        self,
        dictionary: bool = True,
    ) -> Generator[MySQLCursor, None, None]:
        """
        Context manager que provee directamente un cursor.
        Por defecto retorna filas como dict (dictionary=True).

        Ejemplo:
            with db.cursor() as cur:
                cur.execute("SELECT id, text FROM reviews LIMIT 10")
                rows = cur.fetchall()   # List[dict]
        """
        with self.connection() as conn:
            cur = conn.cursor(dictionary=dictionary)
            try:
                yield cur
            finally:
                cur.close()

    # ── Helpers ────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> list:
        """
        Ejecuta una consulta SELECT y devuelve todas las filas como lista de dicts.
        Para INSERT/UPDATE/DELETE usa execute_write().
        """
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """
        Ejecuta INSERT, UPDATE o DELETE.
        Retorna el número de filas afectadas.
        """
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def execute_many(self, sql: str, params_list: list) -> int:
        """
        Inserta/actualiza múltiples filas en un solo batch.
        Retorna el número de filas afectadas.
        """
        with self.cursor() as cur:
            cur.executemany(sql, params_list)
            return cur.rowcount

    def last_insert_id(self) -> Optional[int]:
        """Retorna el último ID auto-generado (útil post-INSERT)."""
        rows = self.execute("SELECT LAST_INSERT_ID() AS id")
        return rows[0]["id"] if rows else None

    # ── Reconexión con reintentos ──────────────────────────────

    def execute_with_retry(
        self,
        sql: str,
        params: tuple = (),
        max_retries: int = 3,
        delay_seconds: float = 1.0,
    ) -> list:
        """
        Reintenta una consulta SELECT ante errores transitorios de conexión.
        """
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                return self.execute(sql, params)
            except MySQLError as e:
                last_error = e
                logger.warning(
                    f"Intento {attempt}/{max_retries} fallido: {e}. "
                    f"Reintentando en {delay_seconds}s..."
                )
                time.sleep(delay_seconds)
                # Forzar reconexión en el próximo intento
                with self._lock:
                    self._pool = None
        raise last_error
