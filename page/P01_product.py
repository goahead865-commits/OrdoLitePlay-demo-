
from __future__ import annotations

from compact_layout import apply_compact_layout

apply_compact_layout()

import math
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import auth
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from splitter_component import apply_vertical_splitter

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.i18n import tr


# =========================
# Config
# =========================
DEFAULT_USER_ID = 1  # TODO: replace with session user id once login is ready
PAGE_SIZE_OPTIONS = [10, 20, 30, 50, 100]
DEFAULT_PAGE_SIZE = 20

st.set_page_config(page_title="P01 產品主檔", layout="wide")

st.markdown(
    """
    <style>
    /* P01 uses a two-panel desktop layout, so keep its form controls compact. */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {
        min-height: 1.55rem !important;
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
    }
    [data-testid="stTextArea"] textarea {
        min-height: 2.4rem !important;
    }
    [data-testid="stTextInput"],
    [data-testid="stNumberInput"],
    [data-testid="stSelectbox"],
    [data-testid="stTextArea"] {
        margin-bottom: 0 !important;
    }
    [data-testid="stDataEditor"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGE_KEY = "P01_product"
auth.require_read(PAGE_KEY)
USER_ID = int(st.session_state.get("user_id", DEFAULT_USER_ID))

LANG_STATE_KEYS = ("lang", "language", "locale", "ui_lang")

UNIT_OPTIONS = ["PCS", "g"]
SPEC_UNIT_OPTIONS = ["mm", "cm"]
WEIGHT_UNIT_OPTIONS = ["g", "kg"]

ACTIVE_OPTIONS = ["active", "inactive"]
FILTER_STATUS_OPTIONS = ["all", "active", "inactive"]



LOCAL_I18N = {
    "zh-TW": {},
    "en": {},
    "vi": {},
}

# -------------------------
# i18n helpers
# -------------------------
def _normalize_lang(lang: str) -> str:
    v = (lang or "").strip().lower()
    if v.startswith("zh"):
        return "zh-TW"
    if v.startswith("en"):
        return "en"
    if v.startswith("vi"):
        return "vi"
    return "zh-TW"


def _t(text_value: str) -> str:
    lang = _normalize_lang(_current_lang())
    local_map = LOCAL_I18N.get(lang, {})
    try:
        translated = tr(text_value)
        if translated and not str(translated).startswith("[MISS:"):
            return translated
    except Exception:
        pass
    return local_map.get(text_value, text_value)


def _current_lang() -> str:
    for key in LANG_STATE_KEYS:
        value = st.session_state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "zh-TW"


def _active_label(value: str) -> str:
    return _t("啟用") if value == "active" else _t("停用")


def _filter_status_label(value: str) -> str:
    mapping = {
        "all": _t("全部"),
        "active": _t("啟用"),
        "inactive": _t("停用"),
    }
    return mapping[value]


def _active_value_to_int(value: str) -> int:
    return 1 if value == "active" else 0


# -------------------------
# DB helpers
# -------------------------
@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    # 1) Prefer project db.py
    try:
        from db import get_engine as _get_engine  # type: ignore

        eng = _get_engine()
        if eng is not None:
            return eng
    except Exception:
        pass

    # 2) Fallback (if db.py not available): use environment variables (MYSQL_*)
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "")

    if not database:
        raise RuntimeError(
            "缺少 MySQL 設定：請確認 db.py get_engine 可用，或設定 MYSQL_DATABASE。"
        )

    from urllib.parse import quote_plus

    pwd = quote_plus(password)
    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def df_from_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    eng = get_engine()
    with eng.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def exec_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> None:
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text(sql), params or {})


def get_index_expression(table_name: str, index_name: str) -> Optional[str]:
    """Return concatenated expression/columns for an index (MySQL 8+ functional indexes)."""
    sql = """
    SELECT GROUP_CONCAT(COALESCE(EXPRESSION, COLUMN_NAME) ORDER BY SEQ_IN_INDEX SEPARATOR ', ') AS exprs
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = :t
      AND INDEX_NAME = :i
    """
    try:
        df = df_from_sql(sql, {"t": table_name, "i": index_name})
        if df.empty:
            return None
        value = df.iloc[0].get("exprs")
        return str(value) if value is not None else None
    except Exception:
        return None


def get_db_identity() -> Dict[str, Any]:
    eng = get_engine()
    sql = """
    SELECT
      DATABASE() AS db_name,
      CURRENT_USER() AS current_user,
      @@hostname AS host_name,
      @@port AS port_no,
      @@version AS version_no,
      NOW() AS server_now
    """
    try:
        with eng.connect() as conn:
            row = conn.execute(text(sql)).mappings().first()
            return dict(row) if row else {}
    except Exception as e:
        return {"error": str(e)}


# -------------------------
# Data loaders
# -------------------------
@st.cache_data(show_spinner=False, ttl=30)
def load_customers(active_only: bool = True) -> pd.DataFrame:
    where = "WHERE COALESCE(c.is_active,1)=1" if active_only else ""
    sql = f"""
    SELECT
      c.customer_id,
      c.customer_code,
      c.customer_shortname,
      c.customer_name
    FROM customer c
    {where}
    ORDER BY c.customer_code
    """
    return df_from_sql(sql)


@st.cache_data(show_spinner=False, ttl=15)
def load_products_count(search: str = "", active_filter: str = "all", customer_id: Optional[int] = None) -> int:
    where = ["1=1"]
    params: Dict[str, Any] = {}

    if search.strip():
        params["q"] = f"%{search.strip()}%"
        where.append("(p.product_code LIKE :q OR p.product_name LIKE :q OR p.product_barcode LIKE :q)")

    if active_filter == "active":
        where.append("p.is_active = 1")
    elif active_filter == "inactive":
        where.append("p.is_active = 0")

    if customer_id:
        where.append("p.customer_id = :customer_id")
        params["customer_id"] = int(customer_id)

    sql = f"""
    SELECT COUNT(1) AS cnt
    FROM product p
    WHERE {" AND ".join(where)}
    """
    df = df_from_sql(sql, params)
    return int(df.iloc[0]["cnt"]) if not df.empty else 0


@st.cache_data(show_spinner=False, ttl=15)
def load_products_page(
    search: str = "",
    active_filter: str = "all",
    customer_id: Optional[int] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    page: int = 1,
) -> pd.DataFrame:
    where = ["1=1"]
    params: Dict[str, Any] = {
        "limit": int(page_size),
        "offset": int((page - 1) * page_size),
    }

    if search.strip():
        params["q"] = f"%{search.strip()}%"
        where.append("(p.product_code LIKE :q OR p.product_name LIKE :q OR p.product_barcode LIKE :q)")

    if active_filter == "active":
        where.append("p.is_active = 1")
    elif active_filter == "inactive":
        where.append("p.is_active = 0")

    if customer_id:
        where.append("p.customer_id = :customer_id")
        params["customer_id"] = int(customer_id)

    sql = f"""
    SELECT
      p.product_id,
      p.product_code,
      p.product_name,
      p.product_barcode,
      p.customer_production_id,
      p.customer_id,
      c.customer_shortname AS customer_shortname,
      p.unit,
      p.`Specification` AS specification,
      p.`Specification_unit` AS specification_unit,
      p.color,
      p.weight,
      p.weight_unit,
      COALESCE(pup.unit_price, p.unit_price) AS unit_price,
      p.qty_per_carton,
      p.is_active,
      p.create_at,
      p.created_by_id,
      COALESCE(NULLIF(s_created.stuff_name, ''), NULLIF(u_created.user_code, ''), CONCAT('User#', p.created_by_id)) AS created_by_display,
      p.update_at,
      p.updated_by_id,
      CASE
        WHEN p.updated_by_id IS NULL THEN ''
        WHEN p.update_at IS NULL THEN ''
        WHEN p.create_at IS NOT NULL
             AND p.update_at = p.create_at
             AND p.updated_by_id = p.created_by_id THEN ''
        ELSE COALESCE(NULLIF(s_updated.stuff_name, ''), NULLIF(u_updated.user_code, ''), CONCAT('User#', p.updated_by_id))
      END AS updated_by_display
    FROM product p
    LEFT JOIN customer c ON c.customer_id = p.customer_id
    LEFT JOIN `user` u_created ON u_created.user_id = p.created_by_id
    LEFT JOIN stuff s_created ON s_created.stuff_id = u_created.stuff_id
    LEFT JOIN `user` u_updated ON u_updated.user_id = p.updated_by_id
    LEFT JOIN stuff s_updated ON s_updated.stuff_id = u_updated.stuff_id
    LEFT JOIN (
      SELECT product_unit_price_id, unit_price
      FROM product_unit_price
      WHERE valid_to IS NULL
    ) pup ON pup.product_unit_price_id = p.product_id
    WHERE {" AND ".join(where)}
    ORDER BY p.product_code
    LIMIT :limit OFFSET :offset
    """
    return df_from_sql(sql, params)


@st.cache_data(show_spinner=False, ttl=15)
def load_product_price_history(product_id: int) -> pd.DataFrame:
    sql = """
    SELECT
      pup.price_id,
      pup.unit_price,
      pup.valid_from,
      pup.valid_to,
      pup.created_at,
      pup.created_by,
      u.user_code,
      s.stuff_name
    FROM product_unit_price pup
    LEFT JOIN `user` u ON u.user_id = pup.created_by
    LEFT JOIN stuff s ON s.stuff_id = u.stuff_id
    WHERE pup.product_unit_price_id = :pid
    ORDER BY pup.valid_from DESC, pup.price_id DESC
    """
    return df_from_sql(sql, {"pid": int(product_id)})


# -------------------------
# Utility helpers
# -------------------------
def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return int(value)
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except Exception:
        return None


def normalize_code39_value(value: Any) -> Optional[str]:
    """
    Normalize Code39 text for display/storage.
    - Trim whitespace
    - If wrapped by *...* (common Code39 start/stop), strip the outer stars
    - Return None if empty
    """
    if value is None:
        return None

    text_value = str(value).strip()
    if not text_value:
        return None

    if len(text_value) >= 2 and text_value.startswith("*") and text_value.endswith("*"):
        text_value = text_value[1:-1].strip()

    return text_value or None


def get_next_product_code(customer_id: int, customer_shortname: Any) -> str:
    """Generate the next code as P-<customer short name>-<five-digit sequence>."""
    shortname = str(customer_shortname or "").strip()
    if not shortname:
        raise ValueError(_t("客戶簡稱為必填，無法產生產品代碼。"))

    sql = """
    SELECT
      COALESCE(MAX(CAST(RIGHT(p.product_code, 5) AS UNSIGNED)), 0) AS max_no
    FROM product p
    WHERE p.customer_id = :customer_id
      AND p.product_code REGEXP '^P-.+-[0-9]{5}$'
    """
    try:
        df = df_from_sql(sql, {"customer_id": int(customer_id)})
        max_no = int(df.iloc[0]["max_no"]) if df is not None and not df.empty else 0
    except Exception:
        max_no = 0
    if max_no >= 99999:
        raise ValueError(_t("產品代碼流水號已達五碼上限。"))
    return f"P-{shortname}-{max_no + 1:05d}"


def _product_barcode_for_display(initial: Dict[str, Any], product_code: str) -> Optional[str]:
    return normalize_code39_value(initial.get("product_barcode")) or normalize_code39_value(product_code)


def _invalidate_page_cache() -> None:
    load_products_page.clear()
    load_products_count.clear()
    load_customers.clear()
    load_product_price_history.clear()


# -------------------------
# Product form
# -------------------------
def _render_product_form(initial: Dict[str, Any], customers: pd.DataFrame, mode: str) -> Tuple[Dict[str, Any], bool]:
    """Returns (payload, submitted). mode: 'create' | 'edit'"""

    create_token = int(st.session_state.get("p01_create_clear_token", 0))

    def _create_key(name: str, preserve_after_create: bool = False) -> Dict[str, str]:
        """
        Streamlit ??雿?銝??widget ?撓?亙潦?        ?啣???敺?擃?p01_create_clear_token嚗??啣?????豢?雿?? key嚗?        ?皜征??嚗恥?嗆?雿輻?箏? key嚗?隞交?靽?銝活?豢???        """
        if mode != "create":
            return {}
        if preserve_after_create:
            return {"key": f"p01_create_{name}"}
        return {"key": f"p01_create_{name}_{create_token}"}

    if mode == "edit":
        st.subheader(_t("編輯產品"))

    cust_options = customers.copy()
    cust_options["label"] = (
        cust_options["customer_code"].astype(str)
        + " | "
        + cust_options["customer_shortname"].astype(str)
    )
    cust_id_to_label = dict(zip(cust_options["customer_id"].astype(int), cust_options["label"]))
    label_to_cust_id = {value: key for key, value in cust_id_to_label.items()}

    default_cust_id = _safe_int(initial.get("customer_id"))
    if default_cust_id is None and not cust_options.empty:
        default_cust_id = int(cust_options["customer_id"].iloc[0])

    if default_cust_id is None:
        st.error(_t("沒有客戶資料，無法建立產品。"))
        return {}, False

    d1, d2, d3 = st.columns(3)
    with d1:
        customer_option_labels = list(label_to_cust_id.keys())
        selected_customer_label = st.selectbox(
            _t("客戶"),
            options=customer_option_labels,
            index=customer_option_labels.index(
                cust_id_to_label.get(default_cust_id, customer_option_labels[0])
            ),
            **_create_key("customer_label", preserve_after_create=True),
        )
        customer_id = int(label_to_cust_id[selected_customer_label])

    selected_shortname = str(
        cust_options.loc[
            cust_options["customer_id"].astype(int) == customer_id,
            "customer_shortname",
        ].iloc[0]
    ).strip()
    product_code = (
        str(initial.get("product_code") or "").strip()
        if mode == "edit"
        else get_next_product_code(customer_id, selected_shortname)
    )

    with d2:
        customer_production_id = st.text_input(
            _t("客戶料號"),
            value=str(initial.get("customer_production_id") or ""),
            **_create_key("customer_production_id"),
        )

    with d3:
        unit_default = str(initial.get("unit") or "PCS")
        unit = st.selectbox(
            _t("單位"),
            options=UNIT_OPTIONS,
            index=UNIT_OPTIONS.index(unit_default) if unit_default in UNIT_OPTIONS else 0,
            **_create_key("unit"),
        )

    c1, c2 = st.columns(2)
    with c1:
        st.text_input(
            _t("產品代碼"),
            value=product_code,
            disabled=True,
            **(
                {"key": f"p01_create_product_code_{create_token}_{customer_id}"}
                if mode == "create"
                else {}
            ),
        )
    with c2:
        product_name = st.text_input(
            _t("產品名稱"),
            value=str(initial.get("product_name") or ""),
            **_create_key("product_name"),
        )

    e1, e2, e3 = st.columns(3)
    with e1:
        specification = st.text_input(
            _t("規格"),
            value=str(initial.get("specification") or initial.get("Specification") or ""),
            **_create_key("specification"),
        )

    with e2:
        spec_unit_default = str(initial.get("specification_unit") or initial.get("Specification_unit") or "mm")
        spec_unit = st.selectbox(
            _t("規格單位"),
            options=SPEC_UNIT_OPTIONS,
            index=SPEC_UNIT_OPTIONS.index(spec_unit_default) if spec_unit_default in SPEC_UNIT_OPTIONS else 0,
            **_create_key("specification_unit"),
        )

    with e3:
        color = st.text_input(
            _t("顏色"),
            value=str(initial.get("color") or ""),
            **_create_key("color"),
        )

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        weight = st.number_input(
            _t("重量"),
            min_value=0.0,
            value=float(_safe_float(initial.get("weight")) or 0.0),
            step=0.001,
            **_create_key("weight"),
        )

    with f2:
        weight_unit_default = str(initial.get("weight_unit") or "g")
        weight_unit = st.selectbox(
            _t("重量單位"),
            options=WEIGHT_UNIT_OPTIONS,
            index=WEIGHT_UNIT_OPTIONS.index(weight_unit_default) if weight_unit_default in WEIGHT_UNIT_OPTIONS else 0,
            **_create_key("weight_unit"),
        )

    with f3:
        st.text_input(
            _t("目前單價"),
            value="***",
            disabled=True,
            **_create_key("unit_price"),
        )

    with f4:
        qty_per_carton = st.number_input(
            _t("箱入數"),
            min_value=0,
            value=int(_safe_int(initial.get("qty_per_carton")) or 0),
            step=1,
            **_create_key("qty_per_carton"),
        )

    g1, g2 = st.columns([3, 1])
    with g1:
        note = st.text_area(
            _t("備註"),
            value=str(initial.get("note") or ""),
            height=36,
            **_create_key("note"),
        )

    active_default = "active" if int(initial.get("is_active", 1) or 1) == 1 else "inactive"
    active_labels = [_active_label(v) for v in ACTIVE_OPTIONS]
    active_label_to_value = dict(zip(active_labels, ACTIVE_OPTIONS))

    with g2:
        active_label = st.selectbox(
            _t("狀態"),
            options=active_labels,
            index=ACTIVE_OPTIONS.index(active_default),
            **_create_key("active_label"),
        )
        active_value = active_label_to_value[active_label]

    code39_value = _product_barcode_for_display(initial, product_code)
    st.caption(
            f"{_t('條碼')}：{code39_value if code39_value else _t('未設定')}"
    )

    b1, b2 = st.columns([1, 1])
    with b1:
        submitted = st.button(
            _t("新增產品") if mode == "create" else _t("儲存變更"),
            type="primary",
            use_container_width=True,
        )
    with b2:
        if st.button(_t("取消"), use_container_width=True):
            st.session_state["p01_show_form"] = False
            st.rerun()

    payload = {
        "product_code": product_code.strip(),
        "product_barcode": code39_value,
        "product_name": product_name.strip() or None,
        "customer_production_id": customer_production_id.strip() or None,
        "customer_id": customer_id,
        "unit": unit,
        "specification": specification.strip() or None,
        "specification_unit": spec_unit,
        "color": color.strip() or None,
        "weight": weight if weight > 0 else None,
        "weight_unit": weight_unit,
        "qty_per_carton": qty_per_carton if qty_per_carton > 0 else None,
        "is_active": _active_value_to_int(active_value),
        "note": note.strip() or None,
    }
    return payload, submitted


# -------------------------
# Mutations
# -------------------------
def insert_product(payload: Dict[str, Any], user_id: int = DEFAULT_USER_ID) -> None:
    if not payload.get("product_code"):
        raise ValueError(_t("產品代碼為必填。"))

    sql = """
    INSERT INTO product (
      product_code, customer_production_id, product_name, unit, customer_id,
      `Specification`, `Specification_unit`,
      weight, weight_unit, color, unit_price, product_barcode, qty_per_carton,
      is_active, create_at, created_by_id, update_at, updated_by_id
    ) VALUES (
      :product_code, :customer_production_id, :product_name, :unit, :customer_id,
      :specification, :specification_unit,
      :weight, :weight_unit, :color, NULL, :product_barcode, :qty_per_carton,
      :is_active, NOW(), :user_id, NULL, NULL
    )
    """
    params = dict(payload)
    params["user_id"] = int(user_id)
    exec_sql(sql, params)


def update_product(product_id: int, payload: Dict[str, Any], user_id: int = DEFAULT_USER_ID) -> None:
    sql = """
    UPDATE product
    SET
      customer_production_id = :customer_production_id,
      product_name = :product_name,
      unit = :unit,
      customer_id = :customer_id,
      `Specification` = :specification,
      `Specification_unit` = :specification_unit,
      weight = :weight,
      weight_unit = :weight_unit,
      color = :color,
      product_barcode = :product_barcode,
      qty_per_carton = :qty_per_carton,
      is_active = :is_active,
      update_at = NOW(),
      updated_by_id = :user_id
    WHERE product_id = :product_id
    """
    params = dict(payload)
    params["product_id"] = int(product_id)
    params["user_id"] = int(user_id)
    exec_sql(sql, params)


def apply_new_product_price(
    product_id: int,
    new_unit_price: Decimal,
    user_id: int = DEFAULT_USER_ID,
    valid_to: Optional[datetime] = None,
) -> int:
    """
    Close current price (if any), insert a new price row, and update product.unit_price.
    valid_from is always "now" in this MVP page.
    """
    now_dt = datetime.now().replace(microsecond=0)
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    valid_to_str = None
    if valid_to is not None:
        valid_to = valid_to.replace(microsecond=0)
        if valid_to <= now_dt:
            raise ValueError("停止時間必須晚於開始時間。")
        valid_to_str = valid_to.strftime("%Y-%m-%d %H:%M:%S")

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE product_unit_price
                SET valid_to = :now
                WHERE product_unit_price_id = :product_id
                  AND valid_to IS NULL
                """
            ),
            {"now": now_str, "product_id": product_id},
        )

        result = conn.execute(
            text(
                """
                INSERT INTO product_unit_price
                    (product_unit_price_id, unit_price, created_at, created_by, is_active, valid_from, valid_to)
                VALUES
                    (:product_id, :price, :created_at, :created_by, 1, :valid_from, :valid_to)
                """
            ),
            {
                "product_id": product_id,
                "price": new_unit_price,
                "created_at": now_str,
                "created_by": user_id,
                "valid_from": now_str,
                "valid_to": valid_to_str,
            },
        )
        price_id = result.lastrowid

        conn.execute(
            text("""
                UPDATE product
                SET unit_price = :p,
                    update_at = :now,
                    updated_by_id = :user_id
                WHERE product_id = :pid
            """),
            {"p": new_unit_price, "now": now_str, "user_id": int(user_id), "pid": product_id},
        )

    return int(price_id)


def render_price_panel(product_id: int, product_label: str) -> None:
    st.info(_t("P01 已隱藏價格設定，請改到 P04 價格級距頁維護價格。"))


def open_price_dialog(product_id: int, product_label: str) -> None:
    st.info(_t("P01 已隱藏價格設定，請改到 P04 價格級距頁維護價格。"))


st.title(_t("P01 產品主檔"))

st.session_state.setdefault("p01_page", 1)
st.session_state.setdefault("p01_page_size", DEFAULT_PAGE_SIZE)
st.session_state.setdefault("p01_show_form", True)
st.session_state.setdefault("p01_q", "")
st.session_state.setdefault("p01_status", "all")
st.session_state.setdefault("p01_customer_label", _t("全部客戶"))
st.session_state.setdefault("p01_create_clear_token", 0)

c1, c2, c3, c4, c5 = st.columns([2.4, 1.1, 1.8, 1.0, 1.0], vertical_alignment="bottom")

with c1:
    q = st.text_input(_t("搜尋（產品代碼 / 名稱 / 條碼）"), value=st.session_state.get("p01_q", ""))
    st.session_state["p01_q"] = q

with c2:
    status_labels = {_t("全部"): "all", _t("啟用"): "active", _t("停用"): "inactive"}
    current_status = st.session_state.get("p01_status", "all")
    current_status_label = next((k for k, v in status_labels.items() if v == current_status), _t("全部"))
    selected_status_label = st.selectbox(
        _t("狀態"),
        options=list(status_labels.keys()),
        index=list(status_labels.keys()).index(current_status_label),
    )
    active_filter = status_labels[selected_status_label]
    st.session_state["p01_status"] = active_filter

with c3:
    customers_df = load_customers(active_only=False)
    all_customer_label = _t("全部客戶")
    customer_option_labels = [all_customer_label]
    cust_id_map: Dict[str, int] = {}
    if not customers_df.empty:
        customers_df = customers_df.copy()
        customers_df["label"] = customers_df["customer_code"].astype(str) + " | " + customers_df["customer_shortname"].astype(str)
        for _, row in customers_df.iterrows():
            label = str(row["label"])
            customer_option_labels.append(label)
            cust_id_map[label] = int(row["customer_id"])

    saved_customer_label = st.session_state.get("p01_customer_label", all_customer_label)
    if saved_customer_label not in customer_option_labels:
        saved_customer_label = all_customer_label
    cust_label = st.selectbox(_t("客戶篩選"), options=customer_option_labels, index=customer_option_labels.index(saved_customer_label))
    st.session_state["p01_customer_label"] = cust_label
    cust_filter_id = cust_id_map.get(cust_label)

with c4:
    page_size = st.selectbox(
        _t("每頁筆數"),
        options=PAGE_SIZE_OPTIONS,
        index=PAGE_SIZE_OPTIONS.index(int(st.session_state.get("p01_page_size", DEFAULT_PAGE_SIZE))),
    )
    if page_size != st.session_state.get("p01_page_size"):
        st.session_state["p01_page_size"] = int(page_size)
        st.session_state["p01_page"] = 1
        st.rerun()

with c5:
    if st.button(_t("重新整理"), use_container_width=True):
        _invalidate_page_cache()
        st.rerun()

total = load_products_count(search=q, active_filter=active_filter, customer_id=cust_filter_id)
total_pages = max(1, math.ceil(total / int(page_size)))
page = min(max(1, int(st.session_state.get("p01_page", 1))), total_pages)
st.session_state["p01_page"] = page

p1, p2, p3 = st.columns([1, 1, 4], vertical_alignment="center")
with p1:
    if st.button(_t("上一頁"), use_container_width=True, disabled=page <= 1):
        st.session_state["p01_page"] = page - 1
        st.rerun()
with p2:
    if st.button(_t("下一頁"), use_container_width=True, disabled=page >= total_pages):
        st.session_state["p01_page"] = page + 1
        st.rerun()
with p3:
    st.caption(f"{_t('共')} {total} {_t('筆')}，{_t('第')} {page}/{total_pages} {_t('頁')}")

products_df = load_products_page(
    search=q,
    active_filter=active_filter,
    customer_id=cust_filter_id,
    page_size=int(page_size),
    page=page,
)

st.subheader(_t("產品清單"))

grid = products_df.copy()
if not grid.empty:
    grid.insert(0, "selected", False)

rename_map = {
    "selected": _t("選取"),
    "product_code": _t("產品代碼"),
    "product_name": _t("產品名稱"),
    "customer_shortname": _t("客戶"),
    "customer_production_id": _t("客戶料號"),
    "unit": _t("單位"),
    "specification": _t("規格"),
    "color": _t("顏色"),
    "unit_price": _t("單價"),
    "qty_per_carton": _t("箱入數"),
    "product_barcode": _t("條碼"),
    "is_active": _t("狀態"),
    "created_by_display": _t("建立者"),
    "updated_by_display": _t("最後修改者"),
}

display_cols = [
    "selected", "product_code", "product_name", "customer_shortname",
    "customer_production_id", "unit", "specification", "color",
    "unit_price", "qty_per_carton", "product_barcode", "is_active",
    "created_by_display", "updated_by_display",
]
display_cols = [col for col in display_cols if col in grid.columns]
grid_display = grid[display_cols].rename(columns=rename_map)

status_col = _t("狀態")
price_col = _t("單價")
select_col = _t("選取")
if status_col in grid_display.columns:
    grid_display[status_col] = grid_display[status_col].map(lambda value: _t("啟用") if int(value) == 1 else _t("停用"))
if price_col in grid_display.columns:
    grid_display[price_col] = "***"

edited = st.data_editor(
    grid_display,
    use_container_width=True,
    hide_index=True,
    height=int(st.session_state.setdefault("p01_top_height", 260)),
    disabled=[col for col in grid_display.columns if col != select_col],
)

selected_idx = None
if select_col in edited.columns:
    selected_rows = edited[select_col] == True
    if selected_rows.any():
        selected_idx = selected_rows[selected_rows].index[0]

selected_product_id: Optional[int] = None
selected_row: Optional[Dict[str, Any]] = None
if selected_idx is not None and selected_idx < len(products_df):
    selected_product_id = int(products_df.iloc[selected_idx]["product_id"])
    selected_row = products_df.iloc[selected_idx].to_dict()

apply_vertical_splitter(
    "p01_top_height",
    "p01_vertical_splitter_control",
    default=260,
    min_top=150,
    max_top=430,
)

st.divider()

a1, a2 = st.columns([1.2, 4.8], vertical_alignment="center")
with a1:
    label = _t("收起新增／編輯區") if st.session_state.get("p01_show_form", True) else _t("展開新增／編輯區")
    if st.button(label, use_container_width=True):
        st.session_state["p01_show_form"] = not st.session_state.get("p01_show_form", True)
        st.rerun()
with a2:
    st.caption(_t("上方勾選一筆即可在下方編輯；未勾選時下方會新增產品。價格請改到 P04 價格級距頁維護。"))

if st.session_state.get("p01_show_form", True):
    customers_for_form = load_customers(active_only=False)
    if selected_product_id and selected_row:
        payload, submitted = _render_product_form(selected_row, customers_for_form, mode="edit")
        if submitted:
            try:
                auth.require_edit(PAGE_KEY)
                update_product(selected_product_id, payload, user_id=USER_ID)
                st.success(_t("已儲存"))
                _invalidate_page_cache()
                st.rerun()
            except Exception as e:
                st.error(f"{_t('儲存失敗')}：{e}")
    else:
        payload, submitted = _render_product_form({}, customers_for_form, mode="create")
        if submitted:
            try:
                auth.require_edit(PAGE_KEY)
                insert_product(payload, user_id=USER_ID)
                st.success(_t("已新增"))
                st.session_state["p01_create_clear_token"] = int(st.session_state.get("p01_create_clear_token", 0)) + 1
                _invalidate_page_cache()
                st.rerun()
            except Exception as e:
                st.error(f"{_t('新增失敗')}：{e}")
