import streamlit as st
from compact_layout import apply_compact_layout
from splitter_component import apply_vertical_splitter
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

apply_compact_layout()

st.markdown("""<style>
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input { min-height:1.55rem!important; padding-top:.1rem!important; padding-bottom:.1rem!important; }
[data-testid="stTextInput"],[data-testid="stNumberInput"],[data-testid="stSelectbox"] { margin-bottom:0!important; }
hr { margin:.25rem 0!important; }
/* B02 的英文、越文操作名稱較長：允許按鈕文字換行，避免溢出按鈕。 */
[data-testid="stFormSubmitButton"] button { height:auto!important; min-height:2.7rem!important; }
[data-testid="stFormSubmitButton"] button p { white-space:normal!important; overflow-wrap:anywhere!important; line-height:1.2!important; }
</style>""", unsafe_allow_html=True)

from db import get_engine

import io
import base64
import streamlit.components.v1 as components

# PDF rendering (A5 print; content is proportionally scaled from the A4 design)
# -------------------------------
# Local PDF HTTP server helper
# -------------------------------
# Chrome/Streamlit 常會封鎖 file:// 內嵌或跳轉；data: URL 又可能太大導致點了「沒反應」。
# 這裡改成：在本機 127.0.0.1 開一個超輕量 HTTP server（隨機可用 port），
# 把 PDF 寫到暫存資料夾，用 http://127.0.0.1:PORT/xxx.pdf 的方式開新分頁。
# 這不算 pop-up（是使用者點連結），也不會碰 file://。
import threading
import http.server
import socketserver
import tempfile
from pathlib import Path as _Path

import auth

# i18n import（正式版：core/i18n.py）
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.i18n import init_language, tr as _t

init_language()
PAGE_KEY = "B02_purchase_order_create"
auth.require_read(PAGE_KEY)
init_language()

PURCHASE_ORDER_CATEGORY_GENERAL = "general"
PURCHASE_ORDER_CATEGORY_SAMPLE = "sample"
PURCHASE_ORDER_CATEGORY_FREE_GIFT = "free_gift"
PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_PAID = "material_replenishment_paid"
PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_UNPAID = "material_replenishment_unpaid"
# Kept only to display existing documents created before replenishment orders
# were separated into paid and unpaid categories.
PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_LEGACY = "material_replenishment"
PURCHASE_ORDER_CATEGORY_OPTIONS = {
    PURCHASE_ORDER_CATEGORY_GENERAL: "一般採購單（要付款）",
    PURCHASE_ORDER_CATEGORY_SAMPLE: "樣品單（不付款）",
    PURCHASE_ORDER_CATEGORY_FREE_GIFT: "搭贈單（不付款）",
    PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_PAID: "補料單（要付款）",
    PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_UNPAID: "補料單（不付款）",
}


def purchase_order_category_label(category: str) -> str:
    """Return a readable category label while preserving old rows as general PO."""
    category = str(category or "").strip()
    if category == PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_LEGACY:
        category = PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_UNPAID
    return _label(PURCHASE_ORDER_CATEGORY_OPTIONS.get(
        category,
        PURCHASE_ORDER_CATEGORY_OPTIONS[PURCHASE_ORDER_CATEGORY_GENERAL],
    ))


def normalize_purchase_order_category(category: str) -> str:
    """Map the original replenishment category to its unpaid replacement."""
    category = str(category or "").strip()
    if category == PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_LEGACY:
        return PURCHASE_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_UNPAID
    return category


def _label(text_value: str) -> str:
    """Translate label if available; if i18n misses, fall back to original Chinese."""
    try:
        value = _t(text_value)
        if isinstance(value, str) and value and not value.startswith("[MISS:"):
            return value
    except Exception:
        pass
    return text_value


_PDF_SERVER = {"thread": None, "port": None, "dir": None, "host": None}
PDF_SERVER_PORT = 8766  # B02 固定用 8766；D02 已使用 8765，避免互搶 port


def _get_lan_ip() -> str:
    """Return a LAN-reachable IP for this host. Fallback to localhost."""
    import socket as _socket
    try:
        # 不需要真的連線，只是讓 OS 告訴我們預設出口 IP。
        with _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        ip = _socket.gethostbyname(_socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "localhost"


def _get_request_host_for_pdf() -> str:
    """Use the same host that the browser used for Streamlit, but replace the port.

    If the browser is on the host itself, Streamlit may be opened as localhost/127.0.0.1.
    In that case, return the LAN IP so other computers can also open the PDF URL.
    """
    host = ""
    try:
        # Streamlit 1.3x+ exposes request headers through st.context.headers.
        headers = getattr(getattr(st, "context", None), "headers", None)
        if headers:
            host = headers.get("host", "") or headers.get("Host", "")
    except Exception:
        host = ""

    if host:
        host = str(host).split(":")[0].strip()
        if host and host not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            return host

    return _get_lan_ip()


def ensure_pdf_server() -> tuple[str, int, str]:
    """確保 B02 PDF server 已啟動，回傳 (base_url, port, dir_path).

    修正版重點：
    - B02 固定使用 8766，並綁定 0.0.0.0，讓其他電腦可以透過主機 IP 開 PDF。
    - PDF 目錄改成專案底下固定資料夾，避免 Streamlit 重跑後，8766 被舊 thread 佔住，
      但新 PDF 寫到另一個暫存資料夾，造成「連得到 server，卻打不開檔案」。
    """
    host_for_url = _get_request_host_for_pdf()
    port = PDF_SERVER_PORT

    # 使用固定目錄。即使舊的 8766 server 還活著，也會服務同一個資料夾。
    cache_dir = ROOT_DIR / "_ordo_print_cache_b02"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if _PDF_SERVER["thread"] is not None and _PDF_SERVER["port"] is not None and _PDF_SERVER["dir"] is not None:
        return f"http://{host_for_url}:{_PDF_SERVER['port']}", int(_PDF_SERVER["port"]), str(_PDF_SERVER["dir"])

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return

    class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True

    class DirHandler(Handler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(cache_dir), **kwargs)

    # 先在主執行緒 bind，這樣 port 被佔用時不會在背景 thread 靜悄悄爆掉。
    try:
        httpd = ThreadingTCPServer(("0.0.0.0", port), DirHandler)
    except OSError:
        # 多半是舊的 Streamlit thread 已經佔住 8766。因為我們改用固定 cache_dir，
        # 只要舊 server 也是新版或曾經服務此資料夾，寫入檔案後仍可被讀到。
        _PDF_SERVER["thread"] = threading.current_thread()
        _PDF_SERVER["port"] = port
        _PDF_SERVER["dir"] = str(cache_dir)
        _PDF_SERVER["host"] = host_for_url
        return f"http://{host_for_url}:{port}", port, str(cache_dir)

    def _serve():
        httpd.serve_forever()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()

    _PDF_SERVER["thread"] = t
    _PDF_SERVER["port"] = port
    _PDF_SERVER["dir"] = str(cache_dir)
    _PDF_SERVER["host"] = host_for_url

    return f"http://{host_for_url}:{port}", port, str(cache_dir)


def write_pdf_and_get_url(pdf_bytes: bytes, filename: str = "PO_po_print.pdf") -> str:
    # 列印/預覽屬於讀取行為；只需要 read 權限，不應要求 edit。
    auth.require_read(PAGE_KEY)
    import time as _time
    import re as _re

    base_url, _, dir_path = ensure_pdf_server()
    # 避免檔名含空白或特殊字元造成 URL 讀不到。
    safe_name = _re.sub(r"[^A-Za-z0-9_.-]", "_", filename or "PO_po_print.pdf")
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"

    p = _Path(dir_path) / safe_name
    p.write_bytes(pdf_bytes)
    return f"{base_url}/{safe_name}?t={int(_time.time())}"

try:
    from reportlab.lib.pagesizes import A4, A5, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    _HAS_REPORTLAB = True
except Exception:
    _HAS_REPORTLAB = False
    # Keep module-level PDF helper defaults evaluable even when ReportLab is
    # unavailable. PDF generation itself remains guarded by _HAS_REPORTLAB.
    mm = 2.834645669


# ------------------------------
# PDF font setup (CJK/VN safe)
# ------------------------------
PDF_FONT_REG = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"

def _setup_pdf_fonts():
    """Register NotoSansTC TTF so Chinese/Vietnamese won't show as □□□.
    Put 'NotoSansTC-VariableFont_wght.ttf' in project root (same folder as this file),
    or set env var ORDO_FONT_TTF / NOTO_SANS_TC_TTF to the full path.
    """
    global PDF_FONT_REG, PDF_FONT_BOLD
    if not _HAS_REPORTLAB:
        return
    try:
        import os
        from pathlib import Path

        # 1) env var path has highest priority
        font_path = (
            os.environ.get("ORDO_FONT_TTF")
            or os.environ.get("NOTO_SANS_TC_TTF")
            or ""
        )

        # 2) common local candidates
        if not font_path:
            here = Path(__file__).resolve().parent
            candidates = [
                here / "NotoSansTC-VariableFont_wght.ttf",
                here / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
                Path.cwd() / "NotoSansTC-VariableFont_wght.ttf",
                Path.cwd() / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
            ]
            for p in candidates:
                if p.exists():
                    font_path = str(p)
                    break

        if font_path and Path(font_path).exists():
            # Note: variable fonts usually work fine; if reportlab rejects it, we'll fall back to Helvetica.
            pdfmetrics.registerFont(TTFont("NotoSansTC", font_path))
            # Bold alias: still same file, but at least avoids missing glyphs.
            pdfmetrics.registerFont(TTFont("NotoSansTC-Bold", font_path))
            PDF_FONT_REG = "NotoSansTC"
            PDF_FONT_BOLD = "NotoSansTC-Bold"
    except Exception:
        # keep default Helvetica
        pass

# run once on import
_setup_pdf_fonts()

# ------------------------------
# DB helpers
# ------------------------------
@st.cache_resource
def _engine():
    return get_engine()

def df_from_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    eng = _engine()
    with eng.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})

def exec_sql(sql: str, params: dict | None = None) -> None:
    eng = _engine()
    with eng.begin() as conn:
        conn.execute(text(sql), params or {})


def _build_in_params(values: list[int], prefix: str = "v") -> tuple[str, dict]:
    """Return (in_clause_sql, params) like (':v0,:v1', {'v0':1,'v1':2})."""
    params = {f"{prefix}{i}": int(v) for i, v in enumerate(values)}
    clause = ", ".join([f":{k}" for k in params.keys()])
    return clause, params


def delete_po_orders(order_ids: list[int]) -> tuple[bool, str]:
    auth.require_delete(PAGE_KEY)
    """
    刪除 PO 的 order_head + order_item。
    回傳：
        (True, "") -> 成功
        (False, "中文訊息") -> 失敗
    """
    ids = [int(x) for x in order_ids if x is not None]
    ids = sorted(set(ids))
    if not ids:
        return False, _t("沒有可刪除的採購單。")

    in_clause, params = _build_in_params(ids, prefix="oid")
    eng = _engine()

    try:
        with eng.begin() as conn:
            # 先刪明細
            conn.execute(
                text(f"DELETE FROM `{ORDER_ITEM}` WHERE {sql_ident(ORDER_ITEM_ORDER_ID_COL)} IN ({in_clause})"),
                params,
            )

            # 再刪抬頭
            conn.execute(
                text(
                    f"DELETE FROM `{ORDER_HEAD}` "
                    f"WHERE {sql_ident(ORDER_HEAD_ID_COL)} IN ({in_clause}) AND {sql_ident(ORDER_HEAD_TYPE_COL)}='PO'"
                ),
                params,
            )

        return True, ""

    except IntegrityError as e:
        err_text = str(e)

        if "fk_msioh_order" in err_text or "material_stock_io_head" in err_text:
            return (
                False,
                _t("無法刪除這張採購單。\n\n原因：這張採購單已經被【原料出入庫／進料紀錄】引用，系統為了避免資料斷裂，不允許直接刪除。\n\n請先檢查並刪除或解除相關的出入庫紀錄，再回來刪除此採購單。")
            )

        return (
            False,
            _t("無法刪除這張採購單。\n\n原因：此單據已經和其他資料建立關聯，系統不能直接刪除。\n\n請先檢查是否已有收貨、入庫、核銷或其他後續紀錄。")
        )

    except Exception as e:
        return False, f"{_t('刪除失敗：')}{str(e)}"

def show_cols(table: str) -> list[str]:
    df = df_from_sql(f"SHOW COLUMNS FROM `{table}`")
    field_col = None
    for c in df.columns:
        if str(c).lower() == "field":
            field_col = c
            break
    if field_col is None:
        return []
    return df[field_col].astype(str).tolist()

def colset(table: str) -> set[str]:
    return set(show_cols(table))

def first_existing(cols: set[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None

def sql_ident(col_name: str) -> str:
    return f"`{col_name}`"


def ensure_purchase_order_category_column() -> None:
    """Add the category column for deployments that have not run the DB migration."""
    try:
        with _engine().begin() as conn:
            exists = conn.execute(text("""
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'order_head'
                  AND column_name = 'purchase_order_category'
                LIMIT 1
            """)).fetchone()
            if not exists:
                conn.execute(text("""
                    ALTER TABLE `order_head`
                    ADD COLUMN `purchase_order_category` VARCHAR(32)
                    NOT NULL DEFAULT 'general' AFTER `order_type`
                """))
    except Exception as exc:
        # Do not hide a failed migration: saving a PO without its category is unsafe.
        raise RuntimeError(f"無法建立 order_head.purchase_order_category：{exc}") from exc


def ensure_purchase_order_number_capacity() -> None:
    """Keep PO numbers and their AP snapshot wide enough for supplier short names.

    PO numbers follow ``RD-<supplier short name>-yymmddxxx``.  The legacy
    VARCHAR(16) definition only supports a three-character short name and lets
    MySQL raise a low-level ``Data too long`` error for normal supplier names.
    AP copies the PO number to ``order_no`` when a material receipt is posted,
    therefore both columns must have the same capacity.
    """
    required_columns = (
        ("order_head", "order_num", "VARCHAR(64) NOT NULL"),
        ("accounts_payable_head", "order_no", "VARCHAR(64) NULL"),
    )
    try:
        with _engine().begin() as conn:
            for table_name, column_name, definition in required_columns:
                row = conn.execute(text("""
                    SELECT character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = :table_name
                      AND column_name = :column_name
                    LIMIT 1
                """), {
                    "table_name": table_name,
                    "column_name": column_name,
                }).fetchone()
                if row is None:
                    continue
                current_length = int(row[0] or 0)
                if current_length < 64:
                    conn.execute(text(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` {definition}"
                    ))
    except Exception as exc:
        # Saving an order which can later break AP generation is unsafe.
        raise RuntimeError(f"無法擴充採購單號欄位長度：{exc}") from exc


# ------------------------------
# Table names & column introspection
# ------------------------------
ORDER_HEAD = "order_head"
ORDER_ITEM = "order_item"
MATERIAL = "material"
SUPPLIER = "supplier"
MATERIAL_UNIT_PRICE = "material_unit_price"

ensure_purchase_order_category_column()
ensure_purchase_order_number_capacity()

@st.cache_data(ttl=3600)
def _colset_cached(table: str) -> set[str]:
    # Cache SHOW COLUMNS results to avoid repeated metadata queries
    return set(show_cols(table))

# A running Streamlit server may still have cached the old order_head structure
# from before this migration.  Clear it once here so new orders immediately
# include purchase_order_category instead of silently using the DB default.
_colset_cached.clear()

ORDER_HEAD_COLS = _colset_cached(ORDER_HEAD)
ORDER_ITEM_COLS = _colset_cached(ORDER_ITEM)
MATERIAL_COLS = _colset_cached(MATERIAL)
MATERIAL_PK_COL = first_existing(MATERIAL_COLS, ["item_id", "material_id", "id"]) or "item_id"
SUPPLIER_COLS = _colset_cached(SUPPLIER)
try:
    MATERIAL_UNIT_PRICE_COLS = _colset_cached(MATERIAL_UNIT_PRICE)
except Exception:
    MATERIAL_UNIT_PRICE_COLS = set()

# material columns (best-effort detection)
MATERIAL_UNIT_COL = first_existing(MATERIAL_COLS, ["purchase_unit", "base_unit", "unit"])
MATERIAL_PRICE_COL = None
MATERIAL_SPEC_COL = first_existing(MATERIAL_COLS, ["spec", "specification", "material_spec", "spec_text"])
MATERIAL_BARCODE_COL = first_existing(MATERIAL_COLS, ["material_barcode", "barcode", "bar_code", "code39", "code_39"])

# order head / item extra columns used across UI
ORDER_HEAD_TYPE_COL = first_existing(ORDER_HEAD_COLS, ["order_type", "type", "doc_type"]) or "order_type"
ORDER_HEAD_PURCHASE_CATEGORY_COL = first_existing(
    ORDER_HEAD_COLS, ["purchase_order_category"]
) or "purchase_order_category"
ORDER_HEAD_CREATED_BY_COL = first_existing(ORDER_HEAD_COLS, ["created_by_id", "created_by", "create_user", "user_id"])
ORDER_HEAD_UPDATED_BY_COL = first_existing(ORDER_HEAD_COLS, ["updated_by_id", "updated_by", "update_user", "last_updated_by"])
ORDER_HEAD_CREATED_AT_COL = first_existing(ORDER_HEAD_COLS, ["create_at", "created_at"])
ORDER_HEAD_UPDATED_AT_COL = first_existing(ORDER_HEAD_COLS, ["update_at", "updated_at"])

def _current_user_id() -> int:
    """目前登入者 user_id；抓不到時才退回 1，避免新增/修改責任人被硬塞錯。"""
    try:
        return int(st.session_state.get("user_id") or 1)
    except Exception:
        return 1

def _audit_user_display_expr(alias: str, user_col: str | None) -> str:
    """把 user_id 類欄位轉成畫面可讀的人名。"""
    if not user_col:
        return "''"
    col_expr = f"{alias}.{sql_ident(user_col)}"
    return (
        "COALESCE("
        "(SELECT NULLIF(s.stuff_name, '') FROM `user` u "
        "LEFT JOIN `stuff` s ON s.stuff_id = u.stuff_id "
        f"WHERE u.user_id = {col_expr} LIMIT 1), "
        "(SELECT NULLIF(u.user_code, '') FROM `user` u "
        f"WHERE u.user_id = {col_expr} LIMIT 1), "
        f"NULLIF(CAST({col_expr} AS CHAR), ''), "
        "'')"
    )

def _audit_updated_display_expr(alias: str = "h") -> str:
    """未修改過時，最後修改人顯示空白；有修改才顯示修改者。"""
    if not ORDER_HEAD_UPDATED_BY_COL:
        return "''"

    updated_col = f"{alias}.{sql_ident(ORDER_HEAD_UPDATED_BY_COL)}"
    blank_conditions = [f"{updated_col} IS NULL", f"{updated_col} = 0"]

    if ORDER_HEAD_CREATED_BY_COL and ORDER_HEAD_CREATED_AT_COL and ORDER_HEAD_UPDATED_AT_COL:
        created_col = f"{alias}.{sql_ident(ORDER_HEAD_CREATED_BY_COL)}"
        created_at_col = f"{alias}.{sql_ident(ORDER_HEAD_CREATED_AT_COL)}"
        updated_at_col = f"{alias}.{sql_ident(ORDER_HEAD_UPDATED_AT_COL)}"
        blank_conditions.append(
            f"({updated_col} = {created_col} AND {created_at_col} IS NOT NULL "
            f"AND {updated_at_col} IS NOT NULL AND ABS(TIMESTAMPDIFF(SECOND, {created_at_col}, {updated_at_col})) <= 1)"
        )

    return (
        "CASE WHEN " + " OR ".join(blank_conditions) +
        " THEN '' ELSE " + _audit_user_display_expr(alias, ORDER_HEAD_UPDATED_BY_COL) + " END"
    )

def _order_head_audit_set_sql(alias: str | None = None) -> tuple[list[str], dict]:
    """回傳更新 order_head 責任欄位需要的 SET 子句與參數。"""
    sets: list[str] = []
    params = {"audit_user_id": _current_user_id()}

    col_prefix = f"{alias}." if alias else ""
    if ORDER_HEAD_UPDATED_BY_COL:
        sets.append(f"{col_prefix}{sql_ident(ORDER_HEAD_UPDATED_BY_COL)}=:audit_user_id")
    if ORDER_HEAD_UPDATED_AT_COL:
        sets.append(f"{col_prefix}{sql_ident(ORDER_HEAD_UPDATED_AT_COL)}=NOW()")
    return sets, params

ORDER_ITEM_PRICE_COL = first_existing(ORDER_ITEM_COLS, ["unit_price", "price_unit", "price", "cost"]) or "unit_price"
ORDER_ITEM_LINE_COL = first_existing(ORDER_ITEM_COLS, ["line_no", "line_num", "seq", "line"])
ORDER_ITEM_AMOUNT_COL = first_existing(ORDER_ITEM_COLS, ["amount", "line_amount", "subtotal", "sub_total"])


def get_index_cols(table: str, key_name: str) -> list[str]:
    """取某個 index / unique key 的欄位順序（依 Seq_in_index）"""
    try:
        df = df_from_sql(
            f"SHOW INDEX FROM `{table}` WHERE Key_name = :k ORDER BY Seq_in_index",
            {"k": key_name},
        )
        if df.empty:
            return []
        col_field = None
        for c in df.columns:
            if str(c).lower() == "column_name":
                col_field = c
                break
        if not col_field:
            return []
        return df[col_field].dropna().astype(str).tolist()
    except Exception:
        return []

def to_decimal(x, default=Decimal("0")) -> Decimal:
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return default
        return Decimal(str(x))
    except (InvalidOperation, ValueError):
        return default
# ------------------------------
# Barcode helpers (offline, no CDN)
# ------------------------------
_CODE39_ALLOWED = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%")

def _code39_clean(val: str) -> str:
    """Sanitize a string to be safe for Code39. Removes surrounding * and illegal chars."""
    if val is None:
        return ""
    s = str(val).strip()
    # common case: stored as *M00001* (with start/stop)
    if s.startswith("*") and s.endswith("*") and len(s) >= 2:
        s = s[1:-1]
    s = s.strip().upper()
    s = "".join(ch for ch in s if ch in _CODE39_ALLOWED)
    return s

def _fmt_qty_barcode(qty: Decimal) -> str:
    """Format qty to an integer-like string when possible (avoid trailing .0)."""
    try:
        q = Decimal(str(qty))
    except Exception:
        return ""
    # normalize without scientific notation
    s = format(q, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

# ---------------------------
# Code39 (3 of 9) rendering
# ---------------------------

_CODE39_PATTERNS = {
    "0": "NnNwWnWnN", "1": "WnNwNnNnW", "2": "NnWwNnNnW", "3": "WnWwNnNnN",
    "4": "NnNwWnNnW", "5": "WnNwWnNnN", "6": "NnWwWnNnN", "7": "NnNwNnWnW",
    "8": "WnNwNnWnN", "9": "NnWwNnWnN",
    "A": "WnNnNwNnW", "B": "NnWnNwNnW", "C": "WnWnNwNnN", "D": "NnNnWwNnW",
    "E": "WnNnWwNnN", "F": "NnWnWwNnN", "G": "NnNnNwWnW", "H": "WnNnNwWnN",
    "I": "NnWnNwWnN", "J": "NnNnWwWnN",
    "K": "WnNnNnNwW", "L": "NnWnNnNwW", "M": "WnWnNnNwN", "N": "NnNnWnNwW",
    "O": "WnNnWnNwN", "P": "NnWnWnNwN", "Q": "NnNnNnWwW", "R": "WnNnNnWwN",
    "S": "NnWnNnWwN", "T": "NnNnWnWwN",
    "U": "WwNnNnNnW", "V": "NwWnNnNnW", "W": "WwWnNnNnN", "X": "NwNnWnNnW",
    "Y": "WwNnWnNnN", "Z": "NwWnWnNnN",
    "-": "NwNnNnWnW", ".": "WwNnNnWnN", " ": "NwWnNnWnN",
    "$": "NwNwNwNnN", "/": "NwNwNnNwN", "+": "NwNnNwNwN", "%": "NnNwNwNwN",
    "*": "NwNnWnWnN",
}

_CODE39_ALLOWED = set(_CODE39_PATTERNS.keys()) - {"*"}  # * is reserved for start/stop


def _code39_clean(s: str) -> str:
    """Clean a string to Code39 basic charset (0-9 A-Z - . space $ / + %)."""
    if s is None:
        return ""
    s = str(s).upper().strip()
    # do NOT allow start/stop to be passed in by user
    s = s.replace("*", "")
    out = []
    for ch in s:
        if ch in _CODE39_ALLOWED:
            out.append(ch)
    return "".join(out)


def _code39_html(code: str, *, height_px: int = 46, narrow_px: int = 2, wide_px: int = 6,
                 show_text: bool = True, label: str | None = None) -> str:
    """
    Return an HTML snippet that renders a Code39 barcode (no external libs).
    Uses a classic narrow/wide CSS bar approach.
    """
    code = _code39_clean(code)
    if not code:
        code = "NA"

    # Wrap with start/stop
    full = f"*{code}*"

    # Unique-ish class scope (avoid colliding with other CSS)
    cls = "ordo_code39"

    # Build bars as inline divs
    bars = []
    for ch in full:
        pattern = _CODE39_PATTERNS.get(ch)
        if not pattern:
            continue
        for token in pattern:
            is_bar = token.isupper()  # N/W = black bar; n/w = white space
            is_wide = token in ("W", "w")
            width = wide_px if is_wide else narrow_px
            color = "#000" if is_bar else "#fff"
            bars.append(f"<div style='height:{height_px}px;width:{width}px;background:{color};display:inline-block;'></div>")
        # inter-character gap: narrow white space
        bars.append(f"<div style='height:{height_px}px;width:{narrow_px}px;background:#fff;display:inline-block;'></div>")

    text_line = ""
    if show_text:
        text_line = f"<div style='font-size:12px;line-height:1.2;text-align:center;margin-top:4px;color:#111;font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace;'>{code}</div>"

    label_line = ""
    if label:
        label_line = f"<div style='font-size:12px;line-height:1.2;text-align:center;margin-bottom:4px;color:#111;'>{label}</div>"

    return f"""
    <div class='{cls}' style='display:inline-block;padding:2px 4px;background:#fff;border:1px solid #e6e6e6;border-radius:6px;'>
      {label_line}
      <div style='white-space:nowrap;'>{''.join(bars)}</div>
      {text_line}
    </div>
    """


def _render_code39_pair(left: str, right: str, *, height_px: int = 52, gap_px: int = 80,
                        narrow_px: int = 2, wide_px: int = 6, show_text: bool = True) -> None:
    """Render two Code39 barcodes on the same row with enough gap to avoid double-scan."""
    left = _code39_clean(left)
    right = _code39_clean(right)

    if not left and not right:
        return

    html = f"""
    <div style='display:flex;align-items:flex-start;gap:{gap_px}px;background:#fff;padding:4px 0;'>
      {_code39_html(left or 'NA', height_px=height_px, narrow_px=narrow_px, wide_px=wide_px, show_text=show_text, label='料號')}
      {_code39_html(right or '0', height_px=height_px, narrow_px=narrow_px, wide_px=wide_px, show_text=show_text, label='數量')}
    </div>
    """
    # Height estimate: bars + optional text + padding
    component_height = height_px + (26 if show_text else 8) + 18
    st.components.v1.html(html, height=component_height, scrolling=False)


def load_suppliers(active_only: bool = False) -> pd.DataFrame:
    cols = SUPPLIER_COLS
    fields: list[str] = []
    for c in ["supplier_id", "supplier_code", "supplier_shortname", "supplier_name", "is_active"]:
        if c in cols:
            fields.append(c)

    if not fields:
        return pd.DataFrame()

    where_sql = ""
    if active_only and "is_active" in cols:
        where_sql = "WHERE is_active = 1"

    # select_cols assembled via fields list

    sql = f"""
      SELECT {", ".join([sql_ident(c) for c in fields])}
      FROM `{SUPPLIER}`
      {where_sql}
      ORDER BY supplier_code
    """
    return df_from_sql(sql)

def _material_current_price_expr(material_alias: str = "m") -> str:
    """
    現行原料單價：
    只從 material_unit_price 抓目前有效價格。
    material 本表已不再保存單價，因此不再 fallback。
    """
    if not MATERIAL_UNIT_PRICE_COLS:
        return "NULL"

    item_col = first_existing(MATERIAL_UNIT_PRICE_COLS, ["material_item_id", "item_id", "material_id"])
    price_col = first_existing(MATERIAL_UNIT_PRICE_COLS, ["material_unit_price", "unit_price", "price", "cost"])
    from_col = first_existing(MATERIAL_UNIT_PRICE_COLS, ["valid_from", "created_at", "material_price_id"])
    id_col = first_existing(MATERIAL_UNIT_PRICE_COLS, ["material_price_id", "id"])
    current_flag_col = first_existing(MATERIAL_UNIT_PRICE_COLS, ["current_flag"])
    valid_to_col = first_existing(MATERIAL_UNIT_PRICE_COLS, ["valid_to", "end_date"])

    if not item_col or not price_col:
        return "NULL"

    current_cond_parts = []
    if current_flag_col:
        current_cond_parts.append(f"mup.{sql_ident(current_flag_col)} = 1")
    if valid_to_col:
        current_cond_parts.append(f"mup.{sql_ident(valid_to_col)} IS NULL")
    current_cond = " OR ".join(current_cond_parts) if current_cond_parts else "1=1"

    order_parts = []
    if from_col:
        order_parts.append(f"mup.{sql_ident(from_col)} DESC")
    if id_col:
        order_parts.append(f"mup.{sql_ident(id_col)} DESC")
    order_sql = ", ".join(order_parts) if order_parts else "1"

    return (
        "("
        f"SELECT mup.{sql_ident(price_col)} "
        f"FROM `{MATERIAL_UNIT_PRICE}` mup "
        f"WHERE mup.{sql_ident(item_col)} = {material_alias}.{sql_ident(MATERIAL_PK_COL)} "
        f"AND ({current_cond}) "
        f"ORDER BY {order_sql} LIMIT 1"
        ")"
    )

@st.cache_data(ttl=120)
def load_materials_by_supplier(supplier_id: int | None) -> pd.DataFrame:
    if supplier_id is None:
        return pd.DataFrame()

    # unit
    unit_expr = "NULL AS unit"
    if "purchase_unit" in MATERIAL_COLS:
        unit_expr = "m.`purchase_unit` AS unit"
    elif "base_unit" in MATERIAL_COLS:
        unit_expr = "m.`base_unit` AS unit"
    elif MATERIAL_UNIT_COL:
        unit_expr = f"m.{sql_ident(MATERIAL_UNIT_COL)} AS unit"

    # price：優先抓 material_unit_price 現行價，抓不到才回退 material.unit_price
    price_expr = f"{_material_current_price_expr('m')} AS unit_price"

    # barcode
    barcode_expr = "NULL AS material_barcode"
    if MATERIAL_BARCODE_COL and MATERIAL_BARCODE_COL in MATERIAL_COLS:
        barcode_expr = f"m.{sql_ident(MATERIAL_BARCODE_COL)} AS material_barcode"

    spec_expr = "NULL AS specification"
    if MATERIAL_SPEC_COL and MATERIAL_SPEC_COL in MATERIAL_COLS:
        spec_expr = f"m.{sql_ident(MATERIAL_SPEC_COL)} AS specification"
    elif "specification" in MATERIAL_COLS:
        spec_expr = "m.`specification` AS specification"

    track_expr = "NULL AS TrackingMod"
    if "TrackingMod" in MATERIAL_COLS:
        track_expr = "m.`TrackingMod` AS TrackingMod"

    statute_col = "statute" if "statute" in MATERIAL_COLS else None
    statute_expr = (f"m.{sql_ident(statute_col)} AS statute") if statute_col else "NULL AS statute"

    where_statute = ""
    if statute_col:
        where_statute = f"AND (m.{sql_ident(statute_col)} = 1 OR m.{sql_ident(statute_col)} IS NULL)"

    select_parts = [
        "m.`item_id` AS item_id",
        "m.`item_code` AS item_code",
        "m.`item_name` AS item_name",
        spec_expr,
        track_expr,
        unit_expr,
        price_expr,
        barcode_expr,
        statute_expr,
    ]

    sql = f"""
        SELECT
          {", ".join(select_parts)}
        FROM `{MATERIAL}` m
        WHERE m.supplier_id = :supplier_id
          {where_statute}
        ORDER BY item_code
    """
    return df_from_sql(sql, {"supplier_id": supplier_id})

@st.cache_data(ttl=120)
def load_all_materials() -> pd.DataFrame:
    # fallback when supplier_id is not available
    select_parts = [
        "m.`item_id` AS item_id",
        "m.`item_code` AS item_code",
        "m.`item_name` AS item_name",
        (f"m.{sql_ident(MATERIAL_SPEC_COL)} AS specification") if MATERIAL_SPEC_COL else "NULL AS specification",
        (f"m.{sql_ident(MATERIAL_UNIT_COL)} AS unit") if MATERIAL_UNIT_COL else ("m.`purchase_unit` AS unit" if "purchase_unit" in MATERIAL_COLS else ("m.`base_unit` AS unit" if "base_unit" in MATERIAL_COLS else "NULL AS unit")),
        f"{_material_current_price_expr('m')} AS unit_price",
        (f"m.{sql_ident(MATERIAL_BARCODE_COL)} AS material_barcode") if (MATERIAL_BARCODE_COL and MATERIAL_BARCODE_COL in MATERIAL_COLS) else "NULL AS material_barcode",
    ]

    sql = f"""
        SELECT {', '.join(select_parts)}
        FROM `{MATERIAL}` m
        ORDER BY m.item_code
    """
    return df_from_sql(sql)

# ------------------------------
# Order num generator: yymmdd + xxx
# ------------------------------
def next_order_num(po_date: date, supplier_shortname: str) -> str:
    """單號格式：RD-供應商簡稱-yymmdd + 3 碼流水號。"""
    shortname = str(supplier_shortname or "").strip()
    if not shortname:
        raise ValueError(_t("供應商簡稱為必填，無法產生採購單號。"))

    ymd = po_date.strftime("%y%m%d")
    prefix = f"RD-{shortname}-{ymd}"

    df = df_from_sql(
        f"""
        SELECT MAX(CAST(RIGHT(order_num, 3) AS UNSIGNED)) AS max_num
        FROM `{ORDER_HEAD}`
        WHERE LEFT(order_num, :prefix_len) = :prefix
          AND CHAR_LENGTH(order_num) = :code_len
          AND RIGHT(order_num, 3) REGEXP '^[0-9]{{3}}$'
        """,
        {"prefix_len": len(prefix), "prefix": prefix, "code_len": len(prefix) + 3},
    )
    max_num = df["max_num"].iloc[0] if not df.empty else None
    try:
        seq = int(max_num or 0)
    except (TypeError, ValueError):
        seq = 0

    if seq >= 999:
        raise ValueError(f"{prefix} {_t('當日流水號已達三碼上限。')}")
    return f"{prefix}{seq+1:03d}"

# ------------------------------
# Save logic
# ------------------------------
def save_new_order(*, supplier_id=None, order_date=None, currency=None, due_date=None, head_remark=None, purchase_order_category=None, lines=None) -> bool:
    """
    建立新的採購單（PO）。
    - 新版 UI 會傳入 supplier_id / order_date / currency / due_date / head_remark / lines（購物車明細）
    - 為了相容舊版，若未傳入參數，會改從 session_state 讀取
    回傳：成功 True；失敗 False
    """
    auth.require_edit(PAGE_KEY)
    # ---- resolve header ----
    if order_date is None:
        order_date = st.session_state.get("po_order_date", date.today())
    if due_date is None:
        due_date = st.session_state.get("po_due_date", None)
    if currency is None:
        currency = st.session_state.get("po_currency", "VND")
    if head_remark is None:
        head_remark = st.session_state.get("po_head_remark", "")
    if purchase_order_category is None:
        purchase_order_category = st.session_state.get(
            "po_purchase_order_category", PURCHASE_ORDER_CATEGORY_GENERAL
        )
    purchase_order_category = normalize_purchase_order_category(purchase_order_category)
    if purchase_order_category not in PURCHASE_ORDER_CATEGORY_OPTIONS:
        st.error(_t("採購單類別不正確，請重新選擇。"))
        return False

    # supplier_id: either provided or parse from supplier_choice
    if supplier_id is None:
        supplier_choice = st.session_state.get("po_supplier_choice", "未選")
        if supplier_choice == "未選":
            st.error(_t("你沒選供應商。沒有對象的訂購單，只是情書。"))
            return False
        try:
            supplier_id = int(str(supplier_choice).split("|")[0].strip())
        except Exception:
            st.error(_t("供應商選項格式怪怪的，請重新選一次。"))
            return False

    # ---- resolve lines ----
    if lines is None:
        # prefer new cart
        if "po_cart_lines" in st.session_state and st.session_state.get("po_cart_lines"):
            lines = st.session_state.get("po_cart_lines", [])
        else:
            # legacy: read multi-line inputs
            legacy_lines = []
            line_count = int(st.session_state.get("po_line_count", 1))
            for i in range(1, line_count + 1):
                item_label = st.session_state.get(f"po_line_{i}_item", "未選")
                qty_str = st.session_state.get(f"po_line_{i}_qty", "0")
                remark = st.session_state.get(f"po_line_{i}_remark", "")
                if not item_label or item_label == "未選":
                    continue
                legacy_lines.append(
                    dict(
                        item_label=item_label,
                        qty_ordered=qty_str,
                        remark=remark,
                    )
                )
            lines = legacy_lines

    if not lines:
        st.error(_t("沒有任何明細。至少要加入一個品項，數量 > 0。"))
        return False

    # ---- supplier sanity check ----
    suppliers = load_suppliers(active_only=False)
    if suppliers.empty or "supplier_id" not in suppliers.columns:
        st.error(_t("供應商資料讀取失敗，請先確認 supplier 表。"))
        return False

    sup_row = suppliers.loc[suppliers["supplier_id"].astype(int) == int(supplier_id)]
    if sup_row.empty:
        st.error(_t("供應商清單裡找不到這個 ID，麻煩你檢查一下資料庫。"))
        return False
    sup = sup_row.iloc[0]

    # ---- normalize lines ----
    cleaned = []
    for r in lines:
        # 支援新 cart 與舊版 legacy
        if "item_label" in r and ("item_id" not in r):
            # legacy: need to map label -> row via materials table
            try:
                mats = load_materials_by_supplier(int(supplier_id))
                label_map = {}
                for _, mr in mats.iterrows():
                    code_ = str(mr.get("item_code") or "")
                    name_ = str(mr.get("item_name") or "")
                    lbl = f"{code_} | {name_}".strip()
                    label_map[lbl] = mr
                mr = label_map.get(r.get("item_label"))
            except Exception:
                mr = None

            if mr is None:
                continue

            item_id = mr.get("item_id")
            item_code = str(mr.get("item_code") or "")
            item_name = str(mr.get("item_name") or "")
            spec = str(mr.get("spec") or "")
            unit = str(mr.get("unit") or "")
            unit_price = to_decimal(mr.get("unit_price"), default=Decimal("0"))
            qty = to_decimal(r.get("qty_ordered"), default=Decimal("0"))
            remark = str(r.get("remark") or "")
        else:
            item_id = r.get("item_id") or r.get("material_id") or r.get("id")
            item_code = str(r.get("item_code") or r.get("material_code") or "")
            item_name = str(r.get("item_name") or r.get("material_name") or "")
            spec = str(r.get("specification") or r.get("spec") or "")
            unit = str(r.get("unit") or "")
            unit_price = to_decimal(r.get("unit_price"), default=Decimal("0"))
            qty = to_decimal(r.get("qty_ordered"), default=Decimal("0"))
            remark = str(r.get("remark") or "")

        if qty <= 0:
            continue
        if unit_price <= 0:
            bad_name = item_name or item_code or _t("（未命名品項）")
            st.error(_t("品項「{name}」的單價為 0，請去原料主檔修改單價後再儲存。").format(name=bad_name))
            return False

        cleaned.append(
            dict(
                item_id=item_id,
                item_code=item_code,
                item_name=item_name,
                specification=spec,
                unit=unit,
                qty_ordered=qty,
                unit_price=unit_price,
                remark=remark,
            )
        )

    if not cleaned:
        st.error(_t("沒有任何有效的明細列。至少要選一個品項，數量 > 0。"))
        return False

    # 行號重排
    for idx, row in enumerate(cleaned, start=1):
        row["line_no"] = idx

    # 總額
    total = Decimal("0")
    for row in cleaned:
        total += row["qty_ordered"] * row["unit_price"]

    supplier_shortname = str(sup.get("supplier_shortname") or "").strip()
    if not supplier_shortname:
        st.error(_t("供應商簡稱為必填，無法產生採購單號。"))
        return False

    # 單號 & 交期
    order_num = next_order_num(order_date, supplier_shortname)
    if ORDER_HEAD_DUE_COL and not due_date:
        due_date = order_date

    # ---- write DB ----
    eng = _engine()
    with eng.begin() as conn:
        insert_cols = []
        insert_vals = {}

        def add_head(col, val):
            if col in ORDER_HEAD_COLS and val is not None:
                insert_cols.append(col)
                insert_vals[col] = val

        # mandatory-ish
        add_head(ORDER_HEAD_TYPE_COL, "PO")
        add_head(ORDER_HEAD_PURCHASE_CATEGORY_COL, purchase_order_category)
        add_head(ORDER_HEAD_DATE_COL, order_date)
        add_head(ORDER_HEAD_NUM_COL, order_num)

        # common optional columns (best effort)
        add_head("currency_code", currency)
        add_head("currency", currency)
        add_head("total_amount", float(total) if "total_amount" in ORDER_HEAD_COLS else None)
        add_head("amount_total", float(total) if "amount_total" in ORDER_HEAD_COLS else None)
        add_head("total", float(total) if "total" in ORDER_HEAD_COLS else None)
        add_head("due_date", due_date)
        add_head("remark", head_remark)

        # supplier fields
        if "supplier_id" in ORDER_HEAD_COLS:
            add_head("supplier_id", int(supplier_id))
        if "supplier_code" in ORDER_HEAD_COLS and "supplier_code" in sup.index:
            add_head("supplier_code", sup.get("supplier_code"))
        if "supplier_shortname" in ORDER_HEAD_COLS and "supplier_shortname" in sup.index:
            add_head("supplier_shortname", sup.get("supplier_shortname"))
        if "supplier_name" in ORDER_HEAD_COLS and "supplier_name" in sup.index:
            add_head("supplier_name", sup.get("supplier_name"))

        # 建檔人：依目前登入者寫入；最後修改人保留空白，等真的修改時才寫入。
        if ORDER_HEAD_CREATED_BY_COL and ORDER_HEAD_CREATED_BY_COL not in insert_cols:
            insert_cols.append(ORDER_HEAD_CREATED_BY_COL)
            insert_vals[ORDER_HEAD_CREATED_BY_COL] = _current_user_id()

        cols_sql = ", ".join([sql_ident(c) for c in insert_cols])
        vals_sql = ", ".join([f":{c}" for c in insert_cols])

        conn.execute(text(f"INSERT INTO `{ORDER_HEAD}` ({cols_sql}) VALUES ({vals_sql})"), insert_vals)
        new_id = conn.execute(text("SELECT LAST_INSERT_ID() AS id")).fetchone()[0]

        for i, row in enumerate(cleaned, start=1):
            insert_cols = []
            insert_vals = {}

            def add_item(col, val):
                if col in ORDER_ITEM_COLS and val is not None:
                    insert_cols.append(col)
                    insert_vals[col] = val

            add_item(ORDER_ITEM_ORDER_ID_COL, int(new_id))

            # material id
            if ORDER_ITEM_MATERIAL_ID_COL in ORDER_ITEM_COLS and row["item_id"] is not None:
                add_item(ORDER_ITEM_MATERIAL_ID_COL, row["item_id"])

            add_item(ORDER_ITEM_MATERIAL_CODE_COL, row["item_code"])
            add_item(ORDER_ITEM_MATERIAL_NAME_COL, row["item_name"])
            add_item(ORDER_ITEM_SPEC_COL, row["specification"])
            add_item(ORDER_ITEM_UNIT_COL, row["unit"] or None)
            add_item(ORDER_ITEM_QTY_COL, float(row["qty_ordered"]))
            add_item(ORDER_ITEM_PRICE_COL, float(row["unit_price"]))
            add_item(ORDER_ITEM_REMARK_COL, row["remark"])

            if ORDER_ITEM_LINE_COL:
                add_item(ORDER_ITEM_LINE_COL, int(row["line_no"]))

            # amount/subtotal often computed; avoid inserting if present
            if ORDER_ITEM_AMOUNT_COL and ORDER_ITEM_AMOUNT_COL in insert_cols:
                insert_cols.remove(ORDER_ITEM_AMOUNT_COL)
                insert_vals.pop(ORDER_ITEM_AMOUNT_COL, None)

            cols_sql = ", ".join([sql_ident(c) for c in insert_cols])
            vals_sql = ", ".join([f":{c}" for c in insert_cols])
            conn.execute(text(f"INSERT INTO `{ORDER_ITEM}` ({cols_sql}) VALUES ({vals_sql})"), insert_vals)

    st.success(f"{_t('✅ 已建立採購單：')}{order_num}")
    # 保存剛建立的採購單，供列印使用
    st.session_state["po_last_created_order_id"] = int(new_id)
    st.session_state["po_last_created_order_num"] = str(order_num)

    # 清空購物車（保留供應商、日期，方便連續開單）
    st.session_state["po_cart_lines"] = []
    return True
ORDER_HEAD_ID_COL = first_existing(ORDER_HEAD_COLS, ["order_id", "id", "head_id", "doc_id"]) or "order_id"
ORDER_ITEM_ID_COL = first_existing(ORDER_ITEM_COLS, ["order_item_id", "id", "item_row_id", "line_id"]) or "order_item_id"

ORDER_HEAD_SUPPLIER_ID_COL = first_existing(ORDER_HEAD_COLS, ["supplier_id", "supplier"]) or "supplier_id"
ORDER_HEAD_SUPPLIER_NAME_COL = first_existing(ORDER_HEAD_COLS, ["supplier_name", "supplier_shortname", "supplier_fullname", "supplier"]) or "supplier_name"
ORDER_HEAD_DATE_COL = first_existing(ORDER_HEAD_COLS, ["order_date", "doc_date", "created_at"]) or "order_date"
ORDER_HEAD_NUM_COL = first_existing(ORDER_HEAD_COLS, ["order_num", "doc_no", "number"]) or "order_num"
ORDER_HEAD_STATUS_COL = first_existing(ORDER_HEAD_COLS, ["status", "state"]) or None


def render_po_status_badge(status_value: str) -> None:
    s = str(status_value or "").strip()
    s_norm = s.lower()
    if s_norm == "have arrived":
        bg = "#e8f7ee"
        bd = "#8fd19e"
        fg = "#1b5e20"
    elif s_norm == "partial arrival":
        bg = "#fff4e5"
        bd = "#ffcc80"
        fg = "#a15c00"
    elif s_norm == "not delivered":
        bg = "#fdecea"
        bd = "#f5a3a3"
        fg = "#9f1c1c"
    else:
        bg = "#f3f4f6"
        bd = "#d1d5db"
        fg = "#374151"

    label = _t_status(s)
    st.markdown(
        f"""
        <div style="margin-top: 0.15rem;">
            <div style="font-size:0.92rem; color:#374151; margin-bottom:0.35rem;">{_t("狀態（系統自動判定）")}</div>
            <span style="
                display:inline-block;
                padding:0.38rem 0.8rem;
                border-radius:999px;
                border:1px solid {bd};
                background:{bg};
                color:{fg};
                font-weight:700;
                font-size:0.94rem;
                line-height:1.2;
            ">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def format_po_status_for_grid(v):
    s = str(v or "").strip()
    s_norm = s.lower()
    if s_norm == "have arrived":
        return f"🟢 {_t('已到貨')}"
    elif s_norm == "partial arrival":
        return f"🟠 {_t('部分到貨')}"
    elif s_norm == "not delivered":
        return f"🔴 {_t('未交貨')}"
    return f"⚪ {_t_status(s)}" if s else ""

ORDER_HEAD_TOTAL_COL = first_existing(ORDER_HEAD_COLS, ["total_amount", "amount_total", "total"]) or None
ORDER_HEAD_DUE_COL = first_existing(ORDER_HEAD_COLS, ["due_date", "eta_date", "delivery_date"]) or None
ORDER_HEAD_REMARK_COL = first_existing(ORDER_HEAD_COLS, ["remark", "note", "memo"]) or None

ORDER_ITEM_ORDER_ID_COL = first_existing(ORDER_ITEM_COLS, ["order_id", "head_id", "doc_id"]) or "order_id"
ORDER_ITEM_MATERIAL_ID_COL = first_existing(ORDER_ITEM_COLS, ["material_id", "material_item_id", "item_id"]) or "material_id"
ORDER_ITEM_MATERIAL_CODE_COL = first_existing(ORDER_ITEM_COLS, ["material_code", "item_code", "code"]) or "material_code"
ORDER_ITEM_MATERIAL_NAME_COL = first_existing(ORDER_ITEM_COLS, ["material_name", "item_name", "name"]) or "material_name"
ORDER_ITEM_SPEC_COL = first_existing(ORDER_ITEM_COLS, ["spec", "specification"]) or "spec"
ORDER_ITEM_UNIT_COL = first_existing(ORDER_ITEM_COLS, ["unit"]) or "unit"
ORDER_ITEM_QTY_COL = first_existing(ORDER_ITEM_COLS, ["qty_ordered", "qty", "quantity"]) or "qty_ordered"
ORDER_ITEM_REMARK_COL = first_existing(ORDER_ITEM_COLS, ["remark", "note", "memo"]) or "remark"

@st.cache_data(ttl=60)
def count_po_heads(
    keyword: str = "",
    supplier_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> int:
    kw = (keyword or "").strip()
    where = "WHERE order_type='PO'"
    params: dict = {}

    if kw:
        where += f" AND ({sql_ident(ORDER_HEAD_NUM_COL)} LIKE :kw OR {sql_ident(ORDER_HEAD_SUPPLIER_NAME_COL)} LIKE :kw)"
        params["kw"] = f"%{kw}%"

    if supplier_id is not None and ORDER_HEAD_SUPPLIER_ID_COL in ORDER_HEAD_COLS:
        where += f" AND {sql_ident(ORDER_HEAD_SUPPLIER_ID_COL)}=:sid"
        params["sid"] = int(supplier_id)

    if date_from is not None:
        where += f" AND {sql_ident(ORDER_HEAD_DATE_COL)}>=:d_from"
        params["d_from"] = date_from
    if date_to is not None:
        # make end inclusive by using < (date_to + 1 day)
        where += f" AND {sql_ident(ORDER_HEAD_DATE_COL)}<:d_to"
        params["d_to"] = date_to + timedelta(days=1)

    sql = f"SELECT COUNT(*) FROM `{ORDER_HEAD}` {where}"
    eng = _engine()
    with eng.begin() as conn:
        return int(conn.execute(text(sql), params).fetchone()[0])


@st.cache_data(ttl=60)
def load_po_heads(
    keyword: str = "",
    supplier_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> pd.DataFrame:
    kw = (keyword or "").strip()
    where = f"WHERE h.{sql_ident(ORDER_HEAD_TYPE_COL)}='PO'"
    params: dict = {}

    if kw:
        where += f" AND (h.{sql_ident(ORDER_HEAD_NUM_COL)} LIKE :kw OR h.{sql_ident(ORDER_HEAD_SUPPLIER_NAME_COL)} LIKE :kw)"
        params["kw"] = f"%{kw}%"

    if supplier_id is not None and ORDER_HEAD_SUPPLIER_ID_COL in ORDER_HEAD_COLS:
        where += f" AND h.{sql_ident(ORDER_HEAD_SUPPLIER_ID_COL)}=:sid"
        params["sid"] = int(supplier_id)

    if date_from is not None:
        where += f" AND h.{sql_ident(ORDER_HEAD_DATE_COL)}>=:d_from"
        params["d_from"] = date_from
    if date_to is not None:
        where += f" AND h.{sql_ident(ORDER_HEAD_DATE_COL)}<:d_to"
        params["d_to"] = date_to + timedelta(days=1)

    cols = [
        f"h.{sql_ident(ORDER_HEAD_ID_COL)} AS order_id",
        f"h.{sql_ident(ORDER_HEAD_NUM_COL)} AS order_num",
        f"h.{sql_ident(ORDER_HEAD_DATE_COL)} AS order_date",
        f"h.{sql_ident(ORDER_HEAD_PURCHASE_CATEGORY_COL)} AS purchase_order_category",
    ]
    if ORDER_HEAD_SUPPLIER_ID_COL in ORDER_HEAD_COLS:
        cols.append(f"h.{sql_ident(ORDER_HEAD_SUPPLIER_ID_COL)} AS supplier_id")
    cols.append(f"h.{sql_ident(ORDER_HEAD_SUPPLIER_NAME_COL)} AS supplier_name")
    if ORDER_HEAD_STATUS_COL:
        cols.append(f"h.{sql_ident(ORDER_HEAD_STATUS_COL)} AS status")
    if ORDER_HEAD_TOTAL_COL:
        cols.append(f"h.{sql_ident(ORDER_HEAD_TOTAL_COL)} AS total_amount")

    # 母表稽核欄位固定放在最右邊：建檔人員、最後修改人
    cols.append(f"{_audit_user_display_expr('h', ORDER_HEAD_CREATED_BY_COL)} AS created_by_name")
    cols.append(f"{_audit_updated_display_expr('h')} AS updated_by_name")

    select_cols = ",\n          ".join(cols)

    sql = f"""
        SELECT
          {select_cols}
        FROM `{ORDER_HEAD}` h
        {where}
        ORDER BY h.{sql_ident(ORDER_HEAD_DATE_COL)} DESC, h.{sql_ident(ORDER_HEAD_ID_COL)} DESC
        LIMIT :lim OFFSET :off
    """
    params["lim"] = int(limit)
    params["off"] = int(offset)
    return df_from_sql(sql, params)

@st.cache_data(ttl=60)
def load_po_items(order_id: int) -> pd.DataFrame:
    """Load PO items for given order_id (includes material_barcode for PDF Code39).
    Uses safe column list join to avoid comma bugs."""
    oi = "oi"
    m = "m"

    cols: list[str] = [
        f"{oi}.{sql_ident(ORDER_ITEM_ID_COL)} AS order_item_id",
    ]
    if ORDER_ITEM_LINE_COL:
        cols.append(f"{oi}.{sql_ident(ORDER_ITEM_LINE_COL)} AS line_no")

    cols.extend([
        f"{oi}.{sql_ident(ORDER_ITEM_MATERIAL_ID_COL)} AS material_id",
        f"{oi}.{sql_ident(ORDER_ITEM_MATERIAL_CODE_COL)} AS material_code",
        f"{oi}.{sql_ident(ORDER_ITEM_MATERIAL_NAME_COL)} AS material_name",
        f"{oi}.{sql_ident(ORDER_ITEM_SPEC_COL)} AS spec",
        f"{oi}.{sql_ident(ORDER_ITEM_UNIT_COL)} AS unit",
        f"{oi}.{sql_ident(ORDER_ITEM_QTY_COL)} AS qty_ordered",
        f"{oi}.{sql_ident(ORDER_ITEM_PRICE_COL)} AS unit_price",
        f"{oi}.{sql_ident(ORDER_ITEM_REMARK_COL)} AS remark",
    ])

    # barcode from material master (preferred)
    if MATERIAL_BARCODE_COL and MATERIAL_BARCODE_COL in MATERIAL_COLS:
        cols.append(f"{m}.{sql_ident(MATERIAL_BARCODE_COL)} AS material_barcode")
    else:
        cols.append("NULL AS material_barcode")

    select_cols = ",\n          ".join(cols)

    sql = f"""
        SELECT
          {select_cols}
        FROM `{ORDER_ITEM}` {oi}
        LEFT JOIN `{MATERIAL}` {m}
          ON {m}.{sql_ident(MATERIAL_PK_COL)} = {oi}.{sql_ident(ORDER_ITEM_MATERIAL_ID_COL)}
        WHERE {oi}.{sql_ident(ORDER_ITEM_ORDER_ID_COL)}=:oid
        ORDER BY {oi}.{sql_ident(ORDER_ITEM_LINE_COL) if ORDER_ITEM_LINE_COL else sql_ident(ORDER_ITEM_ID_COL)}
    """
    return df_from_sql(sql, {"oid": int(order_id)})

def _recalc_and_update_po_total(conn, order_id: int):
    # 權限已在 apply_po_item_changes / save_new_order 等入口檢查。
    # 這裡是內部重算總額，不要再額外要求 edit，避免刪除明細時被 edit 權限擋住。
    if not ORDER_HEAD_TOTAL_COL:
        return
    sql_sum = f"""
        SELECT COALESCE(SUM({sql_ident(ORDER_ITEM_QTY_COL)}*{sql_ident(ORDER_ITEM_PRICE_COL)}),0)
        FROM `{ORDER_ITEM}`
        WHERE {sql_ident(ORDER_ITEM_ORDER_ID_COL)}=:oid
    """
    total = conn.execute(text(sql_sum), {"oid": int(order_id)}).fetchone()[0]
    conn.execute(
        text(f"UPDATE `{ORDER_HEAD}` SET {sql_ident(ORDER_HEAD_TOTAL_COL)}=:t WHERE {sql_ident(ORDER_HEAD_ID_COL)}=:oid"),
        {"t": float(total), "oid": int(order_id)},
    )

def apply_po_item_changes(order_id: int, updates, delete_ids):
    """updates: [{'order_item_id':..,'qty_ordered':..,'remark':..}]"""
    if delete_ids:
        auth.require_delete(PAGE_KEY)
    elif updates:
        auth.require_edit(PAGE_KEY)
    else:
        return

    eng = _engine()
    with eng.begin() as conn:
        for did in delete_ids:
            conn.execute(
                text(f"DELETE FROM `{ORDER_ITEM}` WHERE {sql_ident(ORDER_ITEM_ID_COL)}=:id AND {sql_ident(ORDER_ITEM_ORDER_ID_COL)}=:oid"),
                {"id": int(did), "oid": int(order_id)},
            )
        for u in updates:
            cols = []
            params = {"id": int(u["order_item_id"]), "oid": int(order_id)}
            if "qty_ordered" in u and ORDER_ITEM_QTY_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_QTY_COL)}=:q")
                params["q"] = float(to_decimal(u["qty_ordered"], default=Decimal('0')))
            if "remark" in u and ORDER_ITEM_REMARK_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_REMARK_COL)}=:r")
                params["r"] = str(u["remark"] or "")
            # allow material fields update
            if "material_id" in u and ORDER_ITEM_MATERIAL_ID_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_MATERIAL_ID_COL)}=:mid")
                params["mid"] = int(u["material_id"])
            if "material_code" in u and ORDER_ITEM_MATERIAL_CODE_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_MATERIAL_CODE_COL)}=:mcode")
                params["mcode"] = str(u.get("material_code") or "")
            if "material_name" in u and ORDER_ITEM_MATERIAL_NAME_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_MATERIAL_NAME_COL)}=:mname")
                params["mname"] = str(u.get("material_name") or "")
            if "spec" in u and ORDER_ITEM_SPEC_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_SPEC_COL)}=:mspec")
                params["mspec"] = str(u.get("spec") or "")
            if "unit" in u and ORDER_ITEM_UNIT_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_UNIT_COL)}=:munit")
                params["munit"] = str(u.get("unit") or "")
            if "unit_price" in u and ORDER_ITEM_PRICE_COL in ORDER_ITEM_COLS:
                cols.append(f"{sql_ident(ORDER_ITEM_PRICE_COL)}=:mprice")
                params["mprice"] = float(to_decimal(u.get("unit_price"), default=Decimal('0')))
            if cols:
                conn.execute(
                    text(
                        f"UPDATE `{ORDER_ITEM}` SET {', '.join(cols)} "
                        f"WHERE {sql_ident(ORDER_ITEM_ID_COL)}=:id AND {sql_ident(ORDER_ITEM_ORDER_ID_COL)}=:oid"
                    ),
                    params,
                )
        _recalc_and_update_po_total(conn, order_id)
        audit_sets, audit_params = _order_head_audit_set_sql()
        if audit_sets:
            conn.execute(
                text(f"UPDATE `{ORDER_HEAD}` SET {', '.join(audit_sets)} WHERE {sql_ident(ORDER_HEAD_ID_COL)}=:oid"),
                {**audit_params, "oid": int(order_id)},
            )

def apply_po_head_changes(order_id: int, due, remark, purchase_order_category: str) -> None:
    auth.require_edit(PAGE_KEY)
    category = normalize_purchase_order_category(purchase_order_category)
    if category not in PURCHASE_ORDER_CATEGORY_OPTIONS:
        raise ValueError(_t("採購單類別不正確，請重新選擇。"))

    eng = _engine()
    with eng.begin() as conn:
        sets = []
        params = {"oid": int(order_id)}

        current_category = conn.execute(
            text(f"SELECT {sql_ident(ORDER_HEAD_PURCHASE_CATEGORY_COL)} FROM `{ORDER_HEAD}` "
                 f"WHERE {sql_ident(ORDER_HEAD_ID_COL)}=:oid"),
            params,
        ).fetchone()
        current_category = str(current_category[0] or PURCHASE_ORDER_CATEGORY_GENERAL).strip() if current_category else PURCHASE_ORDER_CATEGORY_GENERAL
        if category != current_category:
            receipt_exists = conn.execute(
                text("""
                    SELECT 1
                    FROM material_stock_io_head
                    WHERE order_id = :oid
                      AND io_type = 'IN'
                    LIMIT 1
                """),
                params,
            ).fetchone()
            if receipt_exists:
                raise ValueError(_t("此採購單已有入庫紀錄；為避免應付帳款不一致，不能再變更單據類型。"))
            sets.append(f"{sql_ident(ORDER_HEAD_PURCHASE_CATEGORY_COL)}=:purchase_category")
            params["purchase_category"] = category

        if ORDER_HEAD_DUE_COL and due is not None:
            sets.append(f"{sql_ident(ORDER_HEAD_DUE_COL)}=:d")
            params["d"] = due
        if ORDER_HEAD_REMARK_COL and remark is not None:
            sets.append(f"{sql_ident(ORDER_HEAD_REMARK_COL)}=:r")
            params["r"] = remark
        audit_sets, audit_params = _order_head_audit_set_sql()
        if audit_sets:
            sets.extend(audit_sets)
            params.update(audit_params)
        if sets:
            conn.execute(
                text(f"UPDATE `{ORDER_HEAD}` SET {', '.join(sets)} WHERE {sql_ident(ORDER_HEAD_ID_COL)}=:oid"),
                params,
            )


SEARCH_MODE_BY_SUPPLIER = "by_supplier"
SEARCH_MODE_BY_DATE = "by_date"
MODE_CREATE = "create"
MODE_EDIT = "edit"

def _search_mode_options():
    return {
        SEARCH_MODE_BY_SUPPLIER: _t("依供應商搜尋"),
        SEARCH_MODE_BY_DATE: _t("依開立時間搜尋"),
    }

def _mode_options():
    return {
        MODE_CREATE: _t("新增採購單"),
        MODE_EDIT: _t("修改採購單"),
    }

def _t_status(status_value: str) -> str:
    s = str(status_value or "").strip()
    s_norm = s.lower()
    if s_norm == "have arrived":
        return _t("已到貨")
    elif s_norm == "partial arrival":
        return _t("部分到貨")
    elif s_norm == "not delivered":
        return _t("未交貨")
    return s or _t("未設定")

def init_state():
    # list / edit selection
    st.session_state.setdefault("po_selected_order_id", None)
    st.session_state.setdefault("po_list_keyword", "")
    st.session_state.setdefault("po_selected_item_ids", [])

    # new PO defaults
    st.session_state.setdefault("po_currency", "VND")

    st.session_state.setdefault("po_order_num_preview", "")

    # new PO cart (single-line add UX)
    st.session_state.setdefault("po_cart_supplier_id", None)
    st.session_state.setdefault("po_cart_lines", [])

    # legacy: keep for backward compat (no longer used in new UI)
    st.session_state.setdefault("po_line_count", 1)

    # single-line input state
    st.session_state.setdefault("po_new_item", "未選")
    st.session_state.setdefault("po_new_qty", "0")
    st.session_state.setdefault("po_new_remark", "")
    st.session_state.setdefault("po_new_spec", "")
    st.session_state.setdefault("po_new_unit", "")
    st.session_state.setdefault("po_new_price", "0")

    # reset new-line inputs (set by add action, applied before widgets instantiate)
    if st.session_state.pop("po_reset_new_line", False):
        st.session_state["po_new_item"] = "未選"
        st.session_state["po_new_qty"] = "0"
        st.session_state["po_new_remark"] = ""
        st.session_state["po_new_spec"] = ""
        st.session_state["po_new_unit"] = ""
        st.session_state["po_new_price"] = "0"

    # one-shot flash message
    st.session_state.setdefault("po_flash", None)

# ---------- page ----------
init_state()

# -------------------------
# Print helpers (PDF preview + browser print dialog)
# -------------------------


def _pdf_wrap_text(text: str, font_name: str, font_size: float, max_width: float, max_lines: int = 2) -> list[str]:
    """Wrap text to fit inside a PDF table cell width.
    CJK/Vietnamese friendly: tries word wrapping first, then character wrapping.
    """
    text = str(text or "").strip()
    if not text:
        return [""]

    def width(t: str) -> float:
        try:
            return pdfmetrics.stringWidth(t, font_name, font_size)
        except Exception:
            return len(t) * font_size * 0.5

    words = text.split()
    lines: list[str] = []

    # Word wrap first. If a word itself is too long, split by character.
    if len(words) > 1:
        cur = ""
        for w in words:
            trial = w if not cur else f"{cur} {w}"
            if width(trial) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    else:
        lines = [text]

    # Character wrap any over-wide line.
    fixed: list[str] = []
    for line in lines:
        if width(line) <= max_width:
            fixed.append(line)
            continue
        cur = ""
        for ch in line:
            trial = cur + ch
            if width(trial) <= max_width:
                cur = trial
            else:
                if cur:
                    fixed.append(cur)
                cur = ch
        if cur:
            fixed.append(cur)

    lines = fixed[:max_lines]
    if len(fixed) > max_lines and lines:
        # Add ellipsis without exceeding width.
        ell = "…"
        last = lines[-1]
        while last and width(last + ell) > max_width:
            last = last[:-1]
        lines[-1] = (last + ell) if last else ell
    return lines or [""]


def _pdf_draw_wrapped_cell(c, text: str, x: float, y_top: float, w: float, h: float,
                           font_name: str, font_size: float = 8.0,
                           max_lines: int = 2, left_pad: float = 2*mm,
                           top_pad: float = 2.8*mm, line_gap: float = 3.8*mm,
                           align: str = "left") -> None:
    """Draw wrapped text inside one PDF table cell. y_top is the top border y of the cell."""
    c.setFont(font_name, font_size)
    lines = _pdf_wrap_text(text, font_name, font_size, max(1, w - left_pad*2), max_lines=max_lines)
    y_text = y_top - top_pad
    min_y = y_top - h + 1.5*mm
    for line in lines:
        if y_text < min_y:
            break
        if align == "center":
            c.drawCentredString(x + w / 2, y_text, line)
        else:
            c.drawString(x + left_pad, y_text, line)
        y_text -= line_gap

def build_po_pdf_from_db(order_id: int, include_prices: bool = True) -> bytes:
    """Generate an A5 PDF for a PO order_id.

    include_prices=False is for warehouse copies: it keeps quantities and remarks,
    but hides unit price, line amount, and total amount.
    """
    if not _HAS_REPORTLAB:
        raise RuntimeError(_t("reportlab 未安裝，無法產生 PDF。請先 pip install reportlab"))

    head_df = df_from_sql(
        f"SELECT * FROM `{ORDER_HEAD}` WHERE {sql_ident(ORDER_HEAD_ID_COL)}=:oid LIMIT 1",
        {"oid": int(order_id)},
    )
    if head_df.empty:
        raise RuntimeError(_t("找不到採購單抬頭資料（order_head）。"))
    head = head_df.iloc[0].to_dict()

    items = load_po_items(int(order_id))
    if items is None or getattr(items, "empty", True):
        items = pd.DataFrame()

    # --- map head fields (best effort, tolerate missing cols) ---
    order_num = str(head.get(ORDER_HEAD_NUM_COL, "") or "")
    order_date = str(head.get(ORDER_HEAD_DATE_COL, "") or "")
    supplier_name = str(head.get(ORDER_HEAD_SUPPLIER_NAME_COL, "") or "")
    due_date = str(head.get(ORDER_HEAD_DUE_COL, "") or "") if ORDER_HEAD_DUE_COL else ""
    remark = str(head.get(ORDER_HEAD_REMARK_COL, "") or "") if ORDER_HEAD_REMARK_COL else ""
    total_amt = head.get(ORDER_HEAD_TOTAL_COL, None) if ORDER_HEAD_TOTAL_COL else None

    # --- build PDF ---
    buf = io.BytesIO()
    # The existing layout is designed in A4 coordinates.  Keep it in its normal
    # reading orientation, but place it on a landscape A5 sheet.
    page_size = landscape(A5)
    c = canvas.Canvas(buf, pagesize=page_size)
    # Set both the PDF media box and its print preference to landscape A5.  This
    # keeps compatible PDF viewers from scaling it to the printer's A4 default.
    c.setPageSize(page_size)
    c.setViewerPreference("PrintScaling", "None")
    # Landscape A5 has the same useful width as the former A4 coordinate grid.
    # Redraw it in native A5 coordinates instead of shrinking a portrait page:
    # this fills the sheet without horizontally/vertically distorting text.
    W, H = page_size

    L, R, T, B = 8*mm, 8*mm, 8*mm, 8*mm
    x0, x1 = L, W - R
    y = H - T

    # Title band (like your screenshot)
    band_h = 16*mm
    c.setFillColorRGB(0.70, 0.78, 0.90)
    c.rect(x0, y - band_h, x1 - x0, band_h, stroke=0, fill=1)

    # Title text: user wants "原料訂購單" in black
    c.setFillColor(colors.black)
    c.setFont(PDF_FONT_BOLD, 15)
    c.drawCentredString((x0+x1)/2, y - 6.5*mm, _t("原料訂購單"))
    c.setFillColor(colors.black)
    c.setFont(PDF_FONT_REG, 8)
    c.drawCentredString((x0+x1)/2, y - 12*mm, "Purchase Order / Phiếu đặt mua nguyên liệu")
    c.setFillColor(colors.black)
    y -= band_h + 3*mm

    # Company block (left)
    c.setFont(PDF_FONT_BOLD, 10)
    c.drawString(x0, y, _t("香巴拉責任有限公司"))
    c.setFont(PDF_FONT_REG, 10)
    y -= 5*mm
    c.setFont(PDF_FONT_REG, 9)
    c.drawString(x0, y, "CÔNG TY TNHH SHANBHALA")
    y -= 6*mm
    c.setFont(PDF_FONT_REG, 8)
    c.drawString(x0, y, _t("地址 / Address："))
    y -= 4*mm
    c.setFont(PDF_FONT_REG, 7.6)
    c.drawString(x0, y, "Lô J1, Đường NA3-DA3, KCN Mỹ phước 2, P. Mỹ Phước, Tx. ")
    y -= 3*mm
    c.drawString(x0, y, "Bến Cát, T. Bình Dương")
    y -= 3*mm
    c.setFont(PDF_FONT_REG, 8)
    c.drawString(x0, y, _t("電話 / Tel：                 Email："))
    y -= 3*mm

    # PO info box (right)
    box_w, box_h = 62*mm, 22*mm
    bx = x1 - box_w
    # The PO barcode was removed, so move the information box upward to use
    # that former barcode space and align it with the company information.
    by = y + 24*mm

    c.rect(bx, by - box_h, box_w, box_h, stroke=1, fill=0)
    c.setFont(PDF_FONT_REG, 8)

    labels = [
        ("PO No:", order_num),
        ("Date:", order_date),
        ("Delivery:", due_date),
        ("Terms:", ""),
    ]
    row_h = box_h / 4
    for i, (k,v) in enumerate(labels):
        yy = by - (i+1)*row_h + 1.5*mm
        c.drawString(bx + 1.5*mm, yy, k)
        c.drawString(bx + 18*mm, yy, str(v))
        if i < 3:
            c.line(bx, by - (i+1)*row_h, bx + box_w, by - (i+1)*row_h)

    # Keep the two lower information panels close to the Tel/Email row.
    y -= 1*mm

    # Supplier / Delivery info box
    info_h = 22*mm
    c.rect(x0, y - info_h, x1 - x0, info_h, stroke=1, fill=0)
    mid = x0 + (x1 - x0)/2
    c.line(mid, y, mid, y - info_h)

    c.setFont(PDF_FONT_BOLD, 8)
    c.drawString(x0 + 1.5*mm, y - 4*mm, _label("收件人資訊 / Supplier"))
    c.drawString(mid + 1.5*mm, y - 4*mm, _label("送貨 / 請款資訊 / Delivery"))

    c.setFont(PDF_FONT_REG, 7.6)
    c.drawString(x0 + 1.5*mm, y - 8*mm, f"{_label('公司 / Company：')}{supplier_name}")
    c.drawString(x0 + 1.5*mm, y - 13*mm, _label("聯絡人 / Attn："))
    c.drawString(x0 + 1.5*mm, y - 18*mm, _label("電話 / Tel："))

    c.drawString(mid + 1.5*mm, y - 8*mm, _label("送貨地 / Ship To："))
    c.setFont(PDF_FONT_REG, 7.1)
    c.drawString(mid + 1.5*mm, y - 12*mm, "Lô J1, Đường NA3-DA3, KCN Mỹ phước 2, P. Mỹ Phước, Tx. Bến")
    c.drawString(mid + 1.5*mm, y - 15.5*mm, "Cát, T. Bình Dương")
    # Keep a long remark inside
    # its printable cell rather than letting ReportLab draw past the right edge.
    note_x = mid + 1.5*mm
    note_text = f"{_label('備註 / Note：')}{remark}"
    note_max_width = x1 - note_x - 2*mm
    note_line = _pdf_wrap_text(note_text, PDF_FONT_REG, 7.2, note_max_width, max_lines=1)[0]
    c.setFont(PDF_FONT_REG, 7.2)
    c.drawString(note_x, y - 19.2*mm, note_line)

    y -= info_h + 4*mm

    # Lines table
    # Header (6 mm) plus six equal 7 mm rows: no residual sliver at the bottom.
    table_h = 48*mm
    c.rect(x0, y - table_h, x1 - x0, table_h, stroke=1, fill=0)

    if include_prices:
        cols = [
            (_t("品名"), 44*mm),
            (_t("規格"), 34*mm),
            (_t("數量"), 14*mm),
            (_t("單位"), 12*mm),
            (_t("單價"), 18*mm),
            (_t("合計"), 20*mm),
            (_t("備註"), (x1-x0) - (44+34+14+12+18+20)*mm),
        ]
    else:
        cols = [
            (_t("品名"), 54*mm),
            (_t("規格"), 42*mm),
            (_t("數量"), 18*mm),
            (_t("單位"), 15*mm),
            (_t("備註"), (x1-x0) - (54+42+18+15)*mm),
        ]
    cx = [x0]
    for _, w in cols[:-1]:
        cx.append(cx[-1] + w)

    xx = x0
    for _, w in cols[:-1]:
        xx += w
        c.line(xx, y, xx, y - table_h)

    header_h = 6*mm
    c.setFillColor(colors.lightgrey)
    c.rect(x0, y - header_h, x1 - x0, header_h, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.setFont(PDF_FONT_BOLD, 8)
    for i, (name, _) in enumerate(cols):
        c.drawString(cx[i] + 1.5*mm, y - 4.2*mm, name)

    # 明細列：加高一點，讓「品名」可以像 Excel 自動換行顯示第二行，避免壓到旁邊規格欄。
    c.setFont(PDF_FONT_REG, 7.4)
    row_h = 7*mm
    max_rows = int((table_h - header_h) // row_h)
    for r in range(max_rows):
        y_line = y - header_h - (r+1)*row_h
        c.line(x0, y_line, x1, y_line)
        if r < len(items):
            ir = items.iloc[r].to_dict()
            item_name = str(ir.get("material_name") or ir.get("item_name") or "")
            spec = str(ir.get("spec") or ir.get("specification") or "")
            qty = ir.get("qty_ordered") or ir.get("qty") or ""
            unit = str(ir.get("unit") or "")
            price = ir.get("unit_price") or ir.get("price") or ""
            amt = ""
            try:
                amt = float(qty) * float(price)
            except Exception:
                amt = ir.get("amount") or ""
            line_remark = str(ir.get("remark") or "")
            # 品名可能很長：限制在品名欄寬內，最多顯示兩行。
            # 這裡不要直接 drawString，否則文字會一路畫到規格欄，現場列印會很難看。
            cell_top = y - header_h - r*row_h
            _pdf_draw_wrapped_cell(
                c, item_name, cx[0], cell_top, cols[0][1], row_h,
                PDF_FONT_REG, font_size=6.6, max_lines=2, top_pad=1.8*mm, line_gap=2.6*mm,
                align="center",
            )

            # Other fields remain single-line and left-aligned.  Warehouse copies
            # omit unit price and line amount to avoid exposing purchase prices.
            vals = [spec, qty, unit, price, amt] if include_prices else [spec, qty, unit]
            for i, v in enumerate(vals, start=1):
                c.setFont(PDF_FONT_REG, 7)
                c.drawString(cx[i] + 1.5*mm, y_line + 2.5*mm, str(v))

            # The final column is the line-item remark, replacing the former barcode.
            remark_col_idx = 6 if include_prices else 4
            _pdf_draw_wrapped_cell(
                c, line_remark, cx[remark_col_idx], cell_top, cols[remark_col_idx][1], row_h,
                PDF_FONT_REG, font_size=6.2, max_lines=2, top_pad=1.8*mm, line_gap=2.6*mm,
            )


    y -= table_h + 3*mm

    # Bottom: total only.  The former standard notes/terms and signature area are
    # intentionally omitted; customers can use the remaining blank space to sign.
    right_w = 55*mm
    rx = x1 - right_w

    if include_prices:
        c.setFont(PDF_FONT_BOLD, 8)
        c.drawString(rx + 1.5*mm, y - 4*mm, _label("總計 / Total："))
        if total_amt is None:
            # best effort sum
            try:
                total_amt = float(items.get("qty_ordered", 0).fillna(0).astype(float) * items.get("unit_price", 0).fillna(0).astype(float)).sum()
            except Exception:
                total_amt = ""
        c.drawRightString(x1 - 1.5*mm, y - 4*mm, str(total_amt))

    c.showPage()
    c.save()
    return buf.getvalue()


def _render_pdf_preview_and_print(pdf_bytes: bytes, key_prefix: str = "po_print", open_label: str = "新分頁開啟PDF", download_label: str | None = None):
    """PDF 列印控制列
    - 新分頁開啟PDF：用 Streamlit 原生 link_button 開啟 PDF
    - 下載PDF(備用)：用 Streamlit 原生 download_button 下載 PDF

    重點：
    兩顆按鈕都改用 Streamlit 原生元件，不再混用 components.html。
    這樣左右按鈕的高度與垂直位置會自然對齊。
    """
    import hashlib
    import streamlit as st

    if not pdf_bytes:
        st.warning(_t("沒有可預覽的 PDF 內容。"))
        return

    pdf_hash = hashlib.md5(pdf_bytes).hexdigest()[:12]
    pdf_filename = f"PO_{key_prefix}_{pdf_hash}.pdf"
    if download_label is None:
        download_label = _t("下載PDF(備用)")

    url = None
    try:
        url = write_pdf_and_get_url(pdf_bytes, filename=pdf_filename)
    except Exception as e:
        st.warning(f"{_t('無法啟動本機 PDF 預覽連結：')}{e}")

    # 兩顆按鈕都用 Streamlit 原生元件，避免 HTML 按鈕與原生按鈕基準線不同造成歪斜。
    c1, c2 = st.columns(2)

    with c1:
        if url:
            st.link_button(
                open_label,
                url,
                use_container_width=True,
            )
        else:
            st.button(
                open_label,
                use_container_width=True,
                disabled=True,
                key=f"{key_prefix}_open_disabled",
            )

    with c2:
        st.download_button(
            download_label,
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True,
            key=f"{key_prefix}_dl",
        )

st.markdown(f"## B02 {_t('採購單（清單 / 新增 / 修改）')}")

# ===== PO List (always visible) =====
st.markdown(f"### {_t('採購單清單')}")

# --- Search / paging controls ---
st.session_state.setdefault("po_list_mode", SEARCH_MODE_BY_SUPPLIER)
st.session_state.setdefault("po_list_keyword", "")
st.session_state.setdefault("po_list_page_size", 20)
st.session_state.setdefault("po_list_page", 0)

search_mode_options = _search_mode_options()

r1c1, r1c2, r1c3, r1c4 = st.columns([1.55, 3.1, 3.3, 1.3], vertical_alignment="bottom")
with r1c1:
    po_list_mode = st.selectbox(
        _t("搜尋模式"),
        options=list(search_mode_options.keys()),
        format_func=lambda x: search_mode_options.get(x, x),
        key="po_list_mode",
    )
with r1c2:
    if po_list_mode == SEARCH_MODE_BY_SUPPLIER:
        suppliers_for_list = load_suppliers(active_only=False)
        sup_opts = [_t("全部")]
        sup_id_map: dict[str, int] = {}
        if not suppliers_for_list.empty and "supplier_id" in suppliers_for_list.columns:
            for _, r in suppliers_for_list.iterrows():
                sid = int(r["supplier_id"])
                code = str(r.get("supplier_code", "") or "")
                name = str(r.get("supplier_name", "") or "")
                label = f"{sid} | {code} | {name}".strip()
                sup_opts.append(label)
                sup_id_map[label] = sid
        supplier_label = st.selectbox(_t("供應商"), sup_opts, key="po_list_supplier_label")
    else:
        d1, d2 = st.columns(2)
        with d1:
            st.date_input(_t("起"), key="po_list_date_from", value=date.today() - timedelta(days=30))
        with d2:
            st.date_input(_t("迄"), key="po_list_date_to", value=date.today())
with r1c3:
    st.text_input(
        _t("關鍵字（採購單號 / 供應商，可空）"),
        key="po_list_keyword",
        placeholder=_t("例如：SU260126 或 供應商名稱"),
    )
with r1c4:
    # 保留欄位標籤的高度，讓按鈕與同列下拉選單的輸入框對齊。
    st.markdown("<div style='height: 1.55rem;'></div>", unsafe_allow_html=True)
    if st.button(_t("重新整理"), use_container_width=True):
        load_po_heads.clear()
        count_po_heads.clear()
        load_po_items.clear()

kw = (st.session_state.get("po_list_keyword") or "").strip()

supplier_id_filter: int | None = None
date_from: date | None = None
date_to: date | None = None

if st.session_state["po_list_mode"] == SEARCH_MODE_BY_SUPPLIER:
    label = st.session_state.get("po_list_supplier_label", _t("全部"))
    if label and label != _t("全部"):
        # sup_id_map exists only inside the column scope; rebuild safely
        suppliers_for_list = load_suppliers(active_only=False)
        if not suppliers_for_list.empty and "supplier_id" in suppliers_for_list.columns:
            # try parse "id | ..."
            try:
                supplier_id_filter = int(str(label).split("|")[0].strip())
            except Exception:
                supplier_id_filter = None
else:
    date_from = st.session_state.get("po_list_date_from")
    date_to = st.session_state.get("po_list_date_to")
    # normalize: if user swaps, fix it
    if isinstance(date_from, date) and isinstance(date_to, date) and date_from > date_to:
        date_from, date_to = date_to, date_from

# reset paging when filters change
page_size = int(st.session_state.get("po_list_page_size", 20))
filter_sig = (st.session_state.get("po_list_mode"), kw, supplier_id_filter, date_from, date_to, page_size)
if st.session_state.get("po_list_filter_sig") != filter_sig:
    st.session_state["po_list_filter_sig"] = filter_sig
    st.session_state["po_list_page"] = 0

total_rows = count_po_heads(keyword=kw, supplier_id=supplier_id_filter, date_from=date_from, date_to=date_to)
page = int(st.session_state.get("po_list_page", 0))
max_page = 0 if total_rows == 0 else (total_rows - 1) // page_size
page = max(0, min(page, max_page))
st.session_state["po_list_page"] = page

pg_spacer, p1, p2, p3, p4 = st.columns([4.98, 1.15, 0.92, 1.15, 1.8], vertical_alignment="center")
with p1:
    if st.button(_t("上一頁"), disabled=(page <= 0), use_container_width=True):
        st.session_state["po_list_page"] = max(0, page - 1)
        st.rerun()
with p2:
    inner_left, inner_mid, inner_right = st.columns([0.1, 0.8, 0.1])
    with inner_mid:
        page_size = st.selectbox("", [10, 20, 30, 50, 100], key="po_list_page_size", label_visibility="collapsed")
with p3:
    if st.button(_t("下一頁"), disabled=(page >= max_page), use_container_width=True):
        st.session_state["po_list_page"] = min(max_page, page + 1)
        st.rerun()
with p4:
    st.caption(f"{_t('第 ')}{page+1} / {max_page+1 if total_rows else 1} {_t('頁 · 共 ')}{total_rows} {_t('筆')}")

page_size = int(page_size)

po_heads = load_po_heads(
    keyword=kw,
    supplier_id=supplier_id_filter,
    date_from=date_from,
    date_to=date_to,
    limit=page_size,
    offset=page * page_size,
)

if po_heads.empty:
    st.info(_t("目前沒有符合條件的採購單（order_type='PO'）。"))
else:
    df_list = po_heads.copy()
    df_list.insert(0, _t("選取"), False)
    if "order_date" in df_list.columns:
        df_list["order_date"] = df_list["order_date"].astype(str)
    if "status" in df_list.columns:
        df_list["status_raw"] = df_list["status"]
        df_list["status"] = df_list["status"].apply(format_po_status_for_grid)
    if "purchase_order_category" in df_list.columns:
        df_list["purchase_order_category"] = df_list["purchase_order_category"].apply(
            purchase_order_category_label
        )

    # 稽核欄位強制放在採購單母表最右邊，並直接改成使用者看得懂的欄名。
    # 只靠 column_config 改標題時，某些 Streamlit 版本容易讓人以為沒出現；
    # 這裡直接 rename + reorder，避免畫面上看不到「建檔人員 / 最後修改人」。
    audit_created_col = _label("建檔人員")
    audit_updated_col = _label("最後修改人")
    rename_audit_cols = {}
    if "created_by_name" in df_list.columns:
        rename_audit_cols["created_by_name"] = audit_created_col
    if "updated_by_name" in df_list.columns:
        rename_audit_cols["updated_by_name"] = audit_updated_col
    if rename_audit_cols:
        normal_cols = [c for c in df_list.columns if c not in ("created_by_name", "updated_by_name")]
        audit_cols = [c for c in ("created_by_name", "updated_by_name") if c in df_list.columns]
        df_list = df_list[normal_cols + audit_cols].rename(columns=rename_audit_cols)

    with st.form("po_list_form", clear_on_submit=False):
        edited = st.data_editor(
            df_list,
            hide_index=True,
            use_container_width=True,
            height=int(st.session_state.setdefault("b02_top_height", 230)),
            num_rows="fixed",
            disabled=[c for c in df_list.columns if c != _t("選取")],
            column_config={
                _t("選取"): st.column_config.CheckboxColumn(_t("選取"), default=False),
                "order_id": None,
                "supplier_id": None,
                "status_raw": None,
                "order_num": st.column_config.TextColumn(_t("採購單號")),
                "order_date": st.column_config.TextColumn(_t("開立日期")),
                "purchase_order_category": st.column_config.TextColumn(_label("採購單類別")),
                "supplier_name": st.column_config.TextColumn(_t("供應商名稱")),
                "status": st.column_config.TextColumn(_t("到貨狀態")),
                "total_amount": st.column_config.TextColumn(_t("總金額")),
                audit_created_col: st.column_config.TextColumn(audit_created_col),
                audit_updated_col: st.column_config.TextColumn(audit_updated_col),
            },
            key="po_list_editor",
        )

        # Give translated English/Vietnamese labels enough width; the button CSS above
        # also wraps an unusually long label inside its own button.
        a1, a2, a3, a4 = st.columns([2.0, 2.0, 2.0, 3.0])
        with a1:
            load_btn = st.form_submit_button(_t("載入到修改採購單"), use_container_width=True)
        with a2:
            delete_btn = st.form_submit_button(_t("刪除勾選採購單"), use_container_width=True)
        with a3:
            print_btn = st.form_submit_button(_t("列印勾選採購單"), use_container_width=True)

        with a4:
            delete_confirm = st.checkbox(_t("確認刪除整張採購單（含明細，不可復原）"), value=False, key="po_delete_confirm")

    apply_vertical_splitter("b02_top_height", "b02_vertical_splitter_control", default=230, min_top=150, max_top=430)

    if load_btn:
        chosen = edited.loc[edited[_t("選取")] == True]
        if chosen.empty:
            st.warning(_t("請先在清單勾選一張採購單。"))
        else:
            if len(chosen) > 1:
                st.info(_t("一次只能載入一張採購單，已自動載入第一張。"))
            oid = int(chosen.iloc[0]["order_id"])
            st.session_state["po_selected_order_id"] = oid
            st.session_state["po_selected_item_ids"] = []
            st.success(f"{_t('已載入採購單：')}{chosen.iloc[0].get('order_num','(no)')}")
            st.session_state["b02_mode_pending"] = MODE_EDIT
            st.rerun()


    if 'print_btn' in locals() and print_btn:
        chosen = edited.loc[edited[_t("選取")] == True]
        if chosen.empty:
            st.warning(_t("請先在清單勾選要列印的採購單。"))
        else:
            if len(chosen) > 1:
                st.info(_t("一次只能列印一張採購單，已自動列印第一張。"))
            oid_print = int(chosen.iloc[0]["order_id"])
            try:
                pdf_bytes = build_po_pdf_from_db(oid_print, include_prices=True)
                _render_pdf_preview_and_print(pdf_bytes, key_prefix=f"po_print_list_{oid_print}")

                pdf_bytes_no_price = build_po_pdf_from_db(oid_print, include_prices=False)
                _render_pdf_preview_and_print(
                    pdf_bytes_no_price,
                    key_prefix=f"po_print_list_noprice_{oid_print}",
                    open_label="新分頁開啟PDF(不含價格)",
                    download_label="下載PDF(不含價格)",
                )
            except Exception as e:
                st.warning(f"{_t('產生 PDF 失敗：')}{e}")

    if delete_btn:
        chosen = edited.loc[edited[_t("選取")] == True]
        if chosen.empty:
            st.warning(_t("請先在清單勾選要刪除的採購單。"))
        elif not delete_confirm:
            st.warning(_t("請先勾選「確認刪除」再按刪除。"))
        else:
            oids = chosen["order_id"].astype(int).tolist()
            ok, msg = delete_po_orders(oids)
            if ok:
                if st.session_state.get("po_selected_order_id") in oids:
                    st.session_state["po_selected_order_id"] = None
                    st.session_state["po_selected_item_ids"] = []
                load_po_heads.clear()
                count_po_heads.clear()
                load_po_items.clear()
                st.success(f"{_t('已刪除 ')}{len(oids)}{_t(' 張採購單（包含明細）。')}")
                st.rerun()
            else:
                st.error(msg)

st.divider()

# ---- mode switch request (must happen before widget instantiation) ----
if "b02_mode_pending" in st.session_state:
    st.session_state["b02_mode"] = st.session_state.pop("b02_mode_pending")

mode_options = _mode_options()
mode = st.radio(
    _t("模式"),
    options=list(mode_options.keys()),
    format_func=lambda x: mode_options.get(x, x),
    horizontal=True,
    key="b02_mode",
)
if mode == MODE_CREATE:
    suppliers = load_suppliers(active_only=("is_active" in SUPPLIER_COLS))

    st.markdown(f"### {_t('採購單抬頭')}")
    h1, h2, h3, h4, h5 = st.columns([1.6, 3.0, 1.2, 1.6, 2.2])

    with h1:
        order_date = st.date_input(_t("訂單日期"), key="po_order_date", value=date.today())

    with h2:
        if suppliers.empty:
            st.error(_t("尚無供應商資料。"))
            supplier_choice = _t("未選")
        else:
            sup_opts = [_t("未選")] + [
                f'{int(r["supplier_id"])} | {r.get("supplier_code","")} | {r.get("supplier_name","")}'
                for _, r in suppliers.iterrows()
            ]
            supplier_choice = st.selectbox(_t("供應商"), sup_opts, key="po_supplier_choice")

    with h3:
        currency = st.selectbox(_t("幣別"), ["VND", "TWD", "USD"], key="po_currency")

    with h4:
        due_date = st.date_input(_t("預計到貨日"), key="po_due_date", value=date.today())
    with h5:
        purchase_order_category = st.selectbox(
            _label("採購單類別"),
            options=list(PURCHASE_ORDER_CATEGORY_OPTIONS.keys()),
            format_func=purchase_order_category_label,
            key="po_purchase_order_category",
        )
    # 採購單號（預覽）與抬頭備註同列：採購單號在左、備註在右（單號唯讀）
    preview_supplier_shortname = ""
    if supplier_choice and supplier_choice != _t("未選"):
        try:
            preview_supplier_id = int(str(supplier_choice).split("|")[0].strip())
            preview_supplier_row = suppliers.loc[suppliers["supplier_id"].astype(int) == preview_supplier_id]
            if not preview_supplier_row.empty:
                preview_supplier_shortname = str(preview_supplier_row.iloc[0].get("supplier_shortname") or "").strip()
        except (TypeError, ValueError):
            preview_supplier_shortname = ""
    try:
        preview_order_num = next_order_num(order_date, preview_supplier_shortname) if preview_supplier_shortname else ""
    except ValueError as e:
        preview_order_num = ""
        st.warning(str(e))
    st.session_state["po_order_num_preview"] = preview_order_num
    hn1, hn2 = st.columns([2, 3])
    with hn1:
        st.text_input(_t("採購單號（預覽）"), key="po_order_num_preview", disabled=True)
    with hn2:
        head_remark = st.text_input(_t("抬頭備註（可空）"), key="po_head_remark")


    supplier_id = None
    if supplier_choice and supplier_choice != _t("未選"):
        try:
            supplier_id = int(str(supplier_choice).split("|")[0].strip())
        except Exception:
            supplier_id = None

    if supplier_id is None:
        st.info(_t("請先選擇供應商，才會出現可選品項。"))
    else:

        mats = load_materials_by_supplier(supplier_id)
        if mats.empty:
            st.error(_t("這個供應商暫時沒有綁任何原料品項，請先去 C01 / Material 補。"))
        else:
            label_map = {}
            for _, r in mats.iterrows():
                code = str(r.get("item_code") or "")
                name = str(r.get("item_name") or "")
                label = f"{code} | {name}".strip()
                label_map[label] = r

            st.markdown(f"### {_t('採購明細（目前已加入）')}")

            # 換供應商就清空暫存（避免跨供應商混入）
            if st.session_state.get("po_cart_supplier_id") != supplier_id:
                st.session_state["po_cart_supplier_id"] = supplier_id
                st.session_state["po_cart_lines"] = []

            cart_lines = st.session_state.get("po_cart_lines", [])

            if cart_lines:
                df_cart = pd.DataFrame(cart_lines).copy()
                df_cart.insert(0, _t("勾選"), False)
                df_cart[_t("小計")] = df_cart.apply(
                    lambda r: to_decimal(r.get("qty_ordered"), default=Decimal("0")) * to_decimal(r.get("unit_price"), default=Decimal("0")),
                    axis=1,
                )
                show_cols = [c for c in [_t("勾選"), "item_code", "item_name", "specification", "unit", "qty_ordered", "unit_price", _t("小計"), "remark"] if c in df_cart.columns]
                edited_cart = st.data_editor(
                    df_cart[show_cols],
                    use_container_width=True,
                    height=180,
                    hide_index=True,
                    num_rows="fixed",
                    disabled=[c for c in show_cols if c != "勾選"],
                    column_config={
                        _t("勾選"): st.column_config.CheckboxColumn(_t("勾選"), default=False),
                        "item_code": st.column_config.TextColumn(_t("料號")),
                        "item_name": st.column_config.TextColumn(_t("品名")),
                        "specification": st.column_config.TextColumn(_t("規格")),
                        "unit": st.column_config.TextColumn(_t("單位")),
                        "qty_ordered": st.column_config.TextColumn(_t("數量")),
                        "unit_price": st.column_config.TextColumn(_t("單價")),
                        "remark": st.column_config.TextColumn(_t("備註")),
                    },
                    key="po_cart_editor",
                )
            else:
                edited_cart = None
                st.info(_t("目前還沒有加入任何明細。請在下方新增一筆。"))

            r1, r2, _ = st.columns([1.4, 1, 2.6])
            with r1:
                delete_cart_btn = st.button(_t("刪除勾選品項"), use_container_width=True, disabled=(len(cart_lines) == 0))
            with r2:
                if st.button(_t("清空明細"), use_container_width=True, disabled=(len(cart_lines) == 0)):
                    st.session_state["po_cart_lines"] = []
                    st.rerun()

            if delete_cart_btn:
                if edited_cart is None or "勾選" not in edited_cart.columns:
                    st.warning(_t("目前沒有可刪除的明細。"))
                else:
                    keep_mask = ~(edited_cart["勾選"].fillna(False).astype(bool))
                    new_cart_lines = pd.DataFrame(cart_lines).loc[keep_mask].to_dict("records")
                    deleted_count = len(cart_lines) - len(new_cart_lines)
                    if deleted_count <= 0:
                        st.warning(_t("請先勾選要刪除的品項。"))
                    else:
                        st.session_state["po_cart_lines"] = new_cart_lines
                        st.session_state["po_flash"] = _t("已刪除 {n} 筆明細。").format(n=deleted_count)
                        st.rerun()

            st.markdown(f"### {_t('新增一筆明細')}")
            flash = st.session_state.pop("po_flash", None)
            if flash:
                st.success(flash)


            cA, cB, cC, cD, cE = st.columns([4, 2, 2, 2, 3])

            with cA:
                item_label = st.selectbox(_t("品項"), [_t("未選")] + list(label_map.keys()), key="po_new_item")

            row = label_map.get(item_label) if item_label and item_label != "未選" else None
            spec_val = str(row.get("spec") or row.get(MATERIAL_SPEC_COL) or "") if row is not None else ""
            unit_val = str(row.get("unit") or row.get(MATERIAL_UNIT_COL) or "") if row is not None else ""
            price_val = to_decimal(row.get("unit_price") if row is not None else None, default=Decimal("0"))

            # disabled textbox 要能跟著選項變動：先灌 session_state
            st.session_state["po_new_spec"] = spec_val
            st.session_state["po_new_unit"] = unit_val
            st.session_state["po_new_price"] = str(price_val)

            with cB:
                st.text_input(_t("規格"), key="po_new_spec", disabled=True)
            with cC:
                qty_str = st.text_input(_t("數量"), key="po_new_qty", placeholder=_t("整數"))
            with cD:
                st.text_input(_t("單位"), key="po_new_unit", disabled=True)
            with cE:
                st.text_input(_t("單價"), key="po_new_price", disabled=True)
                remark = st.text_input(_t("備註"), key="po_new_remark")

            add1, _ = st.columns([1, 5])
            with add1:
                add_btn = st.button(_t("加入明細"), use_container_width=True)

            if add_btn:
                if row is None:
                    st.warning(_t("請先選擇品項。"))
                else:
                    qty_dec = to_decimal(qty_str, default=Decimal("0"))
                    if qty_dec <= 0:
                        st.warning(_t("數量必須大於 0。"))
                    elif price_val <= 0:
                        st.warning(_t("單價不可為 0，請去原料主檔修改單價。"))
                    else:
                        cart_lines.append(
                            dict(
                                item_id=row.get("item_id"),
                                item_code=str(row.get("item_code") or ""),
                                item_name=str(row.get("item_name") or ""),
                                specification=spec_val,
                                unit=unit_val,
                                qty_ordered=qty_dec,
                                unit_price=price_val,
                                remark=remark,
                            )
                        )
                        st.session_state["po_cart_lines"] = cart_lines
                        # request reset on next rerun (cannot modify widget state after instantiation in this run)
                        st.session_state["po_reset_new_line"] = True
                        st.session_state["po_flash"] = _t("已加入一筆明細。")
                        st.rerun()

            total_preview = Decimal("0")
            for r in cart_lines:
                total_preview += to_decimal(r.get("qty_ordered"), default=Decimal("0")) * to_decimal(r.get("unit_price"), default=Decimal("0"))

            st.markdown(f"### {_t('購買總價（預覽）')}: **{total_preview:,}**")

            # --- 儲存採購單（新建時永遠可見）---
            save_c1, save_c2 = st.columns([1.2, 4.8])
            with save_c1:
                if st.button(_t("儲存採購單"), type="primary", disabled=(len(cart_lines) == 0), use_container_width=True):
                    ok = save_new_order(
                        supplier_id=supplier_id,
                        order_date=order_date,
                        currency=currency,
                        due_date=due_date,
                        head_remark=head_remark,
                        purchase_order_category=purchase_order_category,
                        lines=cart_lines,
                    )
                    if ok:
                        load_po_heads.clear()
                        load_po_items.clear()

                        # 不直接回寫 po_order_date / po_currency
                        # 這兩個已經綁到 widget，後面再改 session_state 會觸發 StreamlitAPIException
                        # 所以只清空其餘下方編輯區，日期與幣別維持畫面目前值

                        for _k in [
                            "po_supplier_id",
                            "po_supplier_name",
                            "po_supplier_shortname",
                            "po_due_date",
                            "po_head_remark",
                            "po_print_pdf_bytes",
                            "po_print_opened",
                            "po_last_created_order_id",
                            "po_last_created_order_num",
                        ]:
                            if _k in st.session_state:
                                del st.session_state[_k]

                        for _k in list(st.session_state.keys()):
                            if str(_k).startswith("po_line_") or str(_k).startswith("po_item_"):
                                del st.session_state[_k]

                        # 讓下次顯示時自動抓最新單號（成功建立後自然會 +1）
                        if "po_order_num" in st.session_state:
                            del st.session_state["po_order_num"]

                        st.session_state["po_line_count"] = 1
                        st.rerun()

            # --- 列印（預覽 -> 確認列印）---
            last_id = st.session_state.get("po_last_created_order_id")
            if last_id:
                st.caption(f"{_t('最近建立：')}{st.session_state.get('po_last_created_order_num','')}（order_id={last_id}）")
                if st.button(_t("🖨️ 列印（預覽）"), key="po_print_preview_btn", use_container_width=True):
                    try:
                        pdf_bytes = build_po_pdf_from_db(int(last_id))
                        st.session_state["po_print_pdf_bytes"] = pdf_bytes
                        st.session_state["po_print_opened"] = False
                    except Exception as e:
                        st.error(f"{_t('列印產生失敗：')}{e}")

            # 列印/下載（放在「儲存採購單」下面）
            if st.session_state.get("po_print_pdf_bytes"):
                _render_pdf_preview_and_print(st.session_state["po_print_pdf_bytes"], key_prefix="po_print_create")


else:
    st.markdown(f"### {_t('修改採購單')}")
    oid = st.session_state.get("po_selected_order_id", None)
    if not oid:
        st.info(_t("請先在上方「採購單清單」勾選一張採購單，並按「載入到修改採購單」。"))
    else:
        heads = load_po_heads(st.session_state.get("po_list_keyword", ""))
        head_row = heads.loc[heads["order_id"] == oid]
        if head_row.empty:
            load_po_heads.clear()
            heads = load_po_heads("")
            head_row = heads.loc[heads["order_id"] == oid]

        if not head_row.empty:
            hr = head_row.iloc[0]
            st.subheader(f"{hr.get('order_num','(no)')}　{hr.get('supplier_name','')}")
            # 修改模式：準備原料訂購單 PDF（按鈕放最下方）
            try:
                st.session_state["po_edit_pdf_bytes"] = build_po_pdf_from_db(int(oid))
                st.session_state["po_edit_pdf_ready"] = True
            except Exception as e:
                st.session_state["po_edit_pdf_ready"] = False
                st.session_state["po_edit_pdf_bytes"] = b""
                st.warning(f"{_t('產生 PDF 失敗：')}{e}")
            c1, c2, c3, c4 = st.columns([1.6, 1.8, 2.8, 2.2])
            due_val = None
            remark_val = None
            edit_purchase_order_category = PURCHASE_ORDER_CATEGORY_GENERAL
            with c1:
                if ORDER_HEAD_STATUS_COL and "status" in hr.index:
                    st.text_input(_t("狀態（系統自動判定）"), value=_t_status(str(hr.get("status") or "")), disabled=True)
            with c2:
                if ORDER_HEAD_DUE_COL:
                    due_default = hr.get("due_date") if "due_date" in hr.index else hr.get("due")
                    if due_default is None:
                        due_default = date.today()
                    due_val = st.date_input(_t("預計到貨日"), value=due_default, key="po_edit_due")
            with c3:
                if ORDER_HEAD_REMARK_COL:
                    remark_val = st.text_input(_t("抬頭備註"), value=str(hr.get("remark") or ""), key="po_edit_remark")
            with c4:
                current_category = normalize_purchase_order_category(
                    hr.get("purchase_order_category") or PURCHASE_ORDER_CATEGORY_GENERAL
                )
                if current_category not in PURCHASE_ORDER_CATEGORY_OPTIONS:
                    current_category = PURCHASE_ORDER_CATEGORY_GENERAL
                edit_purchase_order_category = st.selectbox(
                    _label("採購單類別"),
                    options=list(PURCHASE_ORDER_CATEGORY_OPTIONS.keys()),
                    index=list(PURCHASE_ORDER_CATEGORY_OPTIONS.keys()).index(current_category),
                    format_func=purchase_order_category_label,
                    key=f"po_edit_purchase_order_category_{oid}",
                )

            if st.button(_t("儲存抬頭修改")):
                try:
                    apply_po_head_changes(oid, due_val, remark_val, edit_purchase_order_category)
                    st.success(_t("抬頭已更新。"))
                    load_po_heads.clear()
                except ValueError as exc:
                    st.error(str(exc))

        items = load_po_items(int(oid))
        if items.empty:
            st.warning(_t("此採購單目前沒有任何明細。"))
        else:
            st.markdown(f"### {_t('明細（勾選後才會出現 textbox 修改區）')}")
            df = items.copy()
            df[_t("選取")] = False

            show_cols = [_t("選取")]
            if "line_no" in df.columns:
                show_cols.append("line_no")
            show_cols += ["material_code", "material_name", "spec", "unit", "unit_price", "qty_ordered", "remark", "order_item_id"]
            show_cols = [c for c in show_cols if c in df.columns]

            df_tbl = df[show_cols].copy()
            df_tbl.rename(columns={
                "line_no": _t("列"),
                "material_code": _t("料號"),
                "material_name": _t("品名"),
                "spec": _t("規格"),
                "unit": _t("單位"),
                "unit_price": _t("單價"),
                "qty_ordered": _t("數量"),
                "remark": _t("備註"),
                "order_item_id": "item_pk",
            }, inplace=True)

            # checkbox column to the far left; keep item_pk at the end (hidden)
            # The display columns above are localized.  Use the localized names here
            # as well; otherwise English/Vietnamese retains no columns after this
            # ordering step and the detail editor appears blank.
            col_order = [c for c in [
                _t("選取"), _t("列"), _t("料號"), _t("品名"), _t("規格"),
                _t("單位"), _t("單價"), _t("數量"), _t("備註"), "item_pk",
            ] if c in df_tbl.columns]
            df_tbl = df_tbl[col_order]

            if "數量" in df_tbl.columns:
                def _fmt_qty(x):
                    try:
                        fx = float(x)
                        return str(int(fx)) if fx.is_integer() else str(fx)
                    except Exception:
                        return str(x)
                df_tbl["數量"] = df_tbl["數量"].apply(_fmt_qty)

            # Show the whole order's quantity total, not only the checked rows.
            # Calculate from the original values so display formatting never affects it.
            ordered_qty_total = sum(
                (to_decimal(value, default=Decimal("0")) for value in items.get("qty_ordered", [])),
                Decimal("0"),
            )
            ordered_qty_text = f"{ordered_qty_total:,.2f}".rstrip("0").rstrip(".")

            with st.form("po_item_select_form", clear_on_submit=False):
                edited = st.data_editor(
                    df_tbl,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="fixed",
                    disabled=[c for c in df_tbl.columns if c != "選取"],
                    column_config={
                        _t("選取"): st.column_config.CheckboxColumn(_t("選取"), default=False),
                        "item_pk": None,
                    },
                    key="po_items_editor",
                )
                st.markdown(f"**{_t('採購數量總計')}：{ordered_qty_text}**")
                apply_btn = st.form_submit_button(_t("套用勾選（開始修改/刪除）"), use_container_width=True)

            if apply_btn:
                st.session_state["po_selected_item_ids"] = edited.loc[edited[_t("選取")] == True, "item_pk"].astype(int).tolist()
                st.session_state["b02_mode_pending"] = MODE_EDIT
                st.rerun()

            sel_ids = st.session_state.get("po_selected_item_ids", [])
            st.markdown(f"### {_t('修改輸入區（textbox）')}")
            if not sel_ids:
                st.info(_t("請先在明細表勾選要修改/刪除的項目，並按「套用勾選」。"))
            else:
                # materials for dropdown (prefer supplier_id if available)
                supplier_id_for_po = None
                try:
                    if isinstance(hr, pd.Series) and 'supplier_id' in hr.index and pd.notna(hr.get('supplier_id')):
                        supplier_id_for_po = int(hr.get('supplier_id'))
                except Exception:
                    supplier_id_for_po = None
                mats_df = load_materials_by_supplier(supplier_id_for_po) if supplier_id_for_po else load_all_materials()
                mat_options = []
                mat_lookup = {}
                if not mats_df.empty:
                    for _, mr in mats_df.iterrows():
                        mid = int(mr.get('item_id'))
                        opt = f"{mid} | {mr.get('item_code','')} | {mr.get('item_name','')}"
                        mat_options.append(opt)
                        mat_lookup[mid] = mr

                updates = []
                for pk in sel_ids:
                    row = items.loc[items["order_item_id"] == pk]
                    if row.empty:
                        continue
                    r = row.iloc[0]
                    with st.container(border=True):
                        st.write(f"**{r.get('material_code','')} {r.get('material_name','')}**")
                        # allow changing material
                        cur_mid = r.get('material_id')
                        try:
                            cur_mid = int(cur_mid) if pd.notna(cur_mid) else None
                        except Exception:
                            cur_mid = None
                        # ---- edit display fields (spec/unit/price) ----
                        spec_key = f"po_edit_spec_{pk}"
                        unit_key = f"po_edit_unit_{pk}"
                        price_key = f"po_edit_price_{pk}"

                        if spec_key not in st.session_state:
                            st.session_state[spec_key] = str(r.get("spec") or r.get("specification") or "")
                        if unit_key not in st.session_state:
                            st.session_state[unit_key] = str(r.get("unit") or "")
                        if price_key not in st.session_state:
                            st.session_state[price_key] = str(to_decimal(r.get("unit_price"), default=Decimal("0")))

                        def _po_edit_on_mat_change(pk=pk, mat_lookup=mat_lookup):
                            choice = st.session_state.get(f"po_edit_mat_{pk}")
                            try:
                                mid = int(str(choice).split("|")[0].strip()) if choice else None
                            except Exception:
                                mid = None
                            mr = mat_lookup.get(mid) if mid is not None else None
                            if mr is None:
                                st.session_state[f"po_edit_spec_{pk}"] = ""
                                st.session_state[f"po_edit_unit_{pk}"] = ""
                                st.session_state[f"po_edit_price_{pk}"] = "0"
                                return
                            st.session_state[f"po_edit_spec_{pk}"] = str(mr.get("specification") or mr.get("spec") or "")
                            st.session_state[f"po_edit_unit_{pk}"] = str(mr.get("unit") or "")
                            st.session_state[f"po_edit_price_{pk}"] = str(to_decimal(mr.get("unit_price"), default=Decimal("0")))

                        if mat_options:
                            default_idx = 0
                            if cur_mid is not None:
                                for ii, opt in enumerate(mat_options):
                                    if opt.split('|')[0].strip() == str(cur_mid):
                                        default_idx = ii
                                        break
                            mat_choice = st.selectbox(
                                _t("原料"),
                                mat_options,
                                index=default_idx,
                                key=f"po_edit_mat_{pk}",
                                on_change=_po_edit_on_mat_change,
                            )
                            new_mid = int(mat_choice.split('|')[0].strip())
                        else:
                            new_mid = cur_mid

                        d1, d2, d3 = st.columns([3, 1, 1])
                        with d1:
                            st.text_input(_t("規格"), key=spec_key, disabled=True)
                        with d2:
                            st.text_input(_t("單位"), key=unit_key, disabled=True)
                        with d3:
                            st.text_input(_t("單價"), key=price_key, disabled=True)


                        e1, e2 = st.columns([2, 4])
                        with e1:
                            qty0 = r.get("qty_ordered", 0)
                            try:
                                qty0 = int(float(qty0))
                            except Exception:
                                qty0 = 0
                            qty_new = st.text_input(_t("數量（item {pk}）").format(pk=pk), value=str(qty0), key=f"po_edit_qty_{pk}")
                        with e2:
                            remark0 = str(r.get("remark") or "")
                            remark_new = st.text_input(_t("備註（item {pk}）").format(pk=pk), value=remark0, key=f"po_edit_remark_{pk}")
                        u = {"order_item_id": pk, "qty_ordered": qty_new, "remark": remark_new}
                        # material update fields (if user changed)
                        if new_mid is not None and new_mid != cur_mid and new_mid in mat_lookup:
                            mr = mat_lookup[new_mid]
                            u.update({
                                "material_id": int(mr.get('item_id')),
                                "material_code": str(mr.get('item_code') or ""),
                                "material_name": str(mr.get('item_name') or ""),
                                "spec": str(mr.get('specification') or ""),
                                "unit": str(mr.get('unit') or ""),
                                "unit_price": mr.get('unit_price'),
                            })
                        updates.append(u)

                
                del_ids = sel_ids
                if del_ids:
                    st.info(_t("已選取 {n} 筆明細，可在下方修改或刪除。").format(n=len(del_ids)))

                # 確認勾選獨立放在右上，下面兩個按鈕共用同一列，保證水平對齊。
                confirm_spacer, confirm_col = st.columns([1, 1])
                with confirm_col:
                    confirm_del = st.checkbox(
                        _t("確認刪除勾選明細（不可復原）"),
                        value=False,
                        key="po_item_delete_confirm",
                    )

                b_save, b_del = st.columns([1, 1])
                with b_save:
                    if st.button(_t("儲存勾選修改"), type="primary", use_container_width=True, disabled=(len(updates) == 0)):
                        bad_price_ids = []
                        for _pk in sel_ids:
                            _price = to_decimal(st.session_state.get(f"po_edit_price_{_pk}"), default=Decimal("0"))
                            if _price <= 0:
                                bad_price_ids.append(_pk)
                        if bad_price_ids:
                            st.warning(_t("單價不可為 0，請去原料主檔修改單價。"))
                        else:
                            apply_po_item_changes(int(oid), updates, [])
                            st.success(_t("明細已更新。"))
                        load_po_items.clear()
                        load_po_heads.clear()

                        # 修改模式下按「儲存勾選修改」後，清空該分頁所有欄位
                        for _k in [
                            "po_supplier_id",
                            "po_supplier_name",
                            "po_supplier_shortname",
                            "po_due_date",
                            "po_head_remark",
                            "po_print_pdf_bytes",
                            "po_print_opened",
                            "po_last_created_order_id",
                            "po_last_created_order_num",
                            "po_order_num",
                            "po_edit_order_id",
                            "po_edit_mode",
                            "po_selected_item_ids",
                        ]:
                            if _k in st.session_state:
                                del st.session_state[_k]

                        for _k in list(st.session_state.keys()):
                            if str(_k).startswith("po_line_") or str(_k).startswith("po_item_"):
                                del st.session_state[_k]

                        st.session_state["po_line_count"] = 1
                        st.rerun()

                with b_del:
                    if st.button(
                        _t("刪除勾選明細"),
                        type="secondary",
                        use_container_width=True,
                        disabled=(len(del_ids) == 0 or not confirm_del),
                    ):
                        apply_po_item_changes(int(oid), [], del_ids)
                        st.success(_t("已刪除勾選明細。"))
                        load_po_items.clear()
                        load_po_heads.clear()
                        st.session_state["po_selected_item_ids"] = []
                        st.rerun()

# （修改採購單）列印/下載（放在最下方）
if st.session_state.get("po_selected_order_id"):
    try:
        oid2 = int(st.session_state.get("po_selected_order_id"))
    except Exception:
        oid2 = None
    if oid2:
        st.markdown("---")
        st.markdown(f"### {_t('原料訂購單列印')}")
        if st.session_state.get("po_edit_pdf_ready") and st.session_state.get("po_edit_pdf_bytes"):
            _render_pdf_preview_and_print(st.session_state["po_edit_pdf_bytes"], key_prefix=f"po_print_edit_{oid2}")
        else:
            st.info(_t("尚無可列印的 PDF（可能產生失敗或尚未載入）。"))
