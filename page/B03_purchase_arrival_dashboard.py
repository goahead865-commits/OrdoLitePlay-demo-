# -*- coding: utf-8 -*-
"""
B03 | 採購到貨總覽
Purchase Arrival Dashboard

設計目的：
- 不新增 SQL table
- 從既有採購單(order_head/order_item)與入庫紀錄(material_stock_io_head/material_stock_io_line)即時計算
- 主表看整張採購單到貨進度，子表看該張採購單的品項到貨狀況

建議放置位置：
    page/B03_purchase_arrival_dashboard.py

注意：
    若你的專案已有固定 DB 連線函式，請優先在 get_db_connection() 裡改成呼叫你現有的連線函式。
"""

from __future__ import annotations

from compact_layout import apply_compact_layout
from splitter_component import apply_vertical_splitter

apply_compact_layout()

import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import auth

try:
    import mysql.connector
except Exception:  # pragma: no cover
    mysql = None

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

# -----------------------------------------------------------------------------
# i18n fallback + B03 local translations
# -----------------------------------------------------------------------------
B03_LOCAL_TRANSLATIONS = {
    "B03｜採購到貨總覽": {"en": "B03 | Purchase Arrival Dashboard", "vi": "B03 | Tổng quan hàng mua đã về"},
    "Purchase Arrival Dashboard": {"en": "Purchase Arrival Dashboard", "vi": "Bảng tổng quan hàng mua đã về"},
    "查看每張採購單的到貨、未到貨、部分到貨與逾期狀況。": {"en": "View arrived, pending, partial and overdue status for each purchase order.", "vi": "Xem tình trạng đã về, chưa về, về một phần và quá hạn của từng đơn mua hàng."},
    "未到貨採購單": {"en": "Pending Purchase Orders", "vi": "Đơn mua chưa về"},
    "部分到貨": {"en": "Partially Arrived", "vi": "Về một phần"},
    "已到齊": {"en": "Fully Arrived", "vi": "Đã về đủ"},
    "逾期待到貨": {"en": "Overdue Pending", "vi": "Quá hạn chưa về"},
    "今日到貨": {"en": "Arrived Today", "vi": "Hàng về hôm nay"},
    "張": {"en": "orders", "vi": "đơn"},
    "篩選條件": {"en": "Filters", "vi": "Điều kiện lọc"},
    "供應商": {"en": "Supplier", "vi": "Nhà cung cấp"},
    "採購單號": {"en": "PO No.", "vi": "Số đơn mua"},
    "訂單號": {"en": "Order No.", "vi": "Số đơn"},
    "原料種類": {"en": "Material Category", "vi": "Loại vật tư"},
    "品名 / 料號": {"en": "Material Name / Code", "vi": "Tên vật tư / Mã vật tư"},
    "採購日期": {"en": "Purchase Date", "vi": "Ngày mua"},
    "預計到貨日": {"en": "Expected Arrival Date", "vi": "Ngày dự kiến về"},
    "到貨狀態": {"en": "Arrival Status", "vi": "Trạng thái hàng về"},
    "只顯示未完成": {"en": "Show unfinished only", "vi": "Chỉ hiện chưa hoàn tất"},
    "全部": {"en": "All", "vi": "Tất cả"},
    "未到貨": {"en": "Not Arrived", "vi": "Chưa về"},
    "逾期": {"en": "Overdue", "vi": "Quá hạn"},
    "採購單到貨狀況表": {"en": "Purchase Order Arrival Status", "vi": "Tình trạng hàng về theo đơn mua"},
    "勾選": {"en": "Select", "vi": "Chọn"},
    "採購數量總計": {"en": "Total Ordered Qty", "vi": "Tổng SL đặt"},
    "已到貨數量總計": {"en": "Total Arrived Qty", "vi": "Tổng SL đã về"},
    "未到貨數量總計": {"en": "Total Pending Qty", "vi": "Tổng SL chưa về"},
    "到貨率": {"en": "Arrival Rate", "vi": "Tỷ lệ hàng về"},
    "狀態": {"en": "Status", "vi": "Trạng thái"},
    "最後入庫日": {"en": "Last Inbound Date", "vi": "Ngày nhập cuối"},
    "採購單明細到貨狀況": {"en": "Purchase Order Item Arrival Details", "vi": "Chi tiết hàng về của đơn mua"},
    "請在上方主表勾選一張採購單查看明細。": {"en": "Select one purchase order in the main table above to view item details.", "vi": "Chọn một đơn mua ở bảng trên để xem chi tiết."},
    "你勾選了多張採購單，系統先顯示第一張。": {"en": "Multiple purchase orders are selected; showing the first one.", "vi": "Bạn đã chọn nhiều đơn; hệ thống hiển thị đơn đầu tiên."},
    "所選採購單查無明細。": {"en": "No item details found for the selected purchase order.", "vi": "Không tìm thấy chi tiết cho đơn đã chọn."},
    "查無符合條件的採購到貨資料。": {"en": "No purchase arrival records match the filters.", "vi": "Không có dữ liệu hàng mua phù hợp."},
    "匯出 Excel": {"en": "Export Excel", "vi": "Xuất Excel"},
    "資料庫連線或基礎資料讀取失敗：": {"en": "Database connection or master data loading failed: ", "vi": "Kết nối CSDL hoặc tải dữ liệu nền thất bại: "},
    "B03 查詢失敗：": {"en": "B03 query failed: ", "vi": "Truy vấn B03 thất bại: "},
    "Excel 匯出暫時不可用：": {"en": "Excel export is temporarily unavailable: ", "vi": "Tạm thời không thể xuất Excel: "},
    "請輸入品名或料號": {"en": "Enter material name or code", "vi": "Nhập tên vật tư hoặc mã vật tư"},
    "例如：260426001": {"en": "Example: 260426001", "vi": "Ví dụ: 260426001"},
    "料號": {"en": "Material Code", "vi": "Mã vật tư"},
    "品名": {"en": "Material Name", "vi": "Tên vật tư"},
    "規格": {"en": "Spec", "vi": "Quy cách"},
    "採購數量": {"en": "Ordered Qty", "vi": "SL đặt"},
    "已到貨數量": {"en": "Arrived Qty", "vi": "SL đã về"},
    "未到貨數量": {"en": "Pending Qty", "vi": "SL chưa về"},
}

try:
    from core.i18n import tr, get_language  # type: ignore
except Exception:  # pragma: no cover
    tr = None  # type: ignore

    def get_language() -> str:  # type: ignore
        return str(st.session_state.get("language", "zh"))


def _b03_lang_key() -> str:
    try:
        lang = str(get_language()).lower()
    except Exception:
        lang = str(st.session_state.get("language", "zh")).lower()

    if lang.startswith("en"):
        return "en"
    if lang.startswith("vi") or lang.startswith("vn"):
        return "vi"
    return "zh"


def _t(text: str) -> str:
    if tr is not None:
        try:
            value = tr(text)
            if value and value != text and not str(value).startswith("[MISS:"):
                return value
        except TypeError:
            try:
                value = tr(text, get_language())
                if value and value != text and not str(value).startswith("[MISS:"):
                    return value
            except Exception:
                pass
        except Exception:
            pass

    return B03_LOCAL_TRANSLATIONS.get(text, {}).get(_b03_lang_key(), text)


def _status_display(status: str, with_icon: bool = True) -> str:
    icon_map = {"未到貨": "⚪", "部分到貨": "🟠", "已到齊": "🟢", "逾期": "🔴"}
    label = _t(status)
    return f"{icon_map.get(status, '')} {label}".strip() if with_icon else label


def _all_label() -> str:
    return _t("全部")


# -----------------------------------------------------------------------------
# Page config / style
# -----------------------------------------------------------------------------
st.set_page_config(page_title=_t("B03｜採購到貨總覽"), layout="wide")

PAGE_KEY = "B03_purchase_arrival_dashboard"
auth.require_read(PAGE_KEY)

st.markdown(
    """
<style>
    .block-container { padding-top: 0 !important; padding-bottom: 0.65rem; }
    .b03-title { font-size: 2.1rem; font-weight: 800; color: #0f172a; margin-bottom: .15rem; }
    .b03-subtitle { font-size: 1.0rem; color: #475569; margin-bottom: .2rem; }
    .b03-helper { font-size: .95rem; color: #64748b; margin-bottom: 1.0rem; }
    div[data-testid="stMetricValue"] { font-weight: 850; }
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------
def _load_env() -> None:
    """Load .env from common project locations."""
    if load_dotenv is None:
        return

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            load_dotenv(env_path)
            break


def get_db_connection():
    """
    取得 MySQL 連線。

    如果你的專案已經有 core/db.py 或 db.py，可在這裡改成：
        from core.db import get_connection
        return get_connection()
    """
    _load_env()

    if mysql is None:
        raise RuntimeError("找不到 mysql-connector-python，請先安裝：pip install mysql-connector-python")

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ordotest"),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        autocommit=True,
    )


def fetch_df(sql: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
    conn = None
    try:
        conn = get_db_connection()
        return pd.read_sql(sql, conn, params=params or [])
    finally:
        if conn is not None:
            conn.close()


@st.cache_data(ttl=60)
def load_suppliers() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT supplier_id, supplier_code, supplier_shortname, supplier_name
        FROM supplier
        WHERE is_active = 1
        ORDER BY supplier_shortname, supplier_code
        """
    )


@st.cache_data(ttl=60)
def load_material_categories() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT material_category_id, material_name
        FROM material_categories
        ORDER BY material_category_id
        """
    )


# -----------------------------------------------------------------------------
# Query logic
# -----------------------------------------------------------------------------
def build_where(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    where = ["BINARY oh.order_type = BINARY 'PO'"]
    params: List[Any] = []

    if filters.get("supplier_id"):
        where.append("oh.supplier_id = %s")
        params.append(filters["supplier_id"])

    if filters.get("order_num"):
        where.append("oh.order_num LIKE %s")
        params.append(f"%{filters['order_num']}%")

    if filters.get("material_category_id"):
        where.append("m.material_category = %s")
        params.append(filters["material_category_id"])

    if filters.get("material_name"):
        where.append("(oi.material_name LIKE %s OR oi.material_code LIKE %s)")
        kw = f"%{filters['material_name']}%"
        params.extend([kw, kw])

    if filters.get("order_date_start"):
        where.append("oh.order_date >= %s")
        params.append(filters["order_date_start"])

    if filters.get("order_date_end"):
        where.append("oh.order_date <= %s")
        params.append(filters["order_date_end"])

    if filters.get("due_date_start"):
        where.append("oh.due_date >= %s")
        params.append(filters["due_date_start"])

    if filters.get("due_date_end"):
        where.append("oh.due_date <= %s")
        params.append(filters["due_date_end"])

    return " AND ".join(where), params


def load_purchase_arrival_lines(filters: Dict[str, Any]) -> pd.DataFrame:
    where_sql, params = build_where(filters)

    # received_qty：
    # - PCS：優先用 qty_pcs
    # - kg：qty_base 通常是 g，所以轉 kg；若沒有 qty_base，退回 qty_raw
    sql = f"""
    WITH receipt AS (
        SELECT
            h.order_id,
            l.item_id,
            SUM(
                CASE
                    WHEN BINARY COALESCE(m.TrackingMod, oi.unit) = BINARY 'PCS'
                        THEN COALESCE(l.qty_pcs, l.qty_raw, 0)
                    WHEN BINARY oi.unit = BINARY 'kg'
                        THEN COALESCE(l.qty_base / 1000, l.qty_raw, 0)
                    ELSE COALESCE(l.qty_base, l.qty_raw, l.qty_pcs, 0)
                END
            ) AS received_qty,
            MAX(DATE(h.io_time)) AS last_in_date,
            COUNT(*) AS receipt_line_count
        FROM material_stock_io_head h
        JOIN material_stock_io_line l ON l.msioh_id = h.msioh_id
        LEFT JOIN order_item oi ON oi.order_id = h.order_id AND oi.material_id = l.item_id
        LEFT JOIN material m ON m.item_id = l.item_id
        WHERE BINARY h.io_type = BINARY 'IN'
          AND BINARY h.status = BINARY 'posted'
          AND h.order_id IS NOT NULL
        GROUP BY h.order_id, l.item_id
    )
    SELECT
        oh.order_id,
        oi.order_item_id,
        oi.material_id,
        oh.order_num,
        oh.order_date,
        oh.due_date,
        oh.supplier_id,
        COALESCE(CONVERT(s.supplier_shortname USING utf8mb4) COLLATE utf8mb4_unicode_ci, oh.supplier_name) AS supplier_display,
        oi.material_code,
        oi.material_name,
        COALESCE(oi.spec, CONVERT(m.specification USING utf8mb4) COLLATE utf8mb4_unicode_ci, '') AS spec,
        oi.unit,
        oi.qty_ordered,
        COALESCE(r.received_qty, 0) AS received_qty,
        GREATEST(oi.qty_ordered - COALESCE(r.received_qty, 0), 0) AS remaining_qty,
        CASE
            WHEN oi.qty_ordered <= 0 THEN 0
            ELSE ROUND(COALESCE(r.received_qty, 0) / oi.qty_ordered * 100, 1)
        END AS arrival_rate,
        r.last_in_date,
        CASE
            WHEN COALESCE(r.received_qty, 0) >= oi.qty_ordered THEN '已到齊'
            WHEN oh.due_date < CURDATE() AND COALESCE(r.received_qty, 0) < oi.qty_ordered THEN '逾期'
            WHEN COALESCE(r.received_qty, 0) > 0 THEN '部分到貨'
            ELSE '未到貨'
        END AS arrival_status
    FROM order_head oh
    JOIN order_item oi ON oi.order_id = oh.order_id
    LEFT JOIN material m ON m.item_id = oi.material_id
    LEFT JOIN supplier s ON s.supplier_id = oh.supplier_id
    LEFT JOIN receipt r ON r.order_id = oh.order_id AND r.item_id = oi.material_id
    WHERE {where_sql}
    ORDER BY
        CASE
            WHEN oh.due_date < CURDATE() AND COALESCE(r.received_qty, 0) < oi.qty_ordered THEN 1
            WHEN COALESCE(r.received_qty, 0) = 0 THEN 2
            WHEN COALESCE(r.received_qty, 0) < oi.qty_ordered THEN 3
            ELSE 4
        END,
        oh.due_date ASC,
        oh.order_num DESC,
        oi.line_no ASC
    """

    df = fetch_df(sql, params)
    if df.empty:
        return df

    for col in ["qty_ordered", "received_qty", "remaining_qty", "arrival_rate"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df.reset_index(drop=True)


def build_purchase_summary_df(line_df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if line_df.empty:
        return pd.DataFrame()

    work = line_df.copy()
    work["order_date"] = pd.to_datetime(work["order_date"], errors="coerce")
    work["due_date"] = pd.to_datetime(work["due_date"], errors="coerce")
    work["last_in_date"] = pd.to_datetime(work["last_in_date"], errors="coerce")

    grouped = (
        work.groupby(
            [
                "order_id",
                "order_num",
                "supplier_display",
                "order_date",
                "due_date",
            ],
            dropna=False,
        )
        .agg(
            ordered_total=("qty_ordered", "sum"),
            received_total=("received_qty", "sum"),
            remaining_total=("remaining_qty", "sum"),
            last_in_date=("last_in_date", "max"),
        )
        .reset_index()
    )

    grouped["arrival_rate"] = grouped.apply(
        lambda r: 0 if float(r["ordered_total"] or 0) <= 0 else round(float(r["received_total"] or 0) / float(r["ordered_total"] or 0) * 100, 1),
        axis=1,
    )

    today = pd.Timestamp.today().normalize()

    def calc_status(row: pd.Series) -> str:
        ordered = float(row.get("ordered_total") or 0)
        received = float(row.get("received_total") or 0)
        remaining = float(row.get("remaining_total") or 0)
        due = row.get("due_date")
        if ordered > 0 and remaining <= 0:
            return "已到齊"
        if pd.notna(due) and due < today and remaining > 0:
            return "逾期"
        if received > 0 and remaining > 0:
            return "部分到貨"
        return "未到貨"

    grouped["arrival_status"] = grouped.apply(calc_status, axis=1)

    status_filter = filters.get("status_filter")
    if status_filter and status_filter != "全部":
        grouped = grouped[grouped["arrival_status"] == status_filter].copy()

    if filters.get("only_unfinished"):
        grouped = grouped[grouped["arrival_status"].isin(["未到貨", "部分到貨", "逾期"])].copy()

    status_rank = {"逾期": 1, "未到貨": 2, "部分到貨": 3, "已到齊": 4}
    grouped["_status_rank"] = grouped["arrival_status"].map(status_rank).fillna(9)
    grouped = grouped.sort_values(["_status_rank", "due_date", "order_num"], ascending=[True, True, False])
    return grouped.drop(columns=["_status_rank"]).reset_index(drop=True)


# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------
def fmt_num(value: Any) -> str:
    try:
        n = float(value)
        if abs(n - int(n)) < 0.000001:
            return f"{int(n):,}"
        return f"{n:,.2f}"
    except Exception:
        return ""


def make_excel_bytes(order_df: pd.DataFrame, item_df: Optional[pd.DataFrame] = None) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        order_df.to_excel(writer, index=False, sheet_name="B03_採購單到貨總覽")
        if item_df is not None and not item_df.empty:
            item_df.to_excel(writer, index=False, sheet_name="採購單明細到貨狀況")
    return output.getvalue()


def status_badge_text(status: str) -> str:
    return _status_display(status, with_icon=True)


def render_kpi_cards(order_df: pd.DataFrame) -> None:
    if order_df.empty:
        counts = {"未到貨": 0, "部分到貨": 0, "已到齊": 0, "逾期": 0}
        today_count = 0
    else:
        counts = order_df["arrival_status"].value_counts().to_dict()
        today = pd.Timestamp.today().date()
        today_count = int(
            order_df[pd.to_datetime(order_df["last_in_date"], errors="coerce").dt.date == today]["order_id"].nunique()
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📋 " + _t("未到貨採購單"), int(counts.get("未到貨", 0)), _t("張"))
    with c2:
        st.metric("🟠 " + _t("部分到貨"), int(counts.get("部分到貨", 0)), _t("張"))
    with c3:
        st.metric("✅ " + _t("已到齊"), int(counts.get("已到齊", 0)), _t("張"))
    with c4:
        st.metric("⏰ " + _t("逾期待到貨"), int(counts.get("逾期", 0)), _t("張"))
    with c5:
        st.metric("🚚 " + _t("今日到貨"), today_count, _t("張"))


def prepare_main_display_df(order_df: pd.DataFrame) -> pd.DataFrame:
    if order_df.empty:
        return pd.DataFrame()

    show = order_df.copy()
    show[_t("勾選")] = False
    show["_display_status"] = show["arrival_status"].apply(status_badge_text)
    show["_arrival_rate_display"] = show["arrival_rate"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "0%")
    show["_ordered_total_display"] = show["ordered_total"].map(fmt_num)
    show["_received_total_display"] = show["received_total"].map(fmt_num)
    show["_remaining_total_display"] = show["remaining_total"].map(fmt_num)

    display = show[
        [
            _t("勾選"),
            "order_id",
            "order_num",
            "supplier_display",
            "_ordered_total_display",
            "_received_total_display",
            "_remaining_total_display",
            "_arrival_rate_display",
            "order_date",
            "due_date",
            "_display_status",
            "last_in_date",
        ]
    ].rename(
        columns={
            "order_num": _t("採購單號"),
            "supplier_display": _t("供應商"),
            "_ordered_total_display": _t("採購數量總計"),
            "_received_total_display": _t("已到貨數量總計"),
            "_remaining_total_display": _t("未到貨數量總計"),
            "_arrival_rate_display": _t("到貨率"),
            "order_date": _t("採購日期"),
            "due_date": _t("預計到貨日"),
            "_display_status": _t("狀態"),
            "last_in_date": _t("最後入庫日"),
        }
    )
    return display


def prepare_item_display_df(line_df: pd.DataFrame, order_id: int) -> pd.DataFrame:
    if line_df.empty:
        return pd.DataFrame()

    show = line_df[line_df["order_id"] == order_id].copy()
    if show.empty:
        return pd.DataFrame()

    show["_display_status"] = show["arrival_status"].apply(status_badge_text)
    show["_arrival_rate_display"] = show["arrival_rate"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "0%")
    show["_qty_ordered_display"] = show["qty_ordered"].map(fmt_num) + " " + show["unit"].astype(str)
    show["_received_qty_display"] = show["received_qty"].map(fmt_num) + " " + show["unit"].astype(str)
    show["_remaining_qty_display"] = show["remaining_qty"].map(fmt_num) + " " + show["unit"].astype(str)

    return show[
        [
            "material_code",
            "material_name",
            "spec",
            "_qty_ordered_display",
            "_received_qty_display",
            "_remaining_qty_display",
            "_arrival_rate_display",
            "_display_status",
            "last_in_date",
        ]
    ].rename(
        columns={
            "material_code": _t("料號"),
            "material_name": _t("品名"),
            "spec": _t("規格"),
            "_qty_ordered_display": _t("採購數量"),
            "_received_qty_display": _t("已到貨數量"),
            "_remaining_qty_display": _t("未到貨數量"),
            "_arrival_rate_display": _t("到貨率"),
            "_display_status": _t("狀態"),
            "last_in_date": _t("最後入庫日"),
        }
    )


# -----------------------------------------------------------------------------
# Main page
# -----------------------------------------------------------------------------
st.markdown(f'<div class="b03-title">{_t("B03｜採購到貨總覽")}</div>', unsafe_allow_html=True)
st.session_state.setdefault("b03_top_height", 250)
st.markdown("""<style>[data-testid="stTextInput"] input { min-height:1.55rem!important; padding-top:.1rem!important; padding-bottom:.1rem!important; } [data-testid="stTextInput"], [data-testid="stSelectbox"], [data-testid="stDateInput"] { margin-bottom:0!important; } hr { margin:.25rem 0!important; }</style>""", unsafe_allow_html=True)
st.markdown(f'<div class="b03-subtitle">{_t("Purchase Arrival Dashboard")}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="b03-helper">{_t("查看每張採購單的到貨、未到貨、部分到貨與逾期狀況。")}</div>',
    unsafe_allow_html=True,
)

try:
    suppliers_df = load_suppliers()
    categories_df = load_material_categories()
except Exception as e:
    st.error(_t("資料庫連線或基礎資料讀取失敗：") + str(e))
    st.stop()

# ---------------- Filters ----------------
with st.container(border=True):
    st.subheader("🔎 " + _t("篩選條件"))

    supplier_options = {_all_label(): None}
    for _, row in suppliers_df.iterrows():
        label = f"{row['supplier_shortname']}（{row['supplier_code']}）"
        supplier_options[label] = int(row["supplier_id"])

    category_options = {_all_label(): None}
    for _, row in categories_df.iterrows():
        category_options[str(row["material_name"])] = int(row["material_category_id"])

    r1c1, r1c2, r1c3, r1c4 = st.columns([1.2, 1.2, 1.2, 1.5])
    with r1c1:
        supplier_label = st.selectbox(_t("供應商"), list(supplier_options.keys()))
    with r1c2:
        order_num = st.text_input(_t("採購單號"), placeholder=_t("例如：260426001"))
    with r1c3:
        category_label = st.selectbox(_t("原料種類"), list(category_options.keys()))
    with r1c4:
        material_name = st.text_input(_t("品名 / 料號"), placeholder=_t("請輸入品名或料號"))

    r2c1, r2c2, r2c3, r2c4 = st.columns([1.5, 1.5, 1.5, 1.1])
    with r2c1:
        order_date_range = st.date_input(_t("採購日期"), value=(), format="YYYY-MM-DD")
    with r2c2:
        due_date_range = st.date_input(_t("預計到貨日"), value=(), format="YYYY-MM-DD")
    with r2c3:
        status_label_map = {
            _all_label(): "全部",
            _t("未到貨"): "未到貨",
            _t("部分到貨"): "部分到貨",
            _t("已到齊"): "已到齊",
            _t("逾期"): "逾期",
        }
        status_label = st.selectbox(_t("到貨狀態"), list(status_label_map.keys()))
        status_filter = status_label_map[status_label]
    with r2c4:
        only_unfinished = st.toggle(_t("只顯示未完成"), value=True)


def parse_range(v: Any) -> Tuple[Optional[Any], Optional[Any]]:
    if isinstance(v, tuple) and len(v) == 2:
        return v[0], v[1]
    if isinstance(v, list) and len(v) == 2:
        return v[0], v[1]
    return None, None


order_date_start, order_date_end = parse_range(order_date_range)
due_date_start, due_date_end = parse_range(due_date_range)

filters = {
    "supplier_id": supplier_options[supplier_label],
    "order_num": order_num.strip(),
    "material_category_id": category_options[category_label],
    "material_name": material_name.strip(),
    "order_date_start": order_date_start,
    "order_date_end": order_date_end,
    "due_date_start": due_date_start,
    "due_date_end": due_date_end,
    "status_filter": status_filter,
    "only_unfinished": only_unfinished,
}

try:
    line_df = load_purchase_arrival_lines(filters)
except Exception as e:
    st.error(_t("B03 查詢失敗：") + str(e))
    st.stop()

order_summary_df = build_purchase_summary_df(line_df, filters)
render_kpi_cards(order_summary_df)

# ---------------- Main table ----------------
st.markdown("### 📋 " + _t("採購單到貨狀況表"))

if order_summary_df.empty:
    st.info(_t("查無符合條件的採購到貨資料。"))
    st.stop()

main_show_df = prepare_main_display_df(order_summary_df)

edited_main_df = st.data_editor(
    main_show_df.drop(columns=["order_id"]),
    use_container_width=True,
    height=int(st.session_state["b03_top_height"]),
    hide_index=True,
    disabled=[c for c in main_show_df.columns if c not in [_t("勾選")]],
    column_config={
        _t("勾選"): st.column_config.CheckboxColumn(
            _t("勾選"),
            help=_t("請在上方主表勾選一張採購單查看明細。"),
            default=False,
        ),
    },
    key="b03_main_order_selector",
)

selected_positions = edited_main_df.index[edited_main_df[_t("勾選")] == True].tolist()
selected_order_id: Optional[int] = None
if selected_positions:
    if len(selected_positions) > 1:
        st.warning(_t("你勾選了多張採購單，系統先顯示第一張。"))
    selected_order_id = int(main_show_df.iloc[selected_positions[0]]["order_id"])

apply_vertical_splitter("b03_top_height", "b03_vertical_splitter_control", default=250, min_top=150, max_top=430)

# ---------------- Child table ----------------
st.markdown("### 📦 " + _t("採購單明細到貨狀況"))

if selected_order_id is None:
    st.info(_t("請在上方主表勾選一張採購單查看明細。"))
    item_show_df = pd.DataFrame()
else:
    item_show_df = prepare_item_display_df(line_df, selected_order_id)
    if item_show_df.empty:
        st.warning(_t("所選採購單查無明細。"))
    else:
        st.dataframe(item_show_df, use_container_width=True, hide_index=True, height=180)

# ---------------- Export ----------------
export_df = main_show_df.drop(columns=["order_id", _t("勾選")], errors="ignore").copy()
try:
    export_bytes = make_excel_bytes(export_df, item_show_df if not item_show_df.empty else None)
    st.download_button(
        label="📥 " + _t("匯出 Excel"),
        data=export_bytes,
        file_name="B03_purchase_arrival_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
except Exception as e:
    st.warning(_t("Excel 匯出暫時不可用：") + str(e))
