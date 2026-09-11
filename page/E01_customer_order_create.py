import streamlit as st
from compact_layout import apply_compact_layout
import auth
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List, Dict

import sys
from pathlib import Path

apply_compact_layout()

# E01 action labels become much longer in English/Vietnamese.  Let labels wrap
# inside their buttons, and give the order-list actions a shared height so the
# buttons remain aligned even when only one label needs two lines.
st.markdown(
    """<style>
    [data-testid="stButton"] button p {
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        line-height: 1.2 !important;
    }
    .st-key-e01_btn_load_selected_order button,
    .st-key-e01_btn_clear_order_selection button,
    .st-key-e01_btn_refresh_master_table button,
    .st-key-e01_btn_delete_selected_orders button {
        height: 3.25rem !important;
        min-height: 3.25rem !important;
        padding-top: 0.2rem !important;
        padding-bottom: 0.2rem !important;
    }
    </style>""",
    unsafe_allow_html=True,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from core.i18n import init_language, tr as _t


# ---------------------------
# E01 local fallback translations
# ---------------------------
# The central Excel/i18n table is still the main translation source.
# This fallback prevents [MISS:...] on the schedule dialog before the Excel table is updated.
E01_LOCAL_TRANSLATIONS = {
    "訂單類別": {"vi": "Loại đơn hàng", "en": "Order Category"},
    "一般訂單": {"vi": "Đơn hàng thông thường", "en": "General Order"},
    "補料單（要收款）": {"vi": "Đơn bù nguyên liệu (Cần thu tiền)", "en": "Material Replenishment Order (Receivable)"},
    "補料單（不收款）": {"vi": "Đơn bù nguyên liệu (Không thu tiền)", "en": "Material Replenishment Order (Non-Receivable)"},
    "設定交貨排程": {"vi": "Thiết lập lịch giao hàng", "en": "Set Delivery Schedule"},
    "交貨排程": {"vi": "Lịch giao hàng", "en": "Delivery Schedule"},
    "品項": {"vi": "Sản phẩm", "en": "Item"},
    "訂單數量": {"vi": "Số lượng đặt hàng", "en": "Order Quantity"},
    "訂單總數量": {"vi": "Tổng số lượng đặt hàng", "en": "Total Order Quantity"},
    "請輸入每一批預計交貨日期與數量；儲存時系統會檢查分批數量總和是否等於訂單明細數量。": {
        "vi": "Vui lòng nhập ngày giao hàng dự kiến và số lượng cho từng đợt; khi lưu, hệ thống sẽ kiểm tra tổng số lượng các đợt có bằng số lượng chi tiết đơn hàng hay không.",
        "en": "Enter the planned delivery date and quantity for each batch; when saving, the system will check whether the batch total equals the order item quantity.",
    },
    "批次": {"vi": "Đợt", "en": "Batch"},
    "預計交期": {"vi": "Ngày giao hàng dự kiến", "en": "Planned Delivery Date"},
    "本批數量": {"vi": "Số lượng đợt này", "en": "Batch Quantity"},
    "備註": {"vi": "Ghi chú", "en": "Note"},
    "分批合計": {"vi": "Tổng số lượng các đợt", "en": "Batch Total"},
    "差異": {"vi": "Chênh lệch", "en": "Difference"},
    "儲存交貨排程": {"vi": "Lưu lịch giao hàng", "en": "Save Delivery Schedule"},
    "關閉": {"vi": "Đóng", "en": "Close"},
    "提醒：分批數量加總必須等於此訂單明細的總數量。": {
        "vi": "Lưu ý: Tổng số lượng các đợt phải bằng tổng số lượng của chi tiết đơn hàng này.",
        "en": "Reminder: The sum of batch quantities must equal the total quantity of this order item.",
    },
    "目前批數": {"vi": "Số đợt hiện tại", "en": "Current Batches"},
    "排程合計": {"vi": "Tổng số lượng theo lịch", "en": "Scheduled Total"},
    "勾選明細後，可在彈窗中設定多個客戶指定交期；數量合計必須等於明細總數量。": {
        "vi": "Sau khi chọn chi tiết, có thể thiết lập nhiều ngày giao hàng theo yêu cầu khách hàng trong cửa sổ bật lên; tổng số lượng phải bằng số lượng chi tiết.",
        "en": "After selecting an item, you can set multiple customer-requested delivery dates in the dialog; the total quantity must equal the item quantity.",
    },
}


def _e01_lang() -> str:
    lang = st.session_state.get("lang", st.session_state.get("language", "zh"))
    return lang if lang in {"zh", "vi", "en"} else "zh"


def _e01_t(text: str) -> str:
    translated = _t(text)
    if translated != text and not str(translated).startswith("[MISS:"):
        return translated
    if _e01_lang() == "zh":
        return text
    return E01_LOCAL_TRANSLATIONS.get(text, {}).get(_e01_lang(), text)


CUSTOMER_ORDER_CATEGORY_GENERAL = "general"
CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_RECEIVABLE = "material_replenishment_receivable"
CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_NON_RECEIVABLE = "material_replenishment_non_receivable"
CUSTOMER_ORDER_CATEGORY_OPTIONS = {
    CUSTOMER_ORDER_CATEGORY_GENERAL: "一般訂單",
    CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_RECEIVABLE: "補料單（要收款）",
    CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_NON_RECEIVABLE: "補料單（不收款）",
}


def customer_order_category_label(category: str) -> str:
    return _e01_t(CUSTOMER_ORDER_CATEGORY_OPTIONS.get(
        str(category or "").strip(),
        CUSTOMER_ORDER_CATEGORY_OPTIONS[CUSTOMER_ORDER_CATEGORY_GENERAL],
    ))


def _format_total_quantity(value) -> str:
    """Format a quantity without unnecessary decimal zeroes."""
    try:
        return f"{float(value):,.3f}".rstrip("0").rstrip(".")
    except Exception:
        return "0"

# =============================================================================
# E01 - 客戶訂單（輸入）
#   - customer_order (母表)
#   - customer_order_item (子表)
#
# 2026-01-23 更新（依 Cyrus 需求）
# 1) 顯示 customer_order 母表清單（最左勾選，載入後可編輯下方明細）
# 2) 本公司訂單號 customer_order_code：自動生成、不可編輯、移到客戶下拉左邊（欄位縮窄）
# 3) 刪除「重新生成」
# 4) 訂單號邏輯：CO + YYMMDD + 流水號(3碼) 例：CO260123001
# =============================================================================


# ---------------------------
# DB connection (compatible with your db.py)
# ---------------------------
def _fallback_get_connection():
    import os
    import mysql.connector
    from mysql.connector import Error

    cfg = {
        "host": os.getenv("ORDO_DB_HOST", "localhost"),
        "port": int(os.getenv("ORDO_DB_PORT", "3306")),
        "user": os.getenv("ORDO_DB_USER", "root"),
        "password": os.getenv("ORDO_DB_PASSWORD", ""),
        "database": os.getenv("ORDO_DB_NAME", "ordotest"),
    }
    try:
        return mysql.connector.connect(**cfg)
    except Error as e:
        st.error(f"DB connect error: {e}")
        return None


try:
    from db import get_connection  # type: ignore
except Exception:  # pragma: no cover
    try:
        from db import get_engine  # type: ignore

        def get_connection():  # type: ignore
            eng = get_engine()
            return eng.raw_connection()

    except Exception:  # pragma: no cover
        get_connection = _fallback_get_connection  # type: ignore


def ensure_customer_order_category_column() -> None:
    """Add the customer-order category column on databases not yet migrated."""
    conn = get_connection()
    if conn is None:
        raise RuntimeError("DB 連線失敗，無法建立 customer_order.customer_order_category")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'customer_order'
                  AND column_name = 'customer_order_category'
                LIMIT 1
            """)
            if cur.fetchone() is None:
                cur.execute("""
                    ALTER TABLE customer_order
                    ADD COLUMN customer_order_category VARCHAR(48)
                    NOT NULL DEFAULT 'general' AFTER order_source
                """)
                conn.commit()
    finally:
        conn.close()


ensure_customer_order_category_column()


# ---------------------------
# Data access (cached)
# ---------------------------
@st.cache_data(show_spinner=False, ttl=30)
def fetch_customers() -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    sql = """
        SELECT customer_id, customer_code, customer_name, customer_shortname, is_active
        FROM customer
        ORDER BY customer_name ASC
    """
    df = pd.read_sql(sql, conn)
    try:
        conn.close()
    except Exception:
        pass
    return df


@st.cache_data(show_spinner=False, ttl=30)
def fetch_receiving_addresses(customer_id: int) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    sql = """
        SELECT receiving_id, receiving_add, warehouse_contact_person, tel, is_active
        FROM customer_receiving_add
        WHERE customer_id = %s
        ORDER BY receiving_id ASC
    """
    df = pd.read_sql(sql, conn, params=[int(customer_id)])
    try:
        conn.close()
    except Exception:
        pass
    return df


@st.cache_data(show_spinner=False, ttl=30)
def fetch_products_by_customer(customer_id: int) -> pd.DataFrame:
    """
    依客戶取回可選品項清單（product），並帶出「最新單價」。

    最新單價策略（依你的要求）：
    - 先用 product_code(Pxxxxx) 對應 material.item_code(Mxxxxx)，取 material_unit_price(valid_to IS NULL, 最新 valid_from)
    - 若找不到對應原料/單價，再回退 product_unit_price(valid_to IS NULL, 最新 valid_from)
    - 再回退 product.unit_price
    """
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    sql = """
        SELECT
            p.product_id,
            p.product_code,
            p.customer_production_id AS customer_product_id,
            p.product_name,
            p.Specification AS specification,
            p.Specification_unit AS specification_unit,
            p.unit,
            p.color,
            COALESCE(
                (
                    SELECT upp.unit_price
                    FROM product_unit_price upp
                    WHERE upp.product_unit_price_id = p.product_id
                      AND upp.is_active = 1
                      AND upp.valid_from <= NOW()
                      AND (upp.valid_to IS NULL OR upp.valid_to >= NOW())
                    ORDER BY upp.valid_from DESC, upp.price_id DESC
                    LIMIT 1
                ),
                (
                    SELECT upp2.unit_price
                    FROM product_unit_price upp2
                    WHERE upp2.product_unit_price_id = p.product_id
                      AND upp2.is_active = 1
                    ORDER BY upp2.valid_from DESC, upp2.price_id DESC
                    LIMIT 1
                ),
                p.unit_price
            ) AS unit_price
        FROM product p
        WHERE p.customer_id = %s AND p.is_active = 1
        ORDER BY p.product_name ASC
"""
    df = pd.read_sql(sql, conn, params=[int(customer_id)])
    try:
        conn.close()
    except Exception:
        pass
    return df


def build_product_select_label(row) -> str:
    """Build product labels for order item selectors."""
    product_code = str(row.get("product_code") or "").strip()
    product_name = str(row.get("product_name") or "").strip()
    customer_product_id = str(row.get("customer_product_id") or "").strip()
    specification = str(row.get("specification") or "").strip()
    third = customer_product_id or specification
    return " | ".join([part for part in [product_code, product_name, third] if part])


@st.cache_data(show_spinner=False, ttl=30)
def fetch_customer_orders(
    customer_id: int,
    q_customer_order_code: str = "",
    q_customer_order_num: str = "",
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    limit: int = 200,
) -> pd.DataFrame:
    """
    依查詢條件撈 customer_order 清單。
    - q_customer_order_code / q_customer_order_num：模糊查詢（LIKE %...%）
    - created_from / created_to：以 created_at 範圍過濾（日期）
    """
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    where: List[str] = []
    params: List = []

    # customer_id == 0 means "all customers"
    if int(customer_id) != 0:
        where.append("co.customer_id = %s")
        params.append(int(customer_id))

    if q_customer_order_code and str(q_customer_order_code).strip():
        where.append("co.customer_order_code LIKE %s")
        params.append(f"%{str(q_customer_order_code).strip()}%")

    if q_customer_order_num and str(q_customer_order_num).strip():
        where.append("co.customer_order_num LIKE %s")
        params.append(f"%{str(q_customer_order_num).strip()}%")

    if created_from is not None:
        where.append("co.created_at >= %s")
        params.append(datetime.combine(created_from, datetime.min.time()))

    if created_to is not None:
        # 迄日採用「小於隔日 00:00:00」避免時分秒邊界問題
        where.append("co.created_at < %s")
        params.append(datetime.combine(created_to + timedelta(days=1), datetime.min.time()))

    where_sql = " AND ".join(where) if where else "1=1"

    sql = f"""
        SELECT
            co.customer_order_id,
            co.customer_order_code,
            co.customer_order_num,
            c.customer_shortname,
            co.customer_order_category,
            co.deliver_date,
            co.state,
            co.order_status,
            co.created_at,
            COALESCE(created_stuff.stuff_name, created_user.user_code,
                     CASE WHEN co.created_by IS NULL THEN '' ELSE CONCAT('User#', co.created_by) END) AS created_by_name,
            CASE
                WHEN co.updated_by IS NULL THEN ''
                WHEN co.updated_at IS NULL THEN ''
                WHEN co.created_at IS NOT NULL
                     AND co.updated_at IS NOT NULL
                     AND co.updated_by = co.created_by
                     AND ABS(TIMESTAMPDIFF(SECOND, co.created_at, co.updated_at)) <= 2 THEN ''
                ELSE COALESCE(updated_stuff.stuff_name, updated_user.user_code, CONCAT('User#', co.updated_by))
            END AS updated_by_name
        FROM customer_order co
        LEFT JOIN customer c ON c.customer_id = co.customer_id
        LEFT JOIN `user` created_user ON created_user.user_id = co.created_by
        LEFT JOIN stuff created_stuff ON created_stuff.stuff_id = created_user.stuff_id
        LEFT JOIN `user` updated_user ON updated_user.user_id = co.updated_by
        LEFT JOIN stuff updated_stuff ON updated_stuff.stuff_id = updated_user.stuff_id
        WHERE {where_sql}
        ORDER BY co.customer_order_id DESC
        LIMIT %s
    """
    params.append(int(limit))

    df = pd.read_sql(sql, conn, params=params)
    try:
        conn.close()
    except Exception:
        pass
    return df

def fetch_customer_order_head(customer_order_id: int) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    sql = """
        SELECT
            customer_order_id,
            customer_order_code,
            customer_order_num,
            customer_id,
            customer_order_category,
            deliver_to,
            deliver_date,
            state,
            order_status,
            created_at,
            created_by,
            updated_at,
            updated_by
        FROM customer_order
        WHERE customer_order_id = %s
        LIMIT 1
    """
    df = pd.read_sql(sql, conn, params=[int(customer_order_id)])
    try:
        conn.close()
    except Exception:
        pass
    return df






def format_customer_order_status_for_grid(v):
    s = str(v or "").strip()
    if s == "shipped":
        return f"🟢 {_t('已出貨')}"
    elif s == "already_in_stock":
        return f"🔵 {_t('已入庫')}"
    elif s == "partial_warehousing":
        return f"🟠 {_t('部分入庫')}"
    elif s == "not_in_stock":
        return f"🔴 {_t('未入庫')}"
    return f"⚪ {s}" if s else ""


@st.cache_data(show_spinner=False, ttl=10)
def fetch_customer_order_detail(customer_order_id: int) -> pd.DataFrame:
    """Backward-compatible wrapper.
    The UI expects a single-row DataFrame containing customer_order (head) columns.
    """
    return fetch_customer_order_head(customer_order_id)

@st.cache_data(show_spinner=False, ttl=10)
def fetch_customer_order_items(customer_order_id: int) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    sql = """
        SELECT
            i.customer_order_item_id,
            i.customer_order_id,
            i.line_no,
            i.product_id,
            i.price_tier_id,
            CASE
                WHEN i.price_tier_id IS NULL THEN 'base'
                ELSE 'tier'
            END AS price_source,
            p.product_code,
            p.customer_production_id AS customer_product_id,
            p.product_name,
            p.Specification AS specification,
            p.Specification_unit AS specification_unit,

            -- E01 顯示訂單成立時寫入的成交單價快照；不要每次重新抓目前價格
            COALESCE(i.price_unit, p.unit_price) AS price_unit,

            i.unit,
            i.quantity,
            i.barcode,
            i.deliver_date
        FROM customer_order_item i
        JOIN product p ON p.product_id = i.product_id
        WHERE i.customer_order_id = %s
        ORDER BY i.line_no ASC
"""
    df = pd.read_sql(sql, conn, params=[int(customer_order_id)])
    try:
        conn.close()
    except Exception:
        pass
    return df

# ---------------------------
# Customer order code
# ---------------------------
def _generate_customer_order_code(customer_shortname: str, basis_date: Optional[date] = None) -> str:
    """
    CD - customer short name - YYMMDD + seq(3 digits)
    Example: CD-YI-260123001

    The three-digit sequence is independent for each customer and date.
    """
    shortname = str(customer_shortname or "").strip()
    if not shortname:
        raise ValueError("客戶簡稱為必填，無法產生本公司訂單號。")

    d = basis_date or date.today()
    yymmdd = d.strftime("%y%m%d")
    prefix = f"CD-{shortname}-{yymmdd}"

    conn = get_connection()
    if conn is None:
        # This is only for the read-only preview. Actual creation requires a
        # database connection and performs the same sequence lookup again.
        return f"{prefix}001"

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(CAST(RIGHT(customer_order_code, 3) AS UNSIGNED))
                FROM customer_order
                WHERE LEFT(customer_order_code, %s) = %s
                  AND CHAR_LENGTH(customer_order_code) = %s
                  AND RIGHT(customer_order_code, 3) REGEXP '^[0-9]{3}$'
                """,
                (len(prefix), prefix, len(prefix) + 3),
            )
            mx = cur.fetchone()[0]
            seq = int(mx or 0) + 1
    except Exception:
        seq = 1
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if seq > 999:
        raise ValueError(f"{prefix} 當日流水號已達三碼上限。")
    return f"{prefix}{seq:03d}"


# ---------------------------
# Mutations
# ---------------------------
# ---------------------------
# Audit helpers
# ---------------------------
def _current_user_id(default: int = 1) -> int:
    try:
        return int(st.session_state.get("user_id") or default)
    except Exception:
        return int(default)


def _touch_customer_order_head(customer_order_id: int, updated_by: Optional[int] = None) -> None:
    """Mark customer_order as modified by the current user.

    This is used when E01 changes order items. Item changes are still changes to
    the order as a whole, so the mother-table audit columns must reflect them.
    """
    if not customer_order_id:
        return
    user_id = int(updated_by) if updated_by is not None else _current_user_id()
    conn = get_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE customer_order
                SET updated_at = NOW(),
                    updated_by = %s
                WHERE customer_order_id = %s
                """,
                (int(user_id), int(customer_order_id)),
            )
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def create_customer_order_head(
    customer_id: int,
    customer_order_num: str,
    deliver_to: Optional[int],
    deliver_date: date,
    state: str,
    customer_order_category: str = CUSTOMER_ORDER_CATEGORY_GENERAL,
    created_by: int = 1,
) -> Tuple[bool, str, Optional[int], Optional[str]]:
    """
    建立 customer_order (母表)；本公司訂單號一律自動生成，不允許前端覆寫。
    若 customer_order_num 有填：同客戶/單號/日期 -> 載入既有，避免重複建單。
    """
    auth.require_edit(PAGE_KEY)
    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗", None, None

    try:
        customer_order_category = str(customer_order_category or "").strip()
        if customer_order_category not in CUSTOMER_ORDER_CATEGORY_OPTIONS:
            return False, "訂單類別不正確，請重新選擇。", None, None
        cur = conn.cursor()

        # 若有客戶單號：同客戶/單號/日期 -> 載入既有
        if (customer_order_num or "").strip():
            cur.execute(
                """
                SELECT customer_order_id, customer_order_code
                FROM customer_order
                WHERE customer_id = %s AND customer_order_num = %s AND deliver_date = %s
                ORDER BY customer_order_id DESC
                LIMIT 1
                """,
                (int(customer_id), str(customer_order_num), deliver_date),
            )
            row = cur.fetchone()
            if row and row[0]:
                return True, "已載入既有訂單（同客戶/單號/日期）", int(row[0]), str(row[1])

        cur.execute(
            """
            SELECT NULLIF(TRIM(customer_shortname), '')
            FROM customer
            WHERE customer_id = %s
            LIMIT 1
            """,
            (int(customer_id),),
        )
        shortname_row = cur.fetchone()
        customer_shortname = str(shortname_row[0] or "").strip() if shortname_row else ""
        if not customer_shortname:
            return False, "客戶簡稱為必填，無法產生本公司訂單號。", None, None

        # Auto code
        order_code = _generate_customer_order_code(customer_shortname, basis_date=date.today())

        # best-effort uniqueness check
        cur.execute(
            "SELECT customer_order_id FROM customer_order WHERE customer_order_code = %s LIMIT 1",
            (str(order_code),),
        )
        dup = cur.fetchone()
        if dup and dup[0]:
            # rare: regenerate once
            order_code = _generate_customer_order_code(customer_shortname, basis_date=date.today())
            cur.execute(
                "SELECT customer_order_id FROM customer_order WHERE customer_order_code = %s LIMIT 1",
                (str(order_code),),
            )
            dup2 = cur.fetchone()
            if dup2 and dup2[0]:
                return False, f"訂單號碰撞（請重試）：{order_code}", None, None

        cur.execute(
            """
            INSERT INTO customer_order
            (customer_order_num, customer_id, customer_short_name, customer_order_code,
             customer_order_category, deliver_to, deliver_date, created_at, created_by, state)
            VALUES
            (%s, %s, %s, %s, %s,
             %s, %s, NOW(), %s, %s)
            """,
            (
                str(customer_order_num or ""),
                int(customer_id),
                int(customer_id),  # temp: schema is BIGINT, keep system running
                str(order_code),
                customer_order_category,
                int(deliver_to) if deliver_to is not None else None,
                deliver_date,
                int(created_by),
                str(state),
            ),
        )
        order_id = int(cur.lastrowid)
        conn.commit()
        return True, f"建立完成：{order_code}", order_id, str(order_code)

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"建立失敗：{e}", None, None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def update_customer_order_head(
    customer_order_id: int,
    customer_order_num: str,
    deliver_to: Optional[int],
    deliver_date: date,
    state: str,
    customer_order_category: str = CUSTOMER_ORDER_CATEGORY_GENERAL,
    updated_by: int = 1,
) -> Tuple[bool, str]:
    """
    更新抬頭：不允許修改 customer_order_code（前端也不提供編輯）。
    """
    auth.require_edit(PAGE_KEY)
    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"

    try:
        customer_order_category = str(customer_order_category or "").strip()
        if customer_order_category not in CUSTOMER_ORDER_CATEGORY_OPTIONS:
            return False, "訂單類別不正確，請重新選擇。"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT customer_order_category FROM customer_order WHERE customer_order_id = %s LIMIT 1",
                (int(customer_order_id),),
            )
            row = cur.fetchone()
            current_category = str(row[0] or CUSTOMER_ORDER_CATEGORY_GENERAL).strip() if row else CUSTOMER_ORDER_CATEGORY_GENERAL
            if current_category != customer_order_category:
                cur.execute(
                    "SELECT 1 FROM delivery_head WHERE customer_order_id = %s LIMIT 1",
                    (int(customer_order_id),),
                )
                if cur.fetchone() is not None:
                    return False, "此訂單已有送貨紀錄，為避免 AR 帳務不一致，不能再變更訂單類別。"
            cur.execute(
                """
                UPDATE customer_order
                SET
                    customer_order_num = %s,
                    customer_order_category = %s,
                    deliver_to = %s,
                    deliver_date = %s,
                    state = %s,
                    updated_at = NOW(),
                    updated_by = %s
                WHERE customer_order_id = %s
                """,
                (
                    str(customer_order_num or ""),
                    customer_order_category,
                    int(deliver_to) if deliver_to is not None else None,
                    deliver_date,
                    str(state),
                    int(updated_by),
                    int(customer_order_id),
                ),
            )
            conn.commit()
        return True, "訂單抬頭已更新"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"更新失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def insert_customer_order_items(customer_order_id: int, rows, created_by: Optional[int] = None) -> Tuple[bool, str]:
    """
    Insert new rows into customer_order_item. Schedule rows are created only when the user explicitly saves a delivery schedule.

    rows can be either:
      - pandas.DataFrame
      - list[dict]

    Required fields: product_id, unit, quantity
    Optional fields: price_unit, price_tier_id, deliver_date
    """
    auth.require_edit(PAGE_KEY)

    if rows is None:
        return False, "沒有可新增的列"

    # Normalize rows -> DataFrame
    if isinstance(rows, list):
        if len(rows) == 0:
            return False, "沒有可新增的列"
        rows_df = pd.DataFrame(rows)
    elif isinstance(rows, pd.DataFrame):
        if rows.empty:
            return False, "沒有可新增的列"
        rows_df = rows.copy()
    else:
        return False, f"rows 格式錯誤：{type(rows).__name__}"

    # 先檢查本次要寫入的 rows 自己有沒有重複 product_id
    try:
        _pid_series = rows_df["product_id"].dropna().astype(int)
        if _pid_series.duplicated().any():
            return False, "同一張訂單不可出現相同品項。"
    except Exception:
        pass

    user_id = int(created_by) if created_by is not None else _current_user_id()

    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT customer_id, deliver_date FROM customer_order WHERE customer_order_id = %s LIMIT 1",
                (int(customer_order_id),),
            )
            _order_row = cur.fetchone()
            if not _order_row:
                return False, "找不到訂單抬頭，無法新增明細。"
            _order_deliver_date = _order_row[1] if _order_row[1] is not None else date.today()

            # current max line_no
            cur.execute(
                "SELECT COALESCE(MAX(line_no), 0) FROM customer_order_item WHERE customer_order_id = %s",
                (int(customer_order_id),),
            )
            mx = cur.fetchone()[0]
            line_no = int(mx or 0)

            for _, r in rows_df.iterrows():
                _pid = int(r["product_id"])

                # 真正寫入前再檢查一次 DB，避免 UI 漏網或雙擊造成重複
                cur.execute(
                    """
                    SELECT 1
                    FROM customer_order_item
                    WHERE customer_order_id = %s
                      AND product_id = %s
                    LIMIT 1
                    """,
                    (int(customer_order_id), _pid),
                )
                _dup = cur.fetchone()
                if _dup:
                    conn.rollback()
                    return False, "同一張訂單不可出現相同品項。"

                _qty = float(r.get("quantity") or 0)
                _price = float(r.get("price_unit")) if pd.notna(r.get("price_unit")) else None
                _tier = int(r.get("price_tier_id")) if pd.notna(r.get("price_tier_id")) else None
                # 明細交期維持使用者輸入值；未輸入就保持 NULL。
                # 不再自動把 customer_order.deliver_date 灌入明細，也不再自動建立預設分批交期。
                # 原因：未分批的明細若全部被建立 schedule，Home「後續未完成交期」會被未分交期資料塞滿。
                _raw_dd = r.get("deliver_date")
                _dd = None if pd.isna(_raw_dd) or _raw_dd in (None, "") else _raw_dd

                line_no += 1
                cur.execute(
                    """
                    INSERT INTO customer_order_item
                    (customer_order_id, line_no, product_id, unit, quantity, price_unit, price_tier_id, deliver_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(customer_order_id),
                        int(line_no),
                        _pid,
                        str(r.get("unit") or "PCS"),
                        _qty,
                        _price,
                        _tier,
                        _dd,
                    ),
                )

            conn.commit()
        return True, f"已新增 {len(rows_df)} 列"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"新增失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def order_has_same_product(customer_order_id: int, product_id: int, exclude_item_id: Optional[int] = None) -> bool:
    """檢查同一張訂單是否已存在相同 product_id。"""
    conn = get_connection()
    if conn is None:
        return False
    try:
        sql = """
            SELECT 1
            FROM customer_order_item
            WHERE customer_order_id = %s
              AND product_id = %s
        """
        params = [int(customer_order_id), int(product_id)]
        if exclude_item_id is not None:
            sql += " AND customer_order_item_id <> %s"
            params.append(int(exclude_item_id))
        sql += " LIMIT 1"
        df = pd.read_sql(sql, conn, params=params)
        return not df.empty
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def fetch_customer_order_item_id_by_product(customer_order_id: int, product_id: int) -> Optional[int]:
    """Find the order item id for customer_order_id + product_id."""
    conn = get_connection()
    if conn is None:
        return None
    try:
        df = pd.read_sql(
            """
            SELECT customer_order_item_id
            FROM customer_order_item
            WHERE customer_order_id = %s
              AND product_id = %s
            ORDER BY customer_order_item_id DESC
            LIMIT 1
            """,
            conn,
            params=[int(customer_order_id), int(product_id)],
        )
        if df is not None and not df.empty and pd.notna(df.iloc[0]["customer_order_item_id"]):
            return int(df.iloc[0]["customer_order_item_id"])
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return None


def _remember_schedule_focus(customer_order_id: int, product_id: int) -> None:
    """After adding an item, remember it so the page can immediately show schedule button."""
    try:
        item_id = fetch_customer_order_item_id_by_product(int(customer_order_id), int(product_id))
        if item_id:
            st.session_state["e01_schedule_focus_item_id"] = int(item_id)
            st.session_state["e01_schedule_focus_order_id"] = int(customer_order_id)
    except Exception:
        pass


def _clear_schedule_focus() -> None:
    st.session_state.pop("e01_schedule_focus_item_id", None)
    st.session_state.pop("e01_schedule_focus_order_id", None)


def fetch_product_unit(product_id: int) -> str:
    """Fetch unit from product table; fallback to 'PCS'."""
    conn = get_connection()
    if conn is None:
        return "PCS"
    try:
        df = pd.read_sql("SELECT unit FROM product WHERE product_id = %s LIMIT 1", conn, params=[int(product_id)])
        if df is not None and not df.empty and pd.notna(df.iloc[0]["unit"]):
            return str(df.iloc[0]["unit"])
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return "PCS"



def fetch_latest_product_unit_price(product_id: int) -> Optional[float]:
    """抓「最新單價」給 E01 新增明細使用（不改 DB 結構、不改 trigger）。

    規則：
    1) 先抓「目前有效」的最新單價：
       - product_unit_price_id = 指定產品 (FK -> product.product_id)
       - is_active = 1
       - valid_from <= NOW()
       - (valid_to IS NULL OR valid_to >= NOW())
       - ORDER BY valid_from DESC, price_id DESC
    2) 若 1) 找不到（常見原因：你把 valid_from 設到未來、valid_to 設到過去、或 is_active=0），
       再抓「最新一筆 active」(不管有效期間) 作為容錯：
       - ORDER BY valid_from DESC, price_id DESC
    3) 仍找不到才回退 product.unit_price（避免 UI 空白）
    """
    conn = get_connection()
    if conn is None:
        return None

    try:
        # 1) current-effective latest
        df = pd.read_sql(
            """
            SELECT unit_price
            FROM product_unit_price
            WHERE product_unit_price_id = %s
              AND is_active = 1
              AND valid_from <= NOW()
              AND (valid_to IS NULL OR valid_to >= NOW())
            ORDER BY valid_from DESC, price_id DESC
            LIMIT 1
            """,
            conn,
            params=[int(product_id)],
        )
        if df is not None and not df.empty and pd.notna(df.iloc[0]["unit_price"]):
            return float(df.iloc[0]["unit_price"])

        # 2) latest active regardless of date (fallback)
        df2 = pd.read_sql(
            """
            SELECT unit_price
            FROM product_unit_price
            WHERE product_unit_price_id = %s
              AND is_active = 1
            ORDER BY valid_from DESC, price_id DESC
            LIMIT 1
            """,
            conn,
            params=[int(product_id)],
        )
        if df2 is not None and not df2.empty and pd.notna(df2.iloc[0]["unit_price"]):
            return float(df2.iloc[0]["unit_price"])

        # 3) fallback to product table
        df3 = pd.read_sql(
            "SELECT unit_price FROM product WHERE product_id = %s LIMIT 1",
            conn,
            params=[int(product_id)],
        )
        if df3 is not None and not df3.empty and pd.notna(df3.iloc[0]["unit_price"]):
            return float(df3.iloc[0]["unit_price"])
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return None

    try:
        # ---- 1) product_code -> material_code (P00012 -> M00012) ----
        df_code = pd.read_sql(
            "SELECT product_code FROM product WHERE product_id = %s LIMIT 1",
            conn,
            params=[int(product_id)],
        )
        if df_code is not None and not df_code.empty:
            product_code = str(df_code.iloc[0]["product_code"] or "").strip()
        else:
            product_code = ""
        material_code = ""
        if product_code.startswith("P") and len(product_code) >= 2:
            material_code = "M" + product_code[1:]

        # ---- 1a) material latest price ----
        if material_code:
            df_mid = pd.read_sql(
                "SELECT item_id FROM material WHERE item_code = %s LIMIT 1",
                conn,
                params=[material_code],
            )
            if df_mid is not None and not df_mid.empty and pd.notna(df_mid.iloc[0]["item_id"]):
                mid = int(df_mid.iloc[0]["item_id"])
                df_mup = pd.read_sql(
                    """
                    SELECT material_unit_price
                    FROM material_unit_price
                    WHERE material_item_id = %s AND valid_to IS NULL
                    ORDER BY valid_from DESC
                    LIMIT 1
                    """,
                    conn,
                    params=[mid],
                )
                if df_mup is not None and not df_mup.empty and pd.notna(df_mup.iloc[0]["material_unit_price"]):
                    return float(df_mup.iloc[0]["material_unit_price"])
        # ---- 2) product_unit_price latest ----
        # 依「有效期間」抓目前有效的最新單價：
        # - valid_from <= NOW()
        # - valid_to is NULL 或 valid_to >= NOW()
        # - is_active = 1（若欄位未啟用也不影響，因為它在 schema 裡是必填）
        df_pup = pd.read_sql(
            """
            SELECT unit_price
            FROM product_unit_price
            WHERE product_unit_price_id = %s
              AND is_active = 1
              AND valid_from <= NOW()
              AND (valid_to IS NULL OR valid_to >= NOW())
            ORDER BY valid_from DESC, price_id DESC
            LIMIT 1
            """,
            conn,
            params=[int(product_id)],
        )
        if df_pup is not None and not df_pup.empty and pd.notna(df_pup.iloc[0]["unit_price"]):
            return float(df_pup.iloc[0]["unit_price"])

        # fallback: 若沒有任何有效期間價格，回退 product.unit_price（避免 UI 空白）
        df_p = pd.read_sql(
            "SELECT unit_price FROM product WHERE product_id = %s LIMIT 1",
            conn,
            params=[int(product_id)],
        )
        if df_p is not None and not df_p.empty and pd.notna(df_p.iloc[0]["unit_price"]):
            return float(df_p.iloc[0]["unit_price"])
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return None





def fetch_customer_id_by_order(customer_order_id: int) -> Optional[int]:
    """取得訂單所屬客戶 ID。"""
    conn = get_connection()
    if conn is None:
        return None
    try:
        df = pd.read_sql(
            "SELECT customer_id FROM customer_order WHERE customer_order_id = %s LIMIT 1",
            conn,
            params=[int(customer_order_id)],
        )
        if df is not None and not df.empty and pd.notna(df.iloc[0]["customer_id"]):
            return int(df.iloc[0]["customer_id"])
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return None


def resolve_customer_product_price(customer_id: int, product_id: int, quantity: float) -> Tuple[Optional[float], Optional[int], str]:
    """依「客戶 + 品項 + 本次訂購總量」抓成交單價。

    回傳：(unit_price, price_tier_id, source)
    source = 'tier' 表示採用 customer_product_price_tier；'base' 表示回退基礎售價。
    """
    try:
        qty = float(quantity or 0)
    except Exception:
        qty = 0.0

    conn = get_connection()
    if conn is None:
        return None, None, "none"

    try:
        df = pd.read_sql(
            """
            SELECT price_tier_id, unit_price
            FROM customer_product_price_tier
            WHERE customer_id = %s
              AND product_id = %s
              AND qty_threshold <= %s
              AND is_active = 1
              AND (effective_from IS NULL OR effective_from <= CURDATE())
              AND (effective_to IS NULL OR effective_to >= CURDATE())
            ORDER BY qty_threshold DESC, price_tier_id DESC
            LIMIT 1
            """,
            conn,
            params=[int(customer_id), int(product_id), qty],
        )
        if df is not None and not df.empty and pd.notna(df.iloc[0]["unit_price"]):
            return float(df.iloc[0]["unit_price"]), int(df.iloc[0]["price_tier_id"]), "tier"
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    base_price = fetch_latest_product_unit_price(int(product_id))
    if base_price is not None:
        return float(base_price), None, "base"
    return None, None, "none"


def fetch_customer_order_item_schedules(customer_order_item_id: int) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql(
            """
            SELECT schedule_id, customer_order_item_id, schedule_no, due_date, qty, status, note
            FROM customer_order_item_schedule
            WHERE customer_order_item_id = %s
            ORDER BY schedule_no ASC, due_date ASC, schedule_id ASC
            """,
            conn,
            params=[int(customer_order_item_id)],
        )
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def fetch_customer_order_item_basic(customer_order_item_id: int) -> Optional[Dict]:
    conn = get_connection()
    if conn is None:
        return None
    try:
        df = pd.read_sql(
            """
            SELECT
                i.customer_order_item_id,
                i.customer_order_id,
                i.product_id,
                p.product_code,
                p.product_name,
                i.quantity,
                i.deliver_date,
                co.deliver_date AS order_deliver_date,
                i.unit
            FROM customer_order_item i
            JOIN customer_order co ON co.customer_order_id = i.customer_order_id
            JOIN product p ON p.product_id = i.product_id
            WHERE i.customer_order_item_id = %s
            LIMIT 1
            """,
            conn,
            params=[int(customer_order_item_id)],
        )
        if df is None or df.empty:
            return None
        return df.iloc[0].to_dict()
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def replace_customer_order_item_schedules(customer_order_item_id: int, rows, updated_by: int = 1) -> Tuple[bool, str]:
    """以畫面送回的資料重建該訂單品項的分批交期。"""
    auth.require_edit(PAGE_KEY)
    item = fetch_customer_order_item_basic(int(customer_order_item_id))
    if not item:
        return False, "找不到訂單明細。"

    order_qty = float(item.get("quantity") or 0)

    if rows is None:
        return False, "請至少保留一筆交期。"

    rows_df = pd.DataFrame(rows)
    if rows_df.empty:
        return False, "請至少保留一筆交期。"

    clean_rows = []
    for _, r in rows_df.iterrows():
        # data_editor 的空白新增列可能全空，直接略過
        if all(str(r.get(c, "") or "").strip() == "" for c in ["due_date", "qty", "note"]):
            continue

        due_date = r.get("due_date")
        if pd.isna(due_date) or due_date in (None, ""):
            return False, "每一筆分批交期都必須填日期。"
        try:
            due_date = pd.to_datetime(due_date).date()
        except Exception:
            return False, "分批交期日期格式錯誤。"

        try:
            qty = float(r.get("qty") or 0)
        except Exception:
            return False, "每一筆分批數量都必須是數字。"
        if qty <= 0:
            return False, "分批數量必須大於 0。"

        note = str(r.get("note") or "").strip() or None
        clean_rows.append({"due_date": due_date, "qty": qty, "note": note})

    if not clean_rows:
        return False, "請至少保留一筆交期。"

    total_qty = sum(float(r["qty"]) for r in clean_rows)
    if abs(total_qty - order_qty) > 0.0001:
        return False, f"分批數量加總必須等於訂單明細數量。明細數量={order_qty:g}，目前分批合計={total_qty:g}。"

    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM customer_order_item_schedule
                WHERE customer_order_item_id = %s
                  AND status <> 'open'
                """,
                (int(customer_order_item_id),),
            )
            locked_count = int((cur.fetchone() or [0])[0] or 0)
            if locked_count > 0:
                return False, "此明細已有非 open 狀態的分批交期，請先確認出貨狀態後再修改。"

            cur.execute(
                "DELETE FROM customer_order_item_schedule WHERE customer_order_item_id = %s",
                (int(customer_order_item_id),),
            )

            for idx, row in enumerate(clean_rows, start=1):
                cur.execute(
                    """
                    INSERT INTO customer_order_item_schedule
                    (customer_order_item_id, schedule_no, due_date, qty, status, note, created_by, created_at, updated_by, updated_at)
                    VALUES (%s, %s, %s, %s, 'open', %s, %s, NOW(), %s, NOW())
                    """,
                    (
                        int(customer_order_item_id),
                        int(idx),
                        row["due_date"],
                        float(row["qty"]),
                        row["note"],
                        int(updated_by),
                        int(updated_by),
                    ),
                )

            first_due_date = min(r["due_date"] for r in clean_rows)
            cur.execute(
                """
                UPDATE customer_order_item
                SET deliver_date = %s
                WHERE customer_order_item_id = %s
                """,
                (first_due_date, int(customer_order_item_id)),
            )

            conn.commit()

        try:
            _touch_customer_order_head(int(item.get("customer_order_id")), updated_by=int(updated_by))
        except Exception:
            pass

        return True, "分批交期已更新"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"分批交期更新失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _build_schedule_editor_default_df(customer_order_item_id: int) -> pd.DataFrame:
    """Build default editor rows for customer_order_item_schedule."""
    item = fetch_customer_order_item_basic(int(customer_order_item_id))
    if not item:
        return pd.DataFrame(columns=["schedule_no", "due_date", "qty", "note"])

    schedules = fetch_customer_order_item_schedules(int(customer_order_item_id))
    if schedules is None or schedules.empty:
        schedules = pd.DataFrame([{
            "schedule_no": 1,
            "due_date": item.get("deliver_date") or item.get("order_deliver_date") or date.today(),
            "qty": float(item.get("quantity") or 0),
            "note": "",
        }])
    else:
        schedules = schedules.copy()
        if "note" not in schedules.columns:
            schedules["note"] = ""
        schedules = schedules[["schedule_no", "due_date", "qty", "note"]]

    try:
        schedules["schedule_no"] = pd.to_numeric(schedules["schedule_no"], errors="coerce").fillna(0).astype(int)
    except Exception:
        pass
    try:
        schedules["qty"] = pd.to_numeric(schedules["qty"], errors="coerce").fillna(0.0)
    except Exception:
        pass
    return schedules


def _render_schedule_dialog_body(customer_order_item_id: int, key_prefix: str) -> None:
    """Dialog body for editing delivery schedules of a selected order item."""
    item = fetch_customer_order_item_basic(int(customer_order_item_id))
    if not item:
        st.warning("找不到訂單明細，無法設定交貨排程。")
        return

    try:
        order_qty = float(item.get("quantity") or 0)
    except Exception:
        order_qty = 0.0

    st.caption(
        f"{_t('品項')}：{item.get('product_code','')} / {item.get('product_name','')} ｜ "
        f"{_t('訂單數量')}：{order_qty:g} {item.get('unit','')}"
    )
    st.caption(_e01_t("請輸入每一批預計交貨日期與數量；儲存時系統會檢查分批數量總和是否等於訂單明細數量。"))

    schedules = _build_schedule_editor_default_df(int(customer_order_item_id))

    edit_df = st.data_editor(
        schedules,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "schedule_no": st.column_config.NumberColumn(_e01_t("批次"), width="small", disabled=True),
            "due_date": st.column_config.DateColumn(_e01_t("預計交期"), width="medium", required=True),
            "qty": st.column_config.NumberColumn(_e01_t("本批數量"), width="medium", min_value=0.0, step=1.0, required=True),
            "note": st.column_config.TextColumn(_e01_t("備註"), width="large"),
        },
        key=f"{key_prefix}_schedule_dialog_editor",
    )

    try:
        edited_total = float(pd.to_numeric(edit_df.get("qty"), errors="coerce").fillna(0).sum())
    except Exception:
        edited_total = 0.0
    diff = edited_total - order_qty

    if abs(diff) <= 0.0001:
        st.success(f"{_t('分批合計')}：{edited_total:g} ｜ {_t('差異')}：0")
    else:
        st.warning(f"{_t('分批合計')}：{edited_total:g} ｜ {_t('差異')}：{diff:g}")

    c1, c2, c3 = st.columns([1.4, 1.4, 4.0])
    with c1:
        if st.button(_e01_t("儲存交貨排程"), type="primary", use_container_width=True, key=f"{key_prefix}_save_schedule_dialog"):
            ok, msg = replace_customer_order_item_schedules(
                int(customer_order_item_id),
                edit_df,
                updated_by=_current_user_id(),
            )
            if ok:
                _clear_schedule_focus()
                st.success(msg)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(msg)
    with c2:
        if st.button(_e01_t("關閉"), use_container_width=True, key=f"{key_prefix}_close_schedule_dialog"):
            st.rerun()
    with c3:
        st.caption(_e01_t("提醒：分批數量加總必須等於此訂單明細的總數量。"))


# Streamlit 版本差異處理：新版是 st.dialog，舊版可能是 st.experimental_dialog。
_dialog_decorator = None
if hasattr(st, "dialog"):
    try:
        _dialog_decorator = st.dialog(_e01_t("設定交貨排程"), width="large")
    except TypeError:
        _dialog_decorator = st.dialog(_e01_t("設定交貨排程"))
elif hasattr(st, "experimental_dialog"):
    try:
        _dialog_decorator = st.experimental_dialog(_e01_t("設定交貨排程"), width="large")
    except TypeError:
        _dialog_decorator = st.experimental_dialog(_e01_t("設定交貨排程"))

if _dialog_decorator is not None:
    @_dialog_decorator
    def _customer_order_item_schedule_dialog(customer_order_item_id: int, key_prefix: str) -> None:
        _render_schedule_dialog_body(customer_order_item_id, key_prefix)
else:
    def _customer_order_item_schedule_dialog(customer_order_item_id: int, key_prefix: str) -> None:
        st.warning("目前 Streamlit 版本不支援彈窗，改用頁面內嵌方式顯示交貨排程。")
        _render_schedule_dialog_body(customer_order_item_id, key_prefix)


def render_customer_order_item_schedule_editor(customer_order_item_id: int, key_prefix: str) -> None:
    """Render button that opens delivery schedule dialog for the selected item."""
    item = fetch_customer_order_item_basic(int(customer_order_item_id))
    if not item:
        st.warning("找不到訂單明細，無法設定交貨排程。")
        return

    schedules = fetch_customer_order_item_schedules(int(customer_order_item_id))
    try:
        schedule_count = int(len(schedules)) if schedules is not None else 0
        schedule_total = float(pd.to_numeric(schedules.get("qty"), errors="coerce").fillna(0).sum()) if schedules is not None and not schedules.empty else 0.0
    except Exception:
        schedule_count = 0
        schedule_total = 0.0

    try:
        order_qty = float(item.get("quantity") or 0)
    except Exception:
        order_qty = 0.0

    st.markdown(f"<div class='ordo-subtitle'>{_e01_t('交貨排程')}</div>", unsafe_allow_html=True)
    s1, s2, s3 = st.columns([1.35, 3.0, 4.5], vertical_alignment="center")
    with s1:
        if st.button(_e01_t("設定交貨排程"), use_container_width=True, key=f"{key_prefix}_open_schedule_dialog"):
            _customer_order_item_schedule_dialog(int(customer_order_item_id), key_prefix)
    with s2:
        diff = schedule_total - order_qty
        st.caption(f"{_t('目前批數')}：{schedule_count} ｜ {_t('排程合計')}：{schedule_total:g} ｜ {_t('差異')}：{diff:g}")
    with s3:
        st.caption(_e01_t("勾選明細後，可在彈窗中設定多個客戶指定交期；數量合計必須等於明細總數量。"))


def render_recent_schedule_focus(order_id: int, source_key: str) -> None:
    """Show a schedule button immediately after a new item is saved."""
    focus_item_id = st.session_state.get("e01_schedule_focus_item_id")
    focus_order_id = st.session_state.get("e01_schedule_focus_order_id")
    try:
        if int(focus_order_id or 0) != int(order_id):
            return
        focus_item_id = int(focus_item_id or 0)
    except Exception:
        return
    if not focus_item_id:
        return

    item = fetch_customer_order_item_basic(int(focus_item_id))
    if not item:
        _clear_schedule_focus()
        return

    st.markdown("<div class='ordo-panel'>", unsafe_allow_html=True)
    st.markdown(f"<div class='ordo-subtitle'>{_t('剛新增的明細')}</div>", unsafe_allow_html=True)
    st.caption(
        f"{_t('品項')}：{item.get('product_code','')} / {item.get('product_name','')} ｜ "
        f"{_t('數量')}：{float(item.get('quantity') or 0):g} {item.get('unit','')}"
    )
    c1, c2, c3 = st.columns([1.35, 1.35, 5.0], vertical_alignment="center")
    with c1:
        if st.button(_e01_t("設定交貨排程"), use_container_width=True, key=f"{source_key}_focus_schedule_btn_{focus_item_id}"):
            _customer_order_item_schedule_dialog(int(focus_item_id), f"{source_key}_focus_{focus_item_id}")
    with c2:
        if st.button(_t("稍後設定"), use_container_width=True, key=f"{source_key}_clear_focus_schedule_btn_{focus_item_id}"):
            _clear_schedule_focus()
            st.rerun()
    with c3:
        st.caption(_t("明細已儲存，可立即設定客戶指定分批交貨日期與數量。"))
    st.markdown("</div>", unsafe_allow_html=True)


def _sync_single_schedule_after_item_update(cur, customer_order_item_id: int, quantity: float, deliver_date: Optional[date], updated_by: int) -> None:
    """若明細仍是單一交期，更新明細時同步預設 schedule。若已多批，則檢查總量。"""
    cur.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(qty), 0)
        FROM customer_order_item_schedule
        WHERE customer_order_item_id = %s
        """,
        (int(customer_order_item_id),),
    )
    row = cur.fetchone() or (0, 0)
    schedule_count = int(row[0] or 0)
    schedule_total = float(row[1] or 0)
    # 沒有分批交期時，不要因為修改明細而自動補一筆 schedule。
    # 有一筆既有 schedule 時才同步；若明細交期為空，保留原 schedule.due_date，只同步數量。
    if schedule_count == 0:
        return
    elif schedule_count == 1:
        if deliver_date:
            cur.execute(
                """
                UPDATE customer_order_item_schedule
                SET schedule_no = 1,
                    due_date = %s,
                    qty = %s,
                    updated_by = %s,
                    updated_at = NOW()
                WHERE customer_order_item_id = %s
                """,
                (deliver_date, float(quantity or 0), int(updated_by), int(customer_order_item_id)),
            )
        else:
            cur.execute(
                """
                UPDATE customer_order_item_schedule
                SET schedule_no = 1,
                    qty = %s,
                    updated_by = %s,
                    updated_at = NOW()
                WHERE customer_order_item_id = %s
                """,
                (float(quantity or 0), int(updated_by), int(customer_order_item_id)),
            )
    else:
        if abs(schedule_total - float(quantity or 0)) > 0.0001:
            raise ValueError(
                f"此明細已有多筆分批交期，分批合計={schedule_total:g}，新明細數量={float(quantity or 0):g}；請先調整分批交期後再更新。"
            )


def staged_items_have_duplicate_product_ids(rows) -> bool:
    """檢查暫存明細是否有重複 product_id。"""
    try:
        if not rows:
            return False
        pids = []
        for r in rows:
            pid = r.get("product_id") if isinstance(r, dict) else None
            if pid in (None, ""):
                continue
            pids.append(int(pid))
        return len(pids) != len(set(pids))
    except Exception:
        return False


def reset_new_order_form(keep_order_code: bool = True) -> None:
    """清空新建訂單畫面，保留本公司訂單號顯示。"""
    for k in list(st.session_state.keys()):
        if k.startswith("e01_new_") or k.startswith("e01c_new_") or k.startswith("e01_new_stage_"):
            st.session_state.pop(k, None)

    for k in [
        "e01_order_id",
        "e01_create_order_id",
        "e01_reset_new_order_form",
        "e01_new_order_items_customer",
        "e01_items_editor",
        "e01c_items_editor",
    ]:
        st.session_state.pop(k, None)

    for k in list(st.session_state.keys()):
        if k.startswith("e01_new_order_items_"):
            st.session_state.pop(k, None)

    if not keep_order_code:
        st.session_state.pop("e01_create_order_code", None)


def reset_modify_order_form(keep_order_code: bool = True) -> None:
    """清空修改訂單畫面，切回新增訂單，但保留本公司訂單號顯示。"""
    if keep_order_code and st.session_state.get("e01_order_id"):
        try:
            _head_df = fetch_customer_order_head(int(st.session_state.get("e01_order_id")))
            if _head_df is not None and not _head_df.empty:
                st.session_state["e01_create_order_code"] = str(_head_df.iloc[0].get("customer_order_code") or "")
        except Exception:
            pass

    st.session_state["e01_mode_pending"] = MODE_NEW
    st.session_state["e01_orders_editor_nonce"] = int(st.session_state.get("e01_orders_editor_nonce", 0)) + 1

    for k in [
        "e01_order_id",
        "e01c_head_customer_order_no",
        "e01c_head_customer_order_num",
        "e01c_head_deliver_date_top",
        "e01c_head_deliver_to",
        "e01c_head_state",
        "e01c_items_editor",
        "e01_edit_item_pid",
        "e01_edit_item_qty",
        "e01_edit_item_unit",
        "e01_edit_item_price_unit",
        "e01_edit_item_dd",
        "e01_new_item_pid",
        "e01_new_item_qty",
        "e01_new_item_unit",
        "e01_new_item_price_unit",
        "e01_new_item_dd",
        "e01c_edit_item_pid",
        "e01c_edit_item_qty",
        "e01c_edit_item_dd",
        "e01c_new_item_pid",
        "e01c_new_item_qty",
        "e01c_new_item_price_unit",
        "e01c_new_item_dd",
    ]:
        st.session_state.pop(k, None)

    if not keep_order_code:
        st.session_state.pop("e01_create_order_code", None)


def force_refresh_e01_master_table(clear_loaded_order: bool = False) -> None:
    """Refresh E01 customer-order master list and rebuild the data_editor.

    This clears Streamlit cached query results and changes the master-list
    editor key so checkbox selections / stale grid state do not survive refresh.
    """
    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.session_state["e01_orders_editor_nonce"] = int(st.session_state.get("e01_orders_editor_nonce", 0)) + 1

    if clear_loaded_order:
        st.session_state.e01_order_id = None
        st.session_state.pop("e01_mode_pending", None)


# ===== helper: sync readonly price textbox with session_state =====
def _sync_price_state(key: str, signature, price: Optional[float], source: str = "") -> None:
    """Keep a readonly price textbox in sync with the selected customer/product/qty."""
    last_key = f"_last_{key}_signature"
    if st.session_state.get(last_key) != signature:
        if price is None:
            st.session_state[key] = ""
        else:
            suffix = "（級距價）" if source == "tier" else "（基礎價）"
            st.session_state[key] = f"{float(price):.2f}{suffix}"
        st.session_state[last_key] = signature


# ===== helper: render effective unit price (readonly) in a textbox =====
def _render_order_price_readonly(
    key: str,
    customer_id: Optional[int],
    pid: Optional[int],
    qty,
) -> Tuple[Optional[float], Optional[int], str]:
    """Compute effective price by customer + product + order item total qty."""
    try:
        _customer_id = int(customer_id) if customer_id not in (None, "") else None
    except Exception:
        _customer_id = None
    try:
        _pid = int(pid) if pid not in (None, "") else None
    except Exception:
        _pid = None
    try:
        _qty = float(qty or 0)
    except Exception:
        _qty = 0.0

    if _customer_id is not None and _pid is not None:
        _price, _tier_id, _source = resolve_customer_product_price(_customer_id, _pid, _qty)
    elif _pid is not None:
        _price = fetch_latest_product_unit_price(int(_pid))
        _tier_id = None
        _source = "base" if _price is not None else "none"
    else:
        _price, _tier_id, _source = None, None, "none"

    _sync_price_state(key, (_customer_id, _pid, _qty, _tier_id, _source), _price, _source)
    st.text_input("", key=key, disabled=True, label_visibility="collapsed")
    return _price, _tier_id, _source


def _render_latest_price_readonly(key: str, pid: Optional[int]) -> Optional[float]:
    """Backward-compatible helper: show base/latest product price only."""
    _pid = None
    try:
        _pid = int(pid) if pid not in (None, "") else None
    except Exception:
        _pid = None

    _p = fetch_latest_product_unit_price(int(_pid)) if _pid is not None else None
    _sync_price_state(key, (_pid,), _p, "base" if _p is not None else "none")
    st.text_input("", key=key, disabled=True, label_visibility="collapsed")
    return _p


def create_customer_order_item(
    customer_order_id: int,
    product_id: int,
    quantity: float,
    price_unit: Optional[float],
    deliver_date: Optional[date],
    created_by: int = 1,
    update_parent: bool = True,
) -> Tuple[bool, str]:
    """
    UI wrapper.

    單價規則：依 customer_id + product_id + 訂購總量抓 customer_product_price_tier；
    若沒有符合級距，才回退 product_unit_price / product.unit_price。
    """
    auth.require_edit(PAGE_KEY)
    unit = fetch_product_unit(int(product_id))

    if order_has_same_product(int(customer_order_id), int(product_id)):
        return False, "同一張訂單不可出現相同品項。"

    customer_id = fetch_customer_id_by_order(int(customer_order_id))
    if customer_id is None:
        return False, "找不到訂單客戶，無法計算單價。"

    price_unit, price_tier_id, _source = resolve_customer_product_price(
        int(customer_id),
        int(product_id),
        float(quantity or 0),
    )

    if price_unit is None:
        return False, "該產品目前沒有價格，請至產品主檔或客戶級距價格表設定。"

    ok, msg = insert_customer_order_items(
        customer_order_id=int(customer_order_id),
        rows=[{
            "product_id": int(product_id),
            "unit": unit,
            "quantity": float(quantity),
            "price_unit": float(price_unit),
            "price_tier_id": int(price_tier_id) if price_tier_id is not None else None,
            "deliver_date": deliver_date if deliver_date else None,
        }],
        created_by=int(created_by),
    )
    if ok and update_parent:
        _touch_customer_order_head(int(customer_order_id), updated_by=int(created_by))
    return ok, msg


def update_customer_order_item(
    customer_order_item_id: int,
    product_id: int,
    quantity: float,
    price_unit: Optional[float],
    deliver_date: Optional[date],
    updated_by: int = 1,
) -> Tuple[bool, str]:
    """UI wrapper；依客戶級距價格重算成交單價（忽略 UI 傳入 price_unit）。"""
    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"
    try:
        df = pd.read_sql(
            """
            SELECT i.customer_order_id, co.customer_id
            FROM customer_order_item i
            JOIN customer_order co ON co.customer_order_id = i.customer_order_id
            WHERE i.customer_order_item_id = %s
            LIMIT 1
            """,
            conn,
            params=[int(customer_order_item_id)],
        )
        if df.empty:
            return False, "找不到該明細。"
        customer_order_id = int(df.iloc[0]["customer_order_id"])
        customer_id = int(df.iloc[0]["customer_id"])
    except Exception as e:
        return False, f"讀取訂單失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if order_has_same_product(customer_order_id, int(product_id), exclude_item_id=int(customer_order_item_id)):
        return False, "同一張訂單不可出現相同品項。"

    unit = fetch_product_unit(int(product_id))
    price_unit, price_tier_id, _source = resolve_customer_product_price(
        int(customer_id),
        int(product_id),
        float(quantity or 0),
    )
    if price_unit is None:
        return False, "該產品目前沒有價格，請至產品主檔或客戶級距價格表設定。"

    return update_customer_order_item_full(
        customer_order_item_id=int(customer_order_item_id),
        product_id=int(product_id),
        unit=unit,
        quantity=float(quantity),
        price_unit=float(price_unit),
        price_tier_id=int(price_tier_id) if price_tier_id is not None else None,
        deliver_date=deliver_date if deliver_date else None,
        updated_by=int(updated_by),
    )


def update_customer_order_item_full(
    customer_order_item_id: int,
    product_id: int,
    unit: str,
    quantity: float,
    price_unit: Optional[float],
    price_tier_id: Optional[int],
    deliver_date: Optional[date],
    updated_by: int = 1,
) -> Tuple[bool, str]:
    auth.require_edit(PAGE_KEY)
    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"

    try:
        customer_order_id_for_audit = None
        with conn.cursor() as cur:
            cur.execute(
                "SELECT customer_order_id FROM customer_order_item WHERE customer_order_item_id = %s LIMIT 1",
                (int(customer_order_item_id),),
            )
            _row_audit = cur.fetchone()
            if _row_audit and _row_audit[0] is not None:
                customer_order_id_for_audit = int(_row_audit[0])

            # 若已經有多筆分批交期，更新數量前必須先確定分批合計仍能對上。
            _sync_single_schedule_after_item_update(
                cur,
                int(customer_order_item_id),
                float(quantity or 0),
                deliver_date if deliver_date else None,
                int(updated_by),
            )

            cur.execute(
                """
                UPDATE customer_order_item
                SET
                    product_id = %s,
                    unit = %s,
                    quantity = %s,
                    price_unit = %s,
                    price_tier_id = %s,
                    deliver_date = %s
                WHERE customer_order_item_id = %s
                """,
                (
                    int(product_id),
                    str(unit or "PCS"),
                    float(quantity or 0),
                    (float(price_unit) if price_unit is not None else None),
                    (int(price_tier_id) if price_tier_id is not None else None),
                    deliver_date if deliver_date else None,
                    int(customer_order_item_id),
                ),
            )
            conn.commit()
        if customer_order_id_for_audit is not None:
            _touch_customer_order_head(int(customer_order_id_for_audit), updated_by=int(updated_by))
        return True, "已更新"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"更新失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def delete_customer_order_items(item_ids: List[int]) -> Tuple[bool, str]:
    auth.require_delete(PAGE_KEY)
    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"

    try:
        affected_order_ids = set()
        with conn.cursor() as cur:
            for iid in item_ids:
                cur.execute(
                    "SELECT customer_order_id FROM customer_order_item WHERE customer_order_item_id = %s LIMIT 1",
                    (int(iid),),
                )
                _row = cur.fetchone()
                if _row and _row[0] is not None:
                    affected_order_ids.add(int(_row[0]))

            for iid in item_ids:
                cur.execute("DELETE FROM customer_order_item WHERE customer_order_item_id = %s", (int(iid),))
            conn.commit()

        for _oid in affected_order_ids:
            _touch_customer_order_head(int(_oid), updated_by=_current_user_id())
        return True, f"已刪除 {len(item_ids)} 筆"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"刪除失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass



# =============================================================================
# UI
# =============================================================================
st.set_page_config(page_title=_t("E01 客戶訂單"), layout="wide")

PAGE_KEY = "E01_customer_order_create"
auth.require_read(PAGE_KEY)
init_language()

MODE_NEW = "new"
MODE_EDIT = "edit"
MODE_LABELS = {MODE_NEW: _t("新增訂單"), MODE_EDIT: _t("修改訂單")}

st.markdown(
    """
    <style>
      .block-container { padding-top: 0 !important; padding-bottom: 0.65rem; max-width: 100% !important; padding-left: 1rem; padding-right: 1rem; }
      .ordo-soft {
        background: #ffffff;
        border: 1px solid #d9dee7;
        border-radius: 12px;
        padding: 14px 14px 8px 14px;
        margin-bottom: 12px;
      }
      .ordo-panel {
        background: #f5f9ff;
        border: 1px solid #d7e3f4;
        border-radius: 12px;
        padding: 12px 12px 6px 12px;
        margin: 8px 0 18px 0;
      }
      .ordo-section-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0 0 8px 0;
      }
      .ordo-big-total {
        font-size: 20px;
        font-weight: 800;
        line-height: 1.25;
        margin: 3px 0 2px 0;
      }
      .ordo-subtitle {
        font-size: 0.95rem;
        font-weight: 700;
        margin: 0 0 4px 0;
      }
      .ordo-muted { color: #6b7280; font-size: 0.85rem; }
      div[data-testid="stExpander"] > details { border: none !important; background: transparent !important; }
      div[data-testid="stExpander"] > details > summary { border: none !important; }
      div[data-testid="stDataEditor"] { border-radius: 10px; overflow: hidden; }
      div[data-testid="stHorizontalBlock"] button[kind="secondary"], div[data-testid="stHorizontalBlock"] button[kind="primary"] { min-height: 40px; }
    </style>
    """,
    unsafe_allow_html=True,
)

def delete_customer_orders(order_ids: List[int]) -> Tuple[bool, str]:
    """
    刪除 customer_order（母表）。
    schema 上 customer_order_item 對 customer_order 有 ON DELETE CASCADE，
    因此刪除抬頭會一併刪除明細。
    """
    auth.require_delete(PAGE_KEY)
    if not order_ids:
        return False, "未提供要刪除的訂單"

    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"

    try:
        uniq_ids = sorted({int(x) for x in order_ids})
        placeholders = ",".join(["%s"] * len(uniq_ids))
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM customer_order WHERE customer_order_id IN ({placeholders})", tuple(uniq_ids))
            affected = cur.rowcount
            conn.commit()
        return True, f"已刪除 {affected} 張訂單"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"刪除失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass

st.title(_t("E01 客戶訂單"))

# ---------------------------
# Session state (minimal)
# ---------------------------
if "e01_selected_customer_id" not in st.session_state:
    st.session_state.e01_selected_customer_id = None
if "e01_order_id" not in st.session_state:
    st.session_state.e01_order_id = None

# ---------------------------
# Load customers
# ---------------------------
cust_df = fetch_customers()
if cust_df is None or cust_df.empty:
    st.error("找不到客戶資料（customer）。")
    st.stop()

cust_df = cust_df.copy()
cust_df["customer_id"] = cust_df["customer_id"].astype(int)
cust_ids = cust_df["customer_id"].tolist()
cust_labels = {
    int(r["customer_id"]): f'{r["customer_name"]} | {r["customer_code"]} | {r["customer_shortname"]} | ID:{int(r["customer_id"])}'
    for _, r in cust_df.iterrows()
}
cust_shortnames = {
    int(r["customer_id"]): str(r.get("customer_shortname") or "").strip()
    for _, r in cust_df.iterrows()
}
cust_label = cust_labels  # alias for backward compatibility

if st.session_state.e01_selected_customer_id is None:
    st.session_state.e01_selected_customer_id = 0  # 0 means all customers

# ---------------------------

# ---------------------------
# Query filters (top)
# ---------------------------
today = date.today()
first_day_of_month = today.replace(day=1)

st.markdown(f"### {_t('查詢區')}")
with st.expander(_t("展開 / 收合查詢條件"), expanded=True):
    # 這裡是查詢區，只需要 require_read。
    # 原本誤放 auth.require_delete(PAGE_KEY)，會導致「可看見但不可刪除」的使用者無法進入 E01。
    # 頁面開頭已經執行 auth.require_read(PAGE_KEY)，所以這裡不要再要求刪除權限。

    q1, q2, q3 = st.columns([1.4, 2.6, 1.8])
    with q1:
        q_customer_order_code = st.text_input(_t("本公司訂單號"), value="", key="e01_q_customer_order_code")
    with q2:
        query_customer_options = [0] + cust_ids  # 0 => 所有客戶
        sel_customer_id = st.selectbox(
            _t("客戶"),
            options=query_customer_options,
            index=query_customer_options.index(int(st.session_state.e01_selected_customer_id))
            if int(st.session_state.e01_selected_customer_id) in query_customer_options
            else 0,
            format_func=lambda x: _t("所有客戶") if int(x) == 0 else cust_labels.get(int(x), str(x)),
            key="e01_sel_customer_id",
        )
    with q3:
        q_customer_order_num = st.text_input(_t("客戶單號"), value="", key="e01_q_customer_order_num")

    q4, q5 = st.columns([1.0, 1.0])
    with q4:
        q_created_from = st.date_input(
            _t("訂單建立時間（起）"),
            value=first_day_of_month,
            max_value=today,
            key="e01_q_created_from",
        )
    with q5:
        q_created_to = st.date_input(
            _t("訂單建立時間（迄）"),
            value=today,
            max_value=today,
            key="e01_q_created_to",
        )

    # Persist selected customer (0 means all)
    sel_customer_id = int(sel_customer_id)
    st.session_state.e01_selected_customer_id = sel_customer_id

    if q_created_from and q_created_to and q_created_to < q_created_from:
        st.warning(_t("訂單建立時間：迄日不得早於起日。已自動交換。"))
        q_created_from, q_created_to = q_created_to, q_created_from

    # ---------------------------
    # Orders list (customer_order)
    # ---------------------------
    orders_df = fetch_customer_orders(int(sel_customer_id))
    if orders_df is None:
        orders_df = pd.DataFrame()

    orders_df = fetch_customer_orders(
        int(sel_customer_id),
        q_customer_order_code=str(q_customer_order_code or ""),
        q_customer_order_num=str(q_customer_order_num or ""),
        created_from=q_created_from,
        created_to=q_created_to,
    )
    orders_df = orders_df if orders_df is not None else pd.DataFrame()

    if orders_df.empty:
        st.info(_t("查無符合條件的訂單。"))
        show_orders = pd.DataFrame(columns=["select", "customer_order_code", "customer_order_num", "customer_shortname", "customer_order_category", "deliver_date", "order_status", "created_at", "created_by_name", "updated_by_name"])
    else:
        show_orders = orders_df.copy()
        show_orders.insert(0, "select", False)
        if "order_status" in show_orders.columns:
            show_orders["order_status_raw"] = show_orders["order_status"]
            show_orders["order_status"] = show_orders["order_status"].apply(format_customer_order_status_for_grid)
        if "customer_order_category" in show_orders.columns:
            show_orders["customer_order_category"] = show_orders["customer_order_category"].apply(customer_order_category_label)
        # 以 customer_order_id 作為 index，並隱藏 index -> 達成「ID 不呈現」但仍可回溯到實體 ID
        show_orders = show_orders.set_index("customer_order_id", drop=True)


    # ---- list pagination (under-table controls + slicing) ----
    st.session_state.setdefault("e01_list_page_size", 20)
    st.session_state.setdefault("e01_list_page", 1)
    st.session_state.setdefault("e01_orders_editor_nonce", 0)

    _total_rows = int(len(show_orders))
    _page_size = int(st.session_state["e01_list_page_size"] or 20)
    _page_size = _page_size if _page_size > 0 else 20
    _total_pages = max(1, int((_total_rows + _page_size - 1) // _page_size))

    # clamp page
    if st.session_state["e01_list_page"] > _total_pages:
        st.session_state["e01_list_page"] = _total_pages
    if st.session_state["e01_list_page"] < 1:
        st.session_state["e01_list_page"] = 1

    _page = int(st.session_state["e01_list_page"])
    _start = (_page - 1) * _page_size
    _end = _start + _page_size
    show_orders_page = show_orders.iloc[_start:_end].copy()

    _e01_order_list_cols = [
        "select",
        "customer_order_code",
        "customer_order_num",
        "customer_shortname",
        "customer_order_category",
        "deliver_date",
        "order_status",
        "created_at",
        "created_by_name",
        "updated_by_name",
    ]
    _e01_order_list_cols = [c for c in _e01_order_list_cols if c in show_orders_page.columns]

    orders_editor = st.data_editor(
        show_orders_page[_e01_order_list_cols],
        use_container_width=True,
        hide_index=True,
            disabled=[c for c in _e01_order_list_cols if c != "select"],
        height=180,
        column_config={
            "select": st.column_config.CheckboxColumn(_t("選取"), help=_t("可勾選一張載入編輯；也可多選後刪除"), default=False),
            "customer_order_code": st.column_config.TextColumn(_t("本公司訂單號"), width="medium", disabled=True),
            "customer_order_num": st.column_config.TextColumn(_t("客戶單號"), width="medium", disabled=True),
            "customer_shortname": st.column_config.TextColumn(_t("客戶名稱"), width="medium", disabled=True),
            "customer_order_category": st.column_config.TextColumn(_e01_t("訂單類別"), width="medium", disabled=True),
            "deliver_date": st.column_config.DateColumn(_t("交期"), width="small", disabled=True),
            "order_status": st.column_config.TextColumn(_t("訂單狀態"), width="medium", disabled=True),
            "created_at": st.column_config.DatetimeColumn(_t("建立時間"), width="medium", disabled=True),
            "created_by_name": st.column_config.TextColumn(_t("建檔人員"), width="small", disabled=True),
            "updated_by_name": st.column_config.TextColumn(_t("最後修改人"), width="small", disabled=True),
        },
        key=f"e01_orders_editor_{st.session_state['e01_orders_editor_nonce']}",
    )


    # ---- pagination controls (under table) ----
    def _e01_reset_list_page():
        st.session_state["e01_list_page"] = 1

    p1, p2, p3, p4 = st.columns([1.2, 1.2, 1.2, 6.4], vertical_alignment="bottom")
    with p1:
        if st.button(_t("上一頁"), disabled=(_page <= 1), use_container_width=True, key="e01_btn_prev_page"):
            st.session_state["e01_list_page"] = max(1, _page - 1)
            st.rerun()
    with p2:
        st.selectbox(
            _t("一次顯示筆數"),
            [10, 20, 30, 50, 100],
            key="e01_list_page_size",
            on_change=_e01_reset_list_page,
            label_visibility="collapsed",
        )
    with p3:
        if st.button(_t("下一頁"), disabled=(_page >= _total_pages), use_container_width=True, key="e01_btn_next_page"):
            st.session_state["e01_list_page"] = min(_total_pages, _page + 1)
            st.rerun()
    with p4:
        st.caption(f"{_t('第')} {_page} / {_total_pages} {_t('頁')}（{_t('共')} {_total_rows} {_t('筆')}）")


    picked_orders = orders_editor[orders_editor["select"] == True] if "select" in orders_editor.columns else pd.DataFrame()
    picked_order_ids = [int(x) for x in picked_orders.index.tolist()] if picked_orders is not None and not picked_orders.empty else []

    a1, a2, a3, spacer, a4 = st.columns([1.2, 1.2, 1.2, 3.0, 1.6])
    with a1:
        if st.button(_t("載入勾選訂單"), use_container_width=True, key="e01_btn_load_selected_order"):
            if not picked_order_ids:
                st.warning(_t("請先在清單勾選一張訂單。"))
            else:
                st.session_state.e01_order_id = int(picked_order_ids[0])
                st.session_state["e01_mode_pending"] = MODE_EDIT
                st.rerun()
    with a2:
        if st.button(_t("清除選擇"), use_container_width=True, key="e01_btn_clear_order_selection"):
            force_refresh_e01_master_table(clear_loaded_order=True)
            st.rerun()
    with a3:
        if st.button(_t("重新整理"), use_container_width=True, key="e01_btn_refresh_master_table"):
            force_refresh_e01_master_table(clear_loaded_order=False)
            st.rerun()
    with a4:
        if st.button(_t("刪除勾選訂單"), use_container_width=True, disabled=(not picked_order_ids), key="e01_btn_delete_selected_orders"):
            ok, msg = delete_customer_orders(picked_order_ids)
            if ok:
                # 若刪到了目前載入中的訂單，一併清除
                if st.session_state.e01_order_id in picked_order_ids:
                    st.session_state.e01_order_id = None
                st.success(msg)
                force_refresh_e01_master_table(clear_loaded_order=False)
                st.rerun()
            else:
                st.error(msg)

# ---------------------------
# Create order (moved under list)
# ---------------------------

# ---------------------------
# Create order (moved under list)
# ---------------------------
st.markdown(f"### {_t('作業區')}")
# ---- mode switch (radio) ----
st.session_state.setdefault("e01_mode", MODE_NEW)
# allow other actions to request a mode switch (must happen BEFORE the widget is instantiated)
if st.session_state.get("e01_mode_pending"):
    st.session_state["e01_mode"] = st.session_state.pop("e01_mode_pending")

mode_cols = st.columns([1.2, 8.8])
with mode_cols[0]:
    st.markdown(f"<div class='ordo-subtitle'>{_t('模式')}</div>", unsafe_allow_html=True)
with mode_cols[1]:
    _mode = st.radio(
        _t("模式"),
        [MODE_NEW, MODE_EDIT],
        format_func=lambda x: MODE_LABELS.get(x, x),
        horizontal=True,
        key="e01_mode",
        label_visibility="collapsed",
    )

_prev_mode = st.session_state.get("e01_prev_mode", _mode)
if _prev_mode == MODE_EDIT and _mode == MODE_NEW:
    st.session_state.e01_order_id = None
    st.session_state["e01_orders_editor_nonce"] += 1
    st.session_state["e01_prev_mode"] = _mode
    st.rerun()
st.session_state["e01_prev_mode"] = _mode

if _mode == MODE_EDIT:
    # Load selected order head
    # ---------------------------
    head = {}
    if st.session_state.e01_order_id:
        _head_df = fetch_customer_order_head(int(st.session_state.e01_order_id))
        if _head_df is not None and not _head_df.empty:
            head = _head_df.iloc[0].to_dict()
        else:
            st.warning("已選擇的訂單不存在或無法讀取，請重新載入。")
            st.session_state.e01_order_id = None
    else:
        st.info(_t("請先在『訂單清單』勾選一張訂單並按『載入勾選訂單』，才可進入編輯。"))

    if not head:
        st.info(_t("尚未載入任何訂單。請先在『訂單清單』勾選一張訂單並按『載入勾選訂單』。"))
    else:
        # Active loaded order id
        order_id = int(st.session_state.e01_order_id)

        st.divider()
        st.markdown(f"### {_t('檢視與修改訂單')}")

        # Active customer id for the loaded order
        try:
            active_customer_id = int(head.get("customer_id") or sel_customer_id)
        except Exception:
            active_customer_id = int(sel_customer_id) if "sel_customer_id" in locals() else None

        h1, h2, h3, h4, h5 = st.columns([1.2, 1.8, 1.3, 1.7, 1.5])
        with h1:
            st.text_input(_t("本公司訂單號"), value=str(head.get("customer_order_code") or ""), disabled=True)
        with h2:
            edit_customer_order_num = st.text_input(_t("客戶單號（可空）"), value=str(head.get("customer_order_num") or ""))
        with h3:
            try:
                _dd = head.get("deliver_date") if pd.notna(head.get("deliver_date")) else None
                edit_deliver_date = st.date_input(_t("交期（必填）"), value=_dd)
            except Exception:
                edit_deliver_date = st.date_input(_t("交期（必填）"), value=head.get("deliver_date") if pd.notna(head.get("deliver_date")) else date.today())
        with h4:
            st.text_input(_t("建立時間"), value=str(head.get("created_at") or ""), disabled=True)
        with h5:
            current_category = str(head.get("customer_order_category") or CUSTOMER_ORDER_CATEGORY_GENERAL)
            if current_category not in CUSTOMER_ORDER_CATEGORY_OPTIONS:
                current_category = CUSTOMER_ORDER_CATEGORY_GENERAL
            edit_customer_order_category = st.selectbox(
                _e01_t("訂單類別"),
                options=list(CUSTOMER_ORDER_CATEGORY_OPTIONS),
                index=list(CUSTOMER_ORDER_CATEGORY_OPTIONS).index(current_category),
                format_func=customer_order_category_label,
                key=f"e01_edit_customer_order_category_{order_id}",
            )

        addr_df2 = fetch_receiving_addresses(int(active_customer_id))
        addr_ids2 = []
        addr_label2 = {}
        if addr_df2 is not None and not addr_df2.empty:
            for _, r in addr_df2.iterrows():
                rid = int(r["receiving_id"])
                addr_ids2.append(rid)
                addr_label2[rid] = f'{r["receiving_add"]} | ID:{rid}'

        # Second row: optional deliver_to / state / update button (aligned)
        lbl_a, lbl_b, lbl_c = st.columns([2.8, 1.2, 1.2])
        with lbl_a:
            st.markdown(_t("送貨地址"))
        with lbl_b:
            st.markdown(_t("state"))
        with lbl_c:
            st.markdown("&nbsp;", unsafe_allow_html=True)

        h5, h6, h7 = st.columns([2.8, 1.2, 1.2])
        with h5:
            current_deliver_to = head.get("deliver_to")
            try:
                current_deliver_to = int(current_deliver_to) if pd.notna(current_deliver_to) else None
            except Exception:
                current_deliver_to = None
            if current_deliver_to not in addr_ids2:
                current_deliver_to = None
            deliver_to_options = [None] + addr_ids2
            edit_deliver_to = st.selectbox(
                "",
                options=deliver_to_options,
                index=deliver_to_options.index(current_deliver_to),
                format_func=lambda x: "—" if x is None else addr_label2.get(int(x), str(x)),
                label_visibility="collapsed",
            )
        with h6:
            edit_state = st.selectbox(
                "",
                options=["draft", "approve"],
                index=1,
                label_visibility="collapsed",
            )
        with h7:
            if st.button(_t("更新抬頭"), use_container_width=True, key="e01_btn_update_loaded_head"):
                if edit_deliver_date is None:
                    st.warning(_t("交期為必填，請先選擇交期。"))
                else:
                    ok, msg = update_customer_order_head(
                        customer_order_id=int(order_id),
                        customer_order_num=str(edit_customer_order_num or "").strip(),
                        deliver_to=edit_deliver_to,
                        deliver_date=edit_deliver_date,
                        state=str(edit_state),
                        customer_order_category=edit_customer_order_category,
                        updated_by=_current_user_id(),
                    )
                    if ok:
                        st.success(msg)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

        # ---------------------------
        # Items (list + textbox edit)
        # ---------------------------
        # ---------------------------
        # Items (list + edit)
        # ---------------------------
        st.markdown(f"<div class='ordo-section-title'>{_t('訂單產品明細')}</div>", unsafe_allow_html=True)

        order_id = int(st.session_state.e01_order_id)  # active loaded order id
        items_df = fetch_customer_order_items(int(order_id))
        items_df = items_df if items_df is not None else pd.DataFrame()

        # --- 計算小計與總額（強制以最新單價） ---
        try:
            if items_df is not None and not items_df.empty:
                items_df["price_unit"] = pd.to_numeric(items_df.get("price_unit"), errors="coerce")
                items_df["quantity"] = pd.to_numeric(items_df.get("quantity"), errors="coerce")
                items_df["line_total"] = (items_df["price_unit"].fillna(0) * items_df["quantity"].fillna(0))
                order_total_amt = float(items_df["line_total"].fillna(0).sum())
                order_total_qty = float(items_df["quantity"].fillna(0).sum())
            else:
                order_total_amt = 0.0
                order_total_qty = 0.0
        except Exception:
            order_total_amt = 0.0
            order_total_qty = 0.0

        if items_df.empty:
            st.info(_t("此訂單尚無明細。"))
            show_items = pd.DataFrame(columns=["select", "product_code", "customer_product_id", "product_name", "specification", "specification_unit", "unit", "quantity", "price_unit", "line_total", "deliver_date"])
        else:
            show_items = items_df.copy()
            show_items.insert(0, "select", False)
            # 以 customer_order_item_id 作為 index，並隱藏 index -> 達成「ID 不呈現」但仍可回溯到實體 ID
            show_items = show_items.set_index("customer_order_item_id", drop=True)

        st.markdown("<div class='ordo-panel'>", unsafe_allow_html=True)
        items_editor = st.data_editor(
            show_items[["select", "product_code", "customer_product_id", "product_name", "specification", "specification_unit", "unit", "quantity", "price_unit", "line_total", "deliver_date"]],
            use_container_width=True,
            hide_index=True,
            disabled=["product_code","customer_product_id","product_name","specification","specification_unit","unit","quantity","price_unit","line_total","deliver_date","created_at"],
            height=180,
            column_config={
                "select": st.column_config.CheckboxColumn(_t("選取"), help=_t("可勾選一筆進行修改；也可多選後刪除"), default=False),
                "product_code": st.column_config.TextColumn(_t("本公司品號"), width="small", disabled=True),
                "customer_product_id": st.column_config.TextColumn("客戶料號", width="small", disabled=True),
                "product_name": st.column_config.TextColumn(_t("品名"), width="medium", disabled=True),
                "specification": st.column_config.TextColumn(_t("規格"), width="medium", disabled=True),
                "unit": st.column_config.TextColumn(_t("單位"), width="small", disabled=True),
                "price_unit": st.column_config.NumberColumn(_t("單價"), width="small", disabled=True),
                "line_total": st.column_config.NumberColumn(_t("小計"), width="small", disabled=True),
                "quantity": st.column_config.NumberColumn(_t("數量"), width="small", disabled=True),
                "deliver_date": st.column_config.DateColumn(_t("明細交期"), width="small", disabled=True),
                "created_at": st.column_config.DatetimeColumn(_t("建立時間"), width="medium", disabled=True),
            },
            key="e01_items_editor",
        )
        st.markdown(
            f"<div class='ordo-big-total'>{_e01_t('訂單總數量')}：{_format_total_quantity(order_total_qty)}　"
            f"{_t('訂單總額')}：{order_total_amt:,.2f}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        picked_items = items_editor[items_editor["select"] == True] if "select" in items_editor.columns else pd.DataFrame()
        picked_item_ids = [int(x) for x in picked_items.index.tolist()] if picked_items is not None and not picked_items.empty else []

        h1, h2 = st.columns([4.2, 1.2])
        with h1:
            st.markdown(f"<div class='ordo-section-title'>{_t('新增/修改勾選明細')}</div>", unsafe_allow_html=True)
        with h2:
            if st.button(_t("刪除勾選"), use_container_width=True, disabled=(not picked_item_ids), key="e01_btn_delete_loaded_items"):
                ok, msg = delete_customer_order_items(picked_item_ids)
                if ok:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)

        # products for dropdown
        prod_df = fetch_products_by_customer(int(active_customer_id))
        prod_df = prod_df if prod_df is not None else pd.DataFrame()
        prod_ids = [int(x) for x in prod_df["product_id"].tolist()] if not prod_df.empty else []
        prod_label = {int(r["product_id"]): build_product_select_label(r) for _, r in prod_df.iterrows()}

        # ---------------------------
        # Edit selected item
        # ---------------------------
        if picked_items is not None and not picked_items.empty:
            picked_item_id = int(picked_items.index.tolist()[0])

            # 取得目前該明細的 product_id（不在呈現欄位內，但仍可由 items_df 找回）
            current_pid = None
            try:
                current_pid = int(items_df.loc[items_df["customer_order_item_id"] == picked_item_id, "product_id"].iloc[0])
            except Exception:
                current_pid = prod_ids[0] if prod_ids else None

            picked_row = picked_items.iloc[0].to_dict()
            default_qty = picked_row.get("quantity", "")
            default_dd = picked_row.get("deliver_date", None)
            # 為了讓『明細交期』與『更新明細』同列對齊：使用 label row + widget row，並把 widget 的 label 隱藏。
            l1, l2, l3, l4, l5, l6 = st.columns([3.0, 1.0, 1.0, 1.2, 2.2, 1.3])
            with l1:
                st.markdown(_t("品項（勾選明細）"))
            with l2:
                st.markdown(_t("數量（勾選明細）"))
            with l3:
                st.markdown(_t("單位（勾選明細）"))
            with l4:
                st.markdown(_t("單價（勾選明細）"))
            with l5:
                st.markdown(_t("明細交期（勾選明細）"))
            with l6:
                st.markdown("&nbsp;", unsafe_allow_html=True)

            w1, w2, w3, w4, w5, w6 = st.columns([3.0, 1.0, 1.0, 1.2, 2.2, 1.3])
            with w1:
                if prod_ids:
                    edit_pid = st.selectbox(
                        "",
                        options=prod_ids,
                        index=prod_ids.index(current_pid) if current_pid in prod_ids else 0,
                        format_func=lambda x: prod_label.get(int(x), str(x)),
                        key="e01_edit_item_pid",
                        label_visibility="collapsed",
                    )
                else:
                    edit_pid = None
                    st.error("product 表無資料，無法新增/修改明細。")

            with w2:
                edit_qty = st.text_input("", value=str(default_qty), key="e01_edit_item_qty", label_visibility="collapsed")

            with w3:
                # unit：由品項決定，不讓使用者硬改
                unit_val = ""
                try:
                    unit_val = str(prod_df.loc[prod_df["product_id"] == int(edit_pid), "unit"].iloc[0])
                except Exception:
                    pass
                st.text_input("", value=unit_val, disabled=True, key="e01_edit_item_unit", label_visibility="collapsed")


            with w4:
                # 單價：唯讀顯示（不允許手動輸入），一律顯示最新單價
                edit_price_unit, edit_price_tier_id, edit_price_source = _render_order_price_readonly(
                    key="e01_edit_item_price_unit",
                    customer_id=active_customer_id,
                    pid=edit_pid,
                    qty=edit_qty,
                )


            with w5:
                # 日期預設：若 DB 為空，允許空白（不同 streamlit 版本可能不支援 None，故做 fallback）
                try:
                    edit_item_dd = st.date_input("", value=default_dd if pd.notna(default_dd) else None, key="e01_edit_item_dd", label_visibility="collapsed")
                except Exception:
                    edit_item_dd = st.date_input("", value=default_dd if pd.notna(default_dd) else date.today(), key="e01_edit_item_dd_fb", label_visibility="collapsed")

            with w6:
                if st.button(_t("更新明細"), use_container_width=True, disabled=(edit_pid is None), key="e01_btn_update_loaded_item"):
                    try:
                        qty_f = float(edit_qty)
                    except Exception:
                        st.warning(_t("數量必須是數字。"))
                    else:
                        if edit_price_unit is None:
                            st.warning(_t("該產品目前沒有價格，請至產品主檔修改"))
                        else:
                            ok, msg = update_customer_order_item(
                                customer_order_item_id=picked_item_id,
                                product_id=int(edit_pid),
                                quantity=qty_f,
                                price_unit=edit_price_unit,
                                deliver_date=edit_item_dd,
                                updated_by=_current_user_id(),
                            )
                            if ok:
                                st.success(msg)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(msg)

        if picked_items is not None and not picked_items.empty:
            render_customer_order_item_schedule_editor(
                int(picked_item_id),
                key_prefix=f"e01_schedule_{int(picked_item_id)}",
            )
        else:
            render_recent_schedule_focus(int(order_id), source_key="e01")

        # ---------------------------
        # Add new item
        # ---------------------------
        st.markdown(f"<div class='ordo-subtitle'>{_t('新增明細')}</div>", unsafe_allow_html=True)

        # 讓交期欄位與「新增明細」按鈕水平對齊：使用 label row + widget row，並把 widget 的 label 隱藏。
        l1, l2, l3, l4, l5, l6 = st.columns([3.0, 1.0, 1.0, 1.2, 2.2, 1.3])
        with l1:
            st.markdown(_t("新增明細品項"))
        with l2:
            st.markdown(_t("新增明細數量"))
        with l3:
            st.markdown(_t("新增明細單位"))
        with l4:
            st.markdown(_t("新增明細單價"))
        with l5:
            st.markdown(_t("新增明細交期"))
        with l6:
            st.markdown("&nbsp;", unsafe_allow_html=True)

        a1, a2, a3, a4, a5, a6 = st.columns([3.0, 1.0, 1.0, 1.2, 2.2, 1.3])
        with a1:
            if prod_ids:
                new_pid = st.selectbox(
                    "",
                    options=prod_ids,
                    index=0,
                    format_func=lambda x: prod_label.get(int(x), str(x)),
                    key="e01_new_item_pid",
                    label_visibility="collapsed",
                )
            else:
                new_pid = None
                st.error("product 表無資料，無法新增明細。")

        with a2:
            new_qty = st.text_input("", value="1", key="e01_new_item_qty", label_visibility="collapsed")

        with a3:
            base_unit_val2 = ""
            try:
                base_unit_val2 = str(prod_df.loc[prod_df["product_id"] == int(new_pid), "unit"].iloc[0])
            except Exception:
                pass
            st.text_input("", value=base_unit_val2, disabled=True, key="e01_new_item_unit", label_visibility="collapsed")


        with a4:
            # 單價：唯讀顯示（不允許手動輸入），一律顯示最新單價
            new_price_unit, new_price_tier_id, new_price_source = _render_order_price_readonly(
                key="e01_new_item_price_unit",
                customer_id=active_customer_id,
                pid=new_pid,
                qty=new_qty,
            )


        with a5:
            try:
                new_item_dd = st.date_input("", value=None, key="e01_new_item_dd", label_visibility="collapsed")
            except Exception:
                new_item_dd = st.date_input("", value=date.today(), key="e01_new_item_dd_fb", label_visibility="collapsed")

        with a6:
            if st.button(_t("新增明細"), use_container_width=True, disabled=(new_pid is None), key="e01_btn_add_item"):
                try:
                    qty_f = float(new_qty)
                except Exception:
                    st.warning(_t("數量必須是數字。"))
                else:
                    try:
                        _dup_pid = int(new_pid) if new_pid not in (None, "") else None
                    except Exception:
                        _dup_pid = None

                    if _dup_pid is not None and order_has_same_product(int(order_id), _dup_pid):
                        st.warning("同一張訂單不可出現相同品項。")
                    elif new_price_unit is None:
                        st.warning(_t("該產品目前沒有價格，請至產品主檔修改"))
                    else:
                        ok, msg = create_customer_order_item(
                            customer_order_id=int(order_id),
                            product_id=int(new_pid),
                            quantity=qty_f,
                            price_unit=(float(new_price_unit) if new_price_unit is not None else None),
                            deliver_date=new_item_dd,
                            created_by=_current_user_id(),
                        )
                        if ok:
                            _remember_schedule_focus(int(order_id), int(new_pid))
                            st.success(msg)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(msg)


else:
    st.markdown(f"### {_t('新增訂單')}")

    # 若剛建立新訂單：直接在本分頁下方顯示抬頭+明細編輯區（不需要回去勾選訂單清單）
    _created_order_id = st.session_state.get("e01_create_order_id")

    if _created_order_id:
        try:
            _created_order_id = int(_created_order_id)
        except Exception:
            _created_order_id = None

    if _created_order_id:
        st.success(f"{_t('已建立訂單')}：{_created_order_id}（{_t('可直接在下方編輯抬頭、明細與交貨排程')}）")
        st.divider()

        order_id = int(_created_order_id)

        # ---- Load head
        head = {}
        _head_df = fetch_customer_order_head(int(order_id))
        if _head_df is not None and not _head_df.empty:
            head = _head_df.iloc[0].to_dict()
        else:
            st.error(_t("找不到此訂單抬頭資料，請回到訂單清單重新載入。"))
            st.stop()

        # Active customer id for the created order
        try:
            active_customer_id = int(head.get("customer_id"))
        except Exception:
            active_customer_id = None

        # ---------------------------
        # Head editor (same as modify)
        # ---------------------------
        st.markdown(f"### {_t('編輯訂單（抬頭）')}")

        h1, h2, h3, h4 = st.columns([1.1, 1.8, 1.1, 1.1])
        with h1:
            st.text_input("本公司訂單號", value=str(head.get("customer_order_code") or ""), disabled=True, key="e01c_head_code")
        with h2:
            st.text_input(_t("客戶"), value=str(cust_labels.get(int(active_customer_id), "")) if active_customer_id else "", disabled=True, key="e01c_head_customer")
        with h3:
            st.text_input(_t("客戶單號"), value=str(head.get("customer_order_num") or ""), key="e01c_head_customer_order_num")
        with h4:
            try:
                _dd = pd.to_datetime(head.get("deliver_date")).date() if head.get("deliver_date") else date.today()
            except Exception:
                _dd = date.today()
            st.date_input(_t("交期"), value=_dd, key="e01c_head_deliver_date_top")

        # 收貨地址可留空；有建立地址時才供使用者選擇。
        addr_df = fetch_receiving_addresses(int(active_customer_id)) if active_customer_id else pd.DataFrame()
        addr_df = addr_df if addr_df is not None else pd.DataFrame()

        # 欄位名稱以資料庫為準：customer_receiving_add 的主鍵是 receiving_id
        _addr_id_col = 'receiving_id' if 'receiving_id' in addr_df.columns else ('customer_receiving_add_id' if 'customer_receiving_add_id' in addr_df.columns else None)
        if _addr_id_col is None or addr_df.empty:
            addr_ids = []
            addr_label = {}
        else:
            addr_ids = [int(x) for x in addr_df[_addr_id_col].dropna().tolist()]
            addr_label = {}
            for _, r in addr_df.iterrows():
                _rid = r.get(_addr_id_col)
                if pd.isna(_rid):
                    continue
                _add = (r.get('receiving_add') or r.get('receiving_address') or '').strip()
                _person = (r.get('warehouse_contact_person') or '').strip()
                _tel = (r.get('tel') or '').strip()
                _extra = ' / '.join([x for x in [_person, _tel] if x])
                _label = _add if not _extra else f"{_add} ({_extra})"
                addr_label[int(_rid)] = _label

        h5, h6, h7, h8 = st.columns([3.1, 1.0, 1.5, 1.2])
        with h5:
            default_deliver_to = None
            try:
                default_deliver_to = int(head.get("deliver_to")) if head.get("deliver_to") is not None else None
            except Exception:
                default_deliver_to = None

            if default_deliver_to not in addr_ids:
                default_deliver_to = None
            deliver_to_options = [None] + addr_ids
            edit_deliver_to = st.selectbox(
                "送貨地址（可空）",
                options=deliver_to_options,
                index=deliver_to_options.index(default_deliver_to),
                format_func=lambda x: "—" if x is None else addr_label.get(int(x), str(x)),
                key="e01c_head_deliver_to",
            )

        with h6:
            missing_dd = False
            edit_deliver_date = st.session_state.get("e01c_head_deliver_date_top", date.today())
            dd_confirmed = True
            edit_state = st.selectbox(
                "state",
                options=["draft", "approve"],
                index=0 if str(head.get("state") or "") == "draft" else 1,
                key="e01c_head_state",
            )

        with h7:
            current_category = str(head.get("customer_order_category") or CUSTOMER_ORDER_CATEGORY_GENERAL)
            if current_category not in CUSTOMER_ORDER_CATEGORY_OPTIONS:
                current_category = CUSTOMER_ORDER_CATEGORY_GENERAL
            edit_customer_order_category = st.selectbox(
                _e01_t("訂單類別"),
                options=list(CUSTOMER_ORDER_CATEGORY_OPTIONS),
                index=list(CUSTOMER_ORDER_CATEGORY_OPTIONS).index(current_category),
                format_func=customer_order_category_label,
                key=f"e01c_customer_order_category_{order_id}",
            )

        with h8:
            if st.button(_t("更新抬頭"), use_container_width=True, key="e01c_btn_update_head", disabled=(not dd_confirmed)):
                if edit_deliver_date is None:
                    st.warning(_t("交期為必填，請先選擇交期。"))
                else:
                    ok, msg = update_customer_order_head(
                        customer_order_id=int(order_id),
                        customer_order_num=str(st.session_state.get("e01c_head_customer_order_no") or "").strip(),
                        deliver_to=edit_deliver_to,
                        deliver_date=edit_deliver_date,
                        state=str(edit_state),
                        customer_order_category=edit_customer_order_category,
                        updated_by=_current_user_id(),
                    )
                    if ok:
                        st.success(msg)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

        st.divider()

        # ---------------------------
        # Items (list + add/edit)
        # ---------------------------
        st.markdown(f"<div class='ordo-section-title'>{_t('訂單產品明細')}</div>", unsafe_allow_html=True)

        items_df = fetch_customer_order_items(int(order_id))
        items_df = items_df if items_df is not None else pd.DataFrame()

        # --- 計算小計與總額（強制以最新單價） ---
        try:
            if items_df is not None and not items_df.empty:
                items_df["price_unit"] = pd.to_numeric(items_df.get("price_unit"), errors="coerce")
                items_df["quantity"] = pd.to_numeric(items_df.get("quantity"), errors="coerce")
                items_df["line_total"] = (items_df["price_unit"].fillna(0) * items_df["quantity"].fillna(0))
                order_total_amt = float(items_df["line_total"].fillna(0).sum())
                order_total_qty = float(items_df["quantity"].fillna(0).sum())
            else:
                order_total_amt = 0.0
                order_total_qty = 0.0
        except Exception:
            order_total_amt = 0.0
            order_total_qty = 0.0

        if items_df is None or items_df.empty:
            st.info(_t("此訂單尚無明細。"))
            show_items = pd.DataFrame(columns=["select", "product_code", "customer_product_id", "product_name", "specification", "specification_unit", "unit", "quantity", "price_unit", "line_total", "deliver_date"])
        else:
            show_items = items_df.copy()
            show_items.insert(0, "select", False)
            show_items = show_items.set_index("customer_order_item_id", drop=True)

        st.markdown("<div class='ordo-panel'>", unsafe_allow_html=True)
        items_editor = st.data_editor(
            show_items[["select", "product_code", "customer_product_id", "product_name", "specification", "specification_unit", "unit", "quantity", "price_unit", "line_total", "deliver_date"]] if not show_items.empty else show_items,
            use_container_width=True,
            hide_index=True,
            disabled=["product_code","customer_product_id","product_name","specification","specification_unit","unit","quantity","price_unit","line_total","deliver_date","created_at"],
            height=180,
            column_config={
                "select": st.column_config.CheckboxColumn(_t("選取"), help=_t("可勾選一筆進行修改；也可多選後刪除"), default=False),
                "product_code": st.column_config.TextColumn(_t("本公司品號"), width="small", disabled=True),
                "customer_product_id": st.column_config.TextColumn("客戶料號", width="small", disabled=True),
                "product_name": st.column_config.TextColumn(_t("品名"), width="medium", disabled=True),
                "specification": st.column_config.TextColumn(_t("規格"), width="medium", disabled=True),
                "unit": st.column_config.TextColumn(_t("單位"), width="small", disabled=True),
                "quantity": st.column_config.NumberColumn(_t("數量"), width="small", disabled=True),
                "deliver_date": st.column_config.DateColumn(_t("明細交期"), width="small", disabled=True),
            },
            key="e01c_items_editor",
        )
        st.markdown(
            f"<div class='ordo-big-total'>{_e01_t('訂單總數量')}：{_format_total_quantity(order_total_qty)}　"
            f"{_t('訂單總額')}：{order_total_amt:,.2f}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        picked_items = items_editor[items_editor["select"] == True] if (items_editor is not None and "select" in items_editor.columns) else pd.DataFrame()
        picked_item_ids = [int(x) for x in picked_items.index.tolist()] if picked_items is not None and not picked_items.empty else []

        title_l, title_r = st.columns([4.2, 1.2])
        with title_l:
            st.markdown(f"<div class='ordo-section-title'>{_t('新增/修改勾選明細')}</div>", unsafe_allow_html=True)
        with title_r:
            if st.button("刪除勾選", use_container_width=True, disabled=(not picked_item_ids), key="e01c_btn_delete_items"):
                ok, msg = delete_customer_order_items(picked_item_ids)
                if ok:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)

        # products for dropdown
        prod_df = fetch_products_by_customer(int(active_customer_id)) if active_customer_id else pd.DataFrame()
        prod_df = prod_df if prod_df is not None else pd.DataFrame()
        prod_ids = [int(x) for x in prod_df["product_id"].tolist()] if not prod_df.empty else []
        prod_label = {int(r["product_id"]): build_product_select_label(r) for _, r in prod_df.iterrows()}

        # ---- Edit selected item (one at a time)
        if picked_items is not None and not picked_items.empty:
            picked_item_id = int(picked_items.index.tolist()[0])

            current_pid = None
            try:
                current_pid = int(items_df.loc[items_df["customer_order_item_id"] == picked_item_id, "product_id"].iloc[0])
            except Exception:
                current_pid = None

            try:
                default_qty = str(items_df.loc[items_df["customer_order_item_id"] == picked_item_id, "quantity"].iloc[0])
            except Exception:
                default_qty = ""

            try:
                _dd = items_df.loc[items_df["customer_order_item_id"] == picked_item_id, "deliver_date"].iloc[0]
                default_dd = pd.to_datetime(_dd).date() if _dd is not None else date.today()
            except Exception:
                default_dd = date.today()

            # 為了讓交期欄位與按鈕水平對齊：先輸出一排標題(label)，再輸出一排元件(widget)，並把 widget 的 label 隱藏。
            l1, l2, l3, l4 = st.columns([2.8, 1.2, 1.6, 1.2])
            with l1:
                st.markdown(_t("品項（勾選明細）"))
            with l2:
                st.markdown(_t("數量（勾選明細）"))
            with l3:
                st.markdown(_t("交期（勾選明細）"))
            with l4:
                st.markdown("&nbsp;", unsafe_allow_html=True)

            w1, w2, w3, w4 = st.columns([2.8, 1.2, 1.6, 1.2])
            with w1:
                if prod_ids:
                    edit_pid = st.selectbox(
                        "",
                        options=prod_ids,
                        index=prod_ids.index(current_pid) if current_pid in prod_ids else 0,
                        format_func=lambda x: prod_label.get(int(x), str(x)),
                        key="e01c_edit_item_pid",
                        label_visibility="collapsed",
                    )
                else:
                    edit_pid = None
                    st.error("product 表無資料，無法新增/修改明細。")
            with w2:
                edit_qty = st.text_input("", value=str(default_qty), key="e01c_edit_item_qty", label_visibility="collapsed")
            with w3:
                edit_dd = st.date_input("", value=default_dd, key="e01c_edit_item_dd", label_visibility="collapsed")
            with w4:
                if st.button(_t("更新勾選明細"), use_container_width=True, disabled=(edit_pid is None), key="e01c_btn_update_item"):
                    try:
                        qty_f = float(edit_qty)
                    except Exception:
                        st.warning(_t("數量必須是數字。"))
                    else:
                        ok, msg = update_customer_order_item(
                            customer_order_item_id=int(picked_item_id),
                            product_id=int(edit_pid),
                            quantity=qty_f,
                            price_unit=None,
                            deliver_date=edit_dd,
                            updated_by=_current_user_id(),
                        )
                        if ok:
                            st.success(msg)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info(_t("可先在上方勾選一筆明細再修改；或直接新增明細。"))

        if picked_items is not None and not picked_items.empty:
            render_customer_order_item_schedule_editor(
                int(picked_item_id),
                key_prefix=f"e01c_schedule_{int(picked_item_id)}",
            )
        else:
            render_recent_schedule_focus(int(order_id), source_key="e01c")

        # ---- Add new item (aligned row)
        st.markdown(f"<div class='ordo-subtitle'>{_t('新增明細')}</div>", unsafe_allow_html=True)

        # label row
        l1, l2, l3, l4, l5 = st.columns([2.8, 1.2, 1.3, 1.6, 1.2])
        with l1:
            st.markdown(_t("項目（新增明細）"))
        with l2:
            st.markdown(_t("數量（新增明細）"))
        with l3:
            st.markdown(_t("單價（唯讀）"))
        with l4:
            st.markdown(_t("新增明細交期"))
        with l5:
            st.markdown("&nbsp;", unsafe_allow_html=True)

        # widget row
        bcol1, bcol2, bcol3, bcol4, bcol5 = st.columns([2.8, 1.2, 1.3, 1.6, 1.2])
        with bcol1:
            if prod_ids:
                new_pid = st.selectbox(
                    "",
                    options=prod_ids,
                    index=0,
                    format_func=lambda x: prod_label.get(int(x), str(x)),
                    key="e01c_new_item_pid",
                    label_visibility="collapsed",
                )
            else:
                new_pid = None
                st.error("product 表無資料，無法新增明細。")
        with bcol2:
            new_qty = st.text_input("", value="1", key="e01c_new_item_qty", label_visibility="collapsed")

        # 單價：唯讀顯示（不允許在此修改），一律顯示最新單價
        with bcol3:
            _p_new, _p_new_tier_id, _p_new_source = _render_order_price_readonly(
                key="e01c_new_item_price_unit",
                customer_id=active_customer_id,
                pid=new_pid,
                qty=new_qty,
            )

        with bcol4:
            try:
                new_item_dd = st.date_input("", value=None, key="e01c_new_item_dd", label_visibility="collapsed")
            except Exception:
                new_item_dd = st.date_input("", value=date.today(), key="e01c_new_item_dd_fb", label_visibility="collapsed")

        with bcol5:
            if st.button(_t("新增明細"), use_container_width=True, disabled=(new_pid is None), key="e01c_btn_add_item"):
                try:
                    qty_f = float(new_qty)
                except Exception:
                    st.warning(_t("數量必須是數字。"))
                else:
                    try:
                        _dup_pid = int(new_pid) if new_pid not in (None, "") else None
                    except Exception:
                        _dup_pid = None

                    if _dup_pid is not None and order_has_same_product(int(order_id), _dup_pid):
                        st.warning("同一張訂單不可出現相同品項。")
                    elif _p_new is None:
                        st.warning(_t("該產品目前沒有價格，請至產品主檔修改"))
                    else:
                        ok, msg = create_customer_order_item(
                            customer_order_id=int(order_id),
                            product_id=int(new_pid),
                            quantity=qty_f,
                            price_unit=float(_p_new),
                            deliver_date=new_item_dd,
                            created_by=_current_user_id(),
                        )
                        if ok:
                            _remember_schedule_focus(int(order_id), int(new_pid))
                            st.success(msg)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.warning(msg) if "沒有價格" in str(msg) else st.error(msg)

        st.divider()
        finish_col, finish_note_col = st.columns([1.8, 5.2], vertical_alignment="center")
        with finish_col:
            if st.button(_t("完成此訂單，建立下一張"), type="primary", use_container_width=True, key="e01_btn_finish_and_next_order"):
                reset_new_order_form(keep_order_code=False)
                _clear_schedule_focus()
                st.cache_data.clear()
                st.rerun()
        with finish_note_col:
            st.caption(_t("確認抬頭、明細與交貨排程都設定完成後，按此按鈕清空畫面並產生下一張本公司訂單號。"))


    else:
        if st.session_state.get("e01_reset_new_order_form", False):
            for _k in ["e01_new_customer_order_num", "e01_new_deliver_date"]:
                st.session_state.pop(_k, None)
            st.session_state["e01_reset_new_order_form"] = False

        # 必須選客戶（新增訂單不能用「所有客戶」）
        default_new_customer_id = cust_ids[0]

        # session_state 可能出現 None（例如第一次載入或元件尚未初始化），不要直接 int(None)
        _raw_new_cust = st.session_state.get("e01_new_customer_id")
        try:
            _raw_new_cust_int = int(_raw_new_cust) if _raw_new_cust not in (None, "") else None
        except (TypeError, ValueError):
            _raw_new_cust_int = None

        if _raw_new_cust_int in cust_ids:
            default_new_customer_id = _raw_new_cust_int

        preview_shortname = cust_shortnames.get(int(default_new_customer_id), "")
        try:
            preview_code = _generate_customer_order_code(preview_shortname, basis_date=date.today())
        except ValueError as e:
            preview_code = ""
            st.warning(str(e))
        top1, top2, top3, top4, top5 = st.columns([1.0, 1.6, 1.0, 1.0, 1.5])
        with top1:
            st.text_input(_t("本公司訂單號"), value=str(preview_code), disabled=True)
        with top2:
            new_customer_id = st.selectbox(
                _t("客戶"),
                options=cust_ids,
                index=cust_ids.index(default_new_customer_id),
                format_func=lambda x: cust_labels.get(int(x), str(x)),
                key="e01_new_customer_id",
            )
        with top3:
            new_customer_order_num = st.text_input(_t("客戶單號"), value="", key="e01_new_customer_order_num")
        with top4:
            new_deliver_date = st.date_input(_t("交期"), value=date.today(), key="e01_new_deliver_date")
        with top5:
            new_customer_order_category = st.selectbox(
                _e01_t("訂單類別"),
                options=list(CUSTOMER_ORDER_CATEGORY_OPTIONS),
                format_func=customer_order_category_label,
                key="e01_new_customer_order_category",
            )

        addr_df = fetch_receiving_addresses(int(new_customer_id))
        addr_df = addr_df if addr_df is not None else pd.DataFrame()

        # 欄位名稱以資料庫為準：customer_receiving_add 的主鍵是 receiving_id
        _addr_id_col = 'receiving_id' if 'receiving_id' in addr_df.columns else ('customer_receiving_add_id' if 'customer_receiving_add_id' in addr_df.columns else None)
        if _addr_id_col is None or addr_df.empty:
            addr_ids = []
            addr_label = {}
        else:
            addr_ids = [int(x) for x in addr_df[_addr_id_col].dropna().tolist()]
            addr_label = {}
            for _, r in addr_df.iterrows():
                _rid = r.get(_addr_id_col)
                if pd.isna(_rid):
                    continue
                _add = (r.get('receiving_add') or r.get('receiving_address') or '').strip()
                _person = (r.get('warehouse_contact_person') or '').strip()
                _tel = (r.get('tel') or '').strip()
                _extra = ' / '.join([x for x in [_person, _tel] if x])
                _label = _add if not _extra else f"{_add} ({_extra})"
                addr_label[int(_rid)] = _label

        row2a, row2b = st.columns([4.2, 1.2])
        with row2a:
            new_deliver_to = st.selectbox(
                "客戶送貨地址（可空）",
                options=[None] + addr_ids,
                index=0,
                format_func=lambda x: "—" if x is None else addr_label.get(int(x), str(x)),
                key="e01_new_deliver_to",
            )
        with row2b:
            new_state = st.selectbox(_t("狀態"), options=["draft", "approve"], index=0, key="e01_new_state")

        # ---------------------------
        # New-order staged items
        # ---------------------------
        st.markdown(f"<div class='ordo-section-title'>{_t('建立訂單產品明細')}</div>", unsafe_allow_html=True)

        prod_df = fetch_products_by_customer(int(new_customer_id)) if new_customer_id else pd.DataFrame()
        prod_df = prod_df if prod_df is not None else pd.DataFrame()
        prod_ids = [int(x) for x in prod_df["product_id"].tolist()] if not prod_df.empty else []
        prod_label = {int(r["product_id"]): build_product_select_label(r) for _, r in prod_df.iterrows()}

        tmp_key = f"e01_new_order_items_{int(new_customer_id)}"
        if st.session_state.get("e01_new_order_items_customer") != int(new_customer_id):
            st.session_state["e01_new_order_items_customer"] = int(new_customer_id)
            st.session_state[tmp_key] = []
        staged_items = st.session_state.get(tmp_key, [])

        staged_df = pd.DataFrame(staged_items)
        if staged_df.empty:
            show_new_items = pd.DataFrame(columns=["select", "product_code", "customer_product_id", "product_name", "specification", "specification_unit", "unit", "quantity", "price_unit", "line_total", "deliver_date"])
            new_total_amt = 0.0
            new_total_qty = 0.0
        else:
            staged_df = staged_df.copy()
            staged_df.insert(0, "select", False)
            staged_df = staged_df.reset_index(drop=True)
            staged_df.index = staged_df.index + 1
            show_new_items = staged_df
            try:
                show_new_items["line_total"] = pd.to_numeric(show_new_items.get("line_total"), errors="coerce").fillna(0)
                new_total_amt = float(show_new_items["line_total"].sum())
                new_total_qty = float(pd.to_numeric(show_new_items.get("quantity"), errors="coerce").fillna(0).sum())
            except Exception:
                new_total_amt = 0.0
                new_total_qty = 0.0

        st.markdown("<div class='ordo-panel'>", unsafe_allow_html=True)
        staged_editor = st.data_editor(
            show_new_items[["select", "product_code", "customer_product_id", "product_name", "specification", "specification_unit", "unit", "quantity", "price_unit", "line_total", "deliver_date"]] if not show_new_items.empty else show_new_items,
            use_container_width=True,
            hide_index=True,
            disabled=["product_code", "customer_product_id", "product_name", "specification", "specification_unit", "unit", "quantity", "price_unit", "line_total", "deliver_date"],
            height=180,
            column_config={
                "select": st.column_config.CheckboxColumn("選取", help="可多選後刪除", default=False),
                "product_code": st.column_config.TextColumn(_t("本公司品號"), width="small", disabled=True),
                "product_name": st.column_config.TextColumn(_t("品名"), width="medium", disabled=True),
                "specification": st.column_config.TextColumn(_t("規格"), width="medium", disabled=True),
                "unit": st.column_config.TextColumn(_t("單位"), width="small", disabled=True),
                "quantity": st.column_config.NumberColumn(_t("數量"), width="small", disabled=True),
                "price_unit": st.column_config.NumberColumn(_t("單價"), width="small", disabled=True),
                "line_total": st.column_config.NumberColumn(_t("小計"), width="small", disabled=True),
                "deliver_date": st.column_config.DateColumn(_t("明細交期"), width="small", disabled=True),
            },
            key=f"{tmp_key}_editor",
        )
        st.markdown(
            f"<div class='ordo-big-total'>{_e01_t('訂單總數量')}：{_format_total_quantity(new_total_qty)}　"
            f"{_t('訂單總額')}：{new_total_amt:,.2f}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        picked_new_items = staged_editor[staged_editor["select"] == True] if (staged_editor is not None and "select" in staged_editor.columns) else pd.DataFrame()
        picked_new_idx = [int(i) - 1 for i in picked_new_items.index.tolist()] if picked_new_items is not None and not picked_new_items.empty else []

        title_l, title_r = st.columns([4.2, 1.2])
        with title_l:
            st.markdown(f"<div class='ordo-section-title'>{_t('新增明細')}</div>", unsafe_allow_html=True)
        with title_r:
            if st.button(_t("刪除勾選明細"), use_container_width=True, disabled=(not picked_new_idx), key="e01_new_tmp_delete"):
                st.session_state[tmp_key] = [row for idx, row in enumerate(st.session_state.get(tmp_key, [])) if idx not in set(picked_new_idx)]
                st.rerun()

        l1, l2, l3, l4, l5, l6 = st.columns([3.0, 1.0, 1.0, 1.2, 2.2, 1.3])
        with l1:
            st.markdown(_t("新增明細品項"))
        with l2:
            st.markdown(_t("新增明細數量"))
        with l3:
            st.markdown(_t("新增明細單位"))
        with l4:
            st.markdown(_t("新增明細單價"))
        with l5:
            st.markdown(_t("新增明細交期"))
        with l6:
            st.markdown("&nbsp;", unsafe_allow_html=True)

        a1, a2, a3, a4, a5, a6 = st.columns([3.0, 1.0, 1.0, 1.2, 2.2, 1.3])
        with a1:
            if prod_ids:
                new_item_pid = st.selectbox(
                    "",
                    options=prod_ids,
                    index=0,
                    format_func=lambda x: prod_label.get(int(x), str(x)),
                    key="e01_new_stage_item_pid",
                    label_visibility="collapsed",
                )
            else:
                new_item_pid = None
                st.error("product 表無資料，無法新增明細。")
        with a2:
            new_item_qty = st.text_input("", value="1", key="e01_new_stage_item_qty", label_visibility="collapsed")
        with a3:
            _unit_val = ""
            try:
                _unit_val = str(prod_df.loc[prod_df["product_id"] == int(new_item_pid), "unit"].iloc[0])
            except Exception:
                pass
            st.text_input("", value=_unit_val, disabled=True, key="e01_new_stage_item_unit", label_visibility="collapsed")
        with a4:
            new_stage_price, new_stage_price_tier_id, new_stage_price_source = _render_order_price_readonly(
                key="e01_new_stage_item_price",
                customer_id=new_customer_id,
                pid=new_item_pid,
                qty=new_item_qty,
            )
        with a5:
            try:
                new_stage_dd = st.date_input("", value=None, key="e01_new_stage_item_dd", label_visibility="collapsed")
            except Exception:
                new_stage_dd = st.date_input("", value=new_deliver_date if new_deliver_date else date.today(), key="e01_new_stage_item_dd_fb", label_visibility="collapsed")
        with a6:
            if st.button(_t("加入明細"), use_container_width=True, disabled=(new_item_pid is None), key="e01_new_stage_item_add"):
                try:
                    _qty_f = float(new_item_qty)
                except Exception:
                    st.warning(_t("數量必須是數字。"))
                else:
                    if new_stage_price is None:
                        st.warning(_t("該產品目前沒有價格，請至產品主檔修改"))
                    else:
                        _existing_rows = st.session_state.get(tmp_key, [])
                        try:
                            _new_pid_int = int(new_item_pid)
                        except Exception:
                            _new_pid_int = None

                        _already_exists = any(
                            int(r.get("product_id")) == _new_pid_int
                            for r in _existing_rows
                            if isinstance(r, dict) and r.get("product_id") not in (None, "")
                        ) if _new_pid_int is not None else False

                        if _already_exists:
                            st.warning("同一張訂單不可出現相同品項。")
                        else:
                            _row = prod_df.loc[prod_df["product_id"] == int(new_item_pid)].iloc[0].to_dict()
                            st.session_state[tmp_key] = _existing_rows + [{
                                "product_id": int(new_item_pid),
                                "product_code": str(_row.get("product_code") or ""),
                                "customer_product_id": str(_row.get("customer_product_id") or ""),
                                "product_name": str(_row.get("product_name") or ""),
                                "specification": str(_row.get("specification") or ""),
                                "specification_unit": str(_row.get("specification_unit") or ""),
                                "unit": str(_row.get("unit") or ""),
                                "quantity": _qty_f,
                                "price_unit": float(new_stage_price),
                                "price_tier_id": int(new_stage_price_tier_id) if new_stage_price_tier_id is not None else None,
                                "line_total": float(_qty_f) * float(new_stage_price),
                                "deliver_date": new_stage_dd,
                            }]
                            st.rerun()

        save_l, save_r = st.columns([1.6, 3.8])
        with save_l:
            if st.button(_t("儲存整張新建訂單"), type="primary", use_container_width=True, disabled=(len(st.session_state.get(tmp_key, [])) == 0), key="e01_btn_create_full_order"):
                if new_deliver_date is None:
                    st.warning(_t("交期為必填，請先選擇交期。"))
                elif len(st.session_state.get(tmp_key, [])) == 0:
                    st.warning(_t("請先建立至少一筆訂單明細。"))
                else:
                    _staged_rows = st.session_state.get(tmp_key, [])
                    if staged_items_have_duplicate_product_ids(_staged_rows):
                        st.warning("同一張訂單不可出現相同品項。")
                    else:
                        ok, msg, new_id, new_code = create_customer_order_head(
                            customer_id=int(new_customer_id),
                            customer_order_num=str(new_customer_order_num or ""),
                            deliver_to=new_deliver_to,
                            deliver_date=new_deliver_date,
                            state=str(new_state),
                            customer_order_category=new_customer_order_category,
                            created_by=_current_user_id(),
                        )
                        if ok:
                            all_ok = True
                            fail_msgs = []
                            for _it in _staged_rows:
                                _ok2, _msg2 = create_customer_order_item(
                                    customer_order_id=int(new_id),
                                    product_id=int(_it["product_id"]),
                                    quantity=float(_it["quantity"]),
                                    price_unit=float(_it["price_unit"]),
                                    deliver_date=_it.get("deliver_date"),
                                    created_by=_current_user_id(),
                                    update_parent=False,
                                )
                                if not _ok2:
                                    all_ok = False
                                    fail_msgs.append(str(_msg2))
                            if all_ok:
                                st.success(msg)
                                st.session_state["e01_create_order_id"] = int(new_id)
                                st.session_state["e01_order_id"] = int(new_id)
                                st.session_state["e01_create_order_code"] = str(new_code or '')
                                try:
                                    if _staged_rows:
                                        _remember_schedule_focus(int(new_id), int(_staged_rows[-1]["product_id"]))
                                except Exception:
                                    pass
                                # 清掉新建暫存明細，但保留剛建立的正式訂單畫面，方便立刻設定交貨排程。
                                st.session_state[tmp_key] = []
                                st.session_state.pop("e01_new_order_items_customer", None)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("抬頭已建立，但部分明細寫入失敗：" + "；".join(fail_msgs[:3]))
                        else:
                            st.error(msg)
        with save_r:
            if st.button(_t("清空整張新建訂單"), use_container_width=False, key="e01_btn_reset_full_order"):
                reset_new_order_form(keep_order_code=True)
                st.rerun()

# 修改訂單模式：頁面最下方提供一顆僅用於清空畫面並切回新增模式的按鈕
if st.session_state.get("e01_mode") == "修改訂單":
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    _fake_save_col, _fake_save_spacer = st.columns([1.6, 3.8])
    with _fake_save_col:
        if st.button(_t("儲存修改訂單"), type="primary", use_container_width=True, key="e01c_btn_fake_save_order_footer"):
            reset_modify_order_form(keep_order_code=True)
            st.rerun()
