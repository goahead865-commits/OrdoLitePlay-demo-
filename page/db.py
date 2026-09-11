import os
from pathlib import Path
from urllib.parse import quote_plus

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error
from sqlalchemy import create_engine

# A single source of truth for local development and Streamlit Community Cloud.
# Local: project-root .env (ignored by Git) is loaded.
# Cloud: put a [mysql] section in Streamlit Secrets. The values are mirrored
# into the historic DB_ / MYSQL_ / ORDO_DB_ names so legacy pages keep working.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _secret_mysql_value(key: str) -> str | None:
    try:
        import streamlit as st

        value = st.secrets.get("mysql", {}).get(key)
        return str(value) if value is not None else None
    except Exception:
        return None


def _setting(key: str, default: str = "") -> str:
    aliases = {
        "host": ("ORDO_DB_HOST", "MYSQL_HOST", "DB_HOST"),
        "port": ("ORDO_DB_PORT", "MYSQL_PORT", "DB_PORT"),
        "user": ("ORDO_DB_USER", "MYSQL_USER", "DB_USER"),
        "password": ("ORDO_DB_PASSWORD", "MYSQL_PASSWORD", "DB_PASSWORD"),
        "database": ("ORDO_DB_NAME", "MYSQL_DATABASE", "DB_NAME"),
    }[key]
    secret_value = _secret_mysql_value(key)
    if secret_value:
        return secret_value
    for name in aliases:
        value = os.getenv(name)
        if value:
            return value
    return default


def _mirror_legacy_environment() -> None:
    values = {key: _setting(key) for key in ("host", "port", "user", "password", "database")}
    aliases = {
        "host": ("ORDO_DB_HOST", "MYSQL_HOST", "DB_HOST"),
        "port": ("ORDO_DB_PORT", "MYSQL_PORT", "DB_PORT"),
        "user": ("ORDO_DB_USER", "MYSQL_USER", "DB_USER"),
        "password": ("ORDO_DB_PASSWORD", "MYSQL_PASSWORD", "DB_PASSWORD"),
        "database": ("ORDO_DB_NAME", "MYSQL_DATABASE", "DB_NAME"),
    }
    for key, value in values.items():
        if value:
            for name in aliases[key]:
                os.environ.setdefault(name, value)


_mirror_legacy_environment()

DB_CONFIG = {
    "host": _setting("host", "localhost"),
    "port": int(_setting("port", "3306")),
    "user": _setting("user", "root"),
    "password": _setting("password"),
    "database": _setting("database", "ordotest"),
}

def get_connection():
    """舊版：mysql.connector 連線（保留給你現有頁面用）"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            autocommit=True,
            connection_timeout=int(os.getenv("ORDO_DB_TIMEOUT", "10")),
            ssl_disabled=False,
        )
        try:
            cur0 = conn.cursor()
            cur0.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            cur0.close()
        except Exception:
            pass
        return conn
    except Error as e:
        print("DB connect error:", e)
        return None

def get_engine():
    """新版：SQLAlchemy engine（給 pandas.read_sql / 交易 用）

    重要修正：
    - 舊版硬寫 mysql+pymysql，若你越南筆電沒裝 pymysql 會直接掛。
    - 這版預設改用 mysql+mysqlconnector（跟 get_connection 同一套 driver）。
    - 若你真的要用 pymysql：設定環境變數 ORDO_DB_SQLA_DRIVER=pymysql
    """
    user = DB_CONFIG["user"]
    pwd = quote_plus(DB_CONFIG["password"])
    host = DB_CONFIG["host"]
    port = DB_CONFIG["port"]
    db = DB_CONFIG["database"]

    sqla_driver = os.getenv("ORDO_DB_SQLA_DRIVER", "mysqlconnector").strip().lower()
    if sqla_driver not in ("mysqlconnector", "pymysql"):
        sqla_driver = "mysqlconnector"

    url = f"mysql+{sqla_driver}://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=int(os.getenv("ORDO_DB_POOL_RECYCLE", "3600")),
        pool_size=int(os.getenv("ORDO_DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("ORDO_DB_MAX_OVERFLOW", "10")),
    )

def smoke_test():
    """快速測試：在本機直接跑 `python db.py` 看連線是否正常"""
    conn = get_connection()
    if conn is None:
        raise RuntimeError("mysql.connector 連線失敗：請檢查 ORDO_DB_* 環境變數與 MySQL 是否可達")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("mysql.connector OK:", cur.fetchone())
    cur.close()
    conn.close()

    eng = get_engine()
    with eng.connect() as c:
        r = c.exec_driver_sql("SELECT 1").fetchone()
        print("SQLAlchemy OK:", r)

if __name__ == "__main__":
    smoke_test()
