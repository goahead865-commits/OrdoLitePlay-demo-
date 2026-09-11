import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd
import math
import random
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List

apply_compact_layout()

# =============================================================================
# OrdoLite - 產品出貨（出貨紀錄 + 出貨輸入合一）
# - 上方：出貨紀錄（可依客戶查詢 + 上一頁/下一頁）
# - 下方：操作區（新增出貨單 + 明細）
#
# 備註：
# 1) 優先相容你目前專案的 db.py（若可 import get_connection / get_engine 就沿用）。
# 2) 若無法 import，則退回用環境變數 ORDO_DB_* 直接建立連線。
# =============================================================================

# ---------------------------
# DB connection helpers
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
        conn = mysql.connector.connect(**cfg)
        return conn
    except Error as e:
        st.error(f"DB connect error (fallback): {e}")
        return None


# 盡量相容你目前專案的 db.py（沿用 C02_supplier.py 的設計思路）：
# - 優先用 get_connection()
# - 若沒有 get_connection，退回用 get_engine().raw_connection()
# - 若都失敗，再用 fallback
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


# =============================================================================
# SQL helpers
# =============================================================================
@st.cache_data(show_spinner=False, ttl=30)
def fetch_customers() -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    sql = """
        SELECT
            c.customer_id,
            c.customer_code,
            c.customer_name,
            c.is_active
        FROM customer c
        ORDER BY c.customer_name ASC
    """
    df = pd.read_sql(sql, conn)
    try:
        conn.close()
    except Exception:
        pass
    return df


@st.cache_data(show_spinner=False, ttl=30)
def fetch_products(limit: int = 5000) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    sql = """
        SELECT
            p.product_id,
            p.product_code,
            p.product_name,
            p.customer_id,
            p.customer_production_id AS customer_product_id,
            p.Specification AS specification,
            p.Specification_unit AS specification_unit,
            p.color,
            p.qty_per_carton,
            p.is_active
        FROM product p
        ORDER BY p.product_name ASC
        LIMIT %s
    """
    df = pd.read_sql(sql, conn, params=[limit])
    try:
        conn.close()
    except Exception:
        pass
    return df


def _delivery_record_where(
    customer_id: Optional[int],
    date_from: Optional[date],
    date_to: Optional[date],
) -> Tuple[str, list]:
    """Build WHERE clause for delivery queries.

    - date_from/date_to are inclusive dates on dh.created_at.
    - Internally we use: created_at >= date_from 00:00:00 AND created_at < (date_to + 1 day) 00:00:00
    """
    where = []
    params: list = []

    if customer_id:
        where.append("dh.customer_id = %s")
        params.append(int(customer_id))

    if date_from:
        where.append("dh.created_at >= %s")
        params.append(datetime.combine(date_from, datetime.min.time()))

    if date_to:
        where.append("dh.created_at < %s")
        params.append(datetime.combine(date_to + timedelta(days=1), datetime.min.time()))

    where_sql = ""
    if where:
        where_sql = "WHERE " + " AND ".join(where)

    return where_sql, params


def count_delivery_lines(customer_id: Optional[int], date_from: Optional[date], date_to: Optional[date]) -> int:
    conn = get_connection()
    if conn is None:
        return 0

    where_sql, params = _delivery_record_where(customer_id, date_from, date_to)
    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM delivery_head dh
        JOIN delivery_product dp ON dp.delivery_head_id = dh.delivery_note_id
        JOIN customer c ON c.customer_id = dh.customer_id
        {where_sql}
    """
    df = pd.read_sql(sql, conn, params=params)
    try:
        conn.close()
    except Exception:
        pass
    if df.empty:
        return 0
    return int(df.loc[0, "cnt"])


def fetch_delivery_lines(customer_id: Optional[int], date_from: Optional[date], date_to: Optional[date], limit: int, offset: int) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    where_sql, params = _delivery_record_where(customer_id, date_from, date_to)
    sql = f"""
        SELECT
            dh.delivery_note_id,
            dh.delivery_code,
            dh.status,
            dh.customer_order_no,
            dh.vehicle_no,
            dh.created_by,
            dh.created_at,
            c.customer_code,
            c.customer_name,

            dp.delivery_product_id,
            dp.line_no,
            dp.product_id,
            dp.customer_product_id,
            dp.product_name,
            dp.qty,
            dp.specification,
            dp.specification_unit,
            dp.color,
            dp.qty_per_carton
        FROM delivery_head dh
        JOIN delivery_product dp ON dp.delivery_head_id = dh.delivery_note_id
        JOIN customer c ON c.customer_id = dh.customer_id
        {where_sql}
        ORDER BY dh.created_at DESC, dh.delivery_note_id DESC, dp.line_no ASC
        LIMIT %s OFFSET %s
    """
    params2 = params + [int(limit), int(offset)]
    df = pd.read_sql(sql, conn, params=params2)
    try:
        conn.close()
    except Exception:
        pass
    return df


def generate_delivery_code(prefix: str = "DN") -> str:
    # 避免 UNIQUE collision：時間戳 + 3 位隨機碼
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rnd = random.randint(100, 999)
    return f"{prefix}{ts}{rnd}"


def insert_delivery(
    customer_id: int,
    customer_order_no: Optional[str],
    vehicle_no: Optional[str],
    status: str,
    created_by: int,
    lines_df: pd.DataFrame,
) -> Tuple[bool, str]:
    """
    lines_df expected columns:
      - product_id (required)
      - customer_product_id (optional)
      - product_name (optional)
      - qty (required)
      - specification (optional)
      - specification_unit (optional)
      - color (optional)
      - qty_per_carton (optional)
    """
    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗"

    try:
        cur = conn.cursor()

        delivery_code = generate_delivery_code("DN")

        # 1) insert head
        sql_head = """
            INSERT INTO delivery_head
            (delivery_code, customer_id, customer_order_no, vehicle_no, status, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        cur.execute(
            sql_head,
            (
                delivery_code,
                int(customer_id),
                (customer_order_no or None),
                (vehicle_no or None),
                status,
                int(created_by),
            ),
        )
        delivery_note_id = cur.lastrowid

        # 2) insert lines
        sql_line = """
            INSERT INTO delivery_product
            (line_no, delivery_head_id, product_id, customer_product_id, product_name, qty,
             specification, specification_unit, color, qty_per_carton)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        line_no = 1
        for _, r in lines_df.iterrows():
            pid = r.get("product_id")
            qty = r.get("qty")

            if pd.isna(pid) or pid in ("", None):
                continue
            if pd.isna(qty) or float(qty) <= 0:
                continue

            cur.execute(
                sql_line,
                (
                    line_no,
                    int(delivery_note_id),
                    int(pid),
                    (r.get("customer_product_id") or None),
                    (r.get("product_name") or None),
                    float(qty),
                    (r.get("specification") or None),
                    (r.get("specification_unit") or None),
                    (r.get("color") or None),
                    (None if pd.isna(r.get("qty_per_carton")) else int(r.get("qty_per_carton"))),
                ),
            )
            line_no += 1

        if line_no == 1:
            conn.rollback()
            return False, "沒有任何有效的出貨明細（product_id/qty）"

        conn.commit()
        return True, f"新增完成：{delivery_code}（共 {line_no-1} 筆明細）"

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


# =============================================================================
# UI
# =============================================================================
st.set_page_config(page_title="D01 出貨查詢", layout="wide")

st.title("D01 出貨紀錄")

# ---- session state defaults
if "d01q_page" not in st.session_state:
    st.session_state.d01q_page = 1
if "d01q_page_size" not in st.session_state:
    st.session_state.d01q_page_size = 30
if "d01q_customer_id" not in st.session_state:
    st.session_state.d01q_customer_id = None

if "d01q_use_date" not in st.session_state:
    st.session_state.d01q_use_date = False
if "d01q_date_from" not in st.session_state:
    st.session_state.d01q_date_from = date.today() - timedelta(days=30)
if "d01q_date_to" not in st.session_state:
    st.session_state.d01q_date_to = date.today()

# =============================================================================
# Filters (top)
# =============================================================================
with st.container():
    c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1.0, 1.0, 1.0, 1.2, 1.2])
    customers_df = fetch_customers()
    customer_options: List[str] = ["（全部客戶）"]
    customer_map = {"（全部客戶）": None}

    if not customers_df.empty:
        for _, r in customers_df.iterrows():
            label = f"{r['customer_name']}  |  {r['customer_code']}  |  ID:{r['customer_id']}"
            customer_options.append(label)
            customer_map[label] = int(r["customer_id"])

    
    # keep selection when rerun
    current_label = "（全部客戶）"
    if st.session_state.d01q_customer_id is not None:
        for k, v in customer_map.items():
            if v == st.session_state.d01q_customer_id:
                current_label = k
                break
    current_index = customer_options.index(current_label) if current_label in customer_options else 0

    with c1:
        selected_customer_label = st.selectbox(
            "客戶查詢",
            options=customer_options,
            index=current_index,
        )
    with c2:
        page_size = st.selectbox("每頁筆數", options=[10, 20, 30, 50, 100], index=[10,20,30,50,100].index(st.session_state.d01q_page_size))
    with c5:
        use_date = st.checkbox("日期篩選", value=st.session_state.d01q_use_date)
    with c6:
        if use_date:
            dr = st.date_input(
                "日期區間",
                value=(st.session_state.d01q_date_from, st.session_state.d01q_date_to),
            )
            if isinstance(dr, (tuple, list)) and len(dr) == 2:
                st.session_state.d01q_date_from = dr[0]
                st.session_state.d01q_date_to = dr[1]
            else:
                st.session_state.d01q_date_from = dr
                st.session_state.d01q_date_to = dr
        else:
            st.caption("未啟用")

    with c3:
        st.write("")
        st.write("")
        refresh = st.button("刷新", use_container_width=True)
    with c4:
        st.write("")
        st.write("")
        reset = st.button("重置篩選", use_container_width=True)

    if reset:
        st.session_state.d01q_customer_id = None
        st.session_state.d01q_page = 1
        st.session_state.d01q_page_size = 30
        st.session_state.d01q_use_date = False
        st.session_state.d01q_date_from = date.today() - timedelta(days=30)
        st.session_state.d01q_date_to = date.today()
        st.cache_data.clear()

    # apply selections
    prev_customer = st.session_state.d01q_customer_id
    prev_use_date = st.session_state.d01q_use_date
    prev_from = st.session_state.d01q_date_from
    prev_to = st.session_state.d01q_date_to

    st.session_state.d01q_page_size = int(page_size)
    st.session_state.d01q_customer_id = customer_map.get(selected_customer_label)
    st.session_state.d01q_use_date = bool(use_date)

    # 若篩選條件變動，回到第 1 頁
    if (
        (prev_customer != st.session_state.d01q_customer_id)
        or (prev_use_date != st.session_state.d01q_use_date)
        or (prev_from != st.session_state.d01q_date_from)
        or (prev_to != st.session_state.d01q_date_to)
    ):
        st.session_state.d01q_page = 1

    if refresh:

        st.cache_data.clear()

st.divider()

# =============================================================================
# Top 70% - Delivery records (paged)
# =============================================================================
customer_id = st.session_state.d01q_customer_id
use_date = st.session_state.d01q_use_date
q_date_from = st.session_state.d01q_date_from if use_date else None
q_date_to = st.session_state.d01q_date_to if use_date else None
page = int(st.session_state.d01q_page)
page_size = int(st.session_state.d01q_page_size)

total = count_delivery_lines(customer_id, q_date_from, q_date_to)
total_pages = max(1, math.ceil(total / page_size)) if page_size else 1
page = max(1, min(page, total_pages))
offset = (page - 1) * page_size

records_df = fetch_delivery_lines(customer_id, q_date_from, q_date_to, page_size, offset)

# pager controls
p1, p2, p3, p4, p5 = st.columns([1.1, 1.1, 1.1, 2.2, 2.5], vertical_alignment="bottom")
with p1:
    if st.button("上一頁", use_container_width=True, disabled=(page <= 1)):
        st.session_state.d01q_page = max(1, page - 1)
        st.rerun()
with p2:
    if st.button("下一頁", use_container_width=True, disabled=(page >= total_pages)):
        st.session_state.d01q_page = min(total_pages, page + 1)
        st.rerun()
with p3:
    st.number_input("頁碼", min_value=1, max_value=total_pages, value=page, step=1, key="d01q_page")
with p4:
    st.write(f"共 {total} 筆（行） / {total_pages} 頁")
with p5:
    st.caption("提示：上方是出貨『明細行』清單（Head + Line JOIN），所以筆數會比出貨單數多。")

# records table
st.dataframe(
    records_df,
    use_container_width=True,
    height=300,  # 保留表格內捲動，縮減頁面整體高度
)

st.divider()
