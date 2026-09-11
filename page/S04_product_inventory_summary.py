# S04_product_inventory_summary.py
# 產品庫存統計（以 product_stock_io 匯總）
# - 以「截至某日」計算累積庫存：IN 加、OUT 減、ADJUST 依數量正負加減
# - 可依客戶/關鍵字篩選，並支援只顯示有庫存

import datetime
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from compact_layout import apply_compact_layout
import auth

apply_compact_layout()

from db import get_connection

# ================== I18N ==================
TRANSLATIONS = {
    "S04 產品庫存統計": {"vi": "S04 Thống kê tồn kho thành phẩm", "en": "S04 Product Inventory Summary"},
    "查詢條件": {"vi": "Điều kiện truy vấn", "en": "Filter Conditions"},
    "截至日期": {"vi": "Đến ngày", "en": "As of Date"},
    "客戶": {"vi": "Khách hàng", "en": "Customer"},
    "全部": {"vi": "Tất cả", "en": "All"},
    "關鍵字（產品代碼 / 品名 / 客戶料號）": {"vi": "Từ khóa (Mã thành phẩm / Tên hàng / Mã hàng khách)", "en": "Keyword (Product Code / Name / Customer Part No.)"},
    "只顯示有庫存": {"vi": "Chỉ hiển thị mặt hàng còn tồn kho", "en": "Show In-Stock Only"},
    "查詢 / 更新": {"vi": "Truy vấn / Cập nhật", "en": "Query / Refresh"},
    "查詢失敗：": {"vi": "Truy vấn thất bại: ", "en": "Query failed: "},
    "尚未查詢或查無資料。": {"vi": "Chưa truy vấn hoặc không có dữ liệu.", "en": "No query has been run or no data found."},
    "SKU 數": {"vi": "Số SKU", "en": "SKU Count"},
    "現存量合計": {"vi": "Tổng tồn kho hiện tại", "en": "Total On-hand Qty"},
    "庫存金額合計": {"vi": "Tổng giá trị tồn kho", "en": "Total Inventory Value"},
    "下載 CSV": {"vi": "Tải xuống CSV", "en": "Download CSV"},
    "DB 連線失敗：get_connection() 回傳 None": {"vi": "Kết nối DB thất bại: get_connection() trả về None", "en": "DB connection failed: get_connection() returned None"},
    "客戶料號": {"vi": "Mã hàng khách", "en": "Customer Part No."},
    "品名": {"vi": "Tên hàng", "en": "Product Name"},
    "單位": {"vi": "Đơn vị", "en": "Unit"},
    "單價": {"vi": "Đơn giá", "en": "Unit Price"},
    "入庫量": {"vi": "Số lượng nhập kho", "en": "Stock In Qty"},
    "出庫量": {"vi": "Số lượng xuất kho", "en": "Stock Out Qty"},
    "調整量": {"vi": "Số lượng điều chỉnh", "en": "Adjustment Qty"},
    "現存量": {"vi": "Tồn kho hiện tại", "en": "On-hand Qty"},
    "最後異動時間": {"vi": "Thời gian cập nhật cuối", "en": "Last Movement Time"},
    "庫存金額": {"vi": "Giá trị tồn kho", "en": "Inventory Value"},
}

def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    if lang not in {"zh", "vi", "en"}:
        lang = "zh"
    return lang

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)

PAGE_KEY = "S04_product_inventory_summary"
auth.require_read(PAGE_KEY)

TABLE_PRODUCT = "product"
TABLE_CUSTOMER = "customer"
TABLE_STOCK_IO_HEAD = "product_stock_io_head"
TABLE_STOCK_IO_LINE = "product_stock_io_line"


def fetch_df(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        raise RuntimeError(_t("DB 連線失敗：get_connection() 回傳 None"))
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()

@st.cache_data(ttl=3600, show_spinner=False)
def has_column(table: str, column: str) -> bool:
    """檢查資料表是否存在指定欄位。用於不同環境 schema 不一致時的相容處理。"""
    sql = f"SHOW COLUMNS FROM `{table}` LIKE '{column}'"
    try:
        df = fetch_df(sql)
        return not df.empty
    except Exception:
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def stock_io_time_column() -> Optional[str]:
    """product_stock_io_head 的時間欄位：優先 io_time，否則退回 created_at / updated_at。"""
    for col in ("io_time", "created_at", "updated_at"):
        if has_column(TABLE_STOCK_IO_HEAD, col):
            return col
    return None


@st.cache_data(show_spinner=False)
def get_customer_options() -> Dict[str, int]:
    """label -> customer_id"""
    sql = f"""
        SELECT customer_id,
               COALESCE(customer_shortname, '') AS customer_shortname,
               COALESCE(customer_name, '') AS customer_name
        FROM `{TABLE_CUSTOMER}`
        ORDER BY customer_shortname, customer_name, customer_id
    """
    df = fetch_df(sql)
    options: Dict[str, int] = {}
    for _, r in df.iterrows():
        cid = int(r["customer_id"])
        shortname = str(r.get("customer_shortname") or "").strip()
        name = str(r.get("customer_name") or "").strip()
        label = "｜".join([x for x in [shortname, name] if x]) or f"Customer#{cid}"
        options[label] = cid
    return options


def query_product_stock_summary(
    as_of: datetime.date,
    customer_id: Optional[int],
    keyword: str,
    only_in_stock: bool,
) -> pd.DataFrame:
    as_of_end = datetime.datetime.combine(as_of, datetime.time(23, 59, 59))

    where = ["p.is_active = 1"]
    params: Dict[str, Any] = {"as_of_end": as_of_end}

    time_col = stock_io_time_column()
    time_expr = f"h.{time_col}" if time_col else "NULL"
    join_time_cond = f"AND h.{time_col} <= %(as_of_end)s" if time_col else ""

    if customer_id is not None:
        where.append("p.customer_id = %(customer_id)s")
        params["customer_id"] = int(customer_id)

    kw = (keyword or "").strip()
    if kw:
        where.append(
            "(p.product_code LIKE %(kw)s OR p.product_name LIKE %(kw)s OR p.customer_production_id LIKE %(kw)s)"
        )
        params["kw"] = f"%{kw}%"

    where_sql = " AND ".join(where) if where else "1=1"

    sql = f"""
        SELECT
            c.customer_shortname        AS 客戶,
            p.product_code              AS 產品代碼,
            p.customer_production_id    AS 客戶料號,
            p.product_name              AS 品名,
            p.unit                      AS 單位,
            CAST(p.unit_price AS DECIMAL(18,2)) AS 單價,

            COALESCE(SUM(CASE WHEN h.io_type = 'IN'     THEN l.qty_PCS ELSE 0 END), 0) AS 入庫量,
            COALESCE(SUM(CASE WHEN h.io_type = 'OUT'    THEN l.qty_PCS ELSE 0 END), 0) AS 出庫量,
            COALESCE(SUM(CASE WHEN h.io_type = 'ADJUST' THEN l.qty_PCS ELSE 0 END), 0) AS 調整量,

            COALESCE(SUM(
                CASE
                    WHEN h.io_type = 'IN'     THEN  l.qty_PCS
                    WHEN h.io_type = 'OUT'    THEN -l.qty_PCS
                    WHEN h.io_type = 'ADJUST' THEN  l.qty_PCS
                    ELSE 0
                END
            ), 0) AS 現存量,

            MAX({time_expr}) AS 最後異動時間
        FROM `{TABLE_PRODUCT}` p
        LEFT JOIN `{TABLE_CUSTOMER}` c
               ON p.customer_id = c.customer_id
        LEFT JOIN `{TABLE_STOCK_IO_LINE}` l
               ON l.item_id = p.product_id
        LEFT JOIN `{TABLE_STOCK_IO_HEAD}` h
               ON h.psioh_id = l.psioh_id
              AND COALESCE(h.status, 'posted') = 'posted'
              {join_time_cond}
        WHERE {where_sql}
        GROUP BY
            c.customer_shortname,
            p.product_code,
            p.customer_production_id,
            p.product_name,
            p.unit,
            p.unit_price
        ORDER BY
            c.customer_shortname,
            p.product_code
    """

    df = fetch_df(sql, params)

    if only_in_stock and not df.empty:
        df = df[df["現存量"].astype(float).abs() > 1e-9]

    if not df.empty:
        df["單價"] = df["單價"].fillna(0).astype(float)
        df["現存量"] = df["現存量"].fillna(0).astype(float)
        df["庫存金額"] = (df["單價"] * df["現存量"]).round(2)
        df["最後異動時間"] = pd.to_datetime(df["最後異動時間"], errors="coerce")

        lang = get_lang()
        if lang != "zh":
            rename_map = {k: _t(k) for k in [
                "客戶", "產品代碼", "客戶料號", "品名", "單位", "單價",
                "入庫量", "出庫量", "調整量", "現存量", "最後異動時間", "庫存金額"
            ]}
            df = df.rename(columns=rename_map)

    return df


st.header(_t("S04 產品庫存統計"))

st.markdown(
    """
    <style>
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #F3F9FF;
        color: #1F2937;
        border: 1px solid #B7D6F5;
        box-shadow: none;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #F3F9FF;
        color: #1F2937;
        filter: brightness(0.98);
        border: 1px solid #B7D6F5;
        box-shadow: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.expander(_t("查詢條件"), expanded=True):
    c1, c2, c3, c4 = st.columns([1.2, 2.2, 1.6, 1.2])

    with c1:
        as_of = st.date_input(_t("截至日期"), value=datetime.date.today(), key="s04_asof")

    with c2:
        customer_options = get_customer_options()
        customer_label = st.selectbox(_t("客戶"), [_t("全部")] + list(customer_options.keys()), key="s04_cust")
        customer_id = None if customer_label == _t("全部") else int(customer_options[customer_label])

    with c3:
        keyword = st.text_input(_t("關鍵字（產品代碼 / 品名 / 客戶料號）"), value="", key="s04_kw")

    with c4:
        only_in_stock = st.checkbox(_t("只顯示有庫存"), value=True, key="s04_only")

    _, btn_col = st.columns([0.84, 0.16])
    with btn_col:
        run = st.button(_t("查詢 / 更新"), type="primary", use_container_width=True, key="s04_run")


df = pd.DataFrame()
if run:
    try:
        df = query_product_stock_summary(as_of, customer_id, keyword, only_in_stock)
    except Exception as e:
        st.error(f"{_t('查詢失敗：')}{e}")


if df.empty:
    st.info(_t("尚未查詢或查無資料。"))
else:
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric(_t("SKU 數"), int(df.shape[0]))
    with k2:
        current_qty_col = _t("現存量") if _t("現存量") in df.columns else "現存量"
        st.metric(_t("現存量合計"), float(df[current_qty_col].sum()))
    with k3:
        inv_amt_col = _t("庫存金額") if _t("庫存金額") in df.columns else "庫存金額"
        st.metric(_t("庫存金額合計"), float(df[inv_amt_col].sum()) if inv_amt_col in df.columns else 0.0)

    st.dataframe(df, use_container_width=True, hide_index=True, height=220)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        _t("下載 CSV"),
        data=csv,
        file_name=f"product_stock_summary_{as_of.strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
