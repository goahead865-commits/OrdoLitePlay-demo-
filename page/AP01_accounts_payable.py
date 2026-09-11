
import os
import calendar
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from compact_layout import apply_compact_layout

apply_compact_layout()


import auth

# =============================
# I18N helper
# =============================
TRANSLATIONS = {
    "應付帳款": {"vi": "Công nợ phải trả", "en": "Accounts Payable"},
    "應付帳款統計": {"vi": "Thống kê công nợ phải trả", "en": "Accounts Payable Summary"},
    "上一頁": {"vi": "Trang trước", "en": "Previous Page"},
    "下一頁": {"vi": "Trang sau", "en": "Next Page"},
    "顯示筆數": {"vi": "Số dòng hiển thị", "en": "Rows per page"},
    "找不到符合條件的入庫單（io_type='IN' 且 doc_no 不為空）。": {"vi": "Không tìm thấy phiếu nhập phù hợp điều kiện (io_type='IN' và doc_no không rỗng).", "en": "No matching receiving records found (io_type='IN' and doc_no not empty)."},
    "一次只能勾選一筆入庫單。請只留一個勾選 ✅": {"vi": "Mỗi lần chỉ được chọn một phiếu nhập. Vui lòng chỉ giữ lại một dòng được chọn ✅", "en": "You can only select one receiving record at a time. Please keep only one selected ✅"},
    "明細編輯區": {"vi": "Khu vực chỉnh sửa chi tiết", "en": "Detail Editing Area"},
    "基本資訊": {"vi": "Thông tin cơ bản", "en": "Basic Information"},
    "供應商送貨明細": {"vi": "Chi tiết giao hàng của nhà cung cấp", "en": "Supplier Delivery Details"},
    "匯款狀況": {"vi": "Tình trạng thanh toán", "en": "Payment Status"},
    "請先在上方列表勾選一筆入庫單。": {"vi": "Vui lòng chọn một phiếu nhập trong danh sách phía trên trước.", "en": "Please select one receiving record from the list above first."},
    "應付帳款單號": {"vi": "Mã công nợ phải trả", "en": "AP Number"},
    "供應商種類": {"vi": "Loại nhà cung cấp", "en": "Supplier Category"},
    "供應商名稱": {"vi": "Tên nhà cung cấp", "en": "Supplier Name"},
    "依據類型": {"vi": "Loại căn cứ", "en": "Reference Type"},
    "供應商送貨單號": {"vi": "Số phiếu giao hàng NCC", "en": "Supplier Delivery Note No."},
    "送貨日期": {"vi": "Ngày giao hàng", "en": "Delivery Date"},
    "我方訂單號碼": {"vi": "Số đơn hàng của chúng tôi", "en": "Our Order Number"},
    "供應商發票號碼": {"vi": "Số hóa đơn NCC", "en": "Supplier Invoice No."},
    "發票日期": {"vi": "Ngày hóa đơn", "en": "Invoice Date"},
    "結帳日期(自動)": {"vi": "Ngày chốt công nợ (tự động)", "en": "Checkout Date (Auto)"},
    "付款天數(自動)": {"vi": "Số ngày thanh toán (tự động)", "en": "Payment Days (Auto)"},
    "應付日期(自動)": {"vi": "Ngày phải trả (tự động)", "en": "Due Date (Auto)"},
    "金額(未含稅、折扣、折讓)": {"vi": "Số tiền (chưa gồm thuế, chiết khấu, giảm trừ)", "en": "Amount (Before Tax/Discount/Allowance)"},
    "折扣、折讓金額": {"vi": "Chiết khấu / giảm trừ", "en": "Discount / Allowance"},
    "未稅金額": {"vi": "Số tiền chưa thuế", "en": "Untaxed Amount"},
    "稅率(%)": {"vi": "Thuế suất (%)", "en": "Tax Rate (%)"},
    "含稅金額": {"vi": "Số tiền gồm thuế", "en": "Tax Included Amount"},
    "幣別": {"vi": "Tiền tệ", "en": "Currency"},
    "匯率": {"vi": "Tỷ giá", "en": "Exchange Rate"},
    "備註": {"vi": "Ghi chú", "en": "Remark"},
    "儲存/建立AP": {"vi": "Lưu / tạo AP", "en": "Save / Create AP"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "供應商發票號碼不可為空。你要讓財會怎麼活？😅": {"vi": "Số hóa đơn nhà cung cấp không được để trống. Không thì bộ phận kế toán sống sao đây? 😅", "en": "Supplier invoice number cannot be blank. Give accounting a chance to survive 😅"},
    "已更新應付帳款 ✅": {"vi": "Đã cập nhật công nợ phải trả ✅", "en": "Accounts payable updated ✅"},
    "找不到對應的 AP 主檔（delivery）。請確認入庫單已 posted 且 trigger 已正確寫入 accounts_payable_head。": {"vi": "Không tìm thấy dữ liệu AP chính tương ứng (delivery). Vui lòng xác nhận phiếu nhập đã posted và trigger đã ghi đúng vào accounts_payable_head.", "en": "Matching AP head (delivery) not found. Please confirm the receiving record is posted and the trigger wrote into accounts_payable_head correctly."},
    "已建立應付帳款：": {"vi": "Đã tạo công nợ phải trả: ", "en": "Accounts payable created: "},
    "這筆入庫單沒有明細行。": {"vi": "Phiếu nhập này không có dòng chi tiết.", "en": "This receiving record has no detail lines."},
    "送貨單金額加總": {"vi": "Tổng tiền phiếu giao hàng", "en": "Delivery Amount Total"},
    "尚未建立 AP（應付帳款單號）。請先到「基本資訊」儲存/建立 AP。": {"vi": "Chưa tạo AP (mã công nợ phải trả). Vui lòng vào \"Thông tin cơ bản\" để lưu/tạo AP trước.", "en": "AP has not been created yet. Please save/create AP in Basic Information first."},
    "目前沒有付款紀錄。": {"vi": "Hiện chưa có ghi nhận thanh toán.", "en": "No payment records yet."},
    "付款紀錄一次只能勾選一筆。": {"vi": "Mỗi lần chỉ được chọn một bản ghi thanh toán.", "en": "You can only select one payment record at a time."},
    "編輯": {"vi": "Chỉnh sửa", "en": "Edit"},
    "刪除": {"vi": "Xóa", "en": "Delete"},
    "請先勾選要刪除的付款紀錄。": {"vi": "Vui lòng chọn bản ghi thanh toán cần xóa trước.", "en": "Please select a payment record to delete first."},
    "已刪除付款紀錄（標記為 void）✅": {"vi": "Đã xóa bản ghi thanh toán (đánh dấu void) ✅", "en": "Payment record deleted (marked void) ✅"},
    "新增/編輯": {"vi": "Thêm mới / chỉnh sửa", "en": "Add / Edit"},
    "付款日期": {"vi": "Ngày thanh toán", "en": "Payment Date"},
    "付款方式": {"vi": "Phương thức thanh toán", "en": "Payment Method"},
    "實付金額": {"vi": "Số tiền đã trả", "en": "Paid Amount"},
    "銀行/參考": {"vi": "Ngân hàng / tham chiếu", "en": "Bank / Reference"},
    "支票號碼": {"vi": "Số séc", "en": "Cheque No."},
    "供應商帳號": {"vi": "Tài khoản nhà cung cấp", "en": "Supplier Bank Account"},
    "儲存付款紀錄": {"vi": "Lưu ghi nhận thanh toán", "en": "Save Payment Record"},
    "已更新付款紀錄 ✅": {"vi": "Đã cập nhật ghi nhận thanh toán ✅", "en": "Payment record updated ✅"},
    "已新增付款紀錄 ✅": {"vi": "Đã thêm ghi nhận thanh toán ✅", "en": "Payment record added ✅"},
    "起始日期": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "供應商大類": {"vi": "Nhóm lớn nhà cung cấp", "en": "Supplier Major Category"},
    "供應商類別": {"vi": "Loại nhà cung cấp", "en": "Supplier Category"},
    "供應商名稱": {"vi": "Tên nhà cung cấp", "en": "Supplier Name"},
    "選取的入庫單已不存在，已清除明細選取狀態。": {"vi": "Phiếu nhập đã chọn không còn tồn tại, hệ thống đã xóa trạng thái chọn chi tiết.", "en": "The selected receiving record no longer exists; detail selection has been cleared."},
}
def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    return lang if lang in {"zh", "vi", "en"} else "zh"

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)


# Extra table/header translations used by AP01 grids.
# Keep display labels translated without touching internal DataFrame keys.
TRANSLATIONS.update({
    "勾選": {"vi": "Chọn", "en": "Select"},
    "應付帳款單號": {"vi": "Mã công nợ phải trả", "en": "AP Number"},
    "供應商送貨單號": {"vi": "Số phiếu giao hàng NCC", "en": "Supplier Delivery No."},
    "供應商種類": {"vi": "Loại nhà cung cấp", "en": "Supplier Category"},
    "供應商送貨日期": {"vi": "Ngày giao hàng NCC", "en": "Supplier Delivery Date"},
    "我方訂單號": {"vi": "Số đơn hàng của chúng tôi", "en": "Our Order No."},
    "未稅金額(試算)": {"vi": "Số tiền chưa thuế (ước tính)", "en": "Untaxed Amount (Calc)"},
    "含稅金額(已建AP)": {"vi": "Số tiền gồm thuế (AP đã tạo)", "en": "Tax Included Amount (AP)"},
    "應付日期": {"vi": "Ngày phải trả", "en": "Due Date"},
    "狀態": {"vi": "Trạng thái", "en": "Status"},
    "入庫單號": {"vi": "Số phiếu nhập kho", "en": "Receiving No."},
    "入庫時間": {"vi": "Thời gian nhập kho", "en": "Receiving Time"},
    "品名": {"vi": "Tên hàng", "en": "Item Name"},
    "規格": {"vi": "Quy cách", "en": "Specification"},
    "數量": {"vi": "Số lượng", "en": "Quantity"},
    "單位": {"vi": "Đơn vị", "en": "Unit"},
    "單價": {"vi": "Đơn giá", "en": "Unit Price"},
    "小計": {"vi": "Thành tiền", "en": "Subtotal"},
    "付款日期": {"vi": "Ngày thanh toán", "en": "Payment Date"},
    "應付金額": {"vi": "Số tiền phải trả", "en": "Payable Amount"},
    "已付金額": {"vi": "Số tiền đã trả", "en": "Paid So Far"},
    "實付金額": {"vi": "Số tiền đã trả", "en": "Paid Amount"},
    "剩餘金額": {"vi": "Số tiền còn lại", "en": "Remaining Amount"},
    "餘額(自動)": {"vi": "Số dư (tự động)", "en": "Balance (Auto)"},
    "銀行/參考": {"vi": "Ngân hàng / Tham chiếu", "en": "Bank / Reference"},
    "我方付款銀行": {"vi": "Ngân hàng thanh toán của chúng tôi", "en": "Our Paying Bank"},
    "供應商收款銀行": {"vi": "Ngân hàng nhận tiền của NCC", "en": "Supplier Receiving Bank"},
    "燈號": {"vi": "Đèn", "en": "Signal"},
    "付款狀況": {"vi": "Tình trạng thanh toán", "en": "Payment Status"},
    "未建立AP": {"vi": "Chưa tạo AP", "en": "AP Not Created"},
    "未付款": {"vi": "Chưa thanh toán", "en": "Unpaid"},
    "部分付款": {"vi": "Thanh toán một phần", "en": "Partially Paid"},
    "已付款": {"vi": "Đã thanh toán", "en": "Paid"},
    "（不指定）": {"vi": "(Không chỉ định)", "en": "(Unspecified)"},
    "請先到 our_bank 建立我方銀行資料。": {"vi": "Vui lòng tạo dữ liệu ngân hàng của chúng tôi trong our_bank trước.", "en": "Please create our bank data in our_bank first."},
    "請先到 supplier_bank_account 建立供應商銀行資料。": {"vi": "Vui lòng tạo dữ liệu ngân hàng nhà cung cấp trong supplier_bank_account trước.", "en": "Please create supplier bank data in supplier_bank_account first."},
    "更新時間": {"vi": "Thời gian cập nhật", "en": "Updated At"},
    "建檔人員": {"vi": "Người tạo", "en": "Created By"},
    "建檔時間": {"vi": "Thời gian tạo", "en": "Created At"},
    "最後修改人": {"vi": "Người sửa cuối", "en": "Last Modified By"},
    "修改時間": {"vi": "Thời gian sửa", "en": "Modified At"},
    "此筆 AP 已付清，不可再新增付款紀錄。": {"vi": "Khoản AP này đã thanh toán đủ, không thể thêm ghi nhận thanh toán mới.", "en": "This AP has been fully paid. No new payment record can be added."},
    "目前已付金額已大於或等於應付總額，不能再新增付款紀錄。": {"vi": "Số tiền đã trả hiện tại lớn hơn hoặc bằng tổng phải trả, không thể thêm ghi nhận thanh toán mới.", "en": "Paid amount is already greater than or equal to the payable total. A new payment record cannot be added."},
    "付款金額必須大於 0。": {"vi": "Số tiền thanh toán phải lớn hơn 0.", "en": "Payment amount must be greater than 0."},
    "本次付款金額不可大於剩餘應付金額。": {"vi": "Số tiền thanh toán lần này không được lớn hơn số tiền còn phải trả.", "en": "This payment amount cannot exceed the remaining payable amount."},
})


# =============================
# Global CSS
# =============================

PAGE_KEY = "AP01_accounts_payable"
auth.require_read(PAGE_KEY)
st.markdown(
    """
    <style>
    html, body, [class*="st-"], div, span, p, label, input, textarea, small {
        color: #000000 !important;
    }
    input, textarea, select { color: #000000 !important; }
    input::placeholder, textarea::placeholder {
        color: #000000 !important;
        opacity: 1 !important;
    }
    thead, tbody, th, td { color: #000000 !important; }
    label span { color: #000000 !important; }
    button[data-baseweb="tab"] { color: #000000 !important; }
    button { color: #000000 !important; }
    .block-container { padding-top: 0 !important; padding-bottom: 0.65rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(_t("應付帳款"))

# =========================================================
# DB helpers
# =========================================================
@st.cache_resource(show_spinner=False)
def _get_conn():
    """
    連線策略（對齊你專案的 db.py）：
    1) 優先嘗試 import db.get_connection()（使用 ORDO_DB_* 環境變數）
    2) 次選 st.secrets["mysql"]（若專案有設定 secrets.toml）
    3) 最後才用 MYSQL_* 環境變數
    """
    try:
        import mysql.connector  # type: ignore
    except Exception:
        st.error("缺少 mysql-connector-python 套件，請先安裝：pip install mysql-connector-python")
        raise

    # 1) project db.py
    try:
        import db  # type: ignore
        conn = db.get_connection()
        if conn is not None:
            return conn
    except Exception:
        # db.py 不存在或內容不相容就跳過
        pass

    # 2) Streamlit secrets（注意：沒有 secrets.toml 時，讀 st.secrets 會直接丟例外）
    cfg = {}
    try:
        mysql_sec = st.secrets.get("mysql", None)  # type: ignore[attr-defined]
        if mysql_sec:
            cfg = {
                "host": mysql_sec.get("host", "localhost"),
                "port": int(mysql_sec.get("port", 3306)),
                "user": mysql_sec.get("user", "root"),
                "password": mysql_sec.get("password", ""),
                "database": mysql_sec.get("database", ""),
            }
    except Exception:
        cfg = {}

    # 3) env fallback（舊版 MYSQL_*）
    if not cfg:
        cfg = {
            "host": os.getenv("MYSQL_HOST", os.getenv("ORDO_DB_HOST", "localhost")),
            "port": int(os.getenv("MYSQL_PORT", os.getenv("ORDO_DB_PORT", "3306"))),
            "user": os.getenv("MYSQL_USER", os.getenv("ORDO_DB_USER", "root")),
            "password": os.getenv("MYSQL_PASSWORD", os.getenv("ORDO_DB_PASSWORD", "")),
            "database": os.getenv("MYSQL_DATABASE", os.getenv("ORDO_DB_NAME", "")),
        }

    missing = [k for k in ["host", "user", "database"] if not cfg.get(k)]
    if missing:
        st.error(
            "找不到資料庫連線設定。\n"
            "✅ 你專案已有 db.py，建議用 ORDO_DB_* 環境變數：\n"
            "- ORDO_DB_HOST / ORDO_DB_PORT / ORDO_DB_USER / ORDO_DB_PASSWORD / ORDO_DB_NAME\n"
            "或建立 .streamlit/secrets.toml 的 [mysql] 區塊。"
        )
        raise RuntimeError(f"DB config missing: {missing}")

    try:
        conn = mysql.connector.connect(**cfg)
        return conn
    except Exception as e:
        st.error(f"DB 連線失敗：{e}")
        raise


def qdf(sql: str, params=None) -> pd.DataFrame:
    """Query -> DataFrame.

    AP01 uses a cached MySQL connection for speed. After each SELECT we commit the
    read transaction so the next query can see freshly updated rows from
    accounts_payable_head instead of staying on an old InnoDB snapshot.
    """
    conn = _get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    try:
        conn.commit()
    except Exception:
        pass
    return pd.DataFrame(rows)

def qone(sql: str, params=None) -> dict | None:
    """Query -> single row dict (or None).

    Commit after SELECT for the same reason as qdf(): avoid stale cached-connection
    read snapshots when AP data was updated by another page/session.
    """
    conn = _get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    row = cur.fetchone()
    cur.close()
    try:
        conn.commit()
    except Exception:
        pass
    return row


def exec_sql(sql: str, params=None) -> int:
    """Execute (INSERT/UPDATE/DELETE) -> affected rows"""
    sql_upper = (sql or '').lstrip().upper()
    if sql_upper.startswith('DELETE'):
        auth.require_delete(PAGE_KEY)
    else:
        auth.require_edit(PAGE_KEY)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    affected = cur.rowcount
    cur.close()
    return affected

def exec_insert_get_id(sql: str, params=None) -> int:
    auth.require_edit(PAGE_KEY)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    return int(new_id)


# =========================================================
# Schema helpers
# =========================================================
_SCHEMA_CACHE: dict[tuple[str, str], bool] = {}

def _get_active_db_name() -> str:
    """
    Return current connected database name.
    We avoid DB_CONFIG dependency to prevent NameError / unresolved reference.
    """
    try:
        row = qone("SELECT DATABASE() AS db")
        dbname = (row or {}).get("db")
        return str(dbname) if dbname else ""
    except Exception:
        return ""


def has_column(table_name: str, column_name: str) -> bool:
    key = (table_name, column_name)
    if key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[key]
    dbname = _get_active_db_name()
    if not dbname:
        _SCHEMA_CACHE[key] = False
        return False
    try:
        row = qone(
            "SELECT 1 AS ok FROM information_schema.COLUMNS "
            "WHERE table_schema=%s AND table_name=%s AND column_name=%s LIMIT 1",
            (dbname, table_name, column_name),
        )
        _SCHEMA_CACHE[key] = bool(row)
    except Exception:
        _SCHEMA_CACHE[key] = False
    return _SCHEMA_CACHE[key]

HAS_AP_HEAD_TAX_RATE = has_column("accounts_payable_head", "tax_rate")
HAS_ORDER_HEAD_PURCHASE_CATEGORY = has_column("order_head", "purchase_order_category")


def table_exists(table_name: str) -> bool:
    """Return whether a table exists in the active database."""
    dbname = _get_active_db_name()
    if not dbname:
        return False
    try:
        row = qone(
            "SELECT 1 AS ok FROM information_schema.TABLES "
            "WHERE table_schema=%s AND table_name=%s LIMIT 1",
            (dbname, table_name),
        )
        return bool(row)
    except Exception:
        return False


def get_table_column_names(table_name: str) -> set[str]:
    """Return column names for a table; empty set if unavailable."""
    dbname = _get_active_db_name()
    if not dbname:
        return set()
    try:
        df = qdf(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE table_schema=%s AND table_name=%s",
            (dbname, table_name),
        )
        if df.empty or "COLUMN_NAME" not in df.columns:
            return set()
        return {str(x) for x in df["COLUMN_NAME"].dropna().tolist()}
    except Exception:
        return set()


def fetch_user_display_map(user_ids) -> dict[int, str]:
    """Map user_id to human-readable staff/user name.

    Priority:
      1) user.stuff_id -> stuff.stuff_name  （現場真正人名）
      2) user display/name fields
      3) login/account fields only as fallback
      4) User#id
    """
    clean_ids = sorted({int(x) for x in (user_ids or []) if x not in (None, "")})
    if not clean_ids:
        return {}

    fallback = {uid: f"User#{uid}" for uid in clean_ids}
    if not table_exists("user"):
        return fallback

    user_cols = get_table_column_names("user")
    if "user_id" not in user_cols:
        return fallback

    placeholders = ",".join(["%s"] * len(clean_ids))
    result = dict(fallback)

    # Best path: linked staff name.
    if "stuff_id" in user_cols and table_exists("stuff"):
        stuff_cols = get_table_column_names("stuff")
        if {"stuff_id", "stuff_name"}.issubset(stuff_cols):
            try:
                df = qdf(
                    f"""
                    SELECT u.user_id,
                           COALESCE(NULLIF(s.stuff_name, ''), CAST(u.user_id AS CHAR)) AS display_name
                    FROM `user` u
                    LEFT JOIN stuff s ON s.stuff_id = u.stuff_id
                    WHERE u.user_id IN ({placeholders})
                    """,
                    tuple(clean_ids),
                )
                for _, r in df.iterrows():
                    uid = int(r.get("user_id"))
                    name = str(r.get("display_name") or "").strip()
                    if name and name != str(uid):
                        result[uid] = name
            except Exception:
                pass

    # Fallback: readable user fields. Login/account fields are intentionally last.
    display_candidates = [
        "display_name", "full_name", "real_name", "name", "staff_name", "user_name",
        "username", "account", "login_name", "user_code",
    ]
    display_cols = [c for c in display_candidates if c in user_cols]
    if display_cols:
        expr = "COALESCE(" + ", ".join([f"NULLIF(`{c}`, '')" for c in display_cols]) + ", CAST(`user_id` AS CHAR))"
        try:
            df = qdf(
                f"""
                SELECT user_id, {expr} AS display_name
                FROM `user`
                WHERE user_id IN ({placeholders})
                """,
                tuple(clean_ids),
            )
            for _, r in df.iterrows():
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
        return str(value) if str(value) != "NaT" else ""


def build_ap_audit_display(df: pd.DataFrame) -> pd.DataFrame:
    """Return 建檔人/建檔時間/最後修改人/修改時間 for AP master rows."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["建檔人員", "建檔時間", "最後修改人", "修改時間"])

    created_ids = []
    updated_ids = []
    if "audit_created_by" in df.columns:
        created_ids = pd.to_numeric(df["audit_created_by"], errors="coerce").dropna().astype(int).tolist()
    if "audit_updated_by" in df.columns:
        updated_ids = pd.to_numeric(df["audit_updated_by"], errors="coerce").dropna().astype(int).tolist()
    user_map = fetch_user_display_map(created_ids + updated_ids)

    rows = []
    for _, r in df.iterrows():
        created_by = r.get("audit_created_by") if "audit_created_by" in df.columns else None
        updated_by = r.get("audit_updated_by") if "audit_updated_by" in df.columns else None
        created_at = r.get("audit_created_at") if "audit_created_at" in df.columns else None
        updated_at = r.get("audit_updated_at") if "audit_updated_at" in df.columns else None

        def _uid(v):
            try:
                if v is None or pd.isna(v):
                    return None
                return int(v)
            except Exception:
                return None

        c_uid = _uid(created_by)
        u_uid = _uid(updated_by)
        created_name = user_map.get(c_uid, "") if c_uid else ""
        created_time = _format_datetime_blank(created_at)

        # If DB auto-filled updated_at/updated_by on insert, treat it as "not modified yet".
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


def force_refresh_ap01_accounts_payable_head() -> None:
    """Force AP01 to release the cached DB connection and re-read AP Head data.

    This is used by the refresh button under the upper master table. It is mainly
    for cases where AP01 still shows an old accounts_payable_head value after
    another page/session updates AP data.
    """
    try:
        conn = _get_conn()
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

    try:
        _get_conn.clear()
    except Exception:
        pass

    try:
        _SCHEMA_CACHE.clear()
    except Exception:
        pass

    try:
        st.cache_data.clear()
    except Exception:
        pass

# =========================================================
# Business helpers
# =========================================================
TZ = ZoneInfo("Asia/Ho_Chi_Minh")

def today_local() -> date:
    return datetime.now(TZ).date()

def gen_ap_code(prefix_date: date) -> str:
    """
    規則：AP + yy + mm + 4碼流水號
    EX: AP26010001
    """
    yymm = prefix_date.strftime("%y%m")
    like_pat = f"AP{yymm}%"
    df = qdf(
        """
        SELECT ap_code
        FROM accounts_payable_head
        WHERE ap_code LIKE %s
        ORDER BY ap_code DESC
        LIMIT 1
        """,
        (like_pat,),
    )
    if df.empty or not df.iloc[0]["ap_code"]:
        seq = 1
    else:
        last_code = str(df.iloc[0]["ap_code"])
        try:
            seq = int(last_code[-4:]) + 1
        except Exception:
            seq = 1
    return f"AP{yymm}{seq:04d}"

def parse_tax_rate_input(x: str) -> float:
    """
    使用者輸入 8 -> 0.08
    使用者輸入 0.08 -> 0.08
    使用者輸入 8% -> 0.08
    """
    if x is None:
        return 0.0
    s = str(x).strip().replace("％", "%")
    if s == "":
        return 0.0
    s = s.replace("%", "")
    try:
        v = float(s)
    except Exception:
        return 0.0
    # heuristic: >1 treated as percent
    if v > 1:
        return v / 100.0
    return v

def to_decimal(x, default=0.0) -> float:
    try:
        if x is None or str(x).strip() == "":
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def payment_status_light(status: str | None) -> str:
    """Return a simple traffic-light symbol for AP payment status."""
    s = str(status or "").strip()
    if s == "已付款":
        return "🟢"
    if s == "部分付款":
        return "🟡"
    if s == "未付款":
        return "🔴"
    if s == "未建立AP":
        return "⚪"
    return "⚪"


# =========================================================
# Terms helpers: checkout date & due date (30E/360 style)
# =========================================================
def get_supplier_terms(supplier_id: int | None = None, msioh_id: int | None = None):
    """Return (checkout_day:int|None, payment_days:int|None) from supplier master.

    Priority:
      1) If supplier_id provided -> query supplier directly
      2) Else if msioh_id provided -> derive supplier via material_stock_io_head then query terms
    """
    row = None
    if supplier_id:
        row = qone(
            "SELECT checkout_date, payment_days FROM supplier WHERE supplier_id=%s",
            (int(supplier_id),),
        )
    elif msioh_id:
        row = qone(
            """
            SELECT s.checkout_date, s.payment_days
            FROM material_stock_io_head h
            JOIN supplier s ON s.supplier_id = h.supplier_id
            WHERE h.msioh_id = %s
            """,
            (int(msioh_id),),
        )

    if not row:
        return None, None

    checkout_day = row.get("checkout_date")
    pay_days = row.get("payment_days")

    try:
        checkout_day = int(checkout_day) if checkout_day is not None and str(checkout_day).strip() != "" else None
    except Exception:
        checkout_day = None
    try:
        pay_days = int(pay_days) if pay_days is not None and str(pay_days).strip() != "" else None
    except Exception:
        pay_days = None

    # Treat 0 or out-of-range as missing
    if checkout_day is not None and not (1 <= checkout_day <= 31):
        checkout_day = None
    if pay_days is not None and pay_days < 0:
        pay_days = None

    return checkout_day, pay_days



def get_supplier_tax_rate(supplier_id: int | None = None, msioh_id: int | None = None) -> int | None:
    """Return supplier.tax_rate (int) from supplier master.

    Priority:
      1) If supplier_id provided -> query supplier directly
      2) Else if msioh_id provided -> derive supplier via material_stock_io_head then query tax_rate
    """
    row = None
    if supplier_id:
        row = qone("SELECT tax_rate FROM supplier WHERE supplier_id=%s", (int(supplier_id),))
    elif msioh_id:
        row = qone(
            """
            SELECT s.tax_rate
            FROM material_stock_io_head h
            JOIN supplier s ON s.supplier_id = h.supplier_id
            WHERE h.msioh_id = %s
            """,
            (int(msioh_id),),
        )
    if not row:
        return None
    v = row.get("tax_rate")
    try:
        return int(v) if v is not None and str(v).strip() != "" else None
    except Exception:
        return None
def calc_checkout_date(invoice_date: date, checkout_day: int | None):
    """Given invoice date and supplier checkout day-of-month, return the checkout date.
    Rule: if invoice_day <= checkout_day -> same month; else -> next month.
    If checkout_day is None -> None.
    """
    if not invoice_date or not checkout_day:
        return None
    y, m = invoice_date.year, invoice_date.month
    if invoice_date.day > checkout_day:
        # move to next month
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    # clamp checkout_day to actual month end to avoid invalid dates (e.g., Feb 30)
    last_day = calendar.monthrange(y, m)[1]
    d = min(checkout_day, last_day)
    return date(y, m, d)

def add_days_30e_360(d: date, days: int):
    """Add days using 30-day months convention (30E/360).
    Months are treated as 30 days; result is clamped to real calendar month-end if needed.
    """
    if not d or days is None:
        return None
    days = int(days)
    # encode to 30E/360 serial
    day = min(d.day, 30)
    serial = d.year * 360 + (d.month - 1) * 30 + (day - 1)
    serial += days
    y = serial // 360
    rem = serial % 360
    m = rem // 30 + 1
    day30 = rem % 30 + 1
    # clamp to real calendar
    last_day = calendar.monthrange(y, m)[1]
    return date(y, m, min(day30, last_day))



# =========================================================
# Supplier option helpers (for dropdown filters)
# =========================================================
def get_supplier_major_categories():
    """Return the active supplier major categories for the AP filters."""
    sql = """
        SELECT supplier_major_category_id AS id, supplier_major_category_name AS name
        FROM supplier_major_category
        WHERE is_active = 1
        ORDER BY supplier_major_category_name
    """
    try:
        df = qdf(sql, [])
    except Exception:
        return []
    return [{"id": int(r["id"]), "name": str(r["name"])} for _, r in df.iterrows()]


def get_supplier_categories(major_category_id: int | None = None):
    """Return categories; when a major category is selected, show its used subcategories only."""
    if major_category_id is None:
        sql = """
            SELECT supplier_category_id AS id, supplier_category_name AS name
            FROM supplier_category
            ORDER BY supplier_category_name
        """
        params = []
    else:
        sql = """
            SELECT DISTINCT sc.supplier_category_id AS id, sc.supplier_category_name AS name
            FROM supplier_category sc
            JOIN supplier s ON s.supplier_category = sc.supplier_category_id
            WHERE s.supplier_major_category_id = %s
            ORDER BY sc.supplier_category_name
        """
        params = [int(major_category_id)]
    try:
        df = qdf(sql, params)
    except Exception:
        return []
    return [{"id": int(r["id"]), "name": str(r["name"])} for _, r in df.iterrows()]


def get_suppliers_by_category(major_category_id: int | None, category_id: int | None):
    """Return suppliers filtered by the selected major/category pair."""
    where = []
    params = []
    if major_category_id is not None:
        where.append("supplier_major_category_id = %s")
        params.append(int(major_category_id))
    if category_id is not None:
        where.append("supplier_category = %s")
        params.append(int(category_id))

    if not where:
        sql = """
            SELECT supplier_id AS id,
                   CONCAT(COALESCE(supplier_shortname,''), ' ', COALESCE(supplier_name,'')) AS label
            FROM supplier
            ORDER BY supplier_name
        """
    else:
        sql = f"""
            SELECT supplier_id AS id,
                   CONCAT(COALESCE(supplier_shortname,''), ' ', COALESCE(supplier_name,'')) AS label
            FROM supplier
            WHERE {' AND '.join(where)}
            ORDER BY supplier_name
        """
    try:
        df = qdf(sql, params)
    except Exception:
        return []
    return [{"id": int(r["id"]), "label": str(r["label"]).strip()} for _, r in df.iterrows()]


# =========================================================
# Query: deliveries (material IN) + computed base amount + existing AP
# =========================================================
def load_deliveries(start_date: date | None, end_date: date | None, supplier_major_category_id: int | None, supplier_category_id: int | None, supplier_id: int | None, limit: int, offset: int):
    where = [
        "h.io_type='IN'",
        "h.doc_no IS NOT NULL",
        "h.status <> 'void'",
        # AP01 只顯示已經有明細的入庫單。
        # S01 確認主表時會先建立 material_stock_io_head，資料庫 trigger 也會先建立 AP head；
        # 若使用者還沒新增任何 line，就會出現 0 金額 AP。這裡直接排除空主表，避免現場看到假帳款。
        "EXISTS (SELECT 1 FROM material_stock_io_line lx WHERE lx.msioh_id = h.msioh_id)",
    ]
    params = []

    if start_date:
        where.append("DATE(h.io_time) >= %s")
        params.append(start_date)
    if end_date:
        where.append("DATE(h.io_time) <= %s")
        params.append(end_date)

    # 樣品、搭贈及「不付款補料單」不應形成應付帳款；一般採購與
    # 「要付款補料單」則應納入 AP。舊資料與未綁採購單的入庫仍維持
    # 原本可付款的行為。
    if HAS_ORDER_HEAD_PURCHASE_CATEGORY:
        where.append(
            "COALESCE(oh.purchase_order_category, 'general') "
            "IN ('general', 'material_replenishment_paid')"
        )

    if supplier_major_category_id is not None:
        where.append("s.supplier_major_category_id = %s")
        params.append(int(supplier_major_category_id))
    if supplier_category_id is not None:
        where.append("s.supplier_category = %s")
        params.append(int(supplier_category_id))
    if supplier_id is not None:
        where.append("s.supplier_id = %s")
        params.append(int(supplier_id))

    where_sql = " AND ".join(where)

    # amount_base: sum(qty_for_amount * frozen line unit_price)
    sql = f"""
    WITH line_amount AS (
        SELECT
            l.msioh_id,
            SUM(
                CASE
                    WHEN COALESCE(l.subtotal, 0) <> 0 THEN COALESCE(l.subtotal, 0)
                    ELSE
                        (
                            CASE
                                WHEN m.TrackingMod = 'PCS' THEN COALESCE(NULLIF(l.qty_pcs,0), l.qty_raw, 0)
                                ELSE
                                    CASE
                                        WHEN l.weight_unit = 'g' THEN COALESCE(l.qty_raw,0) / 1000.0
                                        ELSE COALESCE(l.qty_raw,0)
                                    END
                            END
                        ) * COALESCE(NULLIF(l.unit_price,0), 0)
                END
            ) AS amount_base
        FROM material_stock_io_line l
        LEFT JOIN material m ON m.item_id = l.item_id
        GROUP BY l.msioh_id
    ),
    payment_sum AS (
        SELECT
            ap_id,
            SUM(
                CASE
                    WHEN COALESCE(status, 'posted') <> 'void' THEN COALESCE(payment_amount, 0)
                    ELSE 0
                END
            ) AS paid_amount
        FROM accounts_payable_payment
        GROUP BY ap_id
    )
    SELECT
        h.msioh_id,
        h.io_time,
        h.doc_no,
        h.supplier_delivery_number,
        sc.supplier_category_name AS supplier_category,
        h.supplier_id,
        s.supplier_name,
        h.order_id,
        oh.order_num,
        COALESCE(la.amount_base, 0) AS amount_base_calc,
        ap.ap_id,
        ap.ap_code,
        ap.supplier_invoice_no,
        ap.supplier_invoice_date,
        ap.amount_total,
        ap.adjustment_amount,
        ap.tax_rate,
        ROUND((COALESCE(ap.amount_total,0) + COALESCE(ap.adjustment_amount,0)) * (1 + COALESCE(ap.tax_rate,0)/100.0), 2) AS amount_include_tax,
        COALESCE(ps.paid_amount, 0) AS paid_amount,
        CASE
            WHEN ap.ap_id IS NULL THEN '未建立AP'
            WHEN COALESCE(ps.paid_amount, 0) <= 0 THEN '未付款'
            WHEN COALESCE(ps.paid_amount, 0) >= ROUND((COALESCE(ap.amount_total,0) + COALESCE(ap.adjustment_amount,0)) * (1 + COALESCE(ap.tax_rate,0)/100.0), 2)
                 AND ROUND((COALESCE(ap.amount_total,0) + COALESCE(ap.adjustment_amount,0)) * (1 + COALESCE(ap.tax_rate,0)/100.0), 2) > 0 THEN '已付款'
            ELSE '部分付款'
        END AS payment_status,
        ap.due_date,
        ap.status,
        ap.created_by AS audit_created_by,
        ap.created_at AS audit_created_at,
        ap.updated_by AS audit_updated_by,
        ap.updated_at AS audit_updated_at
    FROM material_stock_io_head h
    LEFT JOIN supplier s ON s.supplier_id = h.supplier_id
    LEFT JOIN supplier_category sc ON sc.supplier_category_id = s.supplier_category
    LEFT JOIN order_head oh ON oh.order_id = h.order_id
    LEFT JOIN line_amount la ON la.msioh_id = h.msioh_id
    LEFT JOIN accounts_payable_head ap
        ON ap.delivery_no = h.doc_no AND ap.supplier_id = h.supplier_id AND ap.reference_receipts = 'delivery'
    LEFT JOIN payment_sum ps
        ON ps.ap_id = ap.ap_id
    WHERE {where_sql}
    ORDER BY h.io_time DESC
    LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    df = qdf(sql, tuple(params))
    return df

def load_delivery_lines(msioh_id: int) -> pd.DataFrame:
    """Load delivery lines for a material_stock_io_head (msioh_id).

    Rules:
    - Use frozen historical price from material_stock_io_line.unit_price/subtotal.
    - Do NOT read material.price_unit because material master no longer owns AP pricing.
      AP calculation must follow supplier delivery-time price snapshot in material_stock_io_line.
    """
    sql = """
    SELECT
        l.line_no,
        l.item_id,
        l.item_name,
        m.specification,
        m.TrackingMod,
        m.purchase_unit,
        l.qty_raw,
        l.weight_unit,
        l.qty_pcs,
        l.unit_price AS line_unit_price,
        l.subtotal  AS line_subtotal,
        l.note
    FROM material_stock_io_line l
    LEFT JOIN material m ON m.item_id = l.item_id
    WHERE l.msioh_id = %s
    ORDER BY l.line_no
    """
    df = qdf(sql, (msioh_id,))
    if df.empty:
        return df

    def qty_show(r):
        if (r.get("TrackingMod") or "").upper() == "PCS":
            qty = r.get("qty_pcs")
            unit = "PCS"
            try:
                if qty is None or float(qty) == 0:
                    qty = r.get("qty_raw", 0)
                    unit = r.get("purchase_unit") or "PCS"
            except Exception:
                qty = r.get("qty_raw", 0)
                unit = r.get("purchase_unit") or "PCS"
            return float(qty or 0), unit
        # weight display uses raw + unit
        qty = r.get("qty_raw", 0)
        unit = r.get("weight_unit") or (r.get("purchase_unit") or "kg")
        return float(qty or 0), unit

    qty_vals = df.apply(lambda r: qty_show(r), axis=1, result_type="expand")
    df["qty_display"] = qty_vals[0]
    df["unit_display"] = qty_vals[1]

    # Effective unit price: supplier delivery-time price snapshot only.
    # material.price_unit was removed from material master, and AP should not use current master price.
    def pick_unit_price(r):
        try:
            return float(r.get("line_unit_price")) if r.get("line_unit_price") is not None else 0.0
        except Exception:
            return 0.0

    df["unit_price"] = df.apply(pick_unit_price, axis=1)

    # Effective subtotal: frozen line subtotal first; if missing/0, calculate using unit_price * quantity-for-amount
    def pick_subtotal(r):
        try:
            s = float(r.get("line_subtotal")) if r.get("line_subtotal") is not None else 0.0
        except Exception:
            s = 0.0
        if s != 0.0:
            return s
        qty_amt = _qty_for_amount(r.get("TrackingMod"), r.get("qty_raw"), r.get("weight_unit"), r.get("qty_pcs"))
        try:
            return float(r.get("unit_price") or 0.0) * float(qty_amt or 0.0)
        except Exception:
            return 0.0

    df["subtotal"] = df.apply(pick_subtotal, axis=1)
    return df

def _qty_for_amount(tracking_mod: str | None, qty_raw, weight_unit: str | None, qty_pcs):
    """Return numeric quantity used for amount calculation."""
    try:
        q_raw = float(qty_raw) if qty_raw is not None else 0.0
    except Exception:
        q_raw = 0.0
    try:
        q_pcs = float(qty_pcs) if qty_pcs is not None else 0.0
    except Exception:
        q_pcs = 0.0

    if (tracking_mod or "").upper() == "PCS":
        # Prefer PCS count if available
        if q_pcs != 0:
            return q_pcs
        return q_raw

    # weight-based: normalize to kg when possible
    wu = (weight_unit or "").lower()
    if wu == "g":
        return q_raw / 1000.0
    return q_raw


def calc_amount_base_from_lines(df_lines: pd.DataFrame) -> float:
    """Compute amount_base from delivery lines using unit_price."""
    if df_lines is None or df_lines.empty:
        return 0.0
    amt = 0.0
    for _, r in df_lines.iterrows():
        qty = _qty_for_amount(r.get("TrackingMod"), r.get("qty_raw"), r.get("weight_unit"), r.get("qty_pcs"))
        try:
            up = float(r.get("unit_price") or 0.0)
        except Exception:
            up = 0.0
        amt += qty * up
    return float(amt)


def load_payments(ap_id: int) -> pd.DataFrame:
    has_bank_account_id = has_column("accounts_payable_payment", "bank_account_id")
    has_supplier_bank_account_id = has_column("accounts_payable_payment", "supplier_bank_account_id")

    bank_id_select = "p.bank_account_id" if has_bank_account_id else "NULL AS bank_account_id"
    supplier_bank_id_select = "p.supplier_bank_account_id" if has_supplier_bank_account_id else "NULL AS supplier_bank_account_id"

    bank_join = "LEFT JOIN our_bank ob ON ob.our_bank_id = p.bank_account_id" if has_bank_account_id else "LEFT JOIN our_bank ob ON 1=0"
    supplier_bank_join = (
        "LEFT JOIN supplier_bank_account sb ON sb.Supplier_bank_account_id = p.supplier_bank_account_id"
        if has_supplier_bank_account_id
        else "LEFT JOIN supplier_bank_account sb ON 1=0"
    )

    sql = f"""
    SELECT
        p.payment_id,
        p.payment_date,
        p.payment_amount,
        p.payment_method,
        p.payment_reference,
        {bank_id_select},
        {supplier_bank_id_select},
        COALESCE(
            NULLIF(CONCAT_WS(' | ',
                NULLIF(ob.our_company_bank_name, ''),
                NULLIF(ob.our_company_bank_num, ''),
                NULLIF(ob.our_company_account_name, ''),
                NULLIF(ob.our_company_account_code, '')
            ), ''),
            p.payment_reference,
            ''
        ) AS our_bank_display,
        COALESCE(
            NULLIF(CONCAT_WS(' | ',
                NULLIF(sb.bank_name, ''),
                NULLIF(sb.bank_id, ''),
                NULLIF(sb.account_name, ''),
                NULLIF(sb.bank_account, '')
            ), ''),
            p.Supplier_bank_account,
            ''
        ) AS supplier_bank_display,
        p.voucher_no,
        p.Supplier_bank_account,
        p.status,
        p.updated_at
    FROM accounts_payable_payment p
    {bank_join}
    {supplier_bank_join}
    WHERE p.ap_id = %s AND p.status <> 'void'
    ORDER BY p.payment_date ASC, p.payment_id ASC
    """
    return qdf(sql, (ap_id,))


def _ap_resource_amount_total(ap_id: int) -> float:
    """Fallback total from ap_resource when AP head amount_total is empty."""
    amount_candidates = [
        "line_amount", "amount", "amount_total", "subtotal", "sub_total",
        "total_amount", "payable_amount", "payment_total",
    ]
    amount_col = next((c for c in amount_candidates if has_column("ap_resource", c)), None)
    if not amount_col:
        return 0.0
    try:
        row = qone(
            f"SELECT COALESCE(SUM(`{amount_col}`), 0) AS total FROM ap_resource WHERE ap_id=%s",
            (int(ap_id),),
        )
        return float((row or {}).get("total") or 0.0)
    except Exception:
        return 0.0


def calc_ap_payable_total(ap_id: int) -> float:
    """AP01/AP03 unified payable amount.

    delivery: (amount_total or ap_resource fallback + adjustment_amount) * (1 + tax_rate/100)
    manual/order: AP01 already stores the tax-included total in amount_total.
    """
    row = qone(
        """
        SELECT reference_receipts, amount_total, adjustment_amount, tax_rate
        FROM accounts_payable_head
        WHERE ap_id=%s
        LIMIT 1
        """,
        (int(ap_id),),
    )
    if not row:
        return 0.0

    ref_type = str(row.get("reference_receipts") or "delivery").strip()
    amount_total = to_decimal(row.get("amount_total"), 0.0)
    adjustment_amount = to_decimal(row.get("adjustment_amount"), 0.0)
    tax_rate = to_decimal(row.get("tax_rate"), 0.0)

    if ref_type == "delivery":
        base = amount_total if amount_total != 0 else _ap_resource_amount_total(int(ap_id))
        return round((base + adjustment_amount) * (1 + tax_rate / 100.0), 2)

    return round(amount_total, 2)


def calc_ap_paid_total(ap_id: int, exclude_payment_id: int | None = None) -> float:
    params = [int(ap_id)]
    exclude_sql = ""
    if exclude_payment_id:
        exclude_sql = " AND payment_id <> %s"
        params.append(int(exclude_payment_id))
    row = qone(
        f"""
        SELECT COALESCE(SUM(payment_amount), 0) AS paid_total
        FROM accounts_payable_payment
        WHERE ap_id=%s
          AND COALESCE(status, 'draft') <> 'void'
          {exclude_sql}
        """,
        tuple(params),
    )
    return float((row or {}).get("paid_total") or 0.0)


def sync_ap_head_payment_status(ap_id: int) -> None:
    """Keep accounts_payable_head balance/status aligned with posted payments."""
    payable_total = calc_ap_payable_total(int(ap_id))
    paid_total = calc_ap_paid_total(int(ap_id))
    balance = max(round(payable_total - paid_total, 2), 0.0)

    if payable_total > 0 and paid_total >= payable_total:
        status = "paid"
    elif paid_total > 0:
        status = "partial"
    else:
        status = "posted"

    exec_sql(
        """
        UPDATE accounts_payable_head
        SET balance_amount=%s,
            status=%s,
            updated_at=NOW(),
            updated_by=%s
        WHERE ap_id=%s
        """,
        (float(balance), status, int(st.session_state.get("user_id", 1)), int(ap_id)),
    )


def load_our_bank_options() -> pd.DataFrame:
    """Load our payment bank accounts for AP01 payment dropdown."""
    try:
        df = qdf(
            """
            SELECT
                our_bank_id,
                COALESCE(our_company_bank_name, '') AS bank_name,
                COALESCE(our_company_bank_num, '') AS bank_code,
                COALESCE(our_company_account_name, '') AS account_name,
                COALESCE(our_company_account_code, '') AS account_code
            FROM our_bank
            ORDER BY our_company_bank_name, our_company_bank_num, our_company_account_name, our_company_account_code
            """
        )
    except Exception:
        return pd.DataFrame(columns=["our_bank_id", "bank_name", "bank_code", "account_name", "account_code", "display_label"])

    if df.empty:
        df["display_label"] = []
        return df

    def make_label(row) -> str:
        parts = [
            str(row.get("bank_name") or "").strip(),
            str(row.get("bank_code") or "").strip(),
            str(row.get("account_name") or "").strip(),
            str(row.get("account_code") or "").strip(),
        ]
        label = " | ".join([x for x in parts if x])
        return label or f"our_bank_id={int(row.get('our_bank_id') or 0)}"

    df["display_label"] = df.apply(make_label, axis=1)
    return df



def load_supplier_bank_options(supplier_id: int | None) -> pd.DataFrame:
    """Load supplier receiving bank accounts for AP01 payment dropdown.

    Display format follows the requested order:
    bank name | bank code | account name | account number
    """
    if not supplier_id:
        return pd.DataFrame(columns=[
            "Supplier_bank_account_id", "bank_name", "bank_code", "account_name", "account_code", "display_label"
        ])

    try:
        df = qdf(
            """
            SELECT
                Supplier_bank_account_id,
                COALESCE(bank_name, '') AS bank_name,
                COALESCE(bank_id, '') AS bank_code,
                COALESCE(account_name, '') AS account_name,
                COALESCE(bank_account, '') AS account_code
            FROM supplier_bank_account
            WHERE supplier_id = %s
              AND COALESCE(status, 'active') <> 'inactive'
            ORDER BY COALESCE(is_default, 0) DESC, bank_name, bank_id, account_name, bank_account
            """,
            (int(supplier_id),),
        )
    except Exception:
        return pd.DataFrame(columns=[
            "Supplier_bank_account_id", "bank_name", "bank_code", "account_name", "account_code", "display_label"
        ])

    if df.empty:
        df["display_label"] = []
        return df

    def make_label(row) -> str:
        parts = [
            str(row.get("bank_name") or "").strip(),
            str(row.get("bank_code") or "").strip(),
            str(row.get("account_name") or "").strip(),
            str(row.get("account_code") or "").strip(),
        ]
        label = " | ".join([x for x in parts if x])
        return label or f"supplier_bank_id={int(row.get('Supplier_bank_account_id') or 0)}"

    df["display_label"] = df.apply(make_label, axis=1)
    return df

def delivery_exists(msioh_id: int | None) -> bool:
    """Return True only when the selected S01 receiving head still exists.

    AP01 keeps selected IDs in session_state. If S01 deletes an 入庫單 in another tab/session,
    this guard prevents AP01 from continuing to edit a stale AP selection.
    """
    if msioh_id is None:
        return False
    row = qone(
        """
        SELECT 1 AS ok
        FROM material_stock_io_head
        WHERE msioh_id = %s
          AND io_type = 'IN'
          AND doc_no IS NOT NULL
          AND status <> 'void'
        LIMIT 1
        """,
        (int(msioh_id),),
    )
    return bool(row)

# =========================================================
# Session state
# =========================================================
if "ap_selected_msioh_id" not in st.session_state:
    st.session_state.ap_selected_msioh_id = None
if "ap_selected_ap_id" not in st.session_state:
    st.session_state.ap_selected_ap_id = None
if "ap_selected_payment_id" not in st.session_state:
    st.session_state.ap_selected_payment_id = None
if "ap_page" not in st.session_state:
    st.session_state.ap_page = 0
if "ap_page_size" not in st.session_state:
    st.session_state.ap_page_size = 20

# =========================================================
# Search area + pager
# =========================================================
st.subheader(_t("應付帳款統計"))

q1, q2, q3, q4, q5, q6 = st.columns([1.1, 1.1, 1.2, 1.2, 1.2, 2.6], vertical_alignment="bottom")

# Default date range:
# - If today is 1~25: start = last month 26, end = today
# - If today is 26~EOM: start = this month 26, end = today
today_local_date = datetime.now(ZoneInfo("Asia/Taipei")).date()
if today_local_date.day <= 25:
    y = today_local_date.year
    m = today_local_date.month - 1
    if m == 0:
        y -= 1
        m = 12
    default_start = date(y, m, 26)
else:
    default_start = date(today_local_date.year, today_local_date.month, 26)
default_end = today_local_date

with q1:
    st.caption(_t("起始日期"))
    start_date = st.date_input("q_start_date", value=default_start, label_visibility="collapsed")
with q2:
    st.caption(_t("結束日期"))
    end_date = st.date_input("q_end_date", value=default_end, label_visibility="collapsed")

# Supplier major category + category + supplier dropdowns (linked)
major_cats = get_supplier_major_categories()
major_cat_options = [{"id": None, "name": "全部"}] + major_cats
major_cat_labels = [c["name"] for c in major_cat_options]

major_cat_label_selected = st.session_state.get("q_supplier_major_cat_label", "全部")
if major_cat_label_selected not in major_cat_labels:
    major_cat_label_selected = "全部"

with q3:
    st.caption(_t("供應商大類"))
    major_cat_label_selected = st.selectbox(
        "q_supplier_major_cat",
        options=major_cat_labels,
        index=major_cat_labels.index(major_cat_label_selected),
        label_visibility="collapsed",
    )
    st.session_state["q_supplier_major_cat_label"] = major_cat_label_selected

selected_major_cat_id = next(
    (c["id"] for c in major_cat_options if c["name"] == major_cat_label_selected), None
)

cats = get_supplier_categories(selected_major_cat_id)
cat_options = [{"id": None, "name": "全部"}] + cats
cat_labels = [c["name"] for c in cat_options]

# Remember selection
cat_label_selected = st.session_state.get("q_supplier_cat_label", "全部")
if cat_label_selected not in cat_labels:
    cat_label_selected = "全部"

with q4:
    st.caption(_t("供應商類別"))
    cat_label_selected = st.selectbox("q_supplier_cat", options=cat_labels, index=cat_labels.index(cat_label_selected), label_visibility="collapsed")
    st.session_state["q_supplier_cat_label"] = cat_label_selected

selected_cat_id = next((c["id"] for c in cat_options if c["name"] == cat_label_selected), None)

sup_list = get_suppliers_by_category(selected_major_cat_id, selected_cat_id)
sup_options = [{"id": None, "label": "全部"}] + sup_list
sup_labels = [s["label"] for s in sup_options]

sup_label_selected = st.session_state.get("q_supplier_label", "全部")
if sup_label_selected not in sup_labels:
    sup_label_selected = "全部"

with q5:
    st.caption(_t("供應商名稱"))
    sup_label_selected = st.selectbox("q_supplier", options=sup_labels, index=sup_labels.index(sup_label_selected), label_visibility="collapsed")
    st.session_state["q_supplier_label"] = sup_label_selected

selected_supplier_id = next((s["id"] for s in sup_options if s["label"] == sup_label_selected), None)

with q6:
    p1, p2, p3 = st.columns([1, 1, 1], vertical_alignment="bottom")
    with p1:
        st.write("")
        if st.button(_t("上一頁"), key="ap_prev", use_container_width=True):
            st.session_state.ap_page = max(0, st.session_state.ap_page - 1)
    with p2:
        st.write("")
        new_size = st.selectbox(_t("顯示筆數"), options=[10, 20, 50, 100], index=[10,20,50,100].index(st.session_state.ap_page_size), label_visibility="collapsed")
        st.session_state.ap_page_size = int(new_size)
    with p3:
        st.write("")
        if st.button(_t("下一頁"), key="ap_next", use_container_width=True):
            st.session_state.ap_page += 1

st.divider()

# =========================================================
# Main table
# =========================================================
offset = st.session_state.ap_page * st.session_state.ap_page_size
df_del = load_deliveries(
    start_date,
    end_date,
    selected_major_cat_id,
    selected_cat_id,
    selected_supplier_id,
    st.session_state.ap_page_size,
    offset,
)

# Build display dataframe
if df_del.empty:
    st.info(_t("找不到符合條件的入庫單（io_type='IN' 且 doc_no 不為空）。"))
    df_show = pd.DataFrame(columns=[
        "勾選","應付帳款單號","供應商送貨單號","供應商種類","供應商名稱",
        "供應商送貨日期","供應商發票號碼","我方訂單號","未稅金額(試算)","含稅金額(已建AP)","燈號","付款狀況","應付日期","狀態",
        "建檔人員","建檔時間","最後修改人","修改時間"
    ])
else:
    audit_show = build_ap_audit_display(df_del)
    df_show = pd.DataFrame({
        "勾選": [False]*len(df_del),
        "msioh_id": df_del["msioh_id"],
        "ap_id": df_del["ap_id"],
        "應付帳款單號": df_del["ap_code"].fillna(""),
        "供應商送貨單號": df_del["supplier_delivery_number"].fillna(""),
        "供應商種類": df_del["supplier_category"].fillna(""),
        "供應商名稱": df_del["supplier_name"].fillna(""),
        "供應商送貨日期": pd.to_datetime(df_del["io_time"]).dt.date,
        "供應商發票號碼": df_del["supplier_invoice_no"].fillna(""),
        "我方訂單號": df_del["order_num"].fillna(""),
        "未稅金額(試算)": df_del["amount_base_calc"].fillna(0),
        "含稅金額(已建AP)": df_del.get("amount_include_tax", df_del["amount_total"]).fillna(0),
        "燈號": df_del["payment_status"].fillna("未付款").map(payment_status_light),
        "付款狀況": df_del["payment_status"].fillna("未付款").map(lambda x: _t(str(x))),
        "應付日期": pd.to_datetime(df_del["due_date"]).dt.date if "due_date" in df_del.columns else None,
        "狀態": df_del["status"].fillna(""),
        "doc_no": df_del["doc_no"].fillna(""),
        "supplier_id": df_del["supplier_id"].fillna(0).astype("Int64"),
        "supplier_category_name": df_del["supplier_category"].fillna(""),
        "io_time": pd.to_datetime(df_del["io_time"]),
        "order_id": df_del["order_id"],
        "order_num": df_del["order_num"].fillna(""),
        "建檔人員": audit_show["建檔人員"] if not audit_show.empty else [""] * len(df_del),
        "建檔時間": audit_show["建檔時間"] if not audit_show.empty else [""] * len(df_del),
        "最後修改人": audit_show["最後修改人"] if not audit_show.empty else [""] * len(df_del),
        "修改時間": audit_show["修改時間"] if not audit_show.empty else [""] * len(df_del),
    })

    # prettier numeric
    for c in ["未稅金額(試算)","含稅金額(已建AP)"]:
        df_show[c] = pd.to_numeric(df_show[c], errors="coerce").fillna(0.0).round(2)

# Editor (hide internal columns, then translate visible headers)
HIDE_COLS = ["msioh_id", "ap_id", "supplier_id", "supplier_category_name", "order_id", "order_num"]
df_visible = df_show.drop(columns=[c for c in HIDE_COLS if c in df_show.columns], errors="ignore")

# User-facing aliases for technical columns that are still useful on the grid.
display_alias = {
    "doc_no": "入庫單號",
    "io_time": "入庫時間",
}
df_visible = df_visible.rename(columns=display_alias)

if not df_visible.empty:
    select_col = _t("勾選")
    df_visible_i18n = df_visible.rename(columns={c: _t(c) for c in df_visible.columns})
    visible_cols = [select_col] + [c for c in df_visible_i18n.columns if c != select_col]

    edited = st.data_editor(
        df_visible_i18n[visible_cols].copy(),
        use_container_width=True,
        hide_index=True,
        column_config={
            select_col: st.column_config.CheckboxColumn(width="small"),
        },
        disabled=[c for c in df_visible_i18n.columns if c != select_col],  # only checkbox editable
    )

    selected_idx = edited.index[edited[select_col] == True].tolist()
    if len(selected_idx) > 1:
        st.warning(_t("一次只能勾選一筆入庫單。請只留一個勾選 ✅"))
    if len(selected_idx) >= 1:
        idx = selected_idx[0]
        # Use df_show (full columns) to keep internal IDs for downstream logic
        row = df_show.loc[idx]
        st.session_state.ap_selected_msioh_id = int(row["msioh_id"])
        st.session_state.ap_selected_ap_id = int(row["ap_id"]) if pd.notna(row["ap_id"]) else None
        st.session_state.ap_selected_payment_id = None
else:
    st.dataframe(df_visible.rename(columns={c: _t(c) for c in df_visible.columns}), use_container_width=True)

refresh_col, _ = st.columns([1.1, 5.5], vertical_alignment="center")
with refresh_col:
    if st.button(_t("重新整理"), key="ap01_refresh_master_table", use_container_width=True):
        force_refresh_ap01_accounts_payable_head()
        st.session_state.ap_selected_msioh_id = None
        st.session_state.ap_selected_ap_id = None
        st.session_state.ap_selected_payment_id = None
        st.rerun()

st.divider()

# =========================================================
# Detail area
# =========================================================
st.subheader(_t("明細編輯區"))
tab_basic, tab_delivery, tab_pay = st.tabs([_t("基本資訊"), _t("供應商送貨明細"), _t("匯款狀況")])

selected_msioh_id = st.session_state.ap_selected_msioh_id
selected_ap_id = st.session_state.ap_selected_ap_id

# AP01 uses session_state for the selected receiving record.
# If S01 already hard-deleted that receiving record and its AP data, clear stale selection here.
if selected_msioh_id is not None and not delivery_exists(int(selected_msioh_id)):
    st.session_state.ap_selected_msioh_id = None
    st.session_state.ap_selected_ap_id = None
    st.session_state.ap_selected_payment_id = None
    selected_msioh_id = None
    selected_ap_id = None
    st.info(_t("選取的入庫單已不存在，已清除明細選取狀態。"))

# Load selected delivery header details for prefill
sel = {}
if selected_msioh_id is not None and not df_del.empty:
    sel_df = df_del[df_del["msioh_id"] == selected_msioh_id]
    if not sel_df.empty:
        sel = sel_df.iloc[0].to_dict()

# =========================================================
# TAB: 基本資訊
# =========================================================
with tab_basic:
    st.markdown(f"#### {_t('基本資訊')}")

    if selected_msioh_id is None:
        st.info(_t("請先在上方列表勾選一筆入庫單。"))
    else:
        # Defaults from selection / DB
        supplier_id = int(pd.to_numeric(pd.Series([sel.get("supplier_id")]), errors="coerce").fillna(0).iloc[0])
        supplier_name = str(sel.get("supplier_name") or "")
        supplier_category_name = str(sel.get("supplier_category") or "")
        delivery_no = str(sel.get("doc_no") or "")
        supplier_dn_no = str(sel.get("supplier_delivery_number") or "")
        delivery_date = pd.to_datetime(sel.get("io_time")).date() if sel.get("io_time") else None
        order_id = sel.get("order_id")
        order_num = str(sel.get("order_num") or "").strip()
        amount_base_calc = float(sel.get("amount_base_calc") or 0.0)
        # Safety: if header-side calc is 0, recompute from lines + unit price
        df_lines_calc = load_delivery_lines(int(selected_msioh_id))
        if amount_base_calc == 0.0:
            amount_base_calc = calc_amount_base_from_lines(df_lines_calc)

        # If AP exists, load it to prefill editable fields
        ap_row = {}
        if selected_ap_id:
            ap_row_df = qdf("SELECT * FROM accounts_payable_head WHERE ap_id = %s", (selected_ap_id,))
            if not ap_row_df.empty:
                ap_row = ap_row_df.iloc[0].to_dict()

        ap_code_default = ap_row.get("ap_code") or ""
        ref_default = ap_row.get("reference_receipts") or "delivery"
        inv_no_default = ap_row.get("supplier_invoice_no") or ""
        inv_date_default = ap_row.get("supplier_invoice_date") or delivery_date or today_local()
        # Auto-generate AP code preview for new records
        if not ap_code_default and inv_date_default:
            try:
                inv_dt = pd.to_datetime(inv_date_default).date() if not isinstance(inv_date_default, date) else inv_date_default
            except Exception:
                inv_dt = today_local()
            ap_code_default = gen_ap_code(inv_dt)
        adj_default = ap_row.get("adjustment_amount")
        adj_default = float(adj_default) if adj_default is not None else 0.0
        amount_total_default = float(ap_row.get("amount_total") or 0.0)
        currency_default = ap_row.get("currency") or "VND"
        posting_date_default = ap_row.get("posting_date") or inv_date_default
        due_date_default = ap_row.get("due_date") or inv_date_default

        # UI inputs
        r1 = st.columns([1, 1, 1, 1], vertical_alignment="bottom")
        with r1[0]:
            st.caption(_t("應付帳款單號"))
            st.text_input("ap_no", ap_code_default, label_visibility="collapsed", disabled=True)
        with r1[1]:
            st.caption(_t("供應商種類"))
            st.text_input("supplier_type", supplier_category_name, label_visibility="collapsed", disabled=True)
        with r1[2]:
            st.caption(_t("供應商名稱"))
            st.text_input("supplier_name", supplier_name, label_visibility="collapsed", disabled=True)
        with r1[3]:
            st.caption(_t("依據類型"))
            ref_type = st.selectbox(
                "basis_type",
                options=["delivery", "order", "manual"],
                index=["delivery", "order", "manual"].index(ref_default) if ref_default in ["delivery","order","manual"] else 0,
                label_visibility="collapsed",
            )

        st.write("")

        r2 = st.columns([1, 1, 1, 1], vertical_alignment="bottom")
        with r2[0]:
            st.caption(_t("供應商送貨單號"))
            st.text_input("vendor_dn_no", supplier_dn_no, label_visibility="collapsed", disabled=True)
        with r2[1]:
            st.caption(_t("送貨日期"))
            st.date_input("delivery_date", value=delivery_date, label_visibility="collapsed", disabled=True)
        with r2[2]:
            st.caption(_t("我方訂單號碼"))
            st.text_input("our_order_no", order_num, label_visibility="collapsed", disabled=True)
        with r2[3]:
            st.empty()

        st.write("")

        r3a = st.columns([1, 1, 1, 1, 1], vertical_alignment="bottom")
        with r3a[0]:
            st.caption(_t("供應商發票號碼"))
            supplier_invoice_no = st.text_input("vendor_invoice_no", inv_no_default, label_visibility="collapsed")

        with r3a[1]:
            st.caption(_t("發票日期"))
            supplier_invoice_date = st.date_input("invoice_date", value=inv_date_default, label_visibility="collapsed")

        # Auto terms from supplier master
        checkout_day, supplier_payment_days = get_supplier_terms(supplier_id=int(supplier_id) if supplier_id else None, msioh_id=int(selected_msioh_id) if selected_msioh_id else None)
        checkout_date_calc = calc_checkout_date(supplier_invoice_date, checkout_day)

        # If AP already exists, prefer stored terms/due date when master terms are missing
        try:
            stored_checkout = ap_row.get("checkout_date") if isinstance(ap_row, dict) else None
            stored_pay_days = ap_row.get("payment_days") if isinstance(ap_row, dict) else None
            stored_due = ap_row.get("due_date") if isinstance(ap_row, dict) else None
        except Exception:
            stored_checkout = stored_pay_days = stored_due = None

        if checkout_date_calc is None and stored_checkout:
            try:
                checkout_date_calc = pd.to_datetime(stored_checkout).date() if not isinstance(stored_checkout, date) else stored_checkout
            except Exception:
                pass

        if (supplier_payment_days is None) and (stored_pay_days is not None and str(stored_pay_days).strip() != ""):
            try:
                supplier_payment_days = int(stored_pay_days)
            except Exception:
                pass

        with r3a[2]:
            st.caption(_t("結帳日期(自動)"))
            inv_key = supplier_invoice_date.strftime("%Y%m%d") if supplier_invoice_date else "none"
            term_key_base = f"{selected_msioh_id}_{inv_key}"
            key_checkout = f"checkout_date_calc_{term_key_base}"
            if checkout_date_calc:
                st.date_input("checkout_date_calc_disp", value=checkout_date_calc, key=key_checkout, label_visibility="collapsed", disabled=True)
            else:
                st.text_input("checkout_date_calc_disp_txt", value="", key=key_checkout + "_txt", label_visibility="collapsed", disabled=True)

        with r3a[3]:
            st.caption(_t("付款天數(自動)"))
            payment_days_val = int(supplier_payment_days) if supplier_payment_days is not None else 0
            key_pay = f"payment_days_calc_{term_key_base}"
            st.number_input("payment_days_calc_disp", min_value=0, max_value=3650, value=payment_days_val, step=1, key=key_pay, label_visibility="collapsed", disabled=True)

        with r3a[4]:
            st.caption(_t("應付日期(自動)"))
            due_date_calc = add_days_30e_360(checkout_date_calc, payment_days_val) if checkout_date_calc else None
            # If AP exists and due date already stored, prefer it when calculation is not available
            if due_date_calc is None:
                try:
                    if stored_due:
                        due_date_calc = pd.to_datetime(stored_due).date() if not isinstance(stored_due, date) else stored_due
                except Exception:
                    pass

            if due_date_calc:
                st.date_input("due_date_calc_disp", value=due_date_calc, key=f"due_date_calc_{term_key_base}", label_visibility="collapsed", disabled=True)
            else:
                st.text_input("due_date_calc_disp_txt", value="", key=f"due_date_calc_{term_key_base}_txt", label_visibility="collapsed", disabled=True)


        st.write("")
        st.divider()

        # Amount area
        r_amt = st.columns([1.2, 1.1, 1, 0.8, 1], vertical_alignment="bottom")
        with r_amt[0]:
            st.caption(_t("金額(未含稅、折扣、折讓)"))
            st.number_input("amount_base", value=float(amount_base_calc), step=1.0, label_visibility="collapsed", disabled=True)
        with r_amt[1]:
            st.caption(_t("折扣、折讓金額"))
            discount_amount = st.number_input("discount_amount", value=float(-adj_default) if adj_default else 0.0, step=1.0, label_visibility="collapsed")
        with r_amt[2]:
            st.caption(_t("未稅金額"))
            amount_untaxed = float(amount_base_calc) - float(discount_amount)
            st.number_input("amount_untaxed", value=float(amount_untaxed), step=1.0, label_visibility="collapsed", disabled=True)
        with r_amt[3]:
            st.caption(_t("稅率(%)"))
            # 預設稅率：優先用 AP head 已存值；否則從供應商主檔帶入；再不行就 0
            ap_tax = ap_row.get("tax_rate")
            if ap_tax is None or str(ap_tax).strip() == "":
                sup_tax = get_supplier_tax_rate(supplier_id=int(supplier_id) if supplier_id else None,
                                               msioh_id=int(selected_msioh_id) if selected_msioh_id else None)
                default_tax_rate = sup_tax if sup_tax is not None else 0
            else:
                try:
                    default_tax_rate = int(ap_tax)
                except Exception:
                    default_tax_rate = 0

            tax_key = f"tax_rate_input_{int(supplier_id) if supplier_id else 0}_{int(selected_msioh_id) if selected_msioh_id else 0}_{int(selected_ap_id) if selected_ap_id else 0}"
            if tax_key not in st.session_state:
                st.session_state[tax_key] = str(default_tax_rate)

            tax_rate_text = st.text_input(
                "tax_rate",
                key=tax_key,
                label_visibility="collapsed",
                help="輸入 8 代表 8%（含稅金額 = 未稅金額 * 1.08）"
            )
            tax_rate = parse_tax_rate_input(tax_rate_text)
        with r_amt[4]:
            st.caption(_t("含稅金額"))
            amount_taxed = float(amount_untaxed) * (1.0 + float(tax_rate))
            st.number_input("amount_taxed", value=float(amount_taxed), step=1.0, label_visibility="collapsed", disabled=True)

        st.write("")

        r_cur = st.columns([1, 1, 2], vertical_alignment="bottom")
        with r_cur[0]:
            st.caption(_t("幣別"))
            currency = st.text_input("currency", currency_default, label_visibility="collapsed")
        with r_cur[1]:
            st.caption(_t("匯率"))
            exchange_rate = st.number_input("exchange_rate", value=float(ap_row.get("exchange_rate") or 1.0), step=0.0001, label_visibility="collapsed")
        with r_cur[2]:
            st.caption(_t("備註"))
            note = st.text_input("ap_note", ap_row.get("note") or "", label_visibility="collapsed")

        st.write("")

        # Save logic
        save_col1, save_col2, save_col3 = st.columns([1,1,6], vertical_alignment="bottom")
        with save_col1:
            do_save = st.button(_t("儲存/建立AP"), key="ap_save_basic", use_container_width=True)
        with save_col2:
            do_refresh = st.button(_t("重新整理"), key="ap_refresh", use_container_width=True)
        with save_col3:
            st.empty()

        if do_refresh:
            st.rerun()

        if do_save:
            is_delivery = (ref_type == "delivery")

            # validations: delivery 來源允許發票號碼為空（後補）；manual/order 才強制
            if (not supplier_invoice_no.strip()) and (not is_delivery):
                st.error(_t("供應商發票號碼不可為空。你要讓財會怎麼活？😅"))
            else:
                now_ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
                user_id = int(st.session_state.get("user_id", 1))  # fallback
                created_by = user_id
                approved_by = user_id

                # 折扣/折讓：UI 輸入為正數，DB adjustment_amount 用「負數」存（折抵未稅金額）
                adj_amount = -float(discount_amount)

                # tax_rate：UI 解析後為 0.08 形式，DB 欄位用「整數百分比」(8)
                tax_rate_pct = int(round(float(tax_rate) * 100))

                # delivery 類型：amount_total 由 trigger/ap_resource 匯總維護，UI 不寫入（避免被覆蓋造成你看到不一致）
                if is_delivery:
                    # ensure we have ap_id (trigger should have created it)
                    ap_id_to_update = selected_ap_id
                    if not ap_id_to_update:
                        ap_id_df = qdf(
                            """
                            SELECT ap_id
                            FROM accounts_payable_head
                            WHERE supplier_id=%s AND delivery_no=%s AND reference_receipts='delivery'
                            ORDER BY ap_id DESC
                            LIMIT 1
                            """,
                            (supplier_id, delivery_no),
                        )
                        if not ap_id_df.empty:
                            ap_id_to_update = int(ap_id_df.iloc[0]["ap_id"])
                            st.session_state.ap_selected_ap_id = ap_id_to_update

                    if not ap_id_to_update:
                        st.error(_t("找不到對應的 AP 主檔（delivery）。請確認入庫單已 posted 且 trigger 已正確寫入 accounts_payable_head。"))
                    else:
                        exec_sql(
                            """
                            UPDATE accounts_payable_head
                            SET
                                supplier_invoice_no=%s,
                                supplier_invoice_date=%s,
                                adjustment_amount=%s,
                                tax_rate=%s,
                                currency=%s,
                                exchange_rate=%s,
                                note=%s,
                                updated_by=%s,
                                updated_at=%s
                            WHERE ap_id=%s
                            """,
                            (
                                (supplier_invoice_no.strip() or None),
                                supplier_invoice_date,
                                adj_amount,
                                tax_rate_pct,
                                currency.strip() or "VND",
                                float(exchange_rate),
                                note,
                                created_by,
                                now_ts,
                                int(ap_id_to_update),
                            ),
                        )
                        st.success(_t("已更新應付帳款 ✅"))
                        st.rerun()

                # manual / order：維持原本建立/更新邏輯（這類才允許 UI 寫入 amount_total/balance 等）
                amount_total = float(amount_taxed)
                balance_amount = amount_total

                # ---- Safety guards: DB columns due_date/checkout_date are NOT NULL in some schemas ----
                if checkout_date_calc is None:
                    checkout_date_calc = supplier_invoice_date if supplier_invoice_date else date.today()
                if due_date_calc is None:
                    due_date_calc = supplier_invoice_date if supplier_invoice_date else date.today()

                if selected_ap_id:
                    # Update
                    if HAS_AP_HEAD_TAX_RATE:
                        exec_sql(
                            """
                            UPDATE accounts_payable_head
                            SET
                                reference_receipts=%s,
                                supplier_invoice_no=%s,
                                supplier_invoice_date=%s,
                                checkout_date=%s,
                                payment_days=%s,
                                tax_rate=%s,
                                amount_total=%s,
                                adjustment_amount=%s,
                                currency=%s,
                                exchange_rate=%s,
                                due_date=%s,
                                balance_amount=%s,
                                note=%s,
                                updated_by=%s,
                                updated_at=%s
                            WHERE ap_id=%s
                            """,
                            (
                                ref_type,
                                supplier_invoice_no.strip(),
                                supplier_invoice_date,
                                checkout_date_calc,
                                payment_days_val,
                                tax_rate_pct,
                                amount_total,
                                adj_amount,
                                currency.strip() or "VND",
                                float(exchange_rate),
                                due_date_calc,
                                balance_amount,
                                note,
                                created_by,
                                now_ts,
                                selected_ap_id,
                            ),
                        )
                    else:
                        exec_sql(
                            """
                            UPDATE accounts_payable_head
                            SET
                                reference_receipts=%s,
                                supplier_invoice_no=%s,
                                supplier_invoice_date=%s,
                                checkout_date=%s,
                                payment_days=%s,
                                amount_total=%s,
                                adjustment_amount=%s,
                                currency=%s,
                                exchange_rate=%s,
                                due_date=%s,
                                balance_amount=%s,
                                note=%s,
                                updated_by=%s,
                                updated_at=%s
                            WHERE ap_id=%s
                            """,
                            (
                                ref_type,
                                supplier_invoice_no.strip(),
                                supplier_invoice_date,
                                checkout_date_calc,
                                payment_days_val,
                                amount_total,
                                adj_amount,
                                currency.strip() or "VND",
                                float(exchange_rate),
                                due_date_calc,
                                balance_amount,
                                note,
                                created_by,
                                now_ts,
                                selected_ap_id,
                            ),
                        )
                    st.success(_t("已更新應付帳款 ✅"))
                else:
                    # Insert new AP
                    ap_code = ap_code_default or gen_ap_code(prefix_date=supplier_invoice_date)

                    if HAS_AP_HEAD_TAX_RATE:
                        new_ap_id = exec_insert_get_id(
                            """
                            INSERT INTO accounts_payable_head
                            (
                                ap_code, supplier_id, supplier_category, reference_receipts,
                                delivery_no, order_no,
                                supplier_invoice_no, supplier_invoice_date,
                                checkout_date, payment_days, tax_rate,
                                amount_total, due_date,
                                currency, exchange_rate,
                                balance_amount, note, adjustment_amount,
                                posting_date, status, is_overdue,
                                created_by, created_at, approved_by, approved_at
                            )
                            VALUES
                            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'posted',0,%s,%s,%s,%s)
                            """,
                            (
                                ap_code,
                                supplier_id,
                                supplier_category_name or "",
                                ref_type,
                                delivery_no,
                                order_num,
                                supplier_invoice_no.strip(),
                                supplier_invoice_date,
                                checkout_date_calc,
                                payment_days_val,
                                tax_rate_pct,
                                amount_total,
                                due_date_calc,
                                currency.strip() or "VND",
                                float(exchange_rate),
                                balance_amount,
                                note,
                                adj_amount,
                                supplier_invoice_date,  # posting_date
                                created_by,
                                now_ts,
                                approved_by,
                                now_ts,
                            ),
                        )
                    else:
                        new_ap_id = exec_insert_get_id(
                            """
                            INSERT INTO accounts_payable_head
                            (
                                ap_code, supplier_id, supplier_category, reference_receipts,
                                delivery_no, order_no,
                                supplier_invoice_no, supplier_invoice_date,
                                checkout_date, payment_days,
                                amount_total, due_date,
                                currency, exchange_rate,
                                balance_amount, note, adjustment_amount,
                                posting_date, status, is_overdue,
                                created_by, created_at, approved_by, approved_at
                            )
                            VALUES
                            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'posted',0,%s,%s,%s,%s)
                            """,
                            (
                                ap_code,
                                supplier_id,
                                supplier_category_name or "",
                                ref_type,
                                delivery_no,
                                order_num,
                                supplier_invoice_no.strip(),
                                supplier_invoice_date,
                                checkout_date_calc,
                                payment_days_val,
                                amount_total,
                                due_date_calc,
                                currency.strip() or "VND",
                                float(exchange_rate),
                                balance_amount,
                                note,
                                adj_amount,
                                supplier_invoice_date,  # posting_date
                                created_by,
                                now_ts,
                                approved_by,
                                now_ts,
                            ),
                        )

                    st.session_state.ap_selected_ap_id = new_ap_id
                    st.success(f"{_t('已建立應付帳款：')}{ap_code} ✅")

                st.rerun()


# =========================================================
# TAB: 供應商送貨明細
# =========================================================
with tab_delivery:
    st.markdown(f"#### {_t('供應商送貨明細')}")
    if selected_msioh_id is None:
        st.info(_t("請先在上方列表勾選一筆入庫單。"))
    else:
        df_lines = load_delivery_lines(int(selected_msioh_id))
        if df_lines.empty:
            st.warning(_t("這筆入庫單沒有明細行。"))
        else:
            show = pd.DataFrame({
                "品名": df_lines["item_name"],
                "規格": df_lines["specification"].fillna(""),
                "數量": df_lines["qty_display"].round(3),
                "單位": df_lines["unit_display"],
                "單價": pd.to_numeric(df_lines["unit_price"], errors="coerce").fillna(0.0).round(2),
                "小計": pd.to_numeric(df_lines["subtotal"], errors="coerce").fillna(0.0).round(2),
                "備註": df_lines["note"].fillna(""),
            })
            st.dataframe(show.rename(columns={c: _t(c) for c in show.columns}), use_container_width=True, hide_index=True)
            st.write("")
            total = float(show["小計"].sum())
            st.metric(_t("送貨單金額加總"), f"{total:,.2f}")

# =========================================================
# TAB: 匯款狀況
# =========================================================
with tab_pay:
    st.markdown(f"#### {_t('匯款狀況')}")

    if selected_ap_id is None:
        st.info(_t("尚未建立 AP（應付帳款單號）。請先到「基本資訊」儲存/建立 AP。"))
    else:
        ap_id = int(selected_ap_id)
        pay_df = load_payments(ap_id)
        ap_payable_total = calc_ap_payable_total(ap_id)
        ap_paid_total = calc_ap_paid_total(ap_id)
        ap_remaining_total = max(round(ap_payable_total - ap_paid_total, 2), 0.0)

        if pay_df.empty:
            st.info(_t("目前沒有付款紀錄。"))
            pay_show = pd.DataFrame(columns=[
                "勾選", "付款日期", "應付金額", "實付金額", "剩餘金額", "付款方式",
                "我方付款銀行", "供應商收款銀行", "支票號碼", "狀態", "更新時間"
            ])
        else:
            pay_amounts = pd.to_numeric(pay_df["payment_amount"], errors="coerce").fillna(0.0)
            running_paid = pay_amounts.cumsum()
            running_balance = (float(ap_payable_total) - running_paid).clip(lower=0).round(2)
            pay_show = pd.DataFrame({
                "勾選": [False]*len(pay_df),
                "payment_id": pay_df["payment_id"],
                "付款日期": pd.to_datetime(pay_df["payment_date"]).dt.date,
                "應付金額": [round(float(ap_payable_total), 2)] * len(pay_df),
                "實付金額": pay_amounts.round(2),
                "剩餘金額": running_balance,
                "付款方式": pay_df["payment_method"].fillna(""),
                "我方付款銀行": pay_df["our_bank_display"].fillna(pay_df["payment_reference"]).fillna(""),
                "供應商收款銀行": pay_df["supplier_bank_display"].fillna(pay_df["Supplier_bank_account"]).fillna(""),
                "支票號碼": pay_df["voucher_no"].fillna(""),
                "狀態": pay_df["status"].fillna(""),
                "更新時間": pay_df["updated_at"].fillna(""),
            })

        pay_select_col = _t("勾選")
        pay_show_display = pay_show.rename(columns={c: _t(c) for c in pay_show.columns})
        pay_disabled = [c for c in pay_show_display.columns if c != pay_select_col]
        pay_col_cfg = {pay_select_col: st.column_config.CheckboxColumn(width="small")}
        if "payment_id" in pay_show_display.columns:
            pay_col_cfg["payment_id"] = None

        ed = st.data_editor(
            pay_show_display,
            use_container_width=True,
            hide_index=True,
            column_config=pay_col_cfg,
            disabled=pay_disabled,
        )

        chosen = ed.index[ed[pay_select_col] == True].tolist()
        if len(chosen) > 1:
            st.warning(_t("付款紀錄一次只能勾選一筆。"))
        if len(chosen) >= 1 and "payment_id" in pay_show.columns:
            st.session_state.ap_selected_payment_id = int(pay_show.iloc[chosen[0]]["payment_id"])

        b1, b2, b3 = st.columns([1, 1, 4], vertical_alignment="bottom")
        with b1:
            do_edit = st.button(_t("編輯"), key="ap_pay_edit", use_container_width=True)
        with b2:
            do_delete = st.button(_t("刪除"), key="ap_pay_delete", use_container_width=True)
        with b3:
            st.empty()

        if do_delete:
            pid = st.session_state.ap_selected_payment_id
            if not pid:
                st.error(_t("請先勾選要刪除的付款紀錄。"))
            else:
                exec_sql("UPDATE accounts_payable_payment SET status='void' WHERE payment_id=%s", (pid,))
                sync_ap_head_payment_status(ap_id)
                st.success(_t("已刪除付款紀錄（標記為 void）✅"))
                st.session_state.ap_selected_payment_id = None
                st.rerun()

        st.write("")
        st.markdown(f"##### {_t('新增/編輯')}")

        # Prefill for edit
        edit_row = {}
        if do_edit and st.session_state.ap_selected_payment_id:
            pid = st.session_state.ap_selected_payment_id
            df_one = qdf("SELECT * FROM accounts_payable_payment WHERE payment_id=%s", (pid,))
            if not df_one.empty:
                edit_row = df_one.iloc[0].to_dict()

        editing_payment = bool(edit_row.get("payment_id"))
        edit_payment_id = int(edit_row.get("payment_id")) if editing_payment else None
        paid_before_this = calc_ap_paid_total(ap_id, exclude_payment_id=edit_payment_id)
        payable_for_this_entry = max(round(ap_payable_total - paid_before_this, 2), 0.0)

        if (not editing_payment) and ap_payable_total > 0 and ap_paid_total >= ap_payable_total:
            st.warning(_t("此筆 AP 已付清，不可再新增付款紀錄。"))
            st.warning(_t("目前已付金額已大於或等於應付總額，不能再新增付款紀錄。"))
            st.stop()

        p1, p2 = st.columns([1, 1], vertical_alignment="bottom")
        with p1:
            st.caption(_t("付款日期"))
            pay_date = st.date_input(
                "pay_date",
                value=edit_row.get("payment_date") or today_local(),
                label_visibility="collapsed",
            )
        with p2:
            st.caption(_t("付款方式"))
            options = ["cash", "transfer", "cheque", "credit_card"]
            default_method = edit_row.get("payment_method") or "transfer"
            pay_method = st.selectbox(
                "pay_method",
                options=options,
                index=options.index(default_method) if default_method in options else options.index("transfer"),
                label_visibility="collapsed",
            )

        p3, p4, p5 = st.columns([1, 1, 1], vertical_alignment="bottom")
        with p3:
            st.caption(_t("應付金額"))
            payable_amt = st.number_input(
                "ap_payable_amount",
                value=float(payable_for_this_entry),
                step=1.0,
                label_visibility="collapsed",
                disabled=True,
            )
        with p4:
            st.caption(_t("實付金額"))
            paid_amount = st.number_input(
                "paid_amount",
                value=float(edit_row.get("payment_amount") or 0.0),
                min_value=0.0,
                step=1.0,
                label_visibility="collapsed",
            )
        remaining_after_payment = max(round(float(payable_amt) - float(paid_amount), 2), 0.0)
        with p5:
            st.caption(_t("剩餘金額"))
            st.number_input(
                "ap_remaining_amount",
                value=float(remaining_after_payment),
                step=1.0,
                label_visibility="collapsed",
                disabled=True,
            )

        st.caption(_t("我方付款銀行"))
        our_bank_df = load_our_bank_options()
        our_bank_options = [0] + ([int(x) for x in our_bank_df["our_bank_id"].tolist()] if not our_bank_df.empty else [])
        our_bank_label_map = {0: _t("（不指定）")}
        our_bank_ref_map = {0: ""}
        for _, _b in our_bank_df.iterrows():
            _bid = int(_b.get("our_bank_id") or 0)
            our_bank_label_map[_bid] = str(_b.get("display_label") or _bid)
            our_bank_ref_map[_bid] = str(_b.get("account_code") or _b.get("display_label") or "")

        default_bank_id = 0
        try:
            default_bank_id = int(edit_row.get("bank_account_id") or 0)
        except Exception:
            default_bank_id = 0
        if default_bank_id not in our_bank_options:
            default_bank_id = 0

        if len(our_bank_options) <= 1:
            st.info(_t("請先到 our_bank 建立我方銀行資料。"))

        selected_our_bank_id = st.selectbox(
            "our_payment_bank",
            options=our_bank_options,
            index=our_bank_options.index(default_bank_id),
            format_func=lambda x: our_bank_label_map.get(int(x), str(x)),
            label_visibility="collapsed",
        )
        bank_ref = our_bank_ref_map.get(int(selected_our_bank_id), "")

        st.caption(_t("供應商收款銀行"))
        supplier_bank_df = load_supplier_bank_options(int(sel.get("supplier_id") or 0) if sel else None)
        supplier_bank_options = [0] + ([int(x) for x in supplier_bank_df["Supplier_bank_account_id"].tolist()] if not supplier_bank_df.empty else [])
        supplier_bank_label_map = {0: _t("（不指定）")}
        supplier_bank_ref_map = {0: ""}
        for _, _sb in supplier_bank_df.iterrows():
            _sbid = int(_sb.get("Supplier_bank_account_id") or 0)
            supplier_bank_label_map[_sbid] = str(_sb.get("display_label") or _sbid)
            supplier_bank_ref_map[_sbid] = str(_sb.get("account_code") or _sb.get("display_label") or "")

        default_supplier_bank_id = 0
        try:
            default_supplier_bank_id = int(edit_row.get("supplier_bank_account_id") or 0)
        except Exception:
            default_supplier_bank_id = 0

        # Old payment rows may only have Supplier_bank_account text. Try to match it back to a supplier bank account.
        if default_supplier_bank_id <= 0 and edit_row.get("Supplier_bank_account") and not supplier_bank_df.empty:
            old_supplier_bank_text = str(edit_row.get("Supplier_bank_account") or "").strip()
            matched = supplier_bank_df.loc[
                (supplier_bank_df["account_code"].astype(str).str.strip() == old_supplier_bank_text)
                | (supplier_bank_df["display_label"].astype(str).str.strip() == old_supplier_bank_text)
            ]
            if not matched.empty:
                try:
                    default_supplier_bank_id = int(matched.iloc[0]["Supplier_bank_account_id"])
                except Exception:
                    default_supplier_bank_id = 0

        if default_supplier_bank_id not in supplier_bank_options:
            default_supplier_bank_id = 0

        if len(supplier_bank_options) <= 1:
            st.info(_t("請先到 supplier_bank_account 建立供應商銀行資料。"))

        selected_supplier_bank_id = st.selectbox(
            "supplier_receiving_bank",
            options=supplier_bank_options,
            index=supplier_bank_options.index(default_supplier_bank_id),
            format_func=lambda x: supplier_bank_label_map.get(int(x), str(x)),
            label_visibility="collapsed",
        )
        supplier_bank = supplier_bank_ref_map.get(int(selected_supplier_bank_id), "")

        st.caption(_t("支票號碼"))
        voucher_no = st.text_input(
            "voucher_no",
            value=edit_row.get("voucher_no") or "",
            label_visibility="collapsed",
        )

        if st.button(_t("儲存付款紀錄"), key="ap_save_payment", use_container_width=False):
            # 儲存前再回 DB 查一次，避免另一台電腦已經付款但本頁還停在舊畫面。
            edit_payment_id_for_check = int(edit_row.get("payment_id")) if edit_row.get("payment_id") else None
            payable_total_check = calc_ap_payable_total(ap_id)
            paid_before_check = calc_ap_paid_total(ap_id, exclude_payment_id=edit_payment_id_for_check)
            remaining_check = max(round(payable_total_check - paid_before_check, 2), 0.0)

            if remaining_check <= 0:
                st.error(_t("目前已付金額已大於或等於應付總額，不能再新增付款紀錄。"))
                st.stop()
            if float(paid_amount) <= 0:
                st.error(_t("付款金額必須大於 0。"))
                st.stop()
            if float(paid_amount) > float(remaining_check):
                st.error(_t("本次付款金額不可大於剩餘應付金額。"))
                st.stop()

            now_ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
            created_by = int(st.session_state.get("user_id", 1))
            has_payment_bank_col = has_column("accounts_payable_payment", "bank_account_id")
            has_supplier_bank_col = has_column("accounts_payable_payment", "supplier_bank_account_id")
            bank_id_for_save = int(selected_our_bank_id) if int(selected_our_bank_id or 0) > 0 else None
            supplier_bank_id_for_save = int(selected_supplier_bank_id) if int(selected_supplier_bank_id or 0) > 0 else None

            if edit_row.get("payment_id"):
                set_parts = [
                    "payment_date=%s",
                    "payment_method=%s",
                    "payment_amount=%s",
                ]
                params = [pay_date, pay_method, float(paid_amount)]

                if has_payment_bank_col:
                    set_parts.append("bank_account_id=%s")
                    params.append(bank_id_for_save)

                if has_supplier_bank_col:
                    set_parts.append("supplier_bank_account_id=%s")
                    params.append(supplier_bank_id_for_save)

                set_parts.extend([
                    "payment_reference=%s",
                    "voucher_no=%s",
                    "Supplier_bank_account=%s",
                    "updated_by=%s",
                    "updated_at=%s",
                ])
                params.extend([bank_ref, voucher_no, supplier_bank, created_by, now_ts, int(edit_row["payment_id"])])

                exec_sql(
                    f"""
                    UPDATE accounts_payable_payment
                    SET {", ".join(set_parts)}
                    WHERE payment_id=%s
                    """,
                    tuple(params),
                )
                sync_ap_head_payment_status(ap_id)
                st.success(_t("已更新付款紀錄 ✅"))
            else:
                insert_cols = ["ap_id", "payment_date", "payment_method", "payment_amount"]
                values = [ap_id, pay_date, pay_method, float(paid_amount)]

                if has_payment_bank_col:
                    insert_cols.append("bank_account_id")
                    values.append(bank_id_for_save)

                if has_supplier_bank_col:
                    insert_cols.append("supplier_bank_account_id")
                    values.append(supplier_bank_id_for_save)

                insert_cols.extend(["payment_reference", "voucher_no", "Supplier_bank_account", "status", "created_at", "creadted_by"])
                values.extend([bank_ref, voucher_no, supplier_bank, "posted", now_ts, created_by])

                col_sql = ", ".join(insert_cols)
                ph_sql = ", ".join(["%s"] * len(insert_cols))
                exec_insert_get_id(
                    f"""
                    INSERT INTO accounts_payable_payment
                    ({col_sql})
                    VALUES ({ph_sql})
                    """,
                    tuple(values),
                )
                sync_ap_head_payment_status(ap_id)
                st.success(_t("已新增付款紀錄 ✅"))
            st.session_state.ap_selected_payment_id = None
            st.rerun()
