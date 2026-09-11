# -*- coding: utf-8 -*-
"""
E02 | 客戶訂單完成進度
Customer Order Progress Dashboard

設計目的：
- 不新增 SQL table
- 從既有客戶訂單(customer_order/customer_order_item)與送貨單(delivery_head/delivery_product)即時計算
- 主表看整張客戶訂單完成進度，子表看該張訂單的產品明細完成狀況

建議放置位置：
    page/E02_customer_order_progress_dashboard.py
"""

from __future__ import annotations

from compact_layout import apply_compact_layout

apply_compact_layout()

from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import auth
from db import get_connection

# -----------------------------------------------------------------------------
# i18n fallback + E02 local translations
# -----------------------------------------------------------------------------
E02_TRANSLATIONS = {
    "重新整理": {"en": "Refresh", "vi": "Làm mới"},
    "E02｜客戶訂單完成進度": {"en": "E02 | Customer Order Progress", "vi": "E02 | Tiến độ hoàn thành đơn hàng khách"},
    "Customer Order Progress Dashboard": {"en": "Customer Order Progress Dashboard", "vi": "Bảng tổng quan tiến độ đơn hàng khách"},
    "查看每張客戶訂單的出貨、未出貨、部分完成與逾期狀況。": {"en": "View shipped, pending, partial and overdue status for each customer order.", "vi": "Xem tình trạng đã giao, chưa giao, hoàn thành một phần và quá hạn của từng đơn hàng khách."},
    "未完成訂單": {"en": "Unfinished Orders", "vi": "Đơn chưa hoàn tất"},
    "部分完成": {"en": "Partially Completed", "vi": "Hoàn thành một phần"},
    "已完成": {"en": "Completed", "vi": "Đã hoàn thành"},
    "逾期未完成": {"en": "Overdue Unfinished", "vi": "Quá hạn chưa hoàn tất"},
    "今日出貨": {"en": "Shipped Today", "vi": "Giao hàng hôm nay"},
    "張": {"en": "orders", "vi": "đơn"},
    "篩選條件": {"en": "Filters", "vi": "Điều kiện lọc"},
    "客戶": {"en": "Customer", "vi": "Khách hàng"},
    "客戶訂單號": {"en": "Customer PO No.", "vi": "Số PO khách"},
    "本公司訂單號": {"en": "Our Order No.", "vi": "Số đơn nội bộ"},
    "訂單號": {"en": "Order No.", "vi": "Số đơn"},
    "品名 / 料號": {"en": "Product Name / Code", "vi": "Tên hàng / Mã hàng"},
    "訂單日期": {"en": "Order Date", "vi": "Ngày đặt hàng"},
    "交期": {"en": "Due Date", "vi": "Ngày giao"},
    "完成狀態": {"en": "Progress Status", "vi": "Trạng thái tiến độ"},
    "只顯示未完成": {"en": "Show unfinished only", "vi": "Chỉ hiện chưa hoàn tất"},
    "全部": {"en": "All", "vi": "Tất cả"},
    "未完成": {"en": "Unfinished", "vi": "Chưa hoàn tất"},
    "逾期": {"en": "Overdue", "vi": "Quá hạn"},
    "客戶訂單完成進度表": {"en": "Customer Order Progress", "vi": "Bảng tiến độ đơn hàng khách"},
    "勾選": {"en": "Select", "vi": "Chọn"},
    "訂單數量總計": {"en": "Total Ordered Qty", "vi": "Tổng SL đặt"},
    "已出貨數量總計": {"en": "Total Shipped Qty", "vi": "Tổng SL đã giao"},
    "未出貨數量總計": {"en": "Total Pending Qty", "vi": "Tổng SL chưa giao"},
    "完成率": {"en": "Completion Rate", "vi": "Tỷ lệ hoàn thành"},
    "狀態": {"en": "Status", "vi": "Trạng thái"},
    "最後出貨日": {"en": "Last Shipment Date", "vi": "Ngày giao cuối"},
    "客戶訂單明細": {"en": "Customer Order Items", "vi": "Chi tiết đơn hàng khách"},
    "請在上方主表勾選一張客戶訂單查看明細。": {"en": "Select one customer order in the main table above to view item details.", "vi": "Chọn một đơn hàng khách ở bảng trên để xem chi tiết."},
    "你勾選了多張客戶訂單，系統先顯示第一張。": {"en": "Multiple customer orders are selected; showing the first one.", "vi": "Bạn đã chọn nhiều đơn; hệ thống hiển thị đơn đầu tiên."},
    "所選客戶訂單查無明細。": {"en": "No item details found for the selected customer order.", "vi": "Không tìm thấy chi tiết cho đơn đã chọn."},
    "查無符合條件的客戶訂單資料。": {"en": "No customer order records match the filters.", "vi": "Không có dữ liệu đơn hàng khách phù hợp."},
    "匯出 Excel": {"en": "Export Excel", "vi": "Xuất Excel"},
    "資料庫連線或基礎資料讀取失敗：": {"en": "Database connection or master data loading failed: ", "vi": "Kết nối CSDL hoặc tải dữ liệu nền thất bại: "},
    "E02 查詢失敗：": {"en": "E02 query failed: ", "vi": "Truy vấn E02 thất bại: "},
    "Excel 匯出暫時不可用：": {"en": "Excel export is temporarily unavailable: ", "vi": "Tạm thời không thể xuất Excel: "},
    "請輸入品名或料號": {"en": "Enter product name or code", "vi": "Nhập tên hàng hoặc mã hàng"},
    "例如：CO260426001 / 客戶單號": {"en": "Example: CO260426001 / customer PO", "vi": "Ví dụ: CO260426001 / PO khách"},
    "產品編號": {"en": "Product Code", "vi": "Mã sản phẩm"},
    "客戶料號": {"en": "Customer Product No.", "vi": "Mã hàng khách"},
    "品名": {"en": "Product Name", "vi": "Tên hàng"},
    "規格": {"en": "Spec", "vi": "Quy cách"},
    "訂單數量": {"en": "Ordered Qty", "vi": "SL đặt"},
    "已出貨數量": {"en": "Shipped Qty", "vi": "SL đã giao"},
    "未出貨數量": {"en": "Pending Qty", "vi": "SL chưa giao"},

    "批次交期": {"en": "Batch Due Date", "vi": "Ngày giao theo đợt"},
    "最早未完成交期": {"en": "Earliest Pending Due Date", "vi": "Ngày giao chưa hoàn tất sớm nhất"},
    "批次數": {"en": "Batch Count", "vi": "Số đợt"},
    "逾期批次數": {"en": "Overdue Batch Count", "vi": "Số đợt quá hạn"},
    "客戶訂單批次明細": {"en": "Customer Order Batch Details", "vi": "Chi tiết đợt giao đơn hàng khách"},
    "批次": {"en": "Batch", "vi": "Đợt"},
    "批次數量": {"en": "Batch Qty", "vi": "SL theo đợt"},
    "批次狀態": {"en": "Batch Status", "vi": "Trạng thái đợt"},
    "主交期": {"en": "Main Due Date", "vi": "Ngày giao chính"},
    "無批次時以訂單主交期作為批次交期。": {"en": "When no batch schedule exists, the order's main due date is used as the batch due date.", "vi": "Khi không có lịch giao theo đợt, hệ thống dùng ngày giao chính của đơn hàng làm ngày giao theo đợt."},
}

try:
    from core.i18n import tr, get_language  # type: ignore
except Exception:  # pragma: no cover
    tr = None  # type: ignore

    def get_language() -> str:  # type: ignore
        return str(st.session_state.get("language", "zh"))


def _lang_key() -> str:
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
    return E02_TRANSLATIONS.get(text, {}).get(_lang_key(), text)


def _status_display(status: str, with_icon: bool = True) -> str:
    icon_map = {"未完成": "⚪", "部分完成": "🟠", "已完成": "🟢", "逾期": "🔴"}
    label = _t(status)
    return f"{icon_map.get(status, '')} {label}".strip() if with_icon else label


def _all_label() -> str:
    return _t("全部")


# -----------------------------------------------------------------------------
# Page config / style
# -----------------------------------------------------------------------------
st.set_page_config(page_title=_t("E02｜客戶訂單完成進度"), layout="wide")

PAGE_KEY = "E02_customer_order_progress_dashboard"
auth.require_read(PAGE_KEY)

st.markdown(
    """
<style>
    .block-container { padding-top: 0 !important; padding-bottom: 0.65rem; }
    .e02-title { font-size: 2.1rem; font-weight: 800; color: #0f172a; margin-bottom: .15rem; }
    .e02-subtitle { font-size: 1.0rem; color: #475569; margin-bottom: .2rem; }
    .e02-helper { font-size: .95rem; color: #64748b; margin-bottom: 1.0rem; }
    div[data-testid="stMetricValue"] { font-weight: 850; }
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------
def get_db_connection():
    """Use the same connection settings as E01 for all progress queries."""
    conn = get_connection()
    if conn is None:
        raise RuntimeError("DB 連線失敗")
    return conn


def fetch_df(sql: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
    conn = None
    try:
        conn = get_db_connection()
        return pd.read_sql(sql, conn, params=params or [])
    finally:
        if conn is not None:
            conn.close()


@st.cache_data(ttl=60)
def load_customers() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT customer_id, customer_code, customer_shortname, customer_name
        FROM customer
        WHERE is_active = 1
        ORDER BY customer_shortname, customer_code
        """
    )


# -----------------------------------------------------------------------------
# Query logic
# -----------------------------------------------------------------------------
def build_where(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    where = ["1 = 1"]
    params: List[Any] = []

    if filters.get("customer_id"):
        where.append("co.customer_id = %s")
        params.append(filters["customer_id"])

    if filters.get("order_no"):
        where.append("(co.customer_order_code LIKE %s OR co.customer_order_num LIKE %s)")
        kw = f"%{filters['order_no']}%"
        params.extend([kw, kw])

    if filters.get("product_kw"):
        where.append("(p.product_name LIKE %s OR p.product_code LIKE %s OR p.customer_production_id LIKE %s)")
        kw = f"%{filters['product_kw']}%"
        params.extend([kw, kw, kw])

    if filters.get("order_date_start"):
        where.append("DATE(co.created_at) >= %s")
        params.append(filters["order_date_start"])

    if filters.get("order_date_end"):
        where.append("DATE(co.created_at) <= %s")
        params.append(filters["order_date_end"])

    if filters.get("due_date_start"):
        where.append("COALESCE(s.due_date, coi.deliver_date, co.deliver_date) >= %s")
        params.append(filters["due_date_start"])

    if filters.get("due_date_end"):
        where.append("COALESCE(s.due_date, coi.deliver_date, co.deliver_date) <= %s")
        params.append(filters["due_date_end"])

    return " AND ".join(where), params


def load_customer_order_lines(filters: Dict[str, Any]) -> pd.DataFrame:
    """Load customer order progress at batch-schedule level.

    Primary logic:
    - If customer_order_item_schedule exists for an item, each schedule row is one progress row.
    - If an older order item has no schedule row, the item becomes one fallback batch using
      COALESCE(customer_order_item.deliver_date, customer_order.deliver_date).

    This keeps E02 aligned with E01/D02: progress is driven by batch due dates, not only by
    the order header due date.
    """
    where_sql, params = build_where(filters)

    sql = f"""
    WITH shipped_by_schedule AS (
        SELECT
            dp.schedule_id,
            SUM(COALESCE(dp.qty, 0)) AS shipped_qty,
            MAX(dh.delivery_date) AS last_delivery_date
        FROM delivery_product dp
        JOIN delivery_head dh ON dh.delivery_note_id = dp.delivery_head_id
        WHERE dp.schedule_id IS NOT NULL
          AND dh.status = 'posted'
        GROUP BY dp.schedule_id
    ),
    shipped_by_item AS (
        SELECT
            dh.customer_order_id,
            dp.customer_order_item_id,
            dp.product_id,
            SUM(COALESCE(dp.qty, 0)) AS shipped_qty,
            MAX(dh.delivery_date) AS last_delivery_date
        FROM delivery_head dh
        JOIN delivery_product dp ON dp.delivery_head_id = dh.delivery_note_id
        WHERE dh.customer_order_id IS NOT NULL
          AND dh.status = 'posted'
        GROUP BY dh.customer_order_id, dp.customer_order_item_id, dp.product_id
    )
    SELECT
        co.customer_order_id,
        co.customer_order_code,
        co.customer_order_num,
        DATE(co.created_at) AS order_date,
        co.deliver_date AS order_main_due_date,
        COALESCE(s.due_date, coi.deliver_date, co.deliver_date) AS deliver_date,
        co.order_status,
        c.customer_id,
        COALESCE(c.customer_shortname, c.customer_name) AS customer_display,
        coi.customer_order_item_id,
        coi.line_no,
        coi.product_id,
        p.product_code,
        p.customer_production_id,
        COALESCE(p.product_name, '') AS product_name,
        COALESCE(p.Specification, '') AS spec,
        coi.unit,
        s.schedule_id,
        COALESCE(s.schedule_no, 1) AS schedule_no,
        COALESCE(s.status, 'open') AS schedule_status,
        COALESCE(s.qty, coi.quantity, 0) AS order_qty,
        CASE
            WHEN s.schedule_id IS NOT NULL THEN COALESCE(ss.shipped_qty, 0)
            ELSE COALESCE(si.shipped_qty, 0)
        END AS shipped_qty,
        GREATEST(
            COALESCE(s.qty, coi.quantity, 0) -
            CASE
                WHEN s.schedule_id IS NOT NULL THEN COALESCE(ss.shipped_qty, 0)
                ELSE COALESCE(si.shipped_qty, 0)
            END,
            0
        ) AS remaining_qty,
        CASE
            WHEN COALESCE(s.qty, coi.quantity, 0) <= 0 THEN 0
            ELSE ROUND(
                CASE
                    WHEN s.schedule_id IS NOT NULL THEN COALESCE(ss.shipped_qty, 0)
                    ELSE COALESCE(si.shipped_qty, 0)
                END / COALESCE(s.qty, coi.quantity, 0) * 100,
                1
            )
        END AS completion_rate,
        CASE
            WHEN s.schedule_id IS NOT NULL THEN ss.last_delivery_date
            ELSE si.last_delivery_date
        END AS last_delivery_date
    FROM customer_order co
    JOIN customer_order_item coi ON coi.customer_order_id = co.customer_order_id
    LEFT JOIN customer_order_item_schedule s ON s.customer_order_item_id = coi.customer_order_item_id
    LEFT JOIN product p ON p.product_id = coi.product_id
    LEFT JOIN customer c ON c.customer_id = co.customer_id
    LEFT JOIN shipped_by_schedule ss ON ss.schedule_id = s.schedule_id
    LEFT JOIN shipped_by_item si
      ON si.customer_order_id = co.customer_order_id
     AND (
          (si.customer_order_item_id IS NOT NULL AND si.customer_order_item_id = coi.customer_order_item_id)
          OR (si.customer_order_item_id IS NULL AND si.product_id = coi.product_id)
     )
    WHERE {where_sql}
    ORDER BY COALESCE(s.due_date, coi.deliver_date, co.deliver_date) ASC,
             co.customer_order_code DESC,
             coi.line_no ASC,
             COALESCE(s.schedule_no, 1) ASC
    """

    df = fetch_df(sql, params)
    if df.empty:
        return df

    for col in ["order_qty", "shipped_qty", "remaining_qty", "completion_rate"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    today = pd.Timestamp.today().normalize()
    due = pd.to_datetime(df["deliver_date"], errors="coerce")

    def _row_status(row: pd.Series) -> str:
        ordered = float(row.get("order_qty") or 0)
        shipped = float(row.get("shipped_qty") or 0)
        remaining = float(row.get("remaining_qty") or 0)
        due_value = pd.to_datetime(row.get("deliver_date"), errors="coerce")
        if ordered > 0 and remaining <= 0:
            return "已完成"
        if pd.notna(due_value) and due_value < today and remaining > 0:
            return "逾期"
        if shipped > 0 and remaining > 0:
            return "部分完成"
        return "未完成"

    df["batch_status"] = df.apply(_row_status, axis=1)
    df["is_overdue_batch"] = (due < today) & (df["remaining_qty"] > 0)
    return df.reset_index(drop=True)


def build_order_summary_df(line_df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Build order-level summary from batch-level rows.

    An order is considered overdue if ANY unfinished batch due date has passed.
    The displayed due date is the earliest unfinished batch due date; if all batches
    are completed, it uses the latest batch due date as history.
    """
    if line_df.empty:
        return pd.DataFrame()

    work = line_df.copy()
    work["deliver_date"] = pd.to_datetime(work["deliver_date"], errors="coerce")
    work["last_delivery_date"] = pd.to_datetime(work["last_delivery_date"], errors="coerce")
    work["remaining_qty"] = pd.to_numeric(work["remaining_qty"], errors="coerce").fillna(0)
    work["order_qty"] = pd.to_numeric(work["order_qty"], errors="coerce").fillna(0)
    work["shipped_qty"] = pd.to_numeric(work["shipped_qty"], errors="coerce").fillna(0)

    today = pd.Timestamp.today().normalize()

    def _earliest_pending_due(x: pd.DataFrame):
        pending = x[(x["remaining_qty"] > 0) & (x["deliver_date"].notna())]
        if not pending.empty:
            return pending["deliver_date"].min()
        return x["deliver_date"].max()

    grouped = (
        work.groupby(
            [
                "customer_order_id",
                "customer_order_code",
                "customer_order_num",
                "customer_display",
            ],
            dropna=False,
        )
        .agg(
            ordered_total=("order_qty", "sum"),
            shipped_total=("shipped_qty", "sum"),
            remaining_total=("remaining_qty", "sum"),
            last_delivery_date=("last_delivery_date", "max"),
            batch_count=("deliver_date", "size"),
            overdue_batch_count=("is_overdue_batch", "sum"),
        )
        .reset_index()
    )

    due_df = (
        work.groupby("customer_order_id", dropna=False)
        .apply(_earliest_pending_due)
        .reset_index(name="deliver_date")
    )
    grouped = grouped.merge(due_df, on="customer_order_id", how="left")

    grouped["completion_rate"] = grouped.apply(
        lambda r: 0 if float(r["ordered_total"] or 0) <= 0 else round(float(r["shipped_total"] or 0) / float(r["ordered_total"] or 0) * 100, 1),
        axis=1,
    )

    def calc_status(row: pd.Series) -> str:
        ordered = float(row.get("ordered_total") or 0)
        shipped = float(row.get("shipped_total") or 0)
        remaining = float(row.get("remaining_total") or 0)
        overdue_batches = int(row.get("overdue_batch_count") or 0)
        if ordered > 0 and remaining <= 0:
            return "已完成"
        if overdue_batches > 0:
            return "逾期"
        if shipped > 0 and remaining > 0:
            return "部分完成"
        return "未完成"

    grouped["progress_status"] = grouped.apply(calc_status, axis=1)

    status_filter = filters.get("status_filter")
    if status_filter and status_filter != "全部":
        grouped = grouped[grouped["progress_status"] == status_filter].copy()

    if filters.get("only_unfinished"):
        grouped = grouped[grouped["progress_status"].isin(["未完成", "部分完成", "逾期"])].copy()

    status_rank = {"逾期": 1, "未完成": 2, "部分完成": 3, "已完成": 4}
    grouped["_status_rank"] = grouped["progress_status"].map(status_rank).fillna(9)
    grouped = grouped.sort_values(["_status_rank", "deliver_date", "customer_order_code"], ascending=[True, True, False])
    return grouped.drop(columns=["_status_rank"]).reset_index(drop=True)


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
        order_df.to_excel(writer, index=False, sheet_name="E02_客戶訂單完成進度")
        if item_df is not None and not item_df.empty:
            item_df.to_excel(writer, index=False, sheet_name="客戶訂單明細")
    return output.getvalue()


def status_badge_text(status: str) -> str:
    return _status_display(status, with_icon=True)


def render_kpi_cards(order_df: pd.DataFrame) -> None:
    if order_df.empty:
        counts = {"未完成": 0, "部分完成": 0, "已完成": 0, "逾期": 0}
        today_count = 0
        overdue_batches = 0
    else:
        counts = order_df["progress_status"].value_counts().to_dict()
        today = pd.Timestamp.today().date()
        today_count = int(
            order_df[pd.to_datetime(order_df["last_delivery_date"], errors="coerce").dt.date == today]["customer_order_id"].nunique()
        )
        overdue_batches = int(pd.to_numeric(order_df.get("overdue_batch_count"), errors="coerce").fillna(0).sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📋 " + _t("未完成訂單"), int(counts.get("未完成", 0)), _t("張"))
    with c2:
        st.metric("🟠 " + _t("部分完成"), int(counts.get("部分完成", 0)), _t("張"))
    with c3:
        st.metric("✅ " + _t("已完成"), int(counts.get("已完成", 0)), _t("張"))
    with c4:
        st.metric("⏰ " + _t("逾期未完成"), int(counts.get("逾期", 0)), f"{overdue_batches} {_t('批次')}")
    with c5:
        st.metric("🚚 " + _t("今日出貨"), today_count, _t("張"))


def prepare_main_display_df(order_df: pd.DataFrame) -> pd.DataFrame:
    if order_df.empty:
        return pd.DataFrame()

    show = order_df.copy()
    show[_t("勾選")] = False
    show["_display_status"] = show["progress_status"].apply(status_badge_text)
    show["_completion_rate_display"] = show["completion_rate"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "0%")
    show["_ordered_total_display"] = show["ordered_total"].map(fmt_num)
    show["_remaining_total_display"] = show["remaining_total"].map(fmt_num)
    show["_batch_count_display"] = pd.to_numeric(show.get("batch_count"), errors="coerce").fillna(0).astype(int).astype(str)
    show["_overdue_batch_count_display"] = pd.to_numeric(show.get("overdue_batch_count"), errors="coerce").fillna(0).astype(int).astype(str)

    display = show[
        [
            _t("勾選"),
            "customer_order_id",
            "customer_order_code",
            "customer_order_num",
            "customer_display",
            "_ordered_total_display",
            "_remaining_total_display",
            "_completion_rate_display",
            "_batch_count_display",
            "_overdue_batch_count_display",
            "deliver_date",
            "_display_status",
            "last_delivery_date",
        ]
    ].rename(
        columns={
            "customer_order_code": _t("本公司訂單號"),
            "customer_order_num": _t("客戶訂單號"),
            "customer_display": _t("客戶"),
            "_ordered_total_display": _t("訂單數量總計"),
            "_remaining_total_display": _t("未出貨數量總計"),
            "_completion_rate_display": _t("完成率"),
            "_batch_count_display": _t("批次數"),
            "_overdue_batch_count_display": _t("逾期批次數"),
            "deliver_date": _t("最早未完成交期"),
            "_display_status": _t("狀態"),
            "last_delivery_date": _t("最後出貨日"),
        }
    )
    return display


def prepare_item_display_df(line_df: pd.DataFrame, customer_order_id: int) -> pd.DataFrame:
    """Display selected order at batch level instead of only item level."""
    if line_df.empty:
        return pd.DataFrame()

    show = line_df[line_df["customer_order_id"] == customer_order_id].copy()
    if show.empty:
        return pd.DataFrame()

    show["deliver_date"] = pd.to_datetime(show["deliver_date"], errors="coerce").dt.date
    show["_completion_rate_display"] = show["completion_rate"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "0%")
    show["_order_qty_display"] = show["order_qty"].map(fmt_num) + " " + show["unit"].astype(str)
    show["_shipped_qty_display"] = show["shipped_qty"].map(fmt_num) + " " + show["unit"].astype(str)
    show["_remaining_qty_display"] = show["remaining_qty"].map(fmt_num) + " " + show["unit"].astype(str)
    show["_batch_status_display"] = show["batch_status"].apply(status_badge_text)
    show["_schedule_no_display"] = show["schedule_no"].fillna(1).astype(int).astype(str)

    return show[
        [
            "product_code",
            "customer_production_id",
            "product_name",
            "spec",
            "_schedule_no_display",
            "deliver_date",
            "_order_qty_display",
            "_shipped_qty_display",
            "_remaining_qty_display",
            "_completion_rate_display",
            "_batch_status_display",
        ]
    ].rename(
        columns={
            "product_code": _t("產品編號"),
            "customer_production_id": _t("客戶料號"),
            "product_name": _t("品名"),
            "spec": _t("規格"),
            "_schedule_no_display": _t("批次"),
            "deliver_date": _t("批次交期"),
            "_order_qty_display": _t("批次數量"),
            "_shipped_qty_display": _t("已出貨數量"),
            "_remaining_qty_display": _t("未出貨數量"),
            "_completion_rate_display": _t("完成率"),
            "_batch_status_display": _t("批次狀態"),
        }
    )


def load_schedule_status_by_order(customer_order_id: int) -> pd.DataFrame:
    sql = """
        SELECT
            customer_order_code,
            customer_order_num,
            line_no,
            product_code,
            customer_product_id,
            product_name,
            schedule_no,
            due_date,
            schedule_qty,
            delivered_qty,
            remaining_qty,
            computed_status
        FROM v_customer_order_schedule_status
        WHERE customer_order_id = %s
        ORDER BY due_date ASC, line_no ASC, schedule_no ASC
    """
    try:
        return fetch_df(sql, [int(customer_order_id)])
    except Exception:
        return pd.DataFrame()


def _e02_schedule_status_label(row: pd.Series) -> str:
    status = str(row.get("computed_status") or "open").strip()
    try:
        due = pd.to_datetime(row.get("due_date"), errors="coerce")
        remaining = float(row.get("remaining_qty") or 0)
        if pd.notna(due) and due.date() < pd.Timestamp.today().date() and remaining > 0:
            return "🔴 " + _t("逾期")
    except Exception:
        pass
    if status == "shipped":
        return "🟢 " + _t("已完成")
    if status == "partial_shipped":
        return "🟠 " + _t("部分完成")
    return "⚪ " + _t("未完成")


def prepare_schedule_display_df(schedule_df: pd.DataFrame) -> pd.DataFrame:
    if schedule_df.empty:
        return pd.DataFrame()
    show = schedule_df.copy()
    for col in ["schedule_qty", "delivered_qty", "remaining_qty"]:
        show[col] = pd.to_numeric(show[col], errors="coerce").fillna(0)
    show["due_date"] = pd.to_datetime(show["due_date"], errors="coerce").dt.date
    show["status_display"] = show.apply(_e02_schedule_status_label, axis=1)
    show["product_display"] = show["product_code"].fillna("").astype(str) + "｜" + show["product_name"].fillna("").astype(str)
    return show[[
        "line_no", "product_display", "customer_product_id", "schedule_no", "due_date",
        "schedule_qty", "delivered_qty", "remaining_qty", "status_display"
    ]].rename(columns={
        "line_no": _t("明細行號"),
        "product_display": _t("品名"),
        "customer_product_id": _t("客戶料號"),
        "schedule_no": _t("批次"),
        "due_date": _t("交期"),
        "schedule_qty": _t("訂單數量"),
        "delivered_qty": _t("已出貨數量"),
        "remaining_qty": _t("未出貨數量"),
        "status_display": _t("狀態"),
    })

# -----------------------------------------------------------------------------
# Main page
# -----------------------------------------------------------------------------
st.markdown(f'<div class="e02-title">{_t("E02｜客戶訂單完成進度")}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="e02-subtitle">{_t("Customer Order Progress Dashboard")}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="e02-helper">{_t("查看每張客戶訂單的出貨、未出貨、部分完成與逾期狀況。")}</div>',
    unsafe_allow_html=True,
)

if st.button(_t("重新整理"), key="e02_refresh"):
    load_customers.clear()
    st.session_state.pop("e02_main_order_selector", None)

try:
    customers_df = load_customers()
except Exception as e:
    st.error(_t("資料庫連線或基礎資料讀取失敗：") + str(e))
    st.stop()

# ---------------- Filters ----------------
with st.container(border=True):
    st.subheader("🔎 " + _t("篩選條件"))

    customer_options = {_all_label(): None}
    for _, row in customers_df.iterrows():
        label = f"{row['customer_shortname']}（{row['customer_code']}）"
        customer_options[label] = int(row["customer_id"])

    r1c1, r1c2, r1c3 = st.columns([1.2, 1.4, 1.5])
    with r1c1:
        customer_label = st.selectbox(_t("客戶"), list(customer_options.keys()))
    with r1c2:
        order_no = st.text_input(_t("訂單號"), placeholder=_t("例如：CO260426001 / 客戶單號"))
    with r1c3:
        product_kw = st.text_input(_t("品名 / 料號"), placeholder=_t("請輸入品名或料號"))

    r2c1, r2c2, r2c3, r2c4 = st.columns([1.5, 1.5, 1.5, 1.1])
    with r2c1:
        order_date_range = st.date_input(_t("訂單日期"), value=(), format="YYYY-MM-DD")
    with r2c2:
        due_date_range = st.date_input(_t("交期"), value=(), format="YYYY-MM-DD")
    with r2c3:
        status_label_map = {
            _all_label(): "全部",
            _t("未完成"): "未完成",
            _t("部分完成"): "部分完成",
            _t("已完成"): "已完成",
            _t("逾期"): "逾期",
        }
        status_label = st.selectbox(_t("完成狀態"), list(status_label_map.keys()))
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
    "customer_id": customer_options[customer_label],
    "order_no": order_no.strip(),
    "product_kw": product_kw.strip(),
    "order_date_start": order_date_start,
    "order_date_end": order_date_end,
    "due_date_start": due_date_start,
    "due_date_end": due_date_end,
    "status_filter": status_filter,
    "only_unfinished": only_unfinished,
}

try:
    line_df = load_customer_order_lines(filters)
except Exception as e:
    st.error(_t("E02 查詢失敗：") + str(e))
    st.stop()

order_summary_df = build_order_summary_df(line_df, filters)
render_kpi_cards(order_summary_df)

# ---------------- Main table ----------------
st.markdown("### 📋 " + _t("客戶訂單完成進度表"))

if order_summary_df.empty:
    st.info(_t("查無符合條件的客戶訂單資料。"))
    st.stop()

main_show_df = prepare_main_display_df(order_summary_df)

edited_main_df = st.data_editor(
    main_show_df.drop(columns=["customer_order_id"]),
    use_container_width=True,
    hide_index=True,
    disabled=[c for c in main_show_df.columns if c not in [_t("勾選")]],
    column_config={
        _t("勾選"): st.column_config.CheckboxColumn(
            _t("勾選"),
            help=_t("請在上方主表勾選一張客戶訂單查看明細。"),
            default=False,
        ),
    },
    key="e02_main_order_selector",
)

selected_positions = edited_main_df.index[edited_main_df[_t("勾選")] == True].tolist()
selected_order_id: Optional[int] = None
if selected_positions:
    if len(selected_positions) > 1:
        st.warning(_t("你勾選了多張客戶訂單，系統先顯示第一張。"))
    selected_order_id = int(main_show_df.iloc[selected_positions[0]]["customer_order_id"])

# ---------------- Child table ----------------
st.markdown("### 📦 " + _t("客戶訂單批次明細"))
st.caption(_t("無批次時以訂單主交期作為批次交期。"))

if selected_order_id is None:
    st.info(_t("請在上方主表勾選一張客戶訂單查看明細。"))
    item_show_df = pd.DataFrame()
else:
    item_show_df = prepare_item_display_df(line_df, selected_order_id)
    if item_show_df.empty:
        st.warning(_t("所選客戶訂單查無明細。"))
    else:
        st.dataframe(item_show_df, use_container_width=True, hide_index=True)

# ---------------- Export ----------------
export_df = main_show_df.drop(columns=["customer_order_id", _t("勾選")], errors="ignore").copy()
try:
    export_bytes = make_excel_bytes(export_df, item_show_df if not item_show_df.empty else None)
    st.download_button(
        label="📥 " + _t("匯出 Excel"),
        data=export_bytes,
        file_name="E02_customer_order_progress_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
except Exception as e:
    st.warning(_t("Excel 匯出暫時不可用：") + str(e))
