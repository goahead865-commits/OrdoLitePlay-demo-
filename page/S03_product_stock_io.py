# S03_product_stock_io_v2.py
# 產品進出庫作業頁面（product_stock_io_head + product_stock_io_line）
# - 目標：維持既有 UI/使用習慣（查詢區 + 新增區），但底層改為 head/line 結構
# - 支援：IN / OUT / ADJUST
# - 特色：Head「確認」後鎖定，可連續新增多筆 Line；「完成作業」解除鎖定並跳下一張單

from __future__ import annotations

from compact_layout import apply_compact_layout

apply_compact_layout()

import datetime
import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


import auth
from db import get_connection
from splitter_component import apply_vertical_splitter


# ================== I18N ==================
TRANSLATIONS = {
    "S03｜產品進出庫": {"vi": "S03｜Xuất nhập kho thành phẩm", "en": "S03 | Product Stock In/Out"},
    "查詢條件": {"vi": "Điều kiện truy vấn", "en": "Search Filters"},
    "起始日期": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "進出庫類型": {"vi": "Loại xuất nhập kho", "en": "Stock I/O Type"},
    "料號/品名關鍵字": {"vi": "Từ khóa mã SP / tên SP", "en": "Product Code / Name Keyword"},
    "指定產品（可空白）": {"vi": "Chỉ định thành phẩm (có thể để trống)", "en": "Specific Product (Optional)"},
    "（不指定）": {"vi": "(Không chỉ định)", "en": "(Unspecified)"},
    "（全部）": {"vi": "(Tất cả)", "en": "(All)"},
    "入庫": {"vi": "Nhập kho", "en": "Stock In"},
    "出庫": {"vi": "Xuất kho", "en": "Stock Out"},
    "調整": {"vi": "Điều chỉnh", "en": "Adjust"},
    "上一頁": {"vi": "Trang trước", "en": "Previous Page"},
    "下一頁": {"vi": "Trang sau", "en": "Next Page"},
    "顯示筆數": {"vi": "Số dòng hiển thị", "en": "Rows Per Page"},
    "查詢": {"vi": "Tìm kiếm", "en": "Search"},
    "清除條件": {"vi": "Xóa điều kiện", "en": "Clear Filters"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "查無資料": {"vi": "Không có dữ liệu", "en": "No data found"},
    "第": {"vi": "Trang", "en": "Page"},
    "頁，共": {"vi": "/", "en": " / "},
    "筆": {"vi": "dòng", "en": "rows"},
    "勾選": {"vi": "Chọn", "en": "Select"},
    "刪除勾選": {"vi": "Xóa mục đã chọn", "en": "Delete Selected"},
    "已刪除": {"vi": "Đã xóa", "en": "Deleted"},
    "筆資料。": {"vi": "dòng dữ liệu.", "en": "records."},
    "刪除失敗：": {"vi": "Xóa thất bại: ", "en": "Delete failed: "},
    "新增進出庫": {"vi": "Thêm xuất nhập kho", "en": "Add Stock I/O"},
    "新增一筆產品進出庫": {"vi": "Thêm một phiếu xuất nhập kho thành phẩm", "en": "Add a Product Stock I/O Record"},
    "主表（Head）": {"vi": "Thông tin đầu phiếu (Head)", "en": "Header (Head)"},
    "日期": {"vi": "Ngày", "en": "Date"},
    "我方公司訂單號碼（輸入後自動載入明細，可空白）": {"vi": "Mã đơn hàng công ty (nhập để tự tải chi tiết, có thể để trống)", "en": "Our Order No. (auto-load details after input, optional)"},
    "客戶": {"vi": "Khách hàng", "en": "Customer"},
    "客戶訂單號碼（可空白）": {"vi": "Mã đơn hàng khách (có thể để trống)", "en": "Customer Order No. (Optional)"},
    "備註（可空白）": {"vi": "Ghi chú (có thể để trống)", "en": "Remarks (Optional)"},
    "操作人員": {"vi": "Người thao tác", "en": "Operator"},
    "建檔人": {"vi": "Người tạo phiếu", "en": "Created By"},
    "※已依目前登入帳號自動帶入": {"vi": "※ Tự động lấy theo tài khoản đang đăng nhập", "en": "※ Auto-filled from the current login account"},
    "單據號：": {"vi": "Số chứng từ:", "en": "Document No.:"},
    "（確認後自動產生）": {"vi": "(tự tạo sau khi xác nhận)", "en": "(auto-generated after confirmation)"},
    "已載入訂單明細（供選擇/參考）": {"vi": "Đã tải chi tiết đơn hàng (để chọn/tham khảo)", "en": "Order details loaded (for selection/reference)"},
    "確認（鎖定主表）": {"vi": "Xác nhận (khóa head)", "en": "Confirm (Lock Header)"},
    "完成作業（解除鎖定）": {"vi": "Hoàn thành (mở khóa)", "en": "Finish (Unlock)"},
    "流程：先填主表 → 按「確認」鎖定 → 下方連續新增明細 → 按「完成作業」開下一張。": {"vi": "Quy trình: điền head → nhấn Xác nhận để khóa → thêm nhiều dòng bên dưới → nhấn Hoàn thành để mở phiếu mới.", "en": "Flow: fill header → confirm to lock → add lines below → finish to start the next document."},
    "主表已鎖定，可開始新增明細。": {"vi": "Head đã khóa, có thể bắt đầu thêm chi tiết.", "en": "Header locked. You can now add lines."},
    "鎖定主表失敗：": {"vi": "Khóa head thất bại: ", "en": "Failed to lock header: "},
    "已完成作業並解除鎖定。": {"vi": "Đã hoàn thành và mở khóa.", "en": "Completed and unlocked."},
    "子表（Line）": {"vi": "Chi tiết (Line)", "en": "Line Items (Line)"},
    "請先按「確認（鎖定主表）」再新增明細。": {"vi": "Vui lòng nhấn 'Xác nhận (khóa head)' trước khi thêm chi tiết.", "en": "Please click 'Confirm (Lock Header)' before adding lines."},
    "掃描料號（內部產品號碼 / product_code）": {"vi": "Quét mã SP (mã nội bộ / product_code)", "en": "Scan Product Code (internal / product_code)"},
    "產品料號/品名": {"vi": "Mã thành phẩm / Tên thành phẩm", "en": "Product Code / Name"},
    "客戶料號（自動帶入，不可修改）": {"vi": "Mã SP khách hàng (tự động, không chỉnh sửa)", "en": "Customer Product Code (Auto, Read-only)"},
    "數量(PCS)": {"vi": "Số lượng (PCS)", "en": "Quantity (PCS)"},
    "沖銷哪一筆（可空白，數字）": {"vi": "Bù trừ phiếu nào (có thể để trống, số)", "en": "Reverse Which Record (Optional, Number)"},
    "生產批號/工單（數字，預設0）": {"vi": "Lô SX / lệnh sản xuất (số, mặc định 0)", "en": "Production Batch / Work Order (Number, default 0)"},
    "新增紀錄": {"vi": "Thêm bản ghi", "en": "Add Record"},
    "psioh_id 不存在，請重新鎖定主表。": {"vi": "psioh_id không tồn tại, vui lòng khóa lại head.", "en": "psioh_id does not exist. Please lock the header again."},
    "數量不可為 0，請輸入數字。": {"vi": "Số lượng không được bằng 0, vui lòng nhập số lượng.", "en": "Quantity cannot be 0. Please enter a quantity."},
    "新增成功。": {"vi": "Thêm thành công.", "en": "Added successfully."},
    "寫入失敗：": {"vi": "Ghi thất bại: ", "en": "Write failed: "},
    "已載入訂單批次（供入庫選擇）": {"vi": "Đã tải các đợt giao hàng của đơn (để chọn nhập kho)", "en": "Order delivery batches loaded (for stock-in selection)"},
    "訂單批次": {"vi": "Đợt đơn hàng", "en": "Order Batch"},
    "批次": {"vi": "Đợt", "en": "Batch"},
    "明細行號": {"vi": "Dòng", "en": "Line No."},
    "產品編號": {"vi": "Mã SP", "en": "Product Code"},
    "品名": {"vi": "Tên hàng", "en": "Product Name"},
    "規格": {"vi": "Quy cách", "en": "Spec"},
    "客戶料號": {"vi": "Mã hàng khách", "en": "Customer Product No."},
    "預計交期": {"vi": "Ngày giao dự kiến", "en": "Due Date"},
    "訂單總數量": {"vi": "Tổng SL đơn", "en": "Order Qty"},
    "批次數量": {"vi": "SL đợt", "en": "Batch Qty"},
    "已入庫數量": {"vi": "SL đã nhập kho", "en": "Stocked-in Qty"},
    "已出庫數量": {"vi": "SL đã xuất kho", "en": "Stocked-out Qty"},
    "已處理數量": {"vi": "SL đã xử lý", "en": "Processed Qty"},
    "剩餘數量": {"vi": "SL còn lại", "en": "Remaining Qty"},
    "單位": {"vi": "Đơn vị", "en": "Unit"},
    "批次狀態": {"vi": "Trạng thái đợt", "en": "Batch Status"},
    "入庫批次": {"vi": "Đợt nhập kho", "en": "Stock-in Batch"},
    "出庫批次": {"vi": "Đợt xuất kho", "en": "Stock-out Batch"},
    "處理批次": {"vi": "Đợt xử lý", "en": "Processing Batch"},
    "產品": {"vi": "Sản phẩm", "en": "Product"},
    "本批剩餘數量": {"vi": "SL còn lại của đợt", "en": "Batch Remaining Qty"},
    "此批次已無剩餘數量。": {"vi": "Đợt này không còn số lượng.", "en": "This batch has no remaining quantity."},
    "輸入數量不可大於本批剩餘數量。": {"vi": "Số lượng nhập không được lớn hơn số lượng còn lại của đợt.", "en": "Input quantity cannot exceed the remaining quantity of this batch."},
    "product_stock_io_line 缺少批次關聯欄位，請先執行 SQL 補欄位。": {"vi": "product_stock_io_line thiếu cột liên kết đợt; vui lòng chạy SQL cập nhật trước.", "en": "product_stock_io_line is missing batch-link columns. Please run the SQL patch first."},
    "此訂單尚未建立交貨批次，請先到 E01 設定交貨排程。": {"vi": "Đơn này chưa có đợt giao hàng; vui lòng thiết lập lịch giao ở E01 trước.", "en": "This order has no delivery batches yet. Please set the delivery schedule in E01 first."},
}
def get_lang() -> str:
    # home.py / core.i18n 常用 language；舊頁面可能用 lang。兩邊都支援，避免切換語言時 S03 不跟著變。
    lang = st.session_state.get("language", st.session_state.get("lang", "zh"))
    return lang if lang in {"zh", "vi", "en"} else "zh"

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)

def _io_options():
    return ["（全部）", "入庫", "出庫", "調整"]

# ================== 基本設定 ==================

# ================== 權限守門 ==================
PAGE_KEY = "S03_product_stock_io"
auth.require_read(PAGE_KEY)


TABLE_STOCK_IO_H = "product_stock_io_head"
TABLE_STOCK_IO_L = "product_stock_io_line"
TABLE_PRODUCT = "product"
TABLE_STUFF = "stuff"
TABLE_USER = "user"
TABLE_CUSTOMER = "customer"
TABLE_CUSTOMER_ORDER = "customer_order"
TABLE_CUSTOMER_ORDER_ITEM = "customer_order_item"


# ================== DB helper ==================
def fetch_df(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(sql, conn, params=params)


def execute_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> int:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        conn.commit()
        return int(cur.lastrowid or 0)


def execute_sql_many(sql: str, params_seq: List[Dict[str, Any]]) -> None:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.executemany(sql, params_seq)
        conn.commit()


def has_column(table_name: str, col_name: str) -> bool:
    sql = """
        SELECT COUNT(*) AS cnt
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %(t)s
          AND column_name = %(c)s
    """
    df = fetch_df(sql, {"t": table_name, "c": col_name})
    return int(df.iloc[0]["cnt"]) > 0


# ================== 下拉選單資料 ==================
@st.cache_data(show_spinner=False)
def get_customer_options() -> Dict[str, int]:
    sql = f"""
        SELECT customer_id, customer_shortname, customer_name
        FROM `{TABLE_CUSTOMER}`
        ORDER BY customer_shortname
    """
    df = fetch_df(sql)
    out: Dict[str, int] = {"（全部）": 0}
    for _, r in df.iterrows():
        label = f'{r["customer_shortname"]}｜{r["customer_name"]}'
        out[str(label)] = int(r["customer_id"])
    return out


@st.cache_data(show_spinner=False)
def get_stuff_options() -> Dict[str, int]:
    sql = f"SELECT stuff_id, stuff_name FROM `{TABLE_STUFF}` ORDER BY stuff_name"
    df = fetch_df(sql)
    out: Dict[str, int] = {_t("（不指定）"): 0}
    for _, r in df.iterrows():
        out[str(r["stuff_name"])] = int(r["stuff_id"])
    return out


@st.cache_data(show_spinner=False)
def get_user_identity_options() -> Dict[str, Dict[str, Any]]:
    """
    同時提供 user_id（head 用）與 user_code（line 用）
    """
    sql = f"""
        SELECT
            u.user_id,
            u.user_code,
            COALESCE(s.stuff_name, u.user_code) AS display_name
        FROM `{TABLE_USER}` u
        LEFT JOIN `{TABLE_STUFF}` s
               ON u.stuff_id = s.stuff_id
        ORDER BY display_name
    """
    df = fetch_df(sql)
    out: Dict[str, Dict[str, Any]] = {}
    for _, r in df.iterrows():
        out[str(r["display_name"])] = {"user_id": int(r["user_id"]), "user_code": str(r["user_code"])}
    if not out:
        # fallback，避免 UI 無選項直接爆
        out["（未知）"] = {"user_id": 1, "user_code": "UNKNOWN"}
    return out


def get_current_user_identity(user_options: Dict[str, Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """Return the current logged-in user for created_by fields.

    S03 created_by must follow the login account, not a manual dropdown.
    Fallback is only for abnormal sessions, so the page does not crash during testing.
    """
    current_user_id = None
    try:
        raw_user_id = st.session_state.get("user_id")
        if raw_user_id not in (None, ""):
            current_user_id = int(raw_user_id)
    except Exception:
        current_user_id = None

    if current_user_id is not None:
        for display_name, meta in user_options.items():
            try:
                if int(meta.get("user_id")) == int(current_user_id):
                    return str(display_name), meta
            except Exception:
                continue

        username = str(st.session_state.get("username") or st.session_state.get("user_code") or f"User#{current_user_id}")
        return username, {"user_id": int(current_user_id), "user_code": username}

    if user_options:
        first_name = next(iter(user_options.keys()))
        return str(first_name), user_options[first_name]

    return "User#1", {"user_id": 1, "user_code": "UNKNOWN"}


@st.cache_data(show_spinner=False)
def get_product_id_to_label() -> Dict[int, str]:
    sql = f"""
        SELECT p.product_id, p.product_code, COALESCE(p.product_name,'') AS product_name,
               c.customer_shortname
        FROM `{TABLE_PRODUCT}` p
        LEFT JOIN `{TABLE_CUSTOMER}` c ON p.customer_id = c.customer_id
        ORDER BY p.product_code
    """
    df = fetch_df(sql)
    out: Dict[int, str] = {}
    for _, r in df.iterrows():
        out[int(r["product_id"])] = f'{r["product_code"]}｜{r["product_name"]}（{r["customer_shortname"]}）'
    return out


@st.cache_data(show_spinner=False)
def get_product_ids_by_customer(customer_id: int) -> List[int]:
    if not customer_id:
        return []
    sql = f"SELECT product_id FROM `{TABLE_PRODUCT}` WHERE customer_id=%(cid)s ORDER BY product_code"
    df = fetch_df(sql, {"cid": customer_id})
    return [int(x) for x in df["product_id"].tolist()]


@st.cache_data(show_spinner=False)
def get_product_meta(product_id: int) -> Dict[str, Any]:
    sql = f"""
        SELECT product_id, product_code, product_name, customer_id,
               customer_production_id
        FROM `{TABLE_PRODUCT}`
        WHERE product_id=%(pid)s
        LIMIT 1
    """
    df = fetch_df(sql, {"pid": product_id})
    if df.empty:
        return {}
    r = df.iloc[0].to_dict()
    return r


@st.cache_data(show_spinner=False)
def get_product_id_by_code(product_code: str) -> Optional[int]:
    code = (product_code or "").strip()
    if not code:
        return None
    sql = f"SELECT product_id FROM `{TABLE_PRODUCT}` WHERE product_code=%(code)s LIMIT 1"
    df = fetch_df(sql, {"code": code})
    if df.empty:
        return None
    return int(df.iloc[0]["product_id"])


@st.cache_data(show_spinner=False)
def get_customer_order_by_our_num(our_order_num: str) -> Dict[str, Any]:
    """
    以「我方公司訂單號碼」查 customer_order.customer_order_code
    """
    code = (our_order_num or "").strip()
    if not code:
        return {}
    sql = f"""
        SELECT
            customer_order_id,
            customer_order_code,
            customer_order_num,
            customer_id
        FROM `{TABLE_CUSTOMER_ORDER}`
        WHERE customer_order_code=%(code)s
        LIMIT 1
    """
    df = fetch_df(sql, {"code": code})
    return {} if df.empty else df.iloc[0].to_dict()


@st.cache_data(show_spinner=False)
def get_customer_order_items(order_id: int) -> pd.DataFrame:
    """保留原始訂單明細查詢，供 fallback 使用；畫面預覽改用 get_customer_order_schedule_rows。"""
    sql = f"""
        SELECT
            i.customer_order_item_id,
            i.line_no,
            i.product_id,
            p.product_code,
            p.product_name,
            i.quantity,
            i.unit,
            i.barcode
        FROM `{TABLE_CUSTOMER_ORDER_ITEM}` i
        LEFT JOIN `{TABLE_PRODUCT}` p ON i.product_id = p.product_id
        WHERE i.customer_order_id=%(oid)s
        ORDER BY i.line_no
    """
    return fetch_df(sql, {"oid": order_id})


def _io_type_from_label(io_label: str) -> str:
    return {"入庫": "IN", "出庫": "OUT", "調整": "ADJUST"}.get(str(io_label or "入庫"), "IN")


def _handled_qty_label(io_type_code: str) -> str:
    if io_type_code == "IN":
        return _t("已入庫數量")
    if io_type_code == "OUT":
        return _t("已出庫數量")
    return _t("已處理數量")


def _batch_select_label(io_type_code: str) -> str:
    if io_type_code == "IN":
        return _t("入庫批次")
    if io_type_code == "OUT":
        return _t("出庫批次")
    return _t("處理批次")


def _fmt_qty(v: Any) -> str:
    try:
        n = float(v or 0)
        if abs(n - int(n)) < 0.000001:
            return f"{int(n):,}"
        return f"{n:,.2f}"
    except Exception:
        return "0"


def _has_stock_io_schedule_columns() -> bool:
    return has_column(TABLE_STOCK_IO_L, "customer_order_item_id") and has_column(TABLE_STOCK_IO_L, "schedule_id")


def get_customer_order_schedule_rows(order_id: int, io_type_code: str = "IN") -> pd.DataFrame:
    """以 E01 的 customer_order_item_schedule 為核心載入訂單批次。

    若 product_stock_io_line 已補 customer_order_item_id / schedule_id，會計算該批次已入庫/已出庫數量；
    若尚未補欄位，仍可顯示批次，但已處理數量會先顯示 0，新增時會要求先補 SQL 欄位。
    """
    if not order_id:
        return pd.DataFrame()

    has_batch_cols = _has_stock_io_schedule_columns()

    if has_batch_cols:
        handled_join = f"""
            LEFT JOIN (
                SELECT
                    l.schedule_id,
                    SUM(COALESCE(l.qty_PCS, 0)) AS handled_qty
                FROM `{TABLE_STOCK_IO_L}` l
                JOIN `{TABLE_STOCK_IO_H}` h
                  ON h.psioh_id = l.psioh_id
                WHERE h.io_type = %(io_type)s
                  AND COALESCE(h.status, 'posted') <> 'void'
                  AND l.schedule_id IS NOT NULL
                GROUP BY l.schedule_id
            ) io ON io.schedule_id = s.schedule_id
        """
        handled_expr = "COALESCE(io.handled_qty, 0)"
    else:
        handled_join = ""
        handled_expr = "0"

    sql = f"""
        SELECT
            i.customer_order_item_id,
            s.schedule_id,
            i.line_no,
            s.schedule_no,
            i.product_id,
            p.product_code,
            COALESCE(p.customer_production_id, '') AS customer_product_id,
            COALESCE(p.product_name, '') AS product_name,
            COALESCE(p.Specification, '') AS specification,
            COALESCE(i.unit, 'PCS') AS unit,
            COALESCE(i.quantity, 0) AS order_qty,
            s.due_date,
            COALESCE(s.qty, 0) AS schedule_qty,
            {handled_expr} AS handled_qty,
            GREATEST(COALESCE(s.qty, 0) - {handled_expr}, 0) AS remaining_qty,
            COALESCE(s.status, 'open') AS schedule_status,
            COALESCE(s.note, '') AS schedule_note
        FROM `{TABLE_CUSTOMER_ORDER_ITEM}` i
        JOIN customer_order_item_schedule s
          ON s.customer_order_item_id = i.customer_order_item_id
        LEFT JOIN `{TABLE_PRODUCT}` p
          ON p.product_id = i.product_id
        {handled_join}
        WHERE i.customer_order_id = %(oid)s
        ORDER BY i.line_no ASC, s.schedule_no ASC, s.due_date ASC, s.schedule_id ASC
    """
    params: Dict[str, Any] = {"oid": int(order_id)}
    if has_batch_cols:
        params["io_type"] = str(io_type_code or "IN")
    try:
        df = fetch_df(sql, params)
    except Exception:
        return pd.DataFrame()

    for col in ["order_qty", "schedule_qty", "handled_qty", "remaining_qty"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _schedule_status_label(row: pd.Series) -> str:
    raw = str(row.get("schedule_status") or "open").strip()
    try:
        remaining = float(row.get("remaining_qty") or 0)
        due = pd.to_datetime(row.get("due_date"), errors="coerce")
        if pd.notna(due) and due.date() < datetime.date.today() and remaining > 0:
            return "🔴 " + _t("逾期未完成")
    except Exception:
        pass
    if raw in {"shipped", "done", "finished"}:
        return "🟢 " + _t("已完成")
    if raw in {"partial_shipped", "partial", "partial_in"}:
        return "🟠 " + _t("部分出貨")
    if raw == "cancelled":
        return "⚫ " + _t("已取消")
    try:
        remaining = float(row.get("remaining_qty") or 0)
        schedule_qty = float(row.get("schedule_qty") or 0)
        handled_qty = float(row.get("handled_qty") or 0)
        if schedule_qty > 0 and remaining <= 0:
            return "🟢 " + _t("已完成")
        if handled_qty > 0 and remaining > 0:
            return "🟠 " + _t("部分出貨")
    except Exception:
        pass
    return "⚪ " + _t("未完成")


def prepare_order_schedule_display_df(schedule_df: pd.DataFrame, io_type_code: str = "IN") -> pd.DataFrame:
    if schedule_df is None or schedule_df.empty:
        return pd.DataFrame()
    show = schedule_df.copy()
    show["產品"] = show["product_code"].fillna("").astype(str) + "｜" + show["product_name"].fillna("").astype(str)
    show["狀態"] = show.apply(_schedule_status_label, axis=1)
    try:
        show["due_date"] = pd.to_datetime(show["due_date"], errors="coerce").dt.date
    except Exception:
        pass

    display_cols = [
        "line_no", "schedule_no", "產品", "customer_product_id", "specification",
        "due_date", "order_qty", "schedule_qty", "handled_qty", "remaining_qty", "unit", "狀態",
    ]
    display = show[[c for c in display_cols if c in show.columns]].rename(columns={
        "line_no": _t("明細行號"),
        "schedule_no": _t("批次"),
        "customer_product_id": _t("客戶料號"),
        "specification": _t("規格"),
        "due_date": _t("預計交期"),
        "order_qty": _t("訂單總數量"),
        "schedule_qty": _t("批次數量"),
        "handled_qty": _handled_qty_label(io_type_code),
        "remaining_qty": _t("剩餘數量"),
        "unit": _t("單位"),
        "狀態": _t("批次狀態"),
    })
    return display


def format_schedule_option(schedule_id: int, schedule_df: pd.DataFrame, io_type_code: str = "IN") -> str:
    if schedule_df is None or schedule_df.empty:
        return str(schedule_id)
    try:
        row = schedule_df.loc[schedule_df["schedule_id"].astype(int) == int(schedule_id)].iloc[0]
    except Exception:
        return str(schedule_id)
    due = row.get("due_date")
    try:
        due_text = pd.to_datetime(due).date().isoformat() if pd.notna(due) else ""
    except Exception:
        due_text = str(due or "")
    return (
        f"{_t('批次')} {int(row.get('schedule_no') or 0)}｜"
        f"{row.get('product_code','')}｜{row.get('product_name','')}｜"
        f"{_t('預計交期')}:{due_text}｜"
        f"{_t('批次數量')}:{_fmt_qty(row.get('schedule_qty'))}｜"
        f"{_t('剩餘數量')}:{_fmt_qty(row.get('remaining_qty'))} {row.get('unit','')}"
    )



# ================== doc_no 產生 ==================
def _doc_prefix(io_type: str) -> str:
    return {"IN": "PI", "OUT": "PO", "ADJUST": "PA"}.get(io_type, "PX")


def _generate_doc_no(io_date: datetime.date, io_type: str) -> str:
    """
    產生 product_stock_io_head.doc_no（NOT NULL / UNIQUE）
    規則：{prefix}{yymm}{seq4}
    """
    prefix = _doc_prefix(io_type)
    yymm = io_date.strftime("%y%m")
    like = f"{prefix}{yymm}%"
    sql = f"SELECT MAX(doc_no) AS mx FROM `{TABLE_STOCK_IO_H}` WHERE doc_no LIKE %(like)s"
    df = fetch_df(sql, {"like": like})
    mx = str(df.iloc[0]["mx"] or "")
    if mx.startswith(prefix + yymm) and len(mx) >= len(prefix + yymm) + 4:
        try:
            seq = int(mx[-4:]) + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{yymm}{seq:04d}"


# ================== head/line insert ==================
def insert_psio_head(
    io_type: str,
    io_dt: datetime.datetime,
    customer_order_id: Optional[int],
    operator_id: Optional[int],
    created_by_user_id: int,
    note: Optional[str],
    customer_order_code: Optional[int] = None,
    customer_order_num: Optional[str] = None,
    delivery_head_id: Optional[int] = None,
    delivery_code: Optional[str] = None,
    truck_no: Optional[str] = None,
) -> Tuple[int, str]:
    auth.require_edit(PAGE_KEY)
    """
    寫入 product_stock_io_head（新版 schema）
    - doc_no：每筆進出庫自己的單號（本頁面產生）
    - delivery_code：送貨單號（通常由 D02 出貨頁面產生；本頁面預設不產生）
    """
    doc_no = _generate_doc_no(io_dt.date(), io_type)
    period = io_dt.strftime("%Y%m")

    cols = [
        "doc_no",
        "io_type",
        "io_time",
        "customer_order_id",
        "customer_order_code",
        "customer_order_num",
        "delivery_head_id",
        "delivery_code",
        "truck_no",
        "status",
        "note",
        "operator",
        "period",
        "created_by",
    ]
    sql = f"""
        INSERT INTO `{TABLE_STOCK_IO_H}` ({",".join([f"`{c}`" for c in cols])})
        VALUES (
            %(doc_no)s,%(io_type)s,%(io_time)s,
            %(coid)s,%(cocode)s,%(conum)s,
            %(dhid)s,%(dcode)s,%(truck)s,
            %(status)s,%(note)s,%(op)s,%(period)s,%(cby)s
        )
    """
    params = {
        "doc_no": doc_no,
        "io_type": io_type,
        "io_time": io_dt,
        "coid": customer_order_id,
        "cocode": customer_order_code,
        "conum": (customer_order_num or "").strip() or None,
        "dhid": delivery_head_id,
        "dcode": (delivery_code or "").strip() or None,
        "truck": (truck_no or "").strip() or None,
        "status": "posted",
        "note": note,
        "op": operator_id,
        "period": period,
        "cby": created_by_user_id,
    }
    psioh_id = execute_sql(sql, params)
    return psioh_id, doc_no


def insert_psio_line(
    psioh_id: int,
    io_dt: datetime.datetime,
    item_id: int,
    customer_material_num: Optional[str],
    production_num: Optional[int],
    qty_pcs: float,
    carton_used: Optional[int],
    operator_id: Optional[int],
    created_by_user_id: int,
    note: Optional[str],
    reversed_io_id: Optional[int],
    customer_order_item_id: Optional[int] = None,
    schedule_id: Optional[int] = None,
) -> int:
    auth.require_edit(PAGE_KEY)
    """
    寫入 product_stock_io_line（新版 schema）
    欄位：psioh_id, line_no, item_id, customer_material_num, production_num, qty_PCS,
          note, operator, created_by, period, reversed_io_id, carton_used
    """
    # line_no = max + 1
    df = fetch_df(
        f"SELECT COALESCE(MAX(line_no),0) AS mx FROM `{TABLE_STOCK_IO_L}` WHERE psioh_id=%(hid)s",
        {"hid": psioh_id},
    )
    line_no = int(df.iloc[0]["mx"] or 0) + 1
    period = io_dt.strftime("%Y%m")

    pn = int(production_num or 0)
    if pn <= 0:
        pn = int(item_id)  # NOT NULL fallback

    has_coi_col = has_column(TABLE_STOCK_IO_L, "customer_order_item_id")
    has_schedule_col = has_column(TABLE_STOCK_IO_L, "schedule_id")

    cols = [
        "psioh_id",
        "line_no",
        "item_id",
        *( ["customer_order_item_id"] if has_coi_col else [] ),
        *( ["schedule_id"] if has_schedule_col else [] ),
        "customer_material_num",
        "production_num",
        "qty_PCS",
        "note",
        "operator",
        "created_by",
        "period",
        "reversed_io_id",
        "carton_used",
    ]
    sql = f"""
        INSERT INTO `{TABLE_STOCK_IO_L}` ({",".join([f"`{c}`" for c in cols])})
        VALUES (
            %(hid)s,%(ln)s,%(item)s,
            {"%(coi)s," if has_coi_col else ""}
            {"%(schedule)s," if has_schedule_col else ""}
            %(cm)s,%(pn)s,%(qty)s,
            %(note)s,%(op)s,%(cby)s,%(period)s,%(rev)s,%(carton)s
        )
    """
    params = {
        "hid": psioh_id,
        "ln": line_no,
        "item": int(item_id),
        "coi": int(customer_order_item_id) if customer_order_item_id is not None else None,
        "schedule": int(schedule_id) if schedule_id is not None else None,
        "cm": (customer_material_num or "").strip() or None,
        "pn": pn,
        "qty": float(qty_pcs or 0),
        "note": note,
        "op": operator_id,
        "cby": int(created_by_user_id),
        "period": period,
        "rev": reversed_io_id,
        "carton": carton_used,
    }
    return execute_sql(sql, params)


# ================== 查詢 ==================
def fetch_product_stock_io_view(
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    product_id: Optional[int],
    io_label: str,
    product_kw: str,
    limit_rows: int,
) -> pd.DataFrame:
    conditions: List[str] = []
    params: Dict[str, Any] = {}

    if start_date:
        conditions.append("h.io_time >= %(dt_from)s")
        params["dt_from"] = datetime.datetime.combine(start_date, datetime.time.min)

    if end_date:
        conditions.append("h.io_time <= %(dt_to)s")
        params["dt_to"] = datetime.datetime.combine(end_date, datetime.time.max)

    if product_id:
        conditions.append("l.item_id = %(pid)s")
        params["pid"] = int(product_id)

    io_map = {"入庫": "IN", "出庫": "OUT", "調整": "ADJUST"}
    if io_label and io_label != "（全部）":
        code = io_map.get(io_label)
        if code:
            conditions.append("h.io_type = %(io_type)s")
            params["io_type"] = code

    if (product_kw or "").strip():
        conditions.append("(p.product_code LIKE %(kw)s OR p.product_name LIKE %(kw)s)")
        params["kw"] = f"%{product_kw.strip()}%"

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
    SELECT
        h.psioh_id                                        AS `_psioh_id`,
        l.line_no                                         AS `_line_no`,
        h.customer_order_id                               AS `_customer_order_id`,
        h.doc_no                                          AS `進出庫單號`,
        h.delivery_code                                   AS `送貨單號`,
        co.customer_order_code                            AS `我方公司訂單號碼`,
        COALESCE(co.customer_order_num, h.customer_order_num) AS `客戶訂單號碼`,
        p.product_code                                    AS `料號`,
        p.product_name                                    AS `品名`,
        l.customer_material_num                           AS `客戶料號`,
        l.production_num                                  AS `生產批號/工單`,
        h.io_type                                         AS `_io_type_code`,
        l.qty_PCS                                         AS `數量(PCS)`,
        l.carton_used                                     AS `使用箱數`,
        COALESCE(op_direct.stuff_name, op_user_stuff.stuff_name, CAST(COALESCE(l.operator, h.operator) AS CHAR), '') AS `操作人員`,
        COALESCE(creator_stuff.stuff_name, creator_user.user_code, CAST(COALESCE(l.created_by, h.created_by) AS CHAR), '') AS `建檔人`,
        COALESCE(l.period, h.period)                      AS `期間`,
        l.reversed_io_id                                  AS `沖銷哪一筆`,
        COALESCE(l.note, h.note)                          AS `備註`,
        h.io_time                                         AS `時間`
    FROM `{TABLE_STOCK_IO_L}` l
    LEFT JOIN `{TABLE_STOCK_IO_H}` h
           ON l.psioh_id = h.psioh_id
    LEFT JOIN `{TABLE_PRODUCT}` p
           ON l.item_id = p.product_id
    LEFT JOIN `{TABLE_STUFF}` op_direct
           ON COALESCE(l.operator, h.operator) = op_direct.stuff_id
    LEFT JOIN `{TABLE_USER}` op_user
           ON COALESCE(l.operator, h.operator) = op_user.user_id
    LEFT JOIN `{TABLE_STUFF}` op_user_stuff
           ON op_user.stuff_id = op_user_stuff.stuff_id
    LEFT JOIN `{TABLE_USER}` creator_user
           ON COALESCE(l.created_by, h.created_by) = creator_user.user_id
    LEFT JOIN `{TABLE_STUFF}` creator_stuff
           ON creator_user.stuff_id = creator_stuff.stuff_id
    LEFT JOIN `{TABLE_CUSTOMER_ORDER}` co
           ON h.customer_order_id = co.customer_order_id
    {where_clause}
    ORDER BY h.io_time DESC, h.psioh_id DESC, l.line_no DESC
    LIMIT %(lim)s
    """
    params["lim"] = int(limit_rows or 200)
    df = fetch_df(sql, params)

    if not df.empty:
        io_code_to_label = {"IN": "入庫", "OUT": "出庫", "ADJUST": "調整"}
        df.insert(df.columns.get_loc("_io_type_code") + 1, "進出庫類型", df["_io_type_code"].map(io_code_to_label).fillna(df["_io_type_code"]))
        df = df.drop(columns=["_io_type_code"])
    return df




def _build_product_stock_io_filters(
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    product_id: Optional[int],
    io_label: str,
    product_kw: str,
) -> Tuple[str, Dict[str, Any]]:
    conditions: List[str] = []
    params: Dict[str, Any] = {}

    if start_date:
        conditions.append("h.io_time >= %(dt_from)s")
        params["dt_from"] = datetime.datetime.combine(start_date, datetime.time.min)

    if end_date:
        conditions.append("h.io_time <= %(dt_to)s")
        params["dt_to"] = datetime.datetime.combine(end_date, datetime.time.max)

    if product_id:
        conditions.append("l.item_id = %(pid)s")
        params["pid"] = int(product_id)

    io_map = {"入庫": "IN", "出庫": "OUT", "調整": "ADJUST"}
    if io_label and io_label != "（全部）":
        code = io_map.get(io_label)
        if code:
            conditions.append("h.io_type = %(io_type)s")
            params["io_type"] = code

    if (product_kw or "").strip():
        conditions.append("(p.product_code LIKE %(kw)s OR p.product_name LIKE %(kw)s)")
        params["kw"] = f"%{product_kw.strip()}%"

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_clause, params


def fetch_product_stock_io_count(
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    product_id: Optional[int],
    io_label: str,
    product_kw: str,
) -> int:
    where_clause, params = _build_product_stock_io_filters(
        start_date=start_date,
        end_date=end_date,
        product_id=product_id,
        io_label=io_label,
        product_kw=product_kw,
    )
    sql = f"""
    SELECT COUNT(*) AS total_rows
    FROM `{TABLE_STOCK_IO_L}` l
    LEFT JOIN `{TABLE_STOCK_IO_H}` h
           ON l.psioh_id = h.psioh_id
    LEFT JOIN `{TABLE_PRODUCT}` p
           ON l.item_id = p.product_id
    {where_clause}
    """
    df = fetch_df(sql, params)
    if df.empty:
        return 0
    return int(df.iloc[0]["total_rows"] or 0)


def fetch_product_stock_io_page(
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    product_id: Optional[int],
    io_label: str,
    product_kw: str,
    page_size: int,
    page_no: int,
) -> pd.DataFrame:
    where_clause, params = _build_product_stock_io_filters(
        start_date=start_date,
        end_date=end_date,
        product_id=product_id,
        io_label=io_label,
        product_kw=product_kw,
    )
    params["lim"] = max(int(page_size or 20), 1)
    params["ofs"] = max(int(page_no or 1) - 1, 0) * params["lim"]

    sql = f"""
    SELECT
        h.psioh_id                                        AS `_psioh_id`,
        l.line_no                                         AS `_line_no`,
        h.customer_order_id                               AS `_customer_order_id`,
        h.doc_no                                          AS `進出庫單號`,
        h.delivery_code                                   AS `送貨單號`,
        co.customer_order_code                            AS `我方公司訂單號碼`,
        COALESCE(co.customer_order_num, h.customer_order_num) AS `客戶訂單號碼`,
        p.product_code                                    AS `料號`,
        p.product_name                                    AS `品名`,
        l.customer_material_num                           AS `客戶料號`,
        l.production_num                                  AS `生產批號/工單`,
        h.io_type                                         AS `_io_type_code`,
        l.qty_PCS                                         AS `數量(PCS)`,
        l.carton_used                                     AS `使用箱數`,
        COALESCE(op_direct.stuff_name, op_user_stuff.stuff_name, CAST(COALESCE(l.operator, h.operator) AS CHAR), '') AS `操作人員`,
        COALESCE(creator_stuff.stuff_name, creator_user.user_code, CAST(COALESCE(l.created_by, h.created_by) AS CHAR), '') AS `建檔人`,
        COALESCE(l.period, h.period)                      AS `期間`,
        l.reversed_io_id                                  AS `沖銷哪一筆`,
        COALESCE(l.note, h.note)                          AS `備註`,
        h.io_time                                         AS `時間`
    FROM `{TABLE_STOCK_IO_L}` l
    LEFT JOIN `{TABLE_STOCK_IO_H}` h
           ON l.psioh_id = h.psioh_id
    LEFT JOIN `{TABLE_PRODUCT}` p
           ON l.item_id = p.product_id
    LEFT JOIN `{TABLE_STUFF}` op_direct
           ON COALESCE(l.operator, h.operator) = op_direct.stuff_id
    LEFT JOIN `{TABLE_USER}` op_user
           ON COALESCE(l.operator, h.operator) = op_user.user_id
    LEFT JOIN `{TABLE_STUFF}` op_user_stuff
           ON op_user.stuff_id = op_user_stuff.stuff_id
    LEFT JOIN `{TABLE_USER}` creator_user
           ON COALESCE(l.created_by, h.created_by) = creator_user.user_id
    LEFT JOIN `{TABLE_STUFF}` creator_stuff
           ON creator_user.stuff_id = creator_stuff.stuff_id
    LEFT JOIN `{TABLE_CUSTOMER_ORDER}` co
           ON h.customer_order_id = co.customer_order_id
    {where_clause}
    ORDER BY h.io_time DESC, h.psioh_id DESC, l.line_no DESC
    LIMIT %(lim)s OFFSET %(ofs)s
    """
    df = fetch_df(sql, params)
    if not df.empty:
        io_code_to_label = {"IN": "入庫", "OUT": "出庫", "ADJUST": "調整"}
        df.insert(df.columns.get_loc("_io_type_code") + 1, "進出庫類型", df["_io_type_code"].map(io_code_to_label).fillna(df["_io_type_code"]))
        df = df.drop(columns=["_io_type_code"])
    return df



def fetch_order_schedule_status_view(order_keyword: str = "", status_filter: str = "全部", limit_rows: int = 300) -> pd.DataFrame:
    """Query per customer-order delivery schedule status from the shared SQL view."""
    conditions: List[str] = []
    params: Dict[str, Any] = {}
    kw = (order_keyword or "").strip()
    if kw:
        conditions.append("""
            (customer_order_code LIKE %(kw)s
             OR customer_order_num LIKE %(kw)s
             OR product_code LIKE %(kw)s
             OR product_name LIKE %(kw)s
             OR customer_product_id LIKE %(kw)s)
        """)
        params["kw"] = f"%{kw}%"

    if status_filter and status_filter != "全部":
        if status_filter == "逾期未完成":
            conditions.append("due_date < CURDATE() AND COALESCE(remaining_qty, 0) > 0")
        elif status_filter == "未完成":
            conditions.append("COALESCE(remaining_qty, 0) > 0")
        elif status_filter == "已完成":
            conditions.append("COALESCE(remaining_qty, 0) <= 0")
        elif status_filter == "部分出貨":
            conditions.append("computed_status = 'partial_shipped'")

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params["lim"] = int(limit_rows or 300)
    sql = f"""
        SELECT
            customer_order_code,
            customer_order_num,
            customer_name,
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
        {where_sql}
        ORDER BY due_date ASC, customer_order_code ASC, line_no ASC, schedule_no ASC
        LIMIT %(lim)s
    """
    try:
        return fetch_df(sql, params)
    except Exception:
        return pd.DataFrame()


def _s03_schedule_status_label(row: pd.Series) -> str:
    status = str(row.get("computed_status") or "open").strip()
    try:
        due = pd.to_datetime(row.get("due_date"), errors="coerce")
        remaining = float(row.get("remaining_qty") or 0)
        if pd.notna(due) and due.date() < datetime.date.today() and remaining > 0:
            return "🔴 逾期未完成"
    except Exception:
        pass
    if status == "shipped":
        return "🟢 已完成"
    if status == "partial_shipped":
        return "🟠 部分出貨"
    if status == "cancelled":
        return "⚫ 已取消"
    return "⚪ 未完成"


def render_schedule_status_query_block() -> None:
    st.markdown("---")
    st.markdown(f"#### {_t('客戶訂單每批次狀況查詢')}")
    st.caption(_t("資料來源：v_customer_order_schedule_status。可用本公司訂單號、客戶單號、料號或品名查詢。"))

    c1, c2, c3, c4 = st.columns([2.4, 1.4, 1.0, 4.2])
    with c1:
        kw = st.text_input(_t("訂單/料號/品名關鍵字"), key="s03_schedule_status_kw")
    with c2:
        status_filter = st.selectbox(_t("批次狀態"), options=["全部", "未完成", "部分出貨", "逾期未完成", "已完成"], key="s03_schedule_status_filter")
    with c3:
        st.markdown('<div style="height: 0.45rem;"></div>', unsafe_allow_html=True)
        refresh = st.button(_t("查詢批次"), use_container_width=True, key="s03_schedule_status_refresh")
    with c4:
        st.empty()

    df = fetch_order_schedule_status_view(kw, status_filter, limit_rows=300)
    if df.empty:
        st.info(_t("查無批次狀況資料，或尚未建立 View：v_customer_order_schedule_status。"))
        return
    show = df.copy()
    for col in ["schedule_qty", "delivered_qty", "remaining_qty"]:
        show[col] = pd.to_numeric(show.get(col), errors="coerce").fillna(0)
    show["狀態"] = show.apply(_s03_schedule_status_label, axis=1)
    show["產品"] = show["product_code"].fillna("").astype(str) + "｜" + show["product_name"].fillna("").astype(str)
    show["due_date"] = pd.to_datetime(show["due_date"], errors="coerce").dt.date
    display = show[[
        "customer_order_code", "customer_order_num", "customer_name", "line_no", "產品",
        "customer_product_id", "schedule_no", "due_date", "schedule_qty", "delivered_qty", "remaining_qty", "狀態"
    ]].rename(columns={
        "customer_order_code": _t("本公司訂單號"),
        "customer_order_num": _t("客戶訂單號"),
        "customer_name": _t("客戶"),
        "line_no": _t("明細行號"),
        "customer_product_id": _t("客戶料號"),
        "schedule_no": _t("批次"),
        "due_date": _t("預計交期"),
        "schedule_qty": _t("排程數量"),
        "delivered_qty": _t("已出貨數量"),
        "remaining_qty": _t("未出貨數量"),
    })
    st.dataframe(display, use_container_width=True, hide_index=True, height=200)




def fetch_order_schedule_status_by_order_id(customer_order_id: int) -> pd.DataFrame:
    """Query per-batch delivery status for one customer order from shared SQL view."""
    if not customer_order_id:
        return pd.DataFrame()
    sql = """
        SELECT
            customer_order_code,
            customer_order_num,
            customer_name,
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
        WHERE customer_order_id = %(oid)s
        ORDER BY due_date ASC, line_no ASC, schedule_no ASC
    """
    try:
        return fetch_df(sql, {"oid": int(customer_order_id)})
    except Exception:
        return pd.DataFrame()


def render_schedule_status_for_order_id(customer_order_id: int) -> None:
    st.markdown(f"#### {_t('分批訂單交貨狀況')}")
    df = fetch_order_schedule_status_by_order_id(int(customer_order_id))
    if df.empty:
        st.info(_t("查無批次狀況資料，或尚未建立 View：v_customer_order_schedule_status。"))
        return

    show = df.copy()
    for col in ["schedule_qty", "delivered_qty", "remaining_qty"]:
        show[col] = pd.to_numeric(show.get(col), errors="coerce").fillna(0)
    show["狀態"] = show.apply(_s03_schedule_status_label, axis=1)
    show["產品"] = show["product_code"].fillna("").astype(str) + "｜" + show["product_name"].fillna("").astype(str)
    show["due_date"] = pd.to_datetime(show["due_date"], errors="coerce").dt.date
    display = show[[
        "customer_order_code", "customer_order_num", "customer_name", "line_no", "產品",
        "customer_product_id", "schedule_no", "due_date", "schedule_qty", "delivered_qty", "remaining_qty", "狀態"
    ]].rename(columns={
        "customer_order_code": _t("本公司訂單號"),
        "customer_order_num": _t("客戶訂單號"),
        "customer_name": _t("客戶"),
        "line_no": _t("明細行號"),
        "customer_product_id": _t("客戶料號"),
        "schedule_no": _t("批次"),
        "due_date": _t("預計交期"),
        "schedule_qty": _t("排程數量"),
        "delivered_qty": _t("已出貨數量"),
        "remaining_qty": _t("未出貨數量"),
    })
    st.dataframe(display, use_container_width=True, hide_index=True, height=260)


_s03_status_dialog_decorator = None
if hasattr(st, "dialog"):
    try:
        _s03_status_dialog_decorator = st.dialog(_t("分批訂單交貨狀況"), width="large")
    except TypeError:
        _s03_status_dialog_decorator = st.dialog(_t("分批訂單交貨狀況"))
elif hasattr(st, "experimental_dialog"):
    try:
        _s03_status_dialog_decorator = st.experimental_dialog(_t("分批訂單交貨狀況"), width="large")
    except TypeError:
        _s03_status_dialog_decorator = st.experimental_dialog(_t("分批訂單交貨狀況"))

if _s03_status_dialog_decorator is not None:
    @_s03_status_dialog_decorator
    def _s03_order_schedule_status_dialog(customer_order_id: int) -> None:
        render_schedule_status_for_order_id(int(customer_order_id))
else:
    def _s03_order_schedule_status_dialog(customer_order_id: int) -> None:
        st.warning(_t("目前 Streamlit 版本不支援彈窗，改為在頁面內顯示。"))
        render_schedule_status_for_order_id(int(customer_order_id))

def delete_psio_lines(selected_rows: List[Dict[str, Any]]) -> int:
    auth.require_edit(PAGE_KEY)
    rows = [r for r in selected_rows if r.get("_psioh_id") is not None and r.get("_line_no") is not None]
    if not rows:
        return 0

    conn = get_connection()
    with conn.cursor() as cur:
        try:
            conn.start_transaction()
        except Exception:
            pass

        delete_sql = f"""
            DELETE FROM `{TABLE_STOCK_IO_L}`
            WHERE psioh_id=%s AND line_no=%s
        """
        params_seq = [(int(r["_psioh_id"]), int(r["_line_no"])) for r in rows]
        cur.executemany(delete_sql, params_seq)

        affected_heads = sorted({int(r["_psioh_id"]) for r in rows})
        deleted_rows = len(rows)

        for hid in affected_heads:
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM `{TABLE_STOCK_IO_L}` WHERE psioh_id=%s",
                (hid,),
            )
            row = cur.fetchone()
            remain_cnt = int((row[0] if isinstance(row, (list, tuple)) else row.get("cnt", 0)) or 0)
            if remain_cnt > 0:
                continue

            cur.execute(
                f"""
                SELECT psioh_id, doc_no, delivery_head_id
                FROM `{TABLE_STOCK_IO_H}`
                WHERE psioh_id=%s
                """,
                (hid,),
            )
            head_row = cur.fetchone()
            if not head_row:
                continue

            if isinstance(head_row, dict):
                doc_no = str(head_row.get("doc_no") or "")
                delivery_head_id = head_row.get("delivery_head_id")
            else:
                _, doc_no, delivery_head_id = head_row
                doc_no = str(doc_no or "")

            if str(doc_no).startswith("DE") and delivery_head_id:
                cur.execute("DELETE FROM `delivery_product` WHERE delivery_head_id=%s", (int(delivery_head_id),))
                cur.execute(f"DELETE FROM `{TABLE_STOCK_IO_H}` WHERE psioh_id=%s", (hid,))
                cur.execute("DELETE FROM `delivery_head` WHERE delivery_note_id=%s", (int(delivery_head_id),))
            else:
                cur.execute(f"DELETE FROM `{TABLE_STOCK_IO_H}` WHERE psioh_id=%s", (hid,))

        conn.commit()
        return deleted_rows


# ================== Session state ==================
def _ensure_state() -> None:
    st.session_state.setdefault("s03_head_locked", False)
    st.session_state.setdefault("s03_current_psioh_id", None)
    st.session_state.setdefault("s03_current_doc_no", "")

    st.session_state.setdefault("s03_reset_head_inputs", False)
    st.session_state.setdefault("s03_reset_line_inputs", False)

    st.session_state.setdefault("s03_reset_query_inputs", False)

    # query input keys
    st.session_state.setdefault("s03_q_start", datetime.date.today() - datetime.timedelta(days=30))
    st.session_state.setdefault("s03_q_end", datetime.date.today())
    st.session_state.setdefault("s03_q_io", "（全部）")
    st.session_state.setdefault("s03_q_kw", "")
    st.session_state.setdefault("s03_q_lim", 20)
    st.session_state.setdefault("s03_q_page", 1)
    st.session_state.setdefault("s03_q_product", 0)

    # head input keys (must exist before widgets)
    st.session_state.setdefault("s03_h_date", datetime.date.today())
    st.session_state.setdefault("s03_h_our_order_num", "")
    st.session_state.setdefault("s03_h_customer", "（全部）")
    st.session_state.setdefault("s03_h_customer_order_num", "")
    st.session_state.setdefault("s03_h_io_label", "入庫")
    st.session_state.setdefault("s03_h_note", "")
    st.session_state.setdefault("s03_h_operator", _t("（不指定）"))

    # line input keys
    st.session_state.setdefault("s03_l_product_id", None)
    st.session_state.setdefault("s03_l_schedule_id", None)
    st.session_state.setdefault("s03_l_qty_pcs", 0.0)
    st.session_state.setdefault("s03_l_reversed_io_id", None)
    st.session_state.setdefault("s03_l_production_num", 0)
    st.session_state.setdefault("s03_l_scan_code", "")


_ensure_state()


# ================== Reset handlers (must run before widgets) ==================
def _apply_resets() -> None:
    if st.session_state.get("s03_reset_head_inputs"):
        st.session_state["s03_h_date"] = datetime.date.today()
        st.session_state["s03_h_our_order_num"] = ""
        st.session_state["s03_h_customer"] = "（全部）"
        st.session_state["s03_h_customer_order_num"] = ""
        st.session_state["s03_h_io_label"] = "入庫"
        st.session_state["s03_h_note"] = ""
        st.session_state["s03_h_operator"] = _t("（不指定）")
        st.session_state["s03_current_doc_no"] = ""
        st.session_state["s03_reset_head_inputs"] = False

    if st.session_state.get("s03_reset_query_inputs"):
        st.session_state["s03_q_start"] = datetime.date.today() - datetime.timedelta(days=30)
        st.session_state["s03_q_end"] = datetime.date.today()
        st.session_state["s03_q_io"] = "（全部）"
        st.session_state["s03_q_kw"] = ""
        st.session_state["s03_q_lim"] = 20
        st.session_state["s03_q_page"] = 1
        st.session_state["s03_q_product"] = 0
        st.session_state["s03_reset_query_inputs"] = False

    if st.session_state.get("s03_reset_line_inputs"):
        st.session_state["s03_l_product_id"] = None
        st.session_state["s03_l_schedule_id"] = None
        st.session_state["s03_l_qty_pcs"] = 0.0
        st.session_state["s03_l_reversed_io_id"] = None
        st.session_state["s03_l_production_num"] = 0
        st.session_state["s03_l_scan_code"] = ""
        st.session_state["s03_reset_line_inputs"] = False


_apply_resets()


# ================== UI ==================
st.title(_t("S03｜產品進出庫"))

customer_options = get_customer_options()
stuff_options = get_stuff_options()
user_options = get_user_identity_options()
current_created_by_display, current_created_by_meta = get_current_user_identity(user_options)
current_created_by_user_id = int(current_created_by_meta.get("user_id") or 1)
prod_label_map = get_product_id_to_label()

# -------- 查詢條件 --------
with st.expander(_t("查詢條件"), expanded=True):
    q1 = st.columns([1.25, 1.25, 1.6, 1.8, 1.3, 0.9, 0.9, 0.9], vertical_alignment="bottom")
    with q1[0]:
        start_date = st.date_input(_t("起始日期"), key="s03_q_start")
    with q1[1]:
        end_date = st.date_input(_t("結束日期"), key="s03_q_end")
    with q1[2]:
        io_label_q = st.selectbox(_t("進出庫類型"), options=_io_options(), format_func=_t, key="s03_q_io")
    with q1[3]:
        prod_kw_q = st.text_input(_t("料號/品名關鍵字"), key="s03_q_kw")
    with q1[4]:
        product_ids_all = [0] + sorted(prod_label_map.keys())
        product_id_q = st.selectbox(
            _t("指定產品（可空白）"),
            options=product_ids_all,
            format_func=lambda x: _t("（不指定）") if int(x) == 0 else prod_label_map.get(int(x), str(x)),
            key="s03_q_product",
        )
    with q1[5]:
        prev_btn = st.button(_t("上一頁"), use_container_width=True, key="s03_prev")
    with q1[6]:
        page_size = st.selectbox(_t("顯示筆數"), options=[10, 20, 30, 50, 100], key="s03_q_lim")
    with q1[7]:
        next_btn = st.button(_t("下一頁"), use_container_width=True, key="s03_next")

    q2 = st.columns([1.0, 1.0, 0.84, 1.96])
    with q2[0]:
        run_q = st.button(_t("查詢"), use_container_width=True)
    with q2[1]:
        clear_q = st.button(_t("清除條件"), use_container_width=True)
    with q2[2]:
        refresh_q = st.button(_t("重新整理"), use_container_width=True)
    with q2[3]:
        st.empty()

if clear_q:
    st.session_state["s03_reset_query_inputs"] = True
    st.rerun()

sig = "|".join([
    str(st.session_state.get("s03_q_start")),
    str(st.session_state.get("s03_q_end")),
    str(st.session_state.get("s03_q_io", "（全部）")),
    str(st.session_state.get("s03_q_kw", "")),
    str(st.session_state.get("s03_q_product", 0)),
    str(st.session_state.get("s03_q_lim", 20)),
])
if st.session_state.get("s03_q_sig") != sig:
    st.session_state["s03_q_sig"] = sig
    st.session_state["s03_q_page"] = 1

if run_q or refresh_q:
    st.session_state["s03_q_page"] = 1

page_no = int(st.session_state.get("s03_q_page", 1))
page_size = int(st.session_state.get("s03_q_lim", 20))
total_rows = fetch_product_stock_io_count(
    start_date=st.session_state.get("s03_q_start"),
    end_date=st.session_state.get("s03_q_end"),
    product_id=int(st.session_state.get("s03_q_product") or 0) or None,
    io_label=st.session_state.get("s03_q_io", "（全部）"),
    product_kw=st.session_state.get("s03_q_kw", ""),
)
total_pages = max(1, int(math.ceil(total_rows / max(page_size, 1))))
page_no = max(1, min(page_no, total_pages))
st.session_state["s03_q_page"] = page_no

if prev_btn and page_no > 1:
    st.session_state["s03_q_page"] = page_no - 1
    st.rerun()
if next_btn and page_no < total_pages:
    st.session_state["s03_q_page"] = page_no + 1
    st.rerun()

df_view = fetch_product_stock_io_page(
    start_date=st.session_state.get("s03_q_start"),
    end_date=st.session_state.get("s03_q_end"),
    product_id=int(st.session_state.get("s03_q_product") or 0) or None,
    io_label=st.session_state.get("s03_q_io", "（全部）"),
    product_kw=st.session_state.get("s03_q_kw", ""),
    page_size=page_size,
    page_no=page_no,
)

if df_view.empty:
    st.info(_t("查無資料"))
else:
    st.caption(f"{_t('第')} {page_no} / {total_pages} {_t('頁，共')} {total_rows} {_t('筆')}")
    df_select = df_view.copy()
    df_select.insert(0, _t("勾選"), False)
    edited_df = st.data_editor(
        df_select,
        use_container_width=True,
        height=int(st.session_state.setdefault("s03_top_height", 230)),
        hide_index=True,
        disabled=[c for c in df_select.columns if c != _t("勾選")],
        column_config={
            _t("勾選"): st.column_config.CheckboxColumn(_t("勾選")),
            "_psioh_id": None,
            "_line_no": None,
            "_customer_order_id": None,
        },
        key="s03_io_table_editor",
    )

    selected_rows = edited_df[edited_df[_t("勾選")] == True]
    delete_disabled = selected_rows.empty

    selected_order_ids: List[int] = []
    if not selected_rows.empty and "_customer_order_id" in selected_rows.columns:
        for _v in selected_rows["_customer_order_id"].dropna().tolist():
            try:
                selected_order_ids.append(int(_v))
            except Exception:
                pass
        selected_order_ids = sorted(set(selected_order_ids))

    op_cols = st.columns([2.2, 1.2, 5.6])
    with op_cols[0]:
        if st.button(_t("查詢分批訂單交貨狀況"), use_container_width=True, disabled=(len(selected_order_ids) != 1), key="s03_query_schedule_status_dialog"):
            _s03_order_schedule_status_dialog(int(selected_order_ids[0]))
    with op_cols[1]:
        if st.button(_t("刪除勾選"), type="primary", disabled=delete_disabled, key="s03_delete_selected"):
            try:
                deleted_count = delete_psio_lines(selected_rows.to_dict("records"))
                st.success(f"{_t('已刪除')} {deleted_count} {_t('筆資料。')}")
                st.rerun()
            except Exception as e:
                st.error(f"{_t('刪除失敗：')}{e}")
    with op_cols[2]:
        st.caption(_t("勾選同一張訂單的任一筆進出庫紀錄後，可用彈窗查看該訂單所有批次交貨狀況。"))

    apply_vertical_splitter(
        "s03_top_height",
        "s03_vertical_splitter_control",
        default=230,
        min_top=150,
        max_top=430,
    )

st.markdown("---")
st.markdown(f"#### {_t('新增進出庫')}")


# -------- 新增區：Head + Line --------
with st.expander(_t("新增一筆產品進出庫"), expanded=True):
    head_locked = bool(st.session_state.get("s03_head_locked"))

    # Head section
    st.subheader(_t("主表（Head）"))
    r1 = st.columns([1.2, 2.0, 1.6])
    with r1[0]:
        io_date = st.date_input(_t("日期"), key="s03_h_date", disabled=head_locked)
    with r1[1]:
        our_order_num_in = st.text_input(_t("我方公司訂單號碼（輸入後自動載入明細，可空白）"), key="s03_h_our_order_num", disabled=head_locked)
    with r1[2]:
        io_label = st.selectbox(_t("進出庫類型"), options=["入庫", "出庫", "調整"], format_func=_t, key="s03_h_io_label", disabled=head_locked)

    # Auto load order
    order = get_customer_order_by_our_num(our_order_num_in) if (our_order_num_in or "").strip() else {}
    order_id = int(order["customer_order_id"]) if order else None
    order_customer_id = int(order["customer_id"]) if order and order.get("customer_id") is not None else None
    default_customer_order_num = str(order.get("customer_order_num") or "") if order else ""

    r2 = st.columns([1.6, 1.6, 1.6])
    with r2[0]:
        # Customer (lock to order's customer if order exists)
        if order_customer_id:
            # find label
            label = "（全部）"
            for k, v in customer_options.items():
                if v == order_customer_id:
                    label = k
                    break
            st.session_state["s03_h_customer"] = label
            customer_label = st.selectbox(_t("客戶"), options=list(customer_options.keys()), key="s03_h_customer", disabled=True)
        else:
            customer_label = st.selectbox(_t("客戶"), options=list(customer_options.keys()), key="s03_h_customer", disabled=head_locked)
    with r2[1]:
        customer_order_num = st.text_input(_t("客戶訂單號碼（可空白）"), key="s03_h_customer_order_num", disabled=head_locked)
        if (not customer_order_num) and default_customer_order_num and (not head_locked):
            # safe: only set before widget is instantiated? already instantiated; so use a hint only
            st.caption(f"提示：查到訂單客戶單號：{default_customer_order_num}")
    with r2[2]:
        note_head = st.text_area(_t("備註（可空白）"), key="s03_h_note", height=80, disabled=head_locked)

    r3 = st.columns([1.6, 1.6, 1.6])
    with r3[0]:
        operator_label = st.selectbox(_t("操作人員"), options=list(stuff_options.keys()), key="s03_h_operator", disabled=head_locked)
    with r3[1]:
        st.text_input(
            _t("建檔人"),
            value=current_created_by_display,
            disabled=True,
        )
        st.caption(_t("※已依目前登入帳號自動帶入"))
    with r3[2]:
        if head_locked and st.session_state.get("s03_current_doc_no"):
            st.markdown(f"**{_t('單據號：')}** `{st.session_state.get('s03_current_doc_no')}`")
        else:
            st.markdown(f"**{_t('單據號：')}**{_t('（確認後自動產生）')}")

    # order schedule preview：S03 應以 E01 的分批交期為入庫/出庫批次，不再只顯示整筆訂單明細總量。
    schedule_df_for_order = pd.DataFrame()
    io_type_code_preview = _io_type_from_label(st.session_state.get("s03_h_io_label", "入庫"))
    if order_id:
        schedule_df_for_order = get_customer_order_schedule_rows(int(order_id), io_type_code_preview)
        if not schedule_df_for_order.empty:
            st.caption(_t("已載入訂單批次（供入庫選擇）"))
            st.dataframe(
                prepare_order_schedule_display_df(schedule_df_for_order, io_type_code_preview),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning(_t("此訂單尚未建立交貨批次，請先到 E01 設定交貨排程。"))

    # Head confirm / unlock
    c1, c2, c3 = st.columns([1.2, 1.2, 2.6])
    with c1:
        confirm_head = st.button(_t("確認（鎖定主表）"), use_container_width=True, disabled=head_locked)
    with c2:
        finish = st.button(_t("完成作業（解除鎖定）"), use_container_width=True, disabled=not head_locked)
    with c3:
        st.caption(_t("流程：先填主表 → 按「確認」鎖定 → 下方連續新增明細 → 按「完成作業」開下一張。"))

    if confirm_head:
        try:
            io_map = {"入庫": "IN", "出庫": "OUT", "調整": "ADJUST"}
            io_type_code = io_map.get(st.session_state.get("s03_h_io_label", "入庫"), "IN")
            io_dt = datetime.datetime.combine(st.session_state["s03_h_date"], datetime.datetime.now().time())

            coid = order_id if order_id else None
            op_id = stuff_options.get(st.session_state.get("s03_h_operator") or "", 0) or None
            created_by_user_id = current_created_by_user_id
            note_val = (st.session_state.get("s03_h_note") or "").strip() or None

            conum = (st.session_state.get("s03_h_customer_order_num") or "").strip() or None

            psioh_id, doc_no = insert_psio_head(
                io_type=io_type_code,
                io_dt=io_dt,
                customer_order_id=coid,
                customer_order_code=coid,  # head 欄位型別為 bigint，先以 customer_order_id 對應
                customer_order_num=conum,
                operator_id=op_id,
                created_by_user_id=created_by_user_id,
                note=note_val,
            )
            st.session_state["s03_current_psioh_id"] = psioh_id
            st.session_state["s03_current_doc_no"] = doc_no
            st.session_state["s03_head_locked"] = True
            st.success(_t("主表已鎖定，可開始新增明細。"))
            st.rerun()
        except Exception as e:
            st.error(f"{_t('鎖定主表失敗：')}{e}")

    if finish:
        st.session_state["s03_head_locked"] = False
        st.session_state["s03_current_psioh_id"] = None
        st.session_state["s03_current_doc_no"] = ""
        st.session_state["s03_reset_head_inputs"] = True
        st.session_state["s03_reset_line_inputs"] = True
        st.success(_t("已完成作業並解除鎖定。"))
        st.rerun()

    # Line section
    st.subheader(_t("子表（Line）"))
    if not head_locked:
        st.info(_t("請先按「確認（鎖定主表）」再新增明細。"))
    else:
        # product options based on customer/order
        selected_customer_id: Optional[int] = None
        if order_customer_id:
            selected_customer_id = order_customer_id
        else:
            cid = customer_options.get(st.session_state.get("s03_h_customer", "（全部）"), 0)
            selected_customer_id = cid if cid else None

        io_type_code_line = _io_type_from_label(st.session_state.get("s03_h_io_label", "入庫"))
        selected_schedule_row: Optional[pd.Series] = None
        selected_schedule_id: Optional[int] = None

        if order_id:
            # 有我方訂單號時，S03 必須以 E01 的分批交期為作業對象。
            order_schedule_df = get_customer_order_schedule_rows(int(order_id), io_type_code_line)
            if order_schedule_df.empty:
                st.warning(_t("此訂單尚未建立交貨批次，請先到 E01 設定交貨排程。"))
                st.stop()

            schedule_ids = [int(x) for x in order_schedule_df["schedule_id"].dropna().tolist()]
            if st.session_state.get("s03_l_schedule_id") not in schedule_ids:
                st.session_state["s03_l_schedule_id"] = schedule_ids[0] if schedule_ids else None

            s_cols = st.columns([3.4, 2.2, 1.5, 1.3])
            with s_cols[0]:
                selected_schedule_id = st.selectbox(
                    _batch_select_label(io_type_code_line),
                    options=schedule_ids,
                    format_func=lambda x: format_schedule_option(int(x), order_schedule_df, io_type_code_line),
                    key="s03_l_schedule_id",
                )

            selected_schedule_row = order_schedule_df.loc[
                order_schedule_df["schedule_id"].astype(int) == int(selected_schedule_id)
            ].iloc[0]

            product_id = int(selected_schedule_row.get("product_id"))
            customer_material_num = str(selected_schedule_row.get("customer_product_id") or "")
            remaining_qty = float(selected_schedule_row.get("remaining_qty") or 0)

            # 批次切換時，預設數量帶入該批剩餘數量，避免使用者還看到上一批數量。
            sig_key = "s03_l_schedule_qty_signature"
            current_sig = (int(selected_schedule_id), float(remaining_qty), io_type_code_line)
            if st.session_state.get(sig_key) != current_sig:
                st.session_state["s03_l_qty_pcs"] = max(float(remaining_qty), 0.0)
                st.session_state[sig_key] = current_sig

            with s_cols[1]:
                st.text_input(
                    _t("產品"),
                    value=f"{selected_schedule_row.get('product_code','')}｜{selected_schedule_row.get('product_name','')}",
                    disabled=True,
                )
            with s_cols[2]:
                st.text_input(_t("客戶料號"), value=customer_material_num, disabled=True)
            with s_cols[3]:
                st.text_input(_t("本批剩餘數量"), value=f"{_fmt_qty(remaining_qty)} {selected_schedule_row.get('unit','')}", disabled=True)

            qty_pcs = st.number_input(_t("數量(PCS)"), min_value=0.0, step=1.0, key="s03_l_qty_pcs")
            if remaining_qty <= 0:
                st.warning(_t("此批次已無剩餘數量。"))

        else:
            # 沒有我方訂單號時，保留原本以產品做一般入庫/調整的流程。
            product_ids: List[int] = []
            if selected_customer_id:
                product_ids = get_product_ids_by_customer(int(selected_customer_id))
            if not product_ids:
                product_ids = sorted(prod_label_map.keys())

            # handle scan code -> set product selection (must happen before widget instantiate)
            scan_code = st.text_input(_t("掃描料號（內部產品號碼 / product_code）"), key="s03_l_scan_code")
            if scan_code and scan_code.strip():
                pid = get_product_id_by_code(scan_code.strip())
                if pid and pid in product_ids:
                    st.session_state["s03_l_product_id"] = pid

            r4 = st.columns([2.2, 1.0, 1.0])
            with r4[0]:
                if st.session_state.get("s03_l_product_id") not in product_ids:
                    st.session_state["s03_l_product_id"] = product_ids[0] if product_ids else None

                product_id = st.selectbox(
                    _t("產品料號/品名"),
                    options=product_ids,
                    format_func=lambda x: prod_label_map.get(int(x), str(x)),
                    key="s03_l_product_id",
                )
            meta = get_product_meta(int(product_id)) if product_id else {}
            customer_material_num = str(meta.get("customer_production_id") or "") if meta else ""
            with r4[1]:
                st.text_input(_t("客戶料號（自動帶入，不可修改）"), value=customer_material_num, disabled=True)
            with r4[2]:
                qty_pcs = st.number_input(_t("數量(PCS)"), min_value=0.0, step=1.0, key="s03_l_qty_pcs")

        r5 = st.columns([1.2, 2.4])
        with r5[0]:
            reversed_io_id = st.number_input(_t("沖銷哪一筆（可空白，數字）"), min_value=0, step=1, key="s03_l_reversed_io_id")
        with r5[1]:
            production_num = st.number_input(_t("生產批號/工單（數字，預設0）"), min_value=0, step=1, key="s03_l_production_num")

        add_line = st.button(_t("新增紀錄"), use_container_width=True)

        if add_line:
            try:
                psioh_id = int(st.session_state.get("s03_current_psioh_id") or 0)
                if psioh_id <= 0:
                    raise ValueError(_t("psioh_id 不存在，請重新鎖定主表。"))

                qty_pcs_val = float(qty_pcs or 0)
                if qty_pcs_val <= 0:
                    raise ValueError(_t("數量不可為 0，請輸入數字。"))

                selected_coi_id = None
                selected_schedule_id_for_save = None
                selected_remaining_qty = None
                if order_id and selected_schedule_row is not None:
                    selected_coi_id = int(selected_schedule_row.get("customer_order_item_id"))
                    selected_schedule_id_for_save = int(selected_schedule_row.get("schedule_id"))
                    selected_remaining_qty = float(selected_schedule_row.get("remaining_qty") or 0)
                    if not _has_stock_io_schedule_columns():
                        raise ValueError(_t("product_stock_io_line 缺少批次關聯欄位，請先執行 SQL 補欄位。"))
                    if io_type_code_line in {"IN", "OUT"} and qty_pcs_val - selected_remaining_qty > 0.0001:
                        raise ValueError(_t("輸入數量不可大於本批剩餘數量。"))

                io_map = {"入庫": "IN", "出庫": "OUT", "調整": "ADJUST"}
                io_type_code = io_map.get(st.session_state.get("s03_h_io_label", "入庫"), "IN")
                io_dt = datetime.datetime.combine(st.session_state["s03_h_date"], datetime.datetime.now().time())

                coid = order_id if order_id else None
                conum = (st.session_state.get("s03_h_customer_order_num") or "").strip() or None

                op_id = stuff_options.get(st.session_state.get("s03_h_operator") or "", 0) or None
                created_by_user_id = current_created_by_user_id

                note_val = (st.session_state.get("s03_h_note") or "").strip() or None
                rev_val = int(reversed_io_id) if reversed_io_id and int(reversed_io_id) > 0 else None

                insert_psio_line(
                    psioh_id=psioh_id,
                    io_dt=io_dt,
                    item_id=int(product_id),
                    customer_material_num=customer_material_num or None,
                    production_num=int(production_num or 0),
                    qty_pcs=qty_pcs_val,
                    carton_used=None,
                    operator_id=op_id,
                    created_by_user_id=created_by_user_id,
                    note=note_val,
                    reversed_io_id=rev_val,
                    customer_order_item_id=selected_coi_id,
                    schedule_id=selected_schedule_id_for_save,
                )
                st.success(_t("新增成功。"))
                # 清 line inputs（用 reset flag）
                st.session_state["s03_reset_line_inputs"] = True
                st.rerun()
            except Exception as e:
                st.error(f"{_t('寫入失敗：')}{e}")
