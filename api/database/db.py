import os
from urllib.parse import urlparse

try:
    import pymysql
    from pymysql.cursors import DictCursor
except Exception as e:
    raise ImportError(
        "PyMySQL is required for MySQL support. Install with `pip install pymysql`."
    ) from e

from flask_bcrypt import Bcrypt
from flask_login import LoginManager

bcrypt = Bcrypt()
login_manager = LoginManager()

_db_config = None


def _parse_database_url(url: str):
    # Expect format mysql+pymysql://user:pass@host:port/dbname
    if not url:
        return None
    # allow either scheme mysql+pymysql or mysql
    if url.startswith("mysql+pymysql://"):
        url = url.replace("mysql+pymysql://", "mysql://", 1)
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "",
        "password": parsed.password or "",
        "db": parsed.path.lstrip("/") or "",
        "charset": "utf8mb4",
    }


def init_extensions(app):
    """Initialize Flask extensions and DB config with the app."""
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    global _db_config
    db_url = app.config.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    _db_config = _parse_database_url(db_url) if db_url else None


def _get_conn():
    if _db_config is None:
        raise RuntimeError("Database is not configured. Set DATABASE_URL in config or environment.")
    return pymysql.connect(
        host=_db_config["host"],
        user=_db_config["user"],
        password=_db_config["password"],
        database=_db_config["db"],
        port=_db_config["port"],
        charset=_db_config.get("charset", "utf8mb4"),
        cursorclass=DictCursor,
    )


def query_one(sql, params=None):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()


def query_all(sql, params=None):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
        return True
    finally:
        conn.close()


