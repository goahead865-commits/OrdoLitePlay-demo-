# AR_01.py
import streamlit as st
import auth
from compact_layout import apply_compact_layout
import pandas as pd
from datetime import date, timedelta
from math import ceil
from decimal import Decimal, ROUND_HALF_UP

apply_compact_layout()

from db import get_connection

PAGE_KEY = "AR01_Accounts Receivable"

# =============================
# Safe I18N helper
# =============================
TRANSLATIONS = {
    "應收帳款（AR）": {"vi": "Công nợ phải thu (AR)", "en": "Accounts Receivable (AR)"},
    "應收帳款統計": {"vi": "Thống kê công nợ phải thu", "en": "AR Summary"},
    "起始日期": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "客戶名稱": {"vi": "Tên khách hàng", "en": "Customer Name"},
    "(全部)": {"vi": "(Tất cả)", "en": "(All)"},
    "上一頁": {"vi": "Trang trước", "en": "Previous Page"},
    "下一頁": {"vi": "Trang sau", "en": "Next Page"},
    "顯示筆數": {"vi": "Số dòng hiển thị", "en": "Rows per page"},
    "查無資料。": {"vi": "Không tìm thấy dữ liệu.", "en": "No data found."},
    "明細編輯區": {"vi": "Khu vực chỉnh sửa chi tiết", "en": "Detail Editor"},
    "基本資訊": {"vi": "Thông tin cơ bản", "en": "Basic Information"},
    "我方送貨明細": {"vi": "Chi tiết giao hàng của chúng tôi", "en": "Our Delivery Details"},
    "匯款狀況": {"vi": "Tình trạng thanh toán", "en": "Payment Status"},
    "請先在上方列表勾選一筆應收帳款。": {"vi": "Vui lòng chọn một khoản phải thu ở danh sách phía trên trước.", "en": "Please select one AR record from the list above first."},
    "基本資料": {"vi": "Dữ liệu cơ bản", "en": "Basic Data"},
    "應收帳款單號": {"vi": "Mã công nợ phải thu", "en": "AR Code"},
    "客戶種類": {"vi": "Loại khách hàng", "en": "Customer Category"},
    "我方送貨單號": {"vi": "Mã phiếu giao hàng của chúng tôi", "en": "Our Delivery Code"},
    "客戶訂單號碼": {"vi": "Số đơn hàng khách hàng", "en": "Customer Order No."},
    "送貨日期": {"vi": "Ngày giao hàng", "en": "Delivery Date"},
    "我方發票號碼": {"vi": "Số hóa đơn của chúng tôi", "en": "Our Invoice No."},
    "發票日期": {"vi": "Ngày hóa đơn", "en": "Invoice Date"},
    "結帳日期": {"vi": "Ngày chốt công nợ", "en": "Checkout Date"},
    "付款天數": {"vi": "Số ngày thanh toán", "en": "Payment Days"},
    "應收款日期": {"vi": "Ngày phải thu", "en": "Receivable Date"},
    "應收款日期(計算)": {"vi": "Ngày phải thu (tính toán)", "en": "Receivable Date (Calculated)"},
    "金額(未含稅、折扣、折讓)": {"vi": "Số tiền (chưa thuế, chưa chiết khấu/giảm trừ)", "en": "Amount (Before Tax/Discount/Allowance)"},
    "折扣、折讓金額": {"vi": "Số tiền chiết khấu/giảm trừ", "en": "Discount / Allowance"},
    "未稅金額(原始)": {"vi": "Số tiền chưa thuế (gốc)", "en": "Untaxed Amount (Original)"},
    "折扣後未稅": {"vi": "Chưa thuế sau chiết khấu", "en": "Untaxed After Discount"},
    "稅率": {"vi": "Thuế suất", "en": "Tax Rate"},
    "含稅金額": {"vi": "Số tiền gồm thuế", "en": "Tax Included Amount"},
    "幣別": {"vi": "Tiền tệ", "en": "Currency"},
    "匯率": {"vi": "Tỷ giá", "en": "Exchange Rate"},
    "備註": {"vi": "Ghi chú", "en": "Note"},
    "儲存/建立AR": {"vi": "Lưu / Tạo AR", "en": "Save / Create AR"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "已保存 ✅": {"vi": "Đã lưu ✅", "en": "Saved ✅"},
    "我方送貨明細": {"vi": "Chi tiết giao hàng của chúng tôi", "en": "Our Delivery Details"},
    "此 AR 未關聯 delivery_id。": {"vi": "AR này chưa liên kết với delivery_id.", "en": "This AR is not linked to delivery_id."},
    "此送貨單沒有明細。": {"vi": "Phiếu giao hàng này không có chi tiết.", "en": "This delivery has no details."},
    "我方送貨單金額加總：": {"vi": "Tổng tiền phiếu giao hàng của chúng tôi:", "en": "Our Delivery Total:"},
    "客戶付款紀錄": {"vi": "Lịch sử thanh toán của khách hàng", "en": "Customer Payment Records"},
    "尚無付款紀錄。": {"vi": "Hiện chưa có bản ghi thanh toán.", "en": "No payment records yet."},
    "編輯": {"vi": "Chỉnh sửa", "en": "Edit"},
    "刪除": {"vi": "Xóa", "en": "Delete"},
    "已刪除付款紀錄 ✅": {"vi": "Đã xóa bản ghi thanh toán ✅", "en": "Payment record deleted ✅"},
    "新增/編輯": {"vi": "Thêm mới / Chỉnh sửa", "en": "Add / Edit"},
    "此筆 AR 已付清（settled）。依規格不可再新增任何付款。": {"vi": "AR này đã thanh toán xong (settled). Theo quy định không thể thêm thanh toán mới.", "en": "This AR is settled. No new payments can be added."},
    "付款日期": {"vi": "Ngày thanh toán", "en": "Payment Date"},
    "付款方式": {"vi": "Phương thức thanh toán", "en": "Payment Method"},
    "應付金額": {"vi": "Số tiền phải thu", "en": "Receivable Amount"},
    "實付金額": {"vi": "Số tiền thực thu", "en": "Actual Paid Amount"},
    "餘額(自動)": {"vi": "Số dư (tự động)", "en": "Balance (Auto)"},
    "銀行(客戶付款銀行)": {"vi": "Ngân hàng (ngân hàng khách hàng chuyển)", "en": "Bank (Customer Paying Bank)"},
    "匯款到我方銀行": {"vi": "Chuyển vào ngân hàng của chúng tôi", "en": "Remit to Our Bank"},
    "支票號碼(可空)": {"vi": "Số séc (có thể để trống)", "en": "Cheque No. (Optional)"},
    "儲存付款紀錄": {"vi": "Lưu bản ghi thanh toán", "en": "Save Payment Record"},
    "取消編輯": {"vi": "Hủy chỉnh sửa", "en": "Cancel Edit"},
    "付款紀錄已儲存 ✅": {"vi": "Đã lưu bản ghi thanh toán ✅", "en": "Payment record saved ✅"},
    "找不到要編輯的付款紀錄（可能剛剛被刪了）。已回到新增模式。": {"vi": "Không tìm thấy bản ghi thanh toán cần chỉnh sửa. Đã quay về chế độ thêm mới.", "en": "The payment record to edit was not found. Returned to add mode."},

    # 表格欄位
    "勾選": {"vi": "Chọn", "en": "Select"},
    "ID": {"vi": "ID", "en": "ID"},
    "應收帳款ID": {"vi": "ID công nợ phải thu", "en": "AR ID"},
    "狀態": {"vi": "Trạng thái", "en": "Status"},
    "我方送貨日期": {"vi": "Ngày giao hàng của chúng tôi", "en": "Our Delivery Date"},
    "折扣折讓": {"vi": "Chiết khấu / giảm trừ", "en": "Discount / Allowance"},
    "付款ID": {"vi": "ID thanh toán", "en": "Payment ID"},
    "客戶付款日期": {"vi": "Ngày khách thanh toán", "en": "Customer Payment Date"},
    "餘額": {"vi": "Số dư", "en": "Balance"},
    "銀行": {"vi": "Ngân hàng", "en": "Bank"},
    "銀行帳號": {"vi": "Số tài khoản ngân hàng", "en": "Bank Account"},
    "我方銀行": {"vi": "Ngân hàng của chúng tôi", "en": "Our Bank"},
    "我方銀行帳號": {"vi": "Số tài khoản ngân hàng của chúng tôi", "en": "Our Bank Account"},
    "客戶料號": {"vi": "Mã hàng khách", "en": "Customer Item Code"},
    "我方產品編號": {"vi": "Mã sản phẩm của chúng tôi", "en": "Our Product Code"},
    "產品名稱": {"vi": "Tên sản phẩm", "en": "Product Name"},
    "規格": {"vi": "Quy cách", "en": "Specification"},
    "數量": {"vi": "Số lượng", "en": "Quantity"},
    "單位": {"vi": "Đơn vị", "en": "Unit"},
    "單價": {"vi": "Đơn giá", "en": "Unit Price"},
    "小計": {"vi": "Thành tiền", "en": "Subtotal"},
    "未稅金額": {"vi": "Số tiền chưa thuế", "en": "Untaxed Amount"},
    "燈號": {"vi": "Đèn trạng thái", "en": "Signal"},
    "付款狀況": {"vi": "Tình trạng thanh toán", "en": "Payment Status"},
    "未付款": {"vi": "Chưa thanh toán", "en": "Unpaid"},
    "部分付款": {"vi": "Thanh toán một phần", "en": "Partially Paid"},
    "已付款": {"vi": "Đã thanh toán", "en": "Paid"},
    "建檔人員": {"vi": "Người tạo", "en": "Created By"},
    "建檔時間": {"vi": "Thời gian tạo", "en": "Created At"},
    "最後修改人": {"vi": "Người sửa cuối", "en": "Last Modified By"},
    "修改時間": {"vi": "Thời gian sửa", "en": "Modified At"},
}

def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    return lang if lang in {"zh", "vi", "en"} else "zh"

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)


def _translate_table_headers(df: pd.DataFrame, label_map: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Return a display dataframe with localized headers and a reverse map for restoring internal names."""
    if df is None:
        return df, {}
    label_map = label_map or {}
    rename_map = {}
    reverse_map = {}
    used = set()
    for col in df.columns:
        label_key = label_map.get(col, col)
        translated = _t(str(label_key))
        if translated in used:
            translated = f"{translated} ({col})"
        rename_map[col] = translated
        reverse_map[translated] = col
        used.add(translated)
    return df.rename(columns=rename_map), reverse_map


def _restore_table_headers(df: pd.DataFrame, reverse_map: dict) -> pd.DataFrame:
    if df is None or not reverse_map:
        return df
    return df.rename(columns={c: reverse_map.get(c, c) for c in df.columns})


# ==================================================
# DB helpers
# ==================================================
def q(conn, sql, params=None):
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or [])
    rows = cur.fetchall()
    cur.close()
    # 避免 MySQL 連線長時間停在舊的 InnoDB snapshot，造成畫面讀到舊資料。
    try:
        conn.commit()
    except Exception:
        pass
    return rows

def exec_sql(conn, sql, params=None):
    # Permission guard: AR01 only distinguishes delete vs edit.
    # Payment insert/update is still an edit action on this page; do not require approve,
    # otherwise users with 可編輯 / 可刪除 but without 可核准 will be incorrectly blocked.
    sql_l = (sql or '').lstrip()
    sql_u = sql_l.upper()
    if sql_u.startswith('DELETE'):
        auth.require_delete(PAGE_KEY)
    else:
        auth.require_edit(PAGE_KEY)
    cur = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    cur.close()

def get_table_columns(conn, table_name: str):
    rows = q(conn, """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
    """, [table_name])
    return {r["COLUMN_NAME"] for r in rows}


def table_exists(conn, table_name: str) -> bool:
    try:
        rows = q(conn, """
            SELECT 1 AS ok
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            LIMIT 1
        """, [table_name])
        return bool(rows)
    except Exception:
        return False


def _qcol(col_name: str) -> str:
    return "`" + str(col_name).replace("`", "``") + "`"


def _first_existing(cols: set[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None


def current_user_id() -> int:
    try:
        return int(st.session_state.get("user_id", 1) or 1)
    except Exception:
        return 1


def fetch_user_display_map(conn, user_ids) -> dict[int, str]:
    """Map user_id to display name; prefer stuff.stuff_name over login/account."""
    clean_ids = sorted({int(x) for x in (user_ids or []) if x not in (None, "")})
    if not clean_ids:
        return {}

    fallback = {uid: f"User#{uid}" for uid in clean_ids}
    if not table_exists(conn, "user"):
        return fallback

    try:
        user_cols = get_table_columns(conn, "user")
    except Exception:
        return fallback
    if "user_id" not in user_cols:
        return fallback

    placeholders = ",".join(["%s"] * len(clean_ids))
    result = dict(fallback)

    # Best path: user.stuff_id -> stuff.stuff_name, so the grid shows real staff names.
    if "stuff_id" in user_cols and table_exists(conn, "stuff"):
        try:
            stuff_cols = get_table_columns(conn, "stuff")
        except Exception:
            stuff_cols = set()
        if {"stuff_id", "stuff_name"}.issubset(stuff_cols):
            try:
                rows = q(conn, f"""
                    SELECT u.user_id,
                           COALESCE(NULLIF(s.stuff_name, ''), CAST(u.user_id AS CHAR)) AS display_name
                    FROM `user` u
                    LEFT JOIN stuff s ON s.stuff_id = u.stuff_id
                    WHERE u.user_id IN ({placeholders})
                """, clean_ids)
                for r in rows:
                    uid = int(r.get("user_id"))
                    name = str(r.get("display_name") or "").strip()
                    if name and name != str(uid):
                        result[uid] = name
            except Exception:
                pass

    # Fallback: readable fields first; login/account fields last.
    display_candidates = [
        "display_name", "full_name", "real_name", "name", "staff_name", "user_name",
        "username", "account", "login_name", "user_code",
    ]
    display_cols = [c for c in display_candidates if c in user_cols]
    if display_cols:
        expr = "COALESCE(" + ", ".join([f"NULLIF({_qcol(c)}, '')" for c in display_cols]) + ", CAST(`user_id` AS CHAR))"
        try:
            rows = q(conn, f"""
                SELECT user_id, {expr} AS display_name
                FROM `user`
                WHERE user_id IN ({placeholders})
            """, clean_ids)
            for r in rows:
                uid = int(r.get("user_id"))
                if result.get(uid) and result.get(uid) != f"User#{uid}":
                    continue
                name = str(r.get("display_name") or "").strip()
                if name:
                    result[uid] = name
        except Exception:
            pass

    return result


def _format_datetime_blank(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        s = str(value)
        return "" if s == "NaT" else s


def build_ar_audit_display(conn, df: pd.DataFrame) -> pd.DataFrame:
    """Return 建檔人員 / 建檔時間 / 最後修改人 / 修改時間 for AR master rows."""
    cols = ["建檔人員", "建檔時間", "最後修改人", "修改時間"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)

    created_ids = []
    updated_ids = []
    if "audit_created_by" in df.columns:
        created_ids = pd.to_numeric(df["audit_created_by"], errors="coerce").dropna().astype(int).tolist()
    if "audit_updated_by" in df.columns:
        updated_ids = pd.to_numeric(df["audit_updated_by"], errors="coerce").dropna().astype(int).tolist()
    user_map = fetch_user_display_map(conn, created_ids + updated_ids)

    def _uid(v):
        try:
            if v is None or pd.isna(v):
                return None
            return int(v)
        except Exception:
            return None

    rows = []
    for _, r in df.iterrows():
        created_by = r.get("audit_created_by") if "audit_created_by" in df.columns else None
        updated_by = r.get("audit_updated_by") if "audit_updated_by" in df.columns else None
        created_at = r.get("audit_created_at") if "audit_created_at" in df.columns else None
        updated_at = r.get("audit_updated_at") if "audit_updated_at" in df.columns else None

        c_uid = _uid(created_by)
        u_uid = _uid(updated_by)
        created_name = user_map.get(c_uid, "") if c_uid else ""
        created_time = _format_datetime_blank(created_at)

        same_as_created = False
        try:
            ca = pd.to_datetime(created_at) if created_at is not None and not pd.isna(created_at) else None
            ua = pd.to_datetime(updated_at) if updated_at is not None and not pd.isna(updated_at) else None
            if ca is not None and ua is not None:
                same_as_created = abs((ua - ca).total_seconds()) <= 1
        except Exception:
            same_as_created = False

        not_modified = (u_uid is None and not _format_datetime_blank(updated_at)) or (same_as_created and (u_uid is None or u_uid == c_uid))
        if not_modified:
            updated_name = ""
            updated_time = ""
        else:
            updated_name = user_map.get(u_uid, "") if u_uid else ""
            updated_time = _format_datetime_blank(updated_at)

        rows.append({
            "建檔人員": created_name,
            "建檔時間": created_time,
            "最後修改人": updated_name,
            "修改時間": updated_time,
        })

    return pd.DataFrame(rows)


def touch_ar_statement_head(conn, statement_id: int | None) -> None:
    """Mark AR head as modified by the current logged-in user, when audit columns exist."""
    if not statement_id:
        return
    try:
        cols = get_table_columns(conn, "ar_statement_head")
    except Exception:
        return

    set_parts = []
    params = []

    updated_by_col = _first_existing(cols, ["updated_by", "updated_by_id", "modified_by", "modify_by", "last_modified_by"])
    updated_at_col = _first_existing(cols, ["updated_at", "update_at", "modified_at", "modify_at", "last_modified_at"])

    if updated_by_col:
        set_parts.append(f"{_qcol(updated_by_col)}=%s")
        params.append(current_user_id())
    if updated_at_col:
        set_parts.append(f"{_qcol(updated_at_col)}=NOW()")

    if not set_parts:
        return

    params.append(int(statement_id))
    exec_sql(conn, f"UPDATE ar_statement_head SET {', '.join(set_parts)} WHERE statement_id=%s", params)


def force_refresh_ar01(conn=None):
    """Refresh AR01 by releasing current DB transaction/connection and clearing selected rows."""
    try:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass

    # Clear current row/payment selection so old selected detail data does not stay on screen.
    for key in ["ar_selected_id", "ar_pay_selected_id", "ar_pay_edit_id"]:
        try:
            st.session_state[key] = None
        except Exception:
            pass

    try:
        st.cache_data.clear()
    except Exception:
        pass

# ==================================================
# Utils
# ==================================================
def money(x):
    if x is None:
        return None
    try:
        return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None

def default_date_range(today: date):
    # 規格：1~25 -> start=上月26；26~月底 -> start=本月26；end=今天
    if today.day <= 25:
        y = today.year
        m = today.month - 1
        if m == 0:
            m = 12
            y -= 1
        start = date(y, m, 26)
    else:
        start = date(today.year, today.month, 26)
    return start, today

def add_days_assume_30(d: date, days: int) -> date:
    """交易慣例每月=30天：75天=+2個月+15天"""
    if d is None or days is None:
        return None
    months = int(days) // 30
    rem = int(days) % 30

    y, m = d.year, d.month + months
    while m > 12:
        m -= 12
        y += 1

    last_day = (date(y, m, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    day = min(d.day, last_day.day)
    base = date(y, m, day)
    return base + timedelta(days=rem)

def calc_checkout_date(deliver_date: date, checkout_day: int) -> date:
    """
    例：checkout_day=20
    - 送貨日 1~20 -> 當月20
    - 送貨日 21~月底 -> 下月20
    """
    if deliver_date is None or not checkout_day:
        return None
    checkout_day = max(1, min(31, int(checkout_day)))
    current_last_day = (
        (date(deliver_date.year, deliver_date.month, 28) + timedelta(days=4)).replace(day=1)
        - timedelta(days=1)
    )
    current_checkout_day = min(checkout_day, current_last_day.day)

    if deliver_date.day <= current_checkout_day:
        return date(deliver_date.year, deliver_date.month, current_checkout_day)

    y, m = deliver_date.year, deliver_date.month + 1
    if m == 13:
        m = 1
        y += 1
    last_day = (date(y, m, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return date(y, m, min(checkout_day, last_day.day))

def safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

# ==================================================
# Payment column mapping (兼容舊欄位名/新欄位名)
# ==================================================
def payment_colmap(cols: set[str]):
    """
    你目前 dump 的欄位名是：final_total / actual_amount_paid / balance
    我之前建議的新欄位名是：payable_amount / paid_amount / balance_amount
    這裡兩套都支援。
    """
    payable = "payable_amount" if "payable_amount" in cols else "final_total"
    paid = "paid_amount" if "paid_amount" in cols else ("actual_amount_paid" if "actual_amount_paid" in cols else "paid_amount")
    bal = "balance_amount" if "balance_amount" in cols else "balance"
    return payable, paid, bal


def sync_ar_head_payment_status(conn, statement_id: int | None) -> None:
    """Keep the AR head status consistent with all non-void payment rows."""
    if not statement_id:
        return
    payment_cols = get_table_columns(conn, "ar_apyable_payment")
    _, paid_column, _ = payment_colmap(payment_cols)
    rows = q(conn, f"""
        SELECT
            COALESCE(h.final_total, 0) AS total_amount,
            COALESCE(SUM(CASE
                WHEN COALESCE(p.status, 'unpaid') <> 'void'
                THEN COALESCE(p.`{paid_column}`, 0)
                ELSE 0
            END), 0) AS received_amount
        FROM ar_statement_head h
        LEFT JOIN ar_apyable_payment p ON p.ar_id = h.statement_id
        WHERE h.statement_id = %s
        GROUP BY h.statement_id, h.final_total
    """, [int(statement_id)])
    if not rows:
        return

    total = Decimal(str(rows[0].get("total_amount") or 0))
    received = Decimal(str(rows[0].get("received_amount") or 0))
    if total > 0 and received >= total:
        status = "closed"
    elif received > 0:
        status = "confirmed"
    else:
        status = "draft"

    exec_sql(conn, """
        UPDATE ar_statement_head
        SET status=%s, updated_by=%s, updated_at=NOW()
        WHERE statement_id=%s
    """, [status, current_user_id(), int(statement_id)])

# ==================================================
# Page
# ==================================================
def run():
    auth.require_read(PAGE_KEY)
    st.title(_t("應收帳款（AR）"))

    # --- session_state defaults (avoid AttributeError) ---
    if "ar_selected_id" not in st.session_state:
        st.session_state.ar_selected_id = None


    st.markdown("""
<style>
/* 明細編輯區：外框 */
.detail-editor {
  background: #eaf2ff;
  border-radius: 10px;
  padding: 18px 18px 8px 18px;
  border: 1px solid rgba(0,0,0,0.05);
}

/* 標題 */
.detail-editor h2 {
  margin: 0 0 10px 0;
  font-size: 34px;
  font-weight: 900;
}

/* tabs 上方那條線的感覺 */
.detail-editor .tabs-wrap {
  border-bottom: 2px solid rgba(0,0,0,0.08);
  padding-bottom: 6px;
  margin-bottom: 12px;
}

/* Streamlit tabs 字體更像你圖上的小標 */
.detail-editor button[role="tab"] {
  font-size: 16px !important;
  padding: 6px 10px !important;
}

/* 讓 st.info 更接近你圖上的藍底提示 */
.detail-editor .stAlert {
  background: rgba(53, 130, 255, 0.12) !important;
  border: 1px solid rgba(53, 130, 255, 0.25) !important;
}

/* 基本資料區：全部字體黑色 */
.basic-black, .basic-black * {
  color: #000 !important;
}
.basic-black input, .basic-black textarea {
  color: #000 !important;
}

/* 金額區上方灰色細線（只要一條） */
.amount-topline {
  border-top: 1px solid rgba(0,0,0,0.25);
  margin: 10px 0 10px 0;
}

</style>
""", unsafe_allow_html=True)

    conn = get_connection()

    head_cols = get_table_columns(conn, "ar_statement_head")
    pay_cols = get_table_columns(conn, "ar_apyable_payment")

    audit_created_by_col = _first_existing(head_cols, ["created_by", "created_by_id", "create_by", "created_user_id", "create_user_id"])
    audit_created_at_col = _first_existing(head_cols, ["created_at", "create_at", "created_time", "create_time"])
    audit_updated_by_col = _first_existing(head_cols, ["updated_by", "updated_by_id", "modified_by", "modify_by", "last_modified_by"])
    audit_updated_at_col = _first_existing(head_cols, ["updated_at", "update_at", "modified_at", "modify_at", "last_modified_at"])
    audit_created_by_expr = f"h.{_qcol(audit_created_by_col)}" if audit_created_by_col else "NULL"
    audit_created_at_expr = f"h.{_qcol(audit_created_at_col)}" if audit_created_at_col else "NULL"
    audit_updated_by_expr = f"h.{_qcol(audit_updated_by_col)}" if audit_updated_by_col else "NULL"
    audit_updated_at_expr = f"h.{_qcol(audit_updated_at_col)}" if audit_updated_at_col else "NULL"

    has_due_date = "ar_due_date" in head_cols  # 若你有加就可保存
    payable_col, paid_col, bal_col = payment_colmap(pay_cols)

    # -----------------------------
    # Query area + pagination controls (same row height)
    # -----------------------------
    today = date.today()
    d0, d1 = default_date_range(today)

    st.subheader(_t("應收帳款統計"))

    if "ar_page" not in st.session_state:
        st.session_state.ar_page = 1
    if "ar_page_size" not in st.session_state:
        st.session_state.ar_page_size = 10

    # 依目前元件相對比例，直接把整排撐滿，不再保留中間多餘留白
    colA, colB, colD, colNavPrev, colPageSize, colNavNext = st.columns([1.0, 1.0, 2.0, 0.55, 0.9, 0.55], vertical_alignment="bottom")
    with colA:
        date_from = st.date_input(_t("起始日期"), value=d0)
    with colB:
        date_to = st.date_input(_t("結束日期"), value=d1)

    names = q(conn, """
        SELECT DISTINCT h.customer_name
        FROM ar_statement_head h
        INNER JOIN delivery_head dh
                ON dh.delivery_note_id = h.delivery_id
        LEFT JOIN customer_order co
               ON co.customer_order_id = dh.customer_order_id
        LEFT JOIN sample_order_head so
               ON so.sample_order_id = dh.sample_order_id
        WHERE h.deliver_date BETWEEN %s AND %s
          AND COALESCE(co.customer_order_category, 'general') <> 'material_replenishment_non_receivable'
          AND (dh.sample_order_id IS NULL OR COALESCE(so.sample_category, 'receivable') <> 'non_receivable')
          AND h.customer_name IS NOT NULL
        ORDER BY h.customer_name
    """, [date_from, date_to])
    name_opts = [_t("(全部)")] + [r["customer_name"] for r in names]
    with colD:
        name_sel = st.selectbox(_t("客戶名稱"), name_opts, index=0)

    # 同列放分頁控制，讓上一頁 / 每頁筆數 / 下一頁與上方三個查詢欄位保持同一高度
    with colNavPrev:
        _nav_prev_ph = st.empty()

    with colPageSize:
        st.selectbox("", [10, 20, 30, 50, 100], key="ar_page_size", label_visibility="collapsed")
        page_size = int(st.session_state.ar_page_size)

    with colNavNext:
        _nav_next_ph = st.empty()

    # -----------------------------
    # Main list
    # -----------------------------
    # 不收款補料單不可出現在 AR；即使是舊資料曾被觸發器建立 AR，
    # 此條件仍可避免它被列入後續收款作業。
    where = [
        "h.deliver_date BETWEEN %s AND %s",
        "COALESCE(co.customer_order_category, 'general') <> 'material_replenishment_non_receivable'",
        "(dh.sample_order_id IS NULL OR COALESCE(so.sample_category, 'receivable') <> 'non_receivable')",
    ]
    params = [date_from, date_to]
    if name_sel != _t("(全部)"):
        where.append("h.customer_name = %s")
        params.append(name_sel)
    where_sql = " AND ".join(where)

    total = q(conn, f"""
        SELECT COUNT(*) AS cnt
        FROM ar_statement_head h
        INNER JOIN delivery_head dh
                ON dh.delivery_note_id = h.delivery_id
        LEFT JOIN customer_order co
               ON co.customer_order_id = dh.customer_order_id
        LEFT JOIN sample_order_head so
               ON so.sample_order_id = dh.sample_order_id
        WHERE {where_sql}
    """, params)[0]["cnt"]

    total_pages = max(1, ceil(total / page_size))
    # keep page in range
    if st.session_state.ar_page > total_pages:
        st.session_state.ar_page = total_pages
    if st.session_state.ar_page < 1:
        st.session_state.ar_page = 1

    def _go_prev_page():
        st.session_state.ar_page = max(1, st.session_state.ar_page - 1)

    def _go_next_page():
        st.session_state.ar_page = min(total_pages, st.session_state.ar_page + 1)
    # Render pagination controls into placeholders created in the query row
    with _nav_prev_ph:
        st.button(
            _t("上一頁"),
            on_click=_go_prev_page,
            use_container_width=True,
            disabled=(st.session_state.ar_page <= 1),
        )
    with _nav_next_ph:
        st.button(
            _t("下一頁"),
            on_click=_go_next_page,
            use_container_width=True,
            disabled=(st.session_state.ar_page >= total_pages),
        )

    offset = (st.session_state.ar_page - 1) * page_size

    # 母表付款狀態：直接彙總付款紀錄，避免只看 ar_statement_head.status 而吃不到最新付款狀況。
    rows = q(conn, f"""
        SELECT
            h.statement_id,
            h.statement_code,
            h.delivery_code,
            h.customer_category,
            h.customer_name,
            h.customer_order_number,
            h.deliver_date,
            h.our_invoice_number,
            /* non_tax_amount 一律顯示原始未稅金額（= amount_total） */
            h.amount_total AS non_tax_amount,
            h.adjustment_amount,
            (h.amount_total - COALESCE(h.adjustment_amount, 0)) AS amount_after_adjustment,
            h.tax_rate,
            h.final_total,
            COALESCE(pay.paid_amount_total, 0) AS paid_amount_total,
            GREATEST(COALESCE(h.final_total, 0) - COALESCE(pay.paid_amount_total, 0), 0) AS balance_amount_calc,
            CASE
                WHEN COALESCE(pay.paid_amount_total, 0) <= 0 THEN '未付款'
                WHEN COALESCE(pay.paid_amount_total, 0) >= COALESCE(h.final_total, 0) THEN '已付款'
                ELSE '部分付款'
            END AS payment_status_text,
            CASE
                WHEN COALESCE(pay.paid_amount_total, 0) <= 0 THEN '🔴'
                WHEN COALESCE(pay.paid_amount_total, 0) >= COALESCE(h.final_total, 0) THEN '🟢'
                ELSE '🟡'
            END AS payment_light,
            {"h.ar_due_date AS ar_due_date," if has_due_date else "NULL AS ar_due_date,"}
            h.status,
            h.note,
            h.customer_id,
            {audit_created_by_expr} AS audit_created_by,
            {audit_created_at_expr} AS audit_created_at,
            {audit_updated_by_expr} AS audit_updated_by,
            {audit_updated_at_expr} AS audit_updated_at
        FROM ar_statement_head h
        INNER JOIN delivery_head dh
                ON dh.delivery_note_id = h.delivery_id
        LEFT JOIN customer_order co
               ON co.customer_order_id = dh.customer_order_id
        LEFT JOIN sample_order_head so
               ON so.sample_order_id = dh.sample_order_id
        LEFT JOIN (
            SELECT
                ar_id,
                SUM(COALESCE(p.`{paid_col}`, 0)) AS paid_amount_total
            FROM ar_apyable_payment p
            WHERE COALESCE(p.status, 'unpaid') <> 'void'
            GROUP BY ar_id
        ) pay ON pay.ar_id = h.statement_id
        WHERE {where_sql}
        ORDER BY h.deliver_date DESC, h.statement_id DESC
        LIMIT %s OFFSET %s
    """, params + [page_size, offset])

    st.divider()
    st.write(f"筆數：{total}（本頁 {len(rows)}）")

    if not rows:
        st.info(_t("查無資料。"))
        refresh_col, _ = st.columns([1.1, 5.5], vertical_alignment="center")
        with refresh_col:
            if st.button(_t("重新整理"), key="ar01_refresh_master_table_empty", use_container_width=True):
                force_refresh_ar01(conn)
                st.rerun()
        # 仍然顯示下方三區（空白）
        render_bottom(conn, None, None, has_due_date, payable_col, paid_col, bal_col, pay_cols)
        return

    df = pd.DataFrame(rows)

    # 預先抓客戶結帳日/付款天數（優先 customer 表，沒有就用 head 快照欄位）
    cust_ids = df["customer_id"].dropna().unique().tolist()
    cust_map = {}
    if cust_ids:
        cust_rows = q(conn, f"""
            SELECT customer_id, checkout_day, payment_term
            FROM customer
            WHERE customer_id IN ({",".join(["%s"]*len(cust_ids))})
        """, cust_ids)
        cust_map = {r["customer_id"]: r for r in cust_rows}

    def computed_checkout_and_due(row):
        cid = row["customer_id"]
        deliver = row["deliver_date"]
        # fallback 1: customer table
        checkout_day = None
        payment_term = None
        c = cust_map.get(cid)
        if c:
            checkout_day = c.get("checkout_day")
            payment_term = c.get("payment_term")
        # fallback 2: snapshot in head
        if checkout_day is None and "checkout_day" in df.columns:
            checkout_day = row.get("checkout_day")
        if payment_term is None and "customer_payment_days" in df.columns:
            payment_term = row.get("customer_payment_days")

        checkout_dt = calc_checkout_date(deliver, safe_int(checkout_day, 0)) if checkout_day else None
        due_dt = add_days_assume_30(checkout_dt, safe_int(payment_term, 0)) if (checkout_dt and payment_term) else None
        return checkout_dt, due_dt

    # 計算應收日期（若 DB 沒存 ar_due_date 就顯示計算值）
    due_list = []
    for _, r in df.iterrows():
        _, due_dt = computed_checkout_and_due(r)
        due_list.append(r["ar_due_date"] if pd.notna(r["ar_due_date"]) else due_dt)
    df["應收日期"] = due_list

    # 勾選欄：statement_id 保留在內部 show，不顯示在母表畫面。
    show = df[[
        "statement_id", "statement_code", "delivery_code", "customer_category", "customer_name",
        "customer_order_number", "deliver_date", "our_invoice_number",
        "non_tax_amount", "adjustment_amount", "amount_after_adjustment", "tax_rate", "final_total",
        "payment_light", "payment_status_text", "應收日期", "status",
        "audit_created_by", "audit_created_at", "audit_updated_by", "audit_updated_at"
    ]].copy()

    audit_show = build_ar_audit_display(conn, show)
    if not audit_show.empty:
        show["建檔人員"] = audit_show["建檔人員"]
        show["建檔時間"] = audit_show["建檔時間"]
        show["最後修改人"] = audit_show["最後修改人"]
        show["修改時間"] = audit_show["修改時間"]
    else:
        show["建檔人員"] = ""
        show["建檔時間"] = ""
        show["最後修改人"] = ""
        show["修改時間"] = ""

    show = show.drop(columns=["audit_created_by", "audit_created_at", "audit_updated_by", "audit_updated_at"], errors="ignore")

    show.insert(0, "勾選", False)

    # 讓上次選取能記住（你不想每次 rerun 又忘記）
    if st.session_state.ar_selected_id is not None:
        show.loc[show["statement_id"] == st.session_state.ar_selected_id, "勾選"] = True

    ar_grid_label_map = {
        "勾選": "勾選",
        "statement_code": "應收帳款單號",
        "delivery_code": "我方送貨單號",
        "customer_category": "客戶種類",
        "customer_name": "客戶名稱",
        "customer_order_number": "客戶訂單號碼",
        "deliver_date": "我方送貨日期",
        "our_invoice_number": "我方發票號碼",
        "non_tax_amount": "未稅金額(原始)",
        "adjustment_amount": "折扣折讓",
        "amount_after_adjustment": "折扣後未稅",
        "tax_rate": "稅率",
        "final_total": "含稅金額",
        "payment_light": "燈號",
        "payment_status_text": "付款狀況",
        "應收日期": "應收日期",
        "status": "狀態",
        "建檔人員": "建檔人員",
        "建檔時間": "建檔時間",
        "最後修改人": "最後修改人",
        "修改時間": "修改時間",
    }
    show_for_display = show.drop(columns=["statement_id"], errors="ignore")
    show_display, show_reverse_map = _translate_table_headers(show_for_display, ar_grid_label_map)
    checkbox_col = _t("勾選")
    edited_display = st.data_editor(
        show_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            checkbox_col: st.column_config.CheckboxColumn(checkbox_col),
            _t("我方送貨日期"): st.column_config.DateColumn(_t("我方送貨日期")),
            _t("應收日期"): st.column_config.DateColumn(_t("應收日期")),
            _t("未稅金額(原始)"): st.column_config.NumberColumn(_t("未稅金額(原始)"), disabled=True),
            _t("折扣後未稅"): st.column_config.NumberColumn(_t("折扣後未稅"), disabled=True),
            _t("含稅金額"): st.column_config.NumberColumn(_t("含稅金額"), disabled=True),
        },
        disabled=[c for c in show_display.columns if c != checkbox_col],
        key=f"ar_grid_{get_lang()}",
    )
    refresh_col, _ = st.columns([1.1, 5.5], vertical_alignment="center")
    with refresh_col:
        if st.button(_t("重新整理"), key="ar01_refresh_master_table", use_container_width=True):
            force_refresh_ar01(conn)
            st.rerun()

    edited = _restore_table_headers(edited_display, show_reverse_map)

    selected_idx = edited.index[edited["勾選"] == True].tolist() if "勾選" in edited.columns else []
    selected_id = int(show.iloc[selected_idx[0]]["statement_id"]) if selected_idx else None
    st.session_state.ar_selected_id = selected_id

    head = None
    if selected_id is not None:
        head_rows = q(conn, """
            SELECT h.*
            FROM ar_statement_head h
            INNER JOIN delivery_head dh
                    ON dh.delivery_note_id = h.delivery_id
            LEFT JOIN customer_order co
                   ON co.customer_order_id = dh.customer_order_id
            LEFT JOIN sample_order_head so
                   ON so.sample_order_id = dh.sample_order_id
            WHERE h.statement_id=%s
              AND COALESCE(co.customer_order_category, 'general') <> 'material_replenishment_non_receivable'
              AND (dh.sample_order_id IS NULL OR COALESCE(so.sample_category, 'receivable') <> 'non_receivable')
            LIMIT 1
        """, [selected_id])
        if head_rows:
            head = head_rows[0]
        else:
            # The AR source delivery was deleted outside this page. Clear stale selection.
            st.session_state.ar_selected_id = None
            selected_id = None

    render_bottom(conn, selected_id, head, has_due_date, payable_col, paid_col, bal_col, pay_cols)

# ==================================================
# Bottom sections: 基本資訊 / 送貨明細 / 客戶付款狀況
# ==================================================
def render_bottom(conn, sid, head, has_due_date, payable_col, paid_col, bal_col, pay_cols):
    st.divider()

    st.markdown('<div class="detail-editor">', unsafe_allow_html=True)
    st.markdown(f"<h2>{_t('明細編輯區')}</h2>", unsafe_allow_html=True)
    st.markdown('<div class="tabs-wrap">', unsafe_allow_html=True)

    t1, t2, t3 = st.tabs([_t("基本資訊"), _t("我方送貨明細"), _t("匯款狀況")])

    st.markdown('</div>', unsafe_allow_html=True)  # close tabs-wrap

    # 未選取：三個 tab 都給提示（視覺會像你截圖那樣）
    if sid is None or head is None:
        with t1:
            st.info(_t("請先在上方列表勾選一筆應收帳款。"))
        with t2:
            st.info(_t("請先在上方列表勾選一筆應收帳款。"))
        with t3:
            st.info(_t("請先在上方列表勾選一筆應收帳款。"))

        st.markdown('</div>', unsafe_allow_html=True)  # close detail-editor
        return

    # 已選取：各 tab 顯示內容
    with t1:
        render_basic(conn, sid, head, has_due_date)

    with t2:
        render_detail(conn, head)

    with t3:
        render_payment(conn, sid, head, payable_col, paid_col, bal_col, pay_cols)

    st.markdown('</div>', unsafe_allow_html=True)  # close detail-editor


def render_basic_empty():
    st.subheader(_t("基本資料"))
    # 只做框架（disabled），讓 UI 對齊你的設計圖
    r1 = st.columns([1,1,1])
    r1[0].text_input(_t("應收帳款單號"), value="", disabled=True)
    r1[1].text_input(_t("客戶種類"), value="", disabled=True)
    r1[2].text_input(_t("客戶名稱"), value="", disabled=True)

    r2 = st.columns([1,1,1])
    r2[0].text_input(_t("我方送貨單號"), value="", disabled=True)
    r2[1].text_input(_t("客戶訂單號碼"), value="", disabled=True)
    r2[2].text_input(_t("送貨日期"), value="", disabled=True)

    r3 = st.columns([1,1,1,1,1])
    r3[0].text_input(_t("我方發票號碼"), value="", disabled=True)
    r3[1].text_input(_t("發票日期"), value="", disabled=True)
    r3[2].text_input(_t("結帳日期"), value="", disabled=True)
    r3[3].text_input(_t("付款天數"), value="", disabled=True)
    r3[4].text_input(_t("應收款日期"), value="", disabled=True)
    st.markdown('<div class="amount-topline"></div>', unsafe_allow_html=True)

    r4 = st.columns([1.3,1.1,1.1,0.6,1.1])
    r4[0].text_input(_t("金額(未含稅、折扣、折讓)"), value="", disabled=True)
    r4[1].text_input(_t("折扣、折讓金額"), value="", disabled=True)
    r4[2].text_input(_t("未稅金額"), value="", disabled=True)
    r4[3].text_input(_t("稅率"), value="", disabled=True)
    r4[4].text_input(_t("含稅金額"), value="", disabled=True)

    r5 = st.columns([1,1,4])
    r5[0].text_input(_t("幣別"), value="", disabled=True)
    r5[1].text_input(_t("匯率"), value="", disabled=True)
    r5[2].text_input(_t("備註"), value="", disabled=True)

    st.button(_t("儲存/建立AR"), disabled=True)
    st.button(_t("重新整理"), disabled=True)

def render_basic(conn, sid, head, has_due_date):
    st.subheader(_t("基本資料"))


    st.markdown('<div class="basic-black">', unsafe_allow_html=True)
    today = date.today()

    # 基本資料（多數 disabled）
    r1 = st.columns([1,1,1])
    r1[0].text_input(_t("應收帳款單號"), value=head.get("statement_code",""), disabled=True)
    r1[1].text_input(_t("客戶種類"), value=head.get("customer_category",""), disabled=True)
    r1[2].text_input(_t("客戶名稱"), value=head.get("customer_name",""), disabled=True)

    r2 = st.columns([1,1,1])
    r2[0].text_input(_t("我方送貨單號"), value=head.get("delivery_code",""), disabled=True)
    r2[1].text_input(_t("客戶訂單號碼"), value=head.get("customer_order_number",""), disabled=True)
    r2[2].date_input(_t("送貨日期"), value=head.get("deliver_date") or today, disabled=True)

    # checkout_day / payment_term：優先 customer 表
    c = q(conn, "SELECT checkout_day, payment_term FROM customer WHERE customer_id=%s", [head["customer_id"]])
    checkout_day = c[0]["checkout_day"] if c else None
    payment_term = c[0]["payment_term"] if c else None
    checkout_date = calc_checkout_date(head.get("deliver_date"), safe_int(checkout_day, 0)) if checkout_day else None
    auto_due = add_days_assume_30(checkout_date, safe_int(payment_term, 0)) if (checkout_date and payment_term is not None) else None

    r3 = st.columns([1,1,1,1,1])
    with r3[0]:
        our_invoice_number = st.text_input(_t("我方發票號碼"), value=head.get("our_invoice_number") or "")
    with r3[1]:
        our_invoice_date = st.date_input(_t("發票日期"), value=head.get("our_invoice_date") or today)
    with r3[2]:
        st.date_input(_t("結帳日期"), value=checkout_date or today, disabled=True)
    with r3[3]:
        st.number_input(_t("付款天數"), value=safe_int(payment_term, 0), disabled=True)
    with r3[4]:
        if has_due_date:
            due_date = st.date_input(_t("應收款日期"), value=head.get("ar_due_date") or auto_due or today)
        else:
            # 沒有欄位就只能顯示計算值
            due_date = st.date_input(_t("應收款日期(計算)"), value=auto_due or today, disabled=True)

    # 金額區（依你的規則）
    amount_total = money(head.get("amount_total")) or Decimal("0")
    adj0 = money(head.get("adjustment_amount")) or Decimal("0")
    # 稅率：從 our_company 取（不靠 ar_statement_head.tax_rate）
    oc = q(conn, "SELECT our_company_tax_rate FROM our_company LIMIT 1")
    tax_rate = safe_int((oc[0].get("our_company_tax_rate") if oc else 0), 0)

    # - non_tax_amount 一律顯示「原始未稅金額」
    # - amount_after_adjustment = 原始未稅金額 - 折扣折讓
    r4 = st.columns([1.3,1.1,1.1,1.1,0.6,1.1])
    r4[0].number_input(_t("金額(未含稅、折扣、折讓)"), value=float(amount_total), disabled=True)
    adj = r4[1].number_input(_t("折扣、折讓金額"), value=float(adj0), min_value=0.0, step=1.0)

    non_tax_original = amount_total
    amount_after_adj = non_tax_original - money(adj)

    r4[2].number_input(_t("未稅金額(原始)"), value=float(non_tax_original), disabled=True)
    r4[3].number_input(_t("折扣後未稅"), value=float(amount_after_adj), disabled=True)
    r4[4].number_input(_t("稅率"), value=int(tax_rate), disabled=True)
    # Match MySQL ROUND(..., 2) in the AR line-summary triggers.  Decimal's
    # default ROUND_HALF_EVEN would otherwise turn x.xx5 into a one-cent
    # difference depending on whether AR01 or a DB trigger saved the total.
    final_total = (
        amount_after_adj * (Decimal("1") + Decimal(str(tax_rate)) / Decimal("100"))
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    r4[5].number_input(_t("含稅金額"), value=float(final_total), disabled=True)

    r5 = st.columns([1,1,4])
    r5[0].text_input(_t("幣別"), value=head.get("currency","VND"), disabled=True)
    exchange_rate = r5[1].number_input(_t("匯率"), value=safe_int(head.get("exchange_rate"), 1), min_value=0, step=1)
    note = r5[2].text_input(_t("備註"), value=head.get("note") or "")

    btn1, btn2 = st.columns([1,3])
    with btn1:
        if st.button(_t("儲存/建立AR")):
            # 更新主表：invoice / adjustment / non_tax(原始) / final_total(折扣後計算) / exchange_rate / note / (due_date)
            # 注意：你 DB 的 final_total 是 decimal(18,2)，所以直接寫入數值，不要寫字串
            if has_due_date:
                exec_sql(conn, """
                    UPDATE ar_statement_head
                    SET our_invoice_number=%s,
                        our_invoice_date=%s,
                        adjustment_amount=%s,
                        non_tax_amount=%s,
                        final_total=%s,
                        tax_rate=%s,
                        exchange_rate=%s,
                        note=%s,
                        ar_due_date=%s
                    WHERE statement_id=%s
                """, [
                    our_invoice_number or None,
                    our_invoice_date,
                    float(money(adj)),
                    float(non_tax_original),
                    float(final_total),
                    int(tax_rate),
                    int(exchange_rate),
                    note or None,
                    due_date,
                    sid
                ])
            else:
                exec_sql(conn, """
                    UPDATE ar_statement_head
                    SET our_invoice_number=%s,
                        our_invoice_date=%s,
                        adjustment_amount=%s,
                        non_tax_amount=%s,
                        final_total=%s,
                        tax_rate=%s,
                        exchange_rate=%s,
                        note=%s
                    WHERE statement_id=%s
                """, [
                    our_invoice_number or None,
                    our_invoice_date,
                    float(money(adj)),
                    float(non_tax_original),
                    float(final_total),
                    int(tax_rate),
                    int(exchange_rate),
                    note or None,
                    sid
                ])
            touch_ar_statement_head(conn, sid)
            st.success(_t("已保存 ✅"))
            st.rerun()
    with btn2:
        if st.button(_t("重新整理")):
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
def render_detail(conn, head):
    st.subheader(_t("我方送貨明細"))

    did = head.get("delivery_id")
    if did is None:
        st.info(_t("此 AR 未關聯 delivery_id。"))
        return

    sql = """
        SELECT
            dp.line_no,
            dp.customer_product_id       AS 客戶料號,
            p.product_code               AS 我方產品編號,
            COALESCE(dp.product_name, p.product_name) AS 產品名稱,
            COALESCE(dp.specification, p.Specification) AS 規格,
            dp.qty                       AS 數量,
            p.unit                       AS 單位,
            dp.product_unit_price        AS 單價,
            dp.line_amount               AS 小計
        FROM delivery_product dp
        LEFT JOIN product p ON p.product_id = dp.product_id
        WHERE dp.delivery_head_id = %s
        ORDER BY dp.line_no
    """
    detail = q(conn, sql, [did])

    if not detail:
        st.info(_t("此送貨單沒有明細。"))
        return

    ddf = pd.DataFrame(detail)
    ddf_display, _ = _translate_table_headers(ddf)
    st.dataframe(ddf_display, use_container_width=True, hide_index=True)
    total = ddf["小計"].fillna(0).sum() if "小計" in ddf.columns else 0
    st.write(f"{_t('我方送貨單金額加總：')}**{total:,.2f}**")


def render_payment(conn, sid, head, payable_col, paid_col, bal_col, pay_cols):
    st.subheader(_t("客戶付款紀錄"))

    # -----------------------------
    # 付款列表（上半部）
    # -----------------------------
    rows = q(conn, f"""
        SELECT
            ar_payment_id AS 付款ID,
            ar_payment_date AS 客戶付款日期,
            {payable_col} AS 應付金額,
            {paid_col} AS 實付金額,
            {bal_col} AS 餘額,
            ar_payment_method AS 付款方式,
            ar_customer_bank_name AS 銀行,
            ar_customer_bank_code AS 銀行帳號,
            ar_voucher_no AS 支票號碼,
            our_bank_account_name AS 我方銀行,
            our_bank_account_code AS 我方銀行帳號,
            status AS 狀態
        FROM ar_apyable_payment
        WHERE ar_id=%s
        ORDER BY ar_payment_date, ar_payment_id
    """, [sid])

    if rows:
        df = pd.DataFrame(rows)
        df.insert(0, "勾選", False)
        # 記住列表勾選（給「編輯」「刪除」用）
        if "ar_pay_selected_id" not in st.session_state:
            st.session_state.ar_pay_selected_id = None
        if st.session_state.ar_pay_selected_id is not None:
            df.loc[df["付款ID"] == st.session_state.ar_pay_selected_id, "勾選"] = True

        pay_display, pay_reverse_map = _translate_table_headers(df)
        pay_checkbox_col = _t("勾選")
        grid_display = st.data_editor(
            pay_display,
            hide_index=True,
            use_container_width=True,
            disabled=[c for c in pay_display.columns if c != pay_checkbox_col],
            key=f"pay_grid_{get_lang()}",
        )
        grid = _restore_table_headers(grid_display, pay_reverse_map)
        sel = grid[grid["勾選"] == True]
        st.session_state.ar_pay_selected_id = int(sel.iloc[0]["付款ID"]) if not sel.empty else None
    else:
        st.info(_t("尚無付款紀錄。"))
        st.session_state.ar_pay_selected_id = None

    # 上方操作鈕（編輯/刪除）
    b1, b2, b3 = st.columns([1,1,6])
    with b1:
        if st.button(_t("編輯"), disabled=(st.session_state.ar_pay_selected_id is None)):
            st.session_state.ar_pay_edit_id = st.session_state.ar_pay_selected_id
            st.rerun()
    with b2:
        if st.button(_t("刪除"), disabled=(st.session_state.ar_pay_selected_id is None)):
            exec_sql(conn, "DELETE FROM ar_apyable_payment WHERE ar_payment_id=%s", [st.session_state.ar_pay_selected_id])
            sync_ar_head_payment_status(conn, sid)
            st.session_state.ar_pay_selected_id = None
            st.session_state.ar_pay_edit_id = None
            st.success(_t("已刪除付款紀錄 ✅"))
            st.rerun()

    st.divider()
    st.write(_t("新增/編輯"))

    # -----------------------------
    # 新增/編輯表單（下半部）
    # -----------------------------
    edit_id = st.session_state.get("ar_pay_edit_id", None)
    editing = edit_id is not None

    # 取既有資料（編輯模式）
    row = None
    if editing:
        r = q(conn, "SELECT * FROM ar_apyable_payment WHERE ar_payment_id=%s", [edit_id])
        row = r[0] if r else None
        if row is None:
            st.warning(_t("找不到要編輯的付款紀錄（可能剛剛被刪了）。已回到新增模式。"))
            st.session_state.ar_pay_edit_id = None
            editing = False

    # 是否已付清（最後一筆 settled 或餘額<=0）：付清後禁止新增（但允許編輯/刪除既有）
    settled = False
    if rows:
        last = rows[-1]
        try:
            if last.get("狀態") == "settled":
                settled = True
            if last.get("餘額") is not None and Decimal(str(last.get("餘額"))) <= 0:
                settled = True
        except Exception:
            pass

    if settled and not editing:
        st.warning(_t("此筆 AR 已付清（settled）。依規格不可再新增任何付款。"))
        return

    # 應付金額：新增時 = (第一筆: AR 含稅金額) 或 (後續: 上次餘額)
    base_payable = None
    if editing:
        base_payable = float(row.get(payable_col) or row.get("final_total") or 0)
    else:
        if rows and rows[-1].get("餘額") is not None:
            base_payable = float(rows[-1]["餘額"])
        else:
            base_payable = float(head.get("final_total") or 0)

    # 表單欄位（照你的圖：付款日期/方式/應付/實付/銀行等）
    p1, p2 = st.columns([1,1])
    pay_date = p1.date_input(_t("付款日期"), value=(row.get("ar_payment_date") or date.today()) if editing else date.today())
    pay_method = p2.selectbox(
        _t("付款方式"),
        ["cash","transfer","cheque"],
        index=["cash","transfer","cheque"].index((row.get("ar_payment_method") or "transfer") if editing else "transfer")
    )

    p3, p4 = st.columns([1,1])
    payable_amt = p3.number_input(_t("應付金額"), value=float(base_payable), disabled=True)
    paid_default = float(row.get(paid_col) or row.get("actual_amount_paid") or 0) if editing else 0.0
    paid_amt = p4.number_input(_t("實付金額"), value=float(paid_default), min_value=0.0, step=1.0)

    bal = float(Decimal(str(payable_amt)) - Decimal(str(paid_amt)))
    st.number_input(_t("餘額(自動)"), value=bal, disabled=True)

    # 客戶銀行
    cbanks = q(conn, """
        SELECT customer_bank_id, customer_bank_name, customer_bank_num, customer_account_name, customer_bank_code
        FROM customer_bank
        WHERE customer_id=%s
        ORDER BY customer_bank_id
    """, [head["customer_id"]])
    cb_opt = ["(不選)"] + [f'{r["customer_bank_name"]} | {r["customer_bank_code"]}' for r in cbanks]
    cb_sel_default = "(不選)"
    if editing and row.get("ar_customer_bank_account_id"):
        for i, b in enumerate(cbanks):
            if b["customer_bank_id"] == row.get("ar_customer_bank_account_id"):
                cb_sel_default = cb_opt[i+1]
                break
    cb_sel = st.selectbox(_t("銀行(客戶付款銀行)"), cb_opt, index=cb_opt.index(cb_sel_default))

    # 我方銀行
    obanks = q(conn, """
        SELECT our_bank_id, our_company_bank_name, our_company_bank_num, our_company_account_name, our_company_account_code
        FROM our_bank
        ORDER BY our_bank_id
    """)
    ob_opt = ["(不選)"] + [f'{r["our_company_bank_name"]} | {r["our_company_account_code"]}' for r in obanks]
    ob_sel_default = "(不選)"
    if editing and row.get("ar_our_bank_id"):
        for i, b in enumerate(obanks):
            if b["our_bank_id"] == row.get("ar_our_bank_id"):
                ob_sel_default = ob_opt[i+1]
                break
    ob_sel = st.selectbox(_t("匯款到我方銀行"), ob_opt, index=ob_opt.index(ob_sel_default))

    voucher_no = st.text_input(_t("支票號碼(可空)"), value=(row.get("ar_voucher_no") or "") if editing else "")

    # 存檔/取消編輯
    s1, s2, s3 = st.columns([1,1,6])
    with s1:
        if st.button(_t("儲存付款紀錄")):
            paid_decimal = Decimal(str(paid_amt))
            payable_decimal = Decimal(str(payable_amt))
            if paid_decimal <= 0:
                st.error(_t("實付金額必須大於 0。"))
                st.stop()
            if paid_decimal > payable_decimal:
                st.error(_t("實付金額不可超過本次應付金額。"))
                st.stop()

            cb = cbanks[cb_opt.index(cb_sel) - 1] if cb_sel != "(不選)" else None
            ob = obanks[ob_opt.index(ob_sel) - 1] if ob_sel != "(不選)" else None
            status_pay = "settled" if Decimal(str(bal)) <= 0 else "partial"

            # 寫入欄位：兼容兩套欄位名
            # payable
            if "payable_amount" in pay_cols:
                payable_set_col = "payable_amount"
            else:
                payable_set_col = "final_total"
            # paid
            if "paid_amount" in pay_cols:
                paid_set_col = "paid_amount"
            else:
                paid_set_col = "actual_amount_paid"
            # balance
            if "balance_amount" in pay_cols:
                bal_set_col = "balance_amount"
            else:
                bal_set_col = "balance"

            if editing:
                exec_sql(conn, f"""
                    UPDATE ar_apyable_payment
                    SET ar_payment_date=%s,
                        ar_payment_method=%s,
                        {payable_set_col}=%s,
                        {paid_set_col}=%s,
                        {bal_set_col}=%s,
                        ar_customer_bank_account_id=%s,
                        ar_customer_bank_num=%s,
                        ar_customer_bank_name=%s,
                        ar_customer_account_name=%s,
                        ar_customer_bank_code=%s,
                        ar_our_bank_id=%s,
                        our_bank_account_name=%s,
                        our_bank_num=%s,
                        our_bank_account_code=%s,
                        ar_voucher_no=%s,
                        status=%s
                    WHERE ar_payment_id=%s
                """, [
                    pay_date,
                    pay_method,
                    payable_amt,
                    paid_amt,
                    bal,
                    (cb["customer_bank_id"] if cb else None),
                    (cb["customer_bank_num"] if cb else None),
                    (cb["customer_bank_name"] if cb else None),
                    (cb["customer_account_name"] if cb else None),
                    (cb["customer_bank_code"] if cb else None),
                    (ob["our_bank_id"] if ob else None),
                    (ob["our_company_account_name"] if ob else None),
                    (ob["our_company_bank_num"] if ob else None),
                    (ob["our_company_account_code"] if ob else None),
                    voucher_no or None,
                    status_pay,
                    edit_id
                ])
            else:
                exec_sql(conn, f"""
                    INSERT INTO ar_apyable_payment(
                        ar_id, ar_payment_date, ar_payment_method,
                        {payable_set_col}, {paid_set_col}, {bal_set_col},
                        ar_customer_bank_account_id, ar_customer_bank_num, ar_customer_bank_name, ar_customer_account_name, ar_customer_bank_code,
                        ar_our_bank_id, our_bank_account_name, our_bank_num, our_bank_account_code,
                        ar_voucher_no, status, created_at, created_by
                    ) VALUES (
                        %s,%s,%s,
                        %s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,
                        %s,%s,NOW(),%s
                    )
                """, [
                    sid, pay_date, pay_method,
                    payable_amt, paid_amt, bal,
                    (cb["customer_bank_id"] if cb else None),
                    (cb["customer_bank_num"] if cb else None),
                    (cb["customer_bank_name"] if cb else None),
                    (cb["customer_account_name"] if cb else None),
                    (cb["customer_bank_code"] if cb else None),
                    (ob["our_bank_id"] if ob else None),
                    (ob["our_company_account_name"] if ob else None),
                    (ob["our_company_bank_num"] if ob else None),
                    (ob["our_company_account_code"] if ob else None),
                    voucher_no or None,
                    status_pay,
                    current_user_id()
                ])

            sync_ar_head_payment_status(conn, sid)
            st.session_state.ar_pay_edit_id = None
            st.success(_t("付款紀錄已儲存 ✅"))
            st.rerun()
    with s2:
        if st.button(_t("取消編輯"), disabled=not editing):
            st.session_state.ar_pay_edit_id = None
            st.rerun()

if __name__ == "__main__":
    run()
