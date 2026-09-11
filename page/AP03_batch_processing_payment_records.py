import datetime as dt
from typing import Optional

import pandas as pd
import streamlit as st
from compact_layout import apply_compact_layout
from sqlalchemy import text

apply_compact_layout()

from db import get_engine
import auth


# =============================
# Safe I18N helper
# =============================
TRANSLATIONS = {
    "批量處理付款紀錄": {"vi": "Xử lý hàng loạt phiếu thanh toán", "en": "Batch Process Payment Records"},
    "開始日期": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "供應商": {"vi": "Nhà cung cấp", "en": "Supplier"},
    "供應商名稱": {"vi": "Tên nhà cung cấp", "en": "Supplier Name"},
    "全部供應商": {"vi": "Tất cả nhà cung cấp", "en": "All Suppliers"},
    "全選所有顯示資料": {"vi": "Chọn tất cả dữ liệu đang hiển thị", "en": "Select All Displayed Rows"},
    "刪除勾選": {"vi": "Bỏ chọn đã chọn", "en": "Clear Selected"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "勾選": {"vi": "Chọn", "en": "Select"},
    "入庫單號": {"vi": "Số phiếu nhập kho", "en": "Receipt No."},
    "訂單號碼": {"vi": "Số đơn hàng", "en": "Order No."},
    "供應商發票號碼": {"vi": "Số hóa đơn nhà cung cấp", "en": "Supplier Invoice No."},
    "應付日期": {"vi": "Ngày đến hạn thanh toán", "en": "Due Date"},
    "金額總計": {"vi": "Tổng số tiền", "en": "Total Amount"},
    "付款方式": {"vi": "Phương thức thanh toán", "en": "Payment Method"},
    "供應商銀行名稱": {"vi": "Tên ngân hàng nhà cung cấp", "en": "Supplier Bank Name"},
    "供應商銀行代號": {"vi": "Mã ngân hàng nhà cung cấp", "en": "Supplier Bank Code"},
    "供應商帳戶名": {"vi": "Tên tài khoản nhà cung cấp", "en": "Supplier Account Name"},
    "供應商帳號": {"vi": "Số tài khoản nhà cung cấp", "en": "Supplier Bank Account"},
    "我方銀行名稱": {"vi": "Tên ngân hàng của chúng tôi", "en": "Our Bank Name"},
    "我方銀行代號": {"vi": "Mã ngân hàng của chúng tôi", "en": "Our Bank Code"},
    "我方帳戶名": {"vi": "Tên tài khoản của chúng tôi", "en": "Our Account Name"},
    "我方帳號": {"vi": "Số tài khoản của chúng tôi", "en": "Our Bank Account"},
    "付款日期": {"vi": "Ngày thanh toán", "en": "Payment Date"},
    "付款銀行": {"vi": "Ngân hàng thanh toán", "en": "Paying Bank"},
    "銀行代碼": {"vi": "Mã ngân hàng", "en": "Bank Code"},
    "帳戶名稱": {"vi": "Tên tài khoản", "en": "Account Name"},
    "銀行帳號": {"vi": "Số tài khoản ngân hàng", "en": "Bank Account"},
    "我方銀行資訊": {"vi": "Thông tin ngân hàng của chúng tôi", "en": "Our Bank Information"},
    "供應商銀行資訊": {"vi": "Thông tin ngân hàng nhà cung cấp", "en": "Supplier Bank Information"},
    "套用到勾選資料": {"vi": "Áp dụng cho dữ liệu đã chọn", "en": "Apply to Selected Rows"},
    "金額總計：": {"vi": "Tổng số tiền:", "en": "Total Amount:"},
    "已成功套用到 ": {"vi": "Đã áp dụng thành công cho ", "en": "Successfully applied to "},
    " 筆付款紀錄。": {"vi": " bản ghi thanh toán.", "en": " payment records."},
    "批量處理失敗：": {"vi": "Xử lý hàng loạt thất bại: ", "en": "Batch processing failed: "},
    "顯示模式": {"vi": "Chế độ hiển thị", "en": "Display Mode"},
    "顯示所有未付款": {"vi": "Hiển thị tất cả khoản chưa thanh toán", "en": "Show All Unpaid"},
    "顯示已到期未付款": {"vi": "Hiển thị khoản quá hạn chưa thanh toán", "en": "Show Overdue Unpaid"},
    "依應付日期區間": {"vi": "Theo khoảng ngày đến hạn", "en": "By Due Date Range"},
    "顯示所有AP資料": {"vi": "Hiển thị tất cả dữ liệu AP", "en": "Show All AP Records"},
    "燈號": {"vi": "Đèn", "en": "Signal"},
    "付款狀態": {"vi": "Tình trạng thanh toán", "en": "Payment Status"},
    "未付款": {"vi": "Chưa thanh toán", "en": "Unpaid"},
    "部分付款": {"vi": "Thanh toán một phần", "en": "Partially Paid"},
    "已付款": {"vi": "Đã thanh toán", "en": "Paid"},
    "應付總額": {"vi": "Tổng phải trả", "en": "Payable Total"},
    "已付金額": {"vi": "Số tiền đã trả", "en": "Paid Amount"},
    "剩餘應付": {"vi": "Còn phải trả", "en": "Remaining Payable"},
    "勾選資料包含多個供應商，請只選同一個供應商再選供應商銀行。": {"vi": "Dữ liệu đã chọn có nhiều nhà cung cấp. Vui lòng chỉ chọn cùng một nhà cung cấp trước khi chọn tài khoản ngân hàng.", "en": "Selected rows contain multiple suppliers. Please select one supplier before choosing the supplier bank."},
    "勾選資料中有已付清的 AP，請取消勾選後再套用付款。": {"vi": "Dữ liệu đã chọn có AP đã thanh toán xong. Vui lòng bỏ chọn trước khi áp dụng thanh toán.", "en": "Selected rows include fully paid AP records. Please unselect them before applying payment."},
    "此筆 AP 已付清，不可重複付款。": {"vi": "AP này đã thanh toán xong, không thể thanh toán lặp lại.", "en": "This AP is already fully paid and cannot be paid again."},
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


def build_display_i18n_maps(df: pd.DataFrame, protected_cols: Optional[set[str]] = None):
    """Build stable column rename maps for Streamlit display.

    Internal code keeps Chinese column names, but the table shown to users uses
    translated headers. After st.data_editor returns, we rename back so existing
    business logic can still read columns like 勾選 / 金額總計.
    """
    protected_cols = protected_cols or set()
    to_display: dict[str, str] = {}
    to_internal: dict[str, str] = {}
    used: set[str] = set()

    for col in df.columns:
        if col in protected_cols:
            display_col = col
        else:
            display_col = _t(str(col))

        # Streamlit / PyArrow does not accept duplicate column headers.
        if display_col in used:
            display_col = f"{display_col} ({col})"

        used.add(display_col)
        to_display[col] = display_col
        to_internal[display_col] = col

    return to_display, to_internal


PAGE_KEY = "AP03_batch_processing_payment_records"
auth.require_read(PAGE_KEY)

AP03_MODE_ALL_UNPAID = "all_unpaid"
AP03_MODE_OVERDUE_UNPAID = "overdue_unpaid"
AP03_MODE_BY_DUE_DATE = "by_due_date"
AP03_MODE_ALL_AP = "all_ap"

def ap03_mode_options() -> dict[str, str]:
    return {
        AP03_MODE_ALL_AP: _t("顯示所有AP資料"),
        AP03_MODE_ALL_UNPAID: _t("顯示所有未付款"),
        AP03_MODE_OVERDUE_UNPAID: _t("顯示已到期未付款"),
        AP03_MODE_BY_DUE_DATE: _t("依應付日期區間"),
    }

PAYMENT_METHOD_OPTIONS = ["", "cash", "transfer", "cheque", "credit_card"]
PAYMENT_METHOD_LABEL = {
    "": "",
    "cash": "cash",
    "transfer": "transfer",
    "cheque": "cheque",
    "credit_card": "credit_card",
}


@st.cache_resource
def get_db_engine():
    return get_engine()


def _exclude_empty_delivery_ap_condition(alias: str = "h") -> str:
    """Hide ghost AP rows created from an S01 head that has no line details."""
    a = alias
    return f"""
        NOT (
            COALESCE({a}.reference_receipts, 'delivery') = 'delivery'
            AND COALESCE({a}.amount_total, 0) = 0
            AND COALESCE({a}.adjustment_amount, 0) = 0
            AND NOT EXISTS (
                SELECT 1
                FROM ap_resource ar_empty
                WHERE ar_empty.ap_id = {a}.ap_id
            )
            AND NOT EXISTS (
                SELECT 1
                FROM accounts_payable_payment pay_empty
                WHERE pay_empty.ap_id = {a}.ap_id
                  AND COALESCE(pay_empty.status, 'draft') <> 'void'
            )
            AND EXISTS (
                SELECT 1
                FROM material_stock_io_head mh_empty
                WHERE mh_empty.supplier_id = {a}.supplier_id
                  AND mh_empty.doc_no COLLATE utf8mb4_unicode_ci = {a}.delivery_no COLLATE utf8mb4_unicode_ci
                  AND mh_empty.io_type = 'IN'
                  AND mh_empty.doc_no IS NOT NULL
                  AND COALESCE(mh_empty.status, 'posted') <> 'void'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM material_stock_io_line ml_empty
                      WHERE ml_empty.msioh_id = mh_empty.msioh_id
                  )
            )
        )
    """


def force_refresh_batch_data() -> None:
    """Release cached DB resources and clear Streamlit cached query results."""
    try:
        engine = get_db_engine()
        try:
            engine.dispose()
        except Exception:
            pass
    except Exception:
        pass

    try:
        get_db_engine.clear()
    except Exception:
        pass

    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.session_state["ap03_action"] = None
    st.session_state["ap03_editor_seed"] = int(st.session_state.get("ap03_editor_seed", 0)) + 1


@st.cache_data(ttl=3600)
def _table_columns(table_name: str) -> list[str]:
    sql = """
        SELECT COLUMN_NAME
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = :table_name
        ORDER BY ORDINAL_POSITION
    """
    try:
        with get_db_engine().connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"table_name": table_name})
        return df["COLUMN_NAME"].astype(str).tolist()
    except Exception:
        return []


def _first_col(table_name: str, candidates: list[str]) -> Optional[str]:
    cols = set(_table_columns(table_name))
    for c in candidates:
        if c in cols:
            return c
    return None


def table_exists(table_name: str) -> bool:
    """Return whether a table exists in the active database."""
    sql = """
        SELECT 1 AS ok
        FROM information_schema.TABLES
        WHERE table_schema = DATABASE()
          AND table_name = :table_name
        LIMIT 1
    """
    try:
        with get_db_engine().connect() as conn:
            row = conn.execute(text(sql), {"table_name": table_name}).first()
        return bool(row)
    except Exception:
        return False


def get_table_column_names(table_name: str) -> set[str]:
    """Return column names for a table; empty set if unavailable."""
    return set(_table_columns(table_name))


def _named_in_params(values, prefix: str = "v") -> tuple[str, dict]:
    clean_values = [int(x) for x in values]
    params = {f"{prefix}{i}": v for i, v in enumerate(clean_values)}
    clause = ", ".join([f":{k}" for k in params.keys()])
    return clause, params


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

    in_clause, params = _named_in_params(clean_ids, "uid")
    result = dict(fallback)

    # Best path: linked staff name.
    if "stuff_id" in user_cols and table_exists("stuff"):
        stuff_cols = get_table_column_names("stuff")
        if {"stuff_id", "stuff_name"}.issubset(stuff_cols):
            try:
                sql = f"""
                    SELECT u.user_id,
                           COALESCE(NULLIF(s.stuff_name, ''), CAST(u.user_id AS CHAR)) AS display_name
                    FROM `user` u
                    LEFT JOIN stuff s ON s.stuff_id = u.stuff_id
                    WHERE u.user_id IN ({in_clause})
                """
                with get_db_engine().connect() as conn:
                    df = pd.read_sql(text(sql), conn, params=params)
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
            sql = f"""
                SELECT user_id, {expr} AS display_name
                FROM `user`
                WHERE user_id IN ({in_clause})
            """
            with get_db_engine().connect() as conn:
                df = pd.read_sql(text(sql), conn, params=params)
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


def _ap_head_amount_expr(resource_total_expr: str = "0") -> str:
    """
    AP03 金額公式以 AP01 為準。

    AP01 目前有兩種寫入規則：
    1) reference_receipts='delivery'：
       amount_total 是未稅送貨金額；adjustment_amount 以負數保存折讓；tax_rate 存 8 代表 8%。
       AP01 畫面公式：含稅金額 = (未稅金額 + 調整金額) * (1 + 稅率 / 100)。
    2) manual/order：
       AP01 儲存時已把含稅結果寫進 amount_total。AP03 不再二次套折讓與稅率，避免重算。

    若 delivery 類型的 amount_total 是 0 或 NULL，代表 AP 主表未稅金額沒回填，
    才用 ap_resource.line_amount 加總作為未稅金額 fallback。
    """
    return f"""
        ROUND(
            CASE
                WHEN COALESCE(h.reference_receipts, 'delivery') = 'delivery' THEN
                    (
                        COALESCE(NULLIF(h.amount_total, 0), {resource_total_expr}, 0)
                        + COALESCE(h.adjustment_amount, 0)
                    )
                    * (1 + COALESCE(h.tax_rate, 0) / 100)
                ELSE
                    COALESCE(h.amount_total, 0)
            END,
            2
        )
    """


def _ap_resource_total_expr() -> str:
    """
    AP03 金額 fallback：
    若 accounts_payable_head 金額欄位是 0 或 NULL，
    就從 ap_resource 依 ap_id 加總明細金額。
    """
    ap_id_col = _first_col("ap_resource", ["ap_id"])
    amount_col = _first_col("ap_resource", [
        "amount",
        "amount_total",
        "subtotal",
        "sub_total",
        "line_amount",
        "total_amount",
        "payable_amount",
        "payment_total",
    ])

    if not ap_id_col or not amount_col:
        return "0"

    return f"""
        (
            SELECT COALESCE(SUM(ar.`{amount_col}`), 0)
            FROM ap_resource ar
            WHERE ar.`{ap_id_col}` = h.ap_id
        )
    """


@st.cache_data(ttl=300)
def load_supplier_master() -> pd.DataFrame:
    sql = """
        SELECT
            supplier_id,
            supplier_name,
            supplier_shortname,
            checkout_date,
            payment_days,
            is_active
        FROM supplier
        ORDER BY supplier_name
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


@st.cache_data(ttl=300)
def load_suppliers_with_ap(start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    # 供應商下拉列出所有仍有 AP 的供應商，不被付款日卡住；
    # 但排除 S01 只建立主表、沒有任何明細造成的 0 元幽靈 AP。
    empty_ap_filter = _exclude_empty_delivery_ap_condition("h")
    sql = f"""
        SELECT DISTINCT
            h.supplier_id,
            COALESCE(s.supplier_name, CONCAT('Supplier#', h.supplier_id)) AS supplier_name
        FROM accounts_payable_head h
        LEFT JOIN supplier s ON s.supplier_id = h.supplier_id
        WHERE h.supplier_id IS NOT NULL
          AND COALESCE(h.status, 'posted') <> 'void'
          AND {empty_ap_filter}
        ORDER BY supplier_name
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


@st.cache_data(ttl=300)
def load_supplier_banks(supplier_id: Optional[int]) -> pd.DataFrame:
    if not supplier_id:
        return pd.DataFrame(columns=[
            "Supplier_bank_account_id", "bank_id", "bank_name", "account_name", "bank_account", "is_default", "status"
        ])
    sql = """
        SELECT
            Supplier_bank_account_id,
            bank_id,
            bank_name,
            account_name,
            bank_account,
            is_default,
            status
        FROM supplier_bank_account
        WHERE supplier_id = :supplier_id
          AND COALESCE(status, 'active') <> 'inactive'
        ORDER BY COALESCE(is_default, 0) DESC, bank_name, bank_id, account_name, bank_account
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params={"supplier_id": int(supplier_id)})


@st.cache_data(ttl=300)
def load_our_banks() -> pd.DataFrame:
    sql = """
        SELECT
            our_bank_id,
            our_company_id,
            our_company_bank_name,
            our_company_bank_num,
            our_company_account_name,
            our_company_account_code
        FROM our_bank
        ORDER BY our_company_bank_name, our_company_bank_num, our_company_account_name, our_company_account_code
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def fetch_ap_rows(
    start_date: dt.date,
    end_date: dt.date,
    supplier_id: Optional[int],
    display_mode: str = AP03_MODE_ALL_UNPAID,
) -> pd.DataFrame:
    # 付款處理頁要即時反映付款結果，所以這個主查詢不再用 st.cache_data。
    params = {}
    supplier_clause = ""
    if supplier_id:
        supplier_clause = " AND h.supplier_id = :supplier_id "
        params["supplier_id"] = int(supplier_id)

    resource_total_expr = _ap_resource_total_expr()
    head_amount_expr = _ap_head_amount_expr(resource_total_expr)

    paid_amount_expr = f"""
        (
            SELECT COALESCE(SUM(paid_check.payment_amount), 0)
            FROM accounts_payable_payment paid_check
            WHERE paid_check.ap_id = h.ap_id
              AND COALESCE(paid_check.status, 'draft') <> 'void'
        )
    """
    balance_expr = f"GREATEST(CAST({head_amount_expr} AS DECIMAL(18,2)) - COALESCE({paid_amount_expr}, 0), 0)"

    effective_date_expr = """
        COALESCE(
            DATE(h.due_date),
            DATE(h.checkout_date),
            DATE(h.supplier_invoice_date),
            DATE(h.created_at),
            DATE(h.posting_date)
        )
    """

    created_by_col = _first_col("accounts_payable_head", ["created_by", "create_by", "creadted_by"])
    created_at_col = _first_col("accounts_payable_head", ["created_at", "create_at", "created_time"])
    updated_by_col = _first_col("accounts_payable_head", ["updated_by", "update_by", "modified_by"])
    updated_at_col = _first_col("accounts_payable_head", ["updated_at", "update_at", "modified_at"])
    audit_created_by_expr = f"h.`{created_by_col}` AS audit_created_by" if created_by_col else "NULL AS audit_created_by"
    audit_created_at_expr = f"h.`{created_at_col}` AS audit_created_at" if created_at_col else "NULL AS audit_created_at"
    audit_updated_by_expr = f"h.`{updated_by_col}` AS audit_updated_by" if updated_by_col else "NULL AS audit_updated_by"
    audit_updated_at_expr = f"h.`{updated_at_col}` AS audit_updated_at" if updated_at_col else "NULL AS audit_updated_at"

    where_parts = [
        "COALESCE(h.status, 'posted') <> 'void'",
        _exclude_empty_delivery_ap_condition("h"),
    ]

    if display_mode == AP03_MODE_ALL_UNPAID:
        where_parts.append(f"CAST({balance_expr} AS DECIMAL(18,2)) > 0")
    elif display_mode == AP03_MODE_OVERDUE_UNPAID:
        where_parts.append(f"CAST({balance_expr} AS DECIMAL(18,2)) > 0")
        where_parts.append(f"{effective_date_expr} <= CURRENT_DATE()")
    elif display_mode == AP03_MODE_BY_DUE_DATE:
        where_parts.append(f"{effective_date_expr} BETWEEN :start_date AND :end_date")
        params["start_date"] = start_date
        params["end_date"] = end_date
    else:
        # AP03_MODE_ALL_AP：顯示全部 AP，但已付清的金額總計會顯示 0，且不可再套用付款。
        pass

    where_sql = " AND ".join(where_parts)

    sql = f"""
        WITH latest_payment AS (
            SELECT p.*
            FROM accounts_payable_payment p
            INNER JOIN (
                SELECT ap_id, MAX(payment_id) AS max_payment_id
                FROM accounts_payable_payment
                WHERE COALESCE(status, 'draft') <> 'void'
                GROUP BY ap_id
            ) x ON x.max_payment_id = p.payment_id
        ),
        paid_sum AS (
            SELECT
                ap_id,
                COALESCE(SUM(payment_amount), 0) AS paid_total
            FROM accounts_payable_payment
            WHERE COALESCE(status, 'draft') <> 'void'
            GROUP BY ap_id
        )
        SELECT
            h.ap_id,
            h.ap_code,
            h.supplier_id,
            COALESCE(s.supplier_name, CONCAT('Supplier#', h.supplier_id)) AS supplier_name,
            COALESCE(NULLIF(s.supplier_shortname, ''), s.supplier_name, CONCAT('Supplier#', h.supplier_id)) AS supplier_display_name,
            h.delivery_no,
            h.order_no,
            h.supplier_invoice_no,
            h.supplier_invoice_date,
            h.checkout_date,
            {audit_created_by_expr},
            {audit_created_at_expr},
            {audit_updated_by_expr},
            {audit_updated_at_expr},
            {effective_date_expr} AS due_date,
            CAST({head_amount_expr} AS DECIMAL(18,2)) AS payable_total,
            CAST(COALESCE(ps.paid_total, 0) AS DECIMAL(18,2)) AS paid_total,
            CAST(GREATEST({head_amount_expr} - COALESCE(ps.paid_total, 0), 0) AS DECIMAL(18,2)) AS payment_total,
            CASE
                WHEN COALESCE(ps.paid_total, 0) >= CAST({head_amount_expr} AS DECIMAL(18,2))
                     AND CAST({head_amount_expr} AS DECIMAL(18,2)) > 0 THEN 'paid'
                WHEN COALESCE(ps.paid_total, 0) > 0 THEN 'partial'
                ELSE 'unpaid'
            END AS payment_status_code,
            COALESCE(lp.payment_method, '') AS payment_method,
            COALESCE(lp.payment_date, NULL) AS payment_date,
            COALESCE(lp.payment_reference, '') AS payment_reference,
            COALESCE(lp.voucher_no, '') AS voucher_no,
            COALESCE(lp.payment_amount, 0) AS latest_payment_amount,
            COALESCE(lp.bank_account_id, NULL) AS bank_account_id,
            COALESCE(lp.supplier_bank_account_id, NULL) AS supplier_bank_account_id,
            COALESCE(lp.Supplier_bank_account, '') AS supplier_bank_account,
            COALESCE(ob.our_company_bank_name, '') AS our_bank_name,
            COALESCE(ob.our_company_bank_num, '') AS our_bank_num,
            COALESCE(ob.our_company_account_name, '') AS our_account_name,
            COALESCE(ob.our_company_account_code, '') AS our_bank_code,
            COALESCE(sb.bank_name, '') AS supplier_bank_name,
            COALESCE(sb.bank_id, '') AS supplier_bank_num,
            COALESCE(sb.account_name, '') AS supplier_account_name,
            COALESCE(sb.bank_account, '') AS supplier_bank_account_code,
            lp.payment_id
        FROM accounts_payable_head h
        LEFT JOIN supplier s ON s.supplier_id = h.supplier_id
        LEFT JOIN paid_sum ps ON ps.ap_id = h.ap_id
        LEFT JOIN latest_payment lp ON lp.ap_id = h.ap_id
        LEFT JOIN our_bank ob ON ob.our_bank_id = lp.bank_account_id
        LEFT JOIN supplier_bank_account sb ON sb.Supplier_bank_account_id = lp.supplier_bank_account_id
        WHERE {where_sql}
        {supplier_clause}
        ORDER BY
            {effective_date_expr} IS NULL,
            {effective_date_expr},
            h.ap_id DESC
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

def compute_default_start_date(supplier_id: Optional[int], end_date: dt.date) -> dt.date:
    supplier_df = load_supplier_master()
    if not supplier_id:
        return end_date.replace(day=1)

    row = supplier_df.loc[supplier_df["supplier_id"] == int(supplier_id)]
    if row.empty:
        return end_date.replace(day=1)

    raw_checkout_day = row.iloc[0].get("checkout_date", 1)
    checkout_day = pd.to_numeric(pd.Series([raw_checkout_day]), errors="coerce").fillna(1).astype(int).iloc[0]
    checkout_day = max(1, min(int(checkout_day), 31))

    safe_day = max(1, min(checkout_day, 28 if end_date.month == 2 else 31))
    if end_date.day >= safe_day:
        return end_date.replace(day=safe_day)

    prev_month_last = end_date.replace(day=1) - dt.timedelta(days=1)
    safe_prev_day = min(safe_day, prev_month_last.day)
    return prev_month_last.replace(day=safe_prev_day)


def init_state():
    today = dt.date.today()
    st.session_state.setdefault("ap03_end_date", today)
    st.session_state.setdefault("ap03_start_date", today.replace(day=1))
    st.session_state.setdefault("ap03_supplier_id", None)
    st.session_state.setdefault("ap03_display_mode", AP03_MODE_ALL_AP)
    st.session_state.setdefault("ap03_editor_seed", 0)
    st.session_state.setdefault("ap03_action", None)


def trigger_select_all():
    st.session_state["ap03_action"] = "select_all"


def trigger_clear_all():
    st.session_state["ap03_action"] = "clear_all"


def handle_supplier_change():
    supplier_name = st.session_state.get("ap03_supplier_name_widget", "全部供應商")
    supplier_master = load_supplier_master()
    selected_supplier_id = None
    if supplier_name != _t("全部供應商"):
        match = supplier_master.loc[supplier_master["supplier_name"] == supplier_name, "supplier_id"]
        if not match.empty:
            selected_supplier_id = int(match.iloc[0])

    st.session_state["ap03_supplier_id"] = selected_supplier_id
    end_date = st.session_state.get("ap03_end_date", dt.date.today())
    st.session_state["ap03_start_date"] = compute_default_start_date(selected_supplier_id, end_date)


def make_display_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    base_columns = [
        "勾選", "燈號", "付款狀態", "入庫單號", "供應商名稱", "訂單號碼", "供應商發票號碼", "應付日期",
        "應付總額", "已付金額", "金額總計", "付款方式",
        "供應商銀行名稱", "供應商銀行代號", "供應商帳戶名", "供應商帳號",
        "我方銀行名稱", "我方銀行代號", "我方帳戶名", "我方帳號",
        "建檔人員", "建檔時間", "最後修改人", "修改時間",
        "ap_id", "supplier_id", "payment_id", "supplier_bank_account_id", "bank_account_id"
    ]
    if raw_df.empty:
        return pd.DataFrame(columns=base_columns)

    df = raw_df.copy()
    df["勾選"] = False
    df["應付日期"] = pd.to_datetime(df["due_date"]).dt.strftime("%Y-%m-%d").fillna("")

    payable_total = pd.to_numeric(df.get("payable_total", 0), errors="coerce").fillna(0.0)
    paid_total = pd.to_numeric(df.get("paid_total", 0), errors="coerce").fillna(0.0)
    remaining_total = pd.to_numeric(df.get("payment_total", 0), errors="coerce").fillna(0.0)

    def _status_label(code: str, payable: float, paid: float) -> str:
        code = str(code or "").lower()
        if payable > 0 and paid >= payable:
            return "已付款"
        if code == "paid":
            return "已付款"
        if paid > 0 or code == "partial":
            return "部分付款"
        return "未付款"

    status_labels = [
        _status_label(code, float(payable), float(paid))
        for code, payable, paid in zip(df.get("payment_status_code", ""), payable_total, paid_total)
    ]
    light_map = {"未付款": "🔴", "部分付款": "🟡", "已付款": "🟢"}
    lights = [light_map.get(x, "🔴") for x in status_labels]

    audit_display = build_ap_audit_display(df).reset_index(drop=True)

    display_df = pd.DataFrame({
        "勾選": df["勾選"],
        "燈號": lights,
        "付款狀態": status_labels,
        "入庫單號": df["delivery_no"].fillna(""),
        "供應商名稱": df.get("supplier_display_name", df.get("supplier_name", pd.Series([""] * len(df)))).fillna(""),
        "訂單號碼": df["order_no"].fillna(""),
        "供應商發票號碼": df["supplier_invoice_no"].fillna(""),
        "應付日期": df["應付日期"],
        "應付總額": payable_total,
        "已付金額": paid_total,
        # AP03 的批量付款以「剩餘應付」為本次可套用金額；避免已付款資料被重複匯款。
        "金額總計": remaining_total,
        "付款方式": df["payment_method"].fillna(""),
        "供應商銀行名稱": df["supplier_bank_name"].fillna(""),
        "供應商銀行代號": df["supplier_bank_num"].fillna(""),
        "供應商帳戶名": df["supplier_account_name"].fillna(""),
        "供應商帳號": df["supplier_bank_account_code"].fillna(""),
        "我方銀行名稱": df["our_bank_name"].fillna(""),
        "我方銀行代號": df["our_bank_num"].fillna(""),
        "我方帳戶名": df["our_account_name"].fillna(""),
        "我方帳號": df["our_bank_code"].fillna(""),
        "建檔人員": audit_display.get("建檔人員", pd.Series([""] * len(df))),
        "建檔時間": audit_display.get("建檔時間", pd.Series([""] * len(df))),
        "最後修改人": audit_display.get("最後修改人", pd.Series([""] * len(df))),
        "修改時間": audit_display.get("修改時間", pd.Series([""] * len(df))),
        "ap_id": df["ap_id"],
        "supplier_id": df["supplier_id"],
        "payment_id": df["payment_id"],
        "supplier_bank_account_id": df["supplier_bank_account_id"],
        "bank_account_id": df["bank_account_id"],
    })
    return display_df

def apply_action_to_df(display_df: pd.DataFrame) -> pd.DataFrame:
    action = st.session_state.get("ap03_action")
    if action == "select_all" and not display_df.empty:
        display_df["勾選"] = True
    elif action == "clear_all" and not display_df.empty:
        display_df["勾選"] = False
    st.session_state["ap03_action"] = None
    return display_df


def get_selected_rows(edited_df: pd.DataFrame) -> pd.DataFrame:
    if edited_df.empty or "勾選" not in edited_df.columns:
        return edited_df.iloc[0:0].copy()
    mask = edited_df["勾選"].fillna(False).astype(bool)
    return edited_df.loc[mask].copy()


def _selected_supplier_id_for_bank(selected_df: pd.DataFrame, fallback_supplier_id: Optional[int]) -> tuple[Optional[int], bool]:
    """Return supplier_id for supplier-bank dropdowns.

    If the page is showing all suppliers, the supplier-bank options should follow
    the selected rows. Supplier bank data is only meaningful when all selected AP
    rows belong to the same supplier.
    """
    if selected_df is not None and not selected_df.empty and "supplier_id" in selected_df.columns:
        ids = []
        for v in selected_df["supplier_id"].dropna().tolist():
            try:
                ids.append(int(v))
            except Exception:
                pass
        ids = sorted(set(ids))
        if len(ids) == 1:
            return ids[0], False
        if len(ids) > 1:
            return None, True

    if fallback_supplier_id:
        try:
            return int(fallback_supplier_id), False
        except Exception:
            return None, False
    return None, False


def _ensure_selectbox_value(key: str, options: list[str]) -> None:
    if key in st.session_state and st.session_state.get(key) not in options:
        st.session_state[key] = options[0] if options else ""


def upsert_batch_payment(
    selected_df: pd.DataFrame,
    payment_date: dt.date,
    payment_method: str,
    supplier_bank_row: Optional[pd.Series],
    our_bank_row: Optional[pd.Series],
):
    auth.require_edit(PAGE_KEY)
    if selected_df.empty:
        raise ValueError("請先勾選至少一筆資料。")
    if not payment_method:
        raise ValueError("請選擇付款方式。")

    if "金額總計" in selected_df.columns:
        remaining_check = pd.to_numeric(selected_df["金額總計"], errors="coerce").fillna(0.0)
        if (remaining_check <= 0).any():
            raise ValueError(_t("勾選資料中有已付清的 AP，請取消勾選後再套用付款。"))

    supplier_ids = []
    if "supplier_id" in selected_df.columns:
        for v in selected_df["supplier_id"].dropna().tolist():
            try:
                supplier_ids.append(int(v))
            except Exception:
                pass
    if len(set(supplier_ids)) > 1:
        raise ValueError(_t("勾選資料包含多個供應商，請只選同一個供應商再選供應商銀行。"))

    supplier_bank_id = None
    supplier_bank_num = ""
    supplier_bank_name = ""
    supplier_account_name = ""
    supplier_bank_account = ""
    if supplier_bank_row is not None and not supplier_bank_row.empty:
        supplier_bank_id = int(supplier_bank_row["Supplier_bank_account_id"])
        supplier_bank_num = str(supplier_bank_row["bank_id"] or "")
        supplier_bank_name = str(supplier_bank_row["bank_name"] or "")
        supplier_account_name = str(supplier_bank_row["account_name"] or "")
        supplier_bank_account = str(supplier_bank_row["bank_account"] or "")

    our_bank_id = None
    our_bank_num = ""
    our_bank_name = ""
    our_account_name = ""
    our_bank_code = ""
    if our_bank_row is not None and not our_bank_row.empty:
        our_bank_id = int(our_bank_row["our_bank_id"])
        our_bank_num = str(our_bank_row["our_company_bank_num"] or "")
        our_bank_name = str(our_bank_row["our_company_bank_name"] or "")
        our_account_name = str(our_bank_row["our_company_account_name"] or "")
        our_bank_code = str(our_bank_row["our_company_account_code"] or "")

    user_id = int(st.session_state.get("user_id", 1) or 1)

    current_amount_sql = text("""
        SELECT
            ROUND(
                CASE
                    WHEN COALESCE(reference_receipts, 'delivery') = 'delivery' THEN
                        (
                            COALESCE(
                                NULLIF(amount_total, 0),
                                (
                                    SELECT COALESCE(SUM(r.line_amount), 0)
                                    FROM ap_resource r
                                    WHERE r.ap_id = accounts_payable_head.ap_id
                                ),
                                0
                            )
                            + COALESCE(adjustment_amount, 0)
                        )
                        * (1 + COALESCE(tax_rate, 0) / 100)
                    ELSE
                        COALESCE(amount_total, 0)
                END,
                2
            ) AS payable_total,
            (
                SELECT COALESCE(SUM(payment_amount), 0)
                FROM accounts_payable_payment
                WHERE ap_id = accounts_payable_head.ap_id
                  AND COALESCE(status, 'draft') <> 'void'
            ) AS paid_total
        FROM accounts_payable_head
        WHERE ap_id = :ap_id
        FOR UPDATE
    """)

    update_sql = text("""
        UPDATE accounts_payable_payment
        SET payment_date = :payment_date,
            payment_method = :payment_method,
            bank_account_id = :our_bank_id,
            payment_reference = :our_bank_code,
            payment_amount = :payment_amount,
            supplier_bank_account_id = :supplier_bank_id,
            Supplier_bank_account = :supplier_bank_account,
            status = 'posted',
            updated_at = NOW(),
            updated_by = :user_id
        WHERE payment_id = :payment_id
    """)

    insert_sql = text("""
        INSERT INTO accounts_payable_payment (
            ap_id,
            payment_date,
            payment_method,
            bank_account_id,
            payment_reference,
            voucher_no,
            payment_amount,
            supplier_bank_account_id,
            Supplier_bank_account,
            status,
            created_at,
            creadted_by
        ) VALUES (
            :ap_id,
            :payment_date,
            :payment_method,
            :our_bank_id,
            :our_bank_code,
            :voucher_no,
            :payment_amount,
            :supplier_bank_id,
            :supplier_bank_account,
            'posted',
            NOW(),
            :user_id
        )
    """)

    with get_db_engine().begin() as conn:
        for _, row in selected_df.iterrows():
            ap_id = int(row["ap_id"])
            current = conn.execute(current_amount_sql, {"ap_id": ap_id}).mappings().first()
            if not current:
                raise ValueError(f"找不到 AP ID：{ap_id}")

            payable_total = float(current.get("payable_total") or 0.0)
            paid_total = float(current.get("paid_total") or 0.0)
            remaining_now = max(round(payable_total - paid_total, 2), 0.0)
            if payable_total > 0 and paid_total >= payable_total:
                raise ValueError(f"AP ID {ap_id}：{_t('此筆 AP 已付清，不可重複付款。')}")
            if remaining_now <= 0:
                raise ValueError(f"AP ID {ap_id}：{_t('此筆 AP 已付清，不可重複付款。')}")

            requested_amount = float(pd.to_numeric(row["金額總計"], errors="coerce") or 0.0)
            if requested_amount <= 0:
                raise ValueError(f"AP ID {ap_id}：{_t('此筆 AP 已付清，不可重複付款。')}")
            payment_amount = min(requested_amount, remaining_now)

            payload = {
                # AP03 批量付款是新增本次付款紀錄；若已有部分付款，應新增一筆補差額，不能覆寫舊紀錄。
                "payment_id": None,
                "ap_id": ap_id,
                "payment_date": payment_date,
                "payment_method": payment_method,
                "our_bank_id": our_bank_id,
                "our_bank_code": our_bank_code,
                "voucher_no": None,
                "payment_amount": payment_amount,
                "supplier_bank_id": supplier_bank_id,
                "supplier_bank_account": supplier_bank_account,
                "user_id": user_id,
            }
            if payload["payment_id"]:
                conn.execute(update_sql, payload)
            else:
                conn.execute(insert_sql, payload)

            # 同步更新 AP Head 狀態與餘額；公式與 AP01 保持一致。
            conn.execute(text("""
                UPDATE accounts_payable_head
                SET balance_amount = GREATEST(
                        ROUND(
                            CASE
                                WHEN COALESCE(reference_receipts, 'delivery') = 'delivery' THEN
                                    (
                                        COALESCE(
                                            NULLIF(amount_total, 0),
                                            (
                                                SELECT COALESCE(SUM(r.line_amount), 0)
                                                FROM ap_resource r
                                                WHERE r.ap_id = accounts_payable_head.ap_id
                                            ),
                                            0
                                        )
                                        + COALESCE(adjustment_amount, 0)
                                    )
                                    * (1 + COALESCE(tax_rate, 0) / 100)
                                ELSE
                                    COALESCE(amount_total, 0)
                            END,
                            2
                        ) - (
                            SELECT COALESCE(SUM(payment_amount), 0)
                            FROM accounts_payable_payment
                            WHERE ap_id = :ap_id
                              AND COALESCE(status, 'draft') <> 'void'
                        ),
                        0
                    ),
                    posting_date = :payment_date,
                    bank_account = :our_bank_id,
                    status = CASE
                        WHEN GREATEST(
                            ROUND(
                                CASE
                                    WHEN COALESCE(reference_receipts, 'delivery') = 'delivery' THEN
                                        (
                                            COALESCE(
                                                NULLIF(amount_total, 0),
                                                (
                                                    SELECT COALESCE(SUM(r.line_amount), 0)
                                                    FROM ap_resource r
                                                    WHERE r.ap_id = accounts_payable_head.ap_id
                                                ),
                                                0
                                            )
                                            + COALESCE(adjustment_amount, 0)
                                        )
                                        * (1 + COALESCE(tax_rate, 0) / 100)
                                    ELSE
                                        COALESCE(amount_total, 0)
                                END,
                                2
                            ) - (
                                SELECT COALESCE(SUM(payment_amount), 0)
                                FROM accounts_payable_payment
                                WHERE ap_id = :ap_id
                                  AND COALESCE(status, 'draft') <> 'void'
                            ),
                            0
                        ) <= 0 THEN 'paid'
                        WHEN (
                            SELECT COALESCE(SUM(payment_amount), 0)
                            FROM accounts_payable_payment
                            WHERE ap_id = :ap_id
                              AND COALESCE(status, 'draft') <> 'void'
                        ) > 0 THEN 'partial'
                        ELSE COALESCE(status, 'posted')
                    END,
                    updated_at = NOW(),
                    updated_by = :user_id
                WHERE ap_id = :ap_id
            """), {"ap_id": ap_id, "payment_date": payment_date, "our_bank_id": our_bank_id, "user_id": user_id})

def main():
    init_state()
    st.title(_t("批量處理付款紀錄"))

    today = dt.date.today()
    supplier_master = load_supplier_master()

    top1, top2, top3, top4 = st.columns([1, 1, 1.25, 1.35])
    with top1:
        start_date = st.date_input(_t("開始日期"), key="ap03_start_date")
    with top2:
        end_date = st.date_input(_t("結束日期"), key="ap03_end_date")
    with top3:
        mode_map = ap03_mode_options()
        display_mode = st.selectbox(
            _t("顯示模式"),
            options=list(mode_map.keys()),
            format_func=lambda x: mode_map.get(x, x),
            key="ap03_display_mode",
        )
    with top4:
        suppliers_df = load_suppliers_with_ap(start_date, end_date)
        supplier_options = [_t("全部供應商")] + suppliers_df["supplier_name"].dropna().tolist()
        current_supplier_name = _t("全部供應商")
        if st.session_state.get("ap03_supplier_id"):
            row = supplier_master.loc[supplier_master["supplier_id"] == st.session_state["ap03_supplier_id"]]
            if not row.empty and row.iloc[0]["supplier_name"] in supplier_options:
                current_supplier_name = row.iloc[0]["supplier_name"]
        if "ap03_supplier_name_widget" not in st.session_state:
            st.session_state["ap03_supplier_name_widget"] = current_supplier_name
        elif st.session_state["ap03_supplier_name_widget"] not in supplier_options:
            st.session_state["ap03_supplier_name_widget"] = current_supplier_name

        st.selectbox(
            _t("供應商"),
            supplier_options,
            key="ap03_supplier_name_widget",
            on_change=handle_supplier_change,
        )

    selected_supplier_id = st.session_state.get("ap03_supplier_id")

    b1, b2, b3 = st.columns([1, 1.2, 1])
    with b1:
        st.button(_t("全選所有顯示資料"), on_click=trigger_select_all, use_container_width=True)
    with b2:
        st.button(_t("刪除勾選"), on_click=trigger_clear_all, use_container_width=True)
    with b3:
        if st.button(_t("重新整理"), key="ap03_force_refresh", use_container_width=True):
            force_refresh_batch_data()
            st.rerun()

    raw_df = fetch_ap_rows(start_date, end_date, selected_supplier_id, st.session_state.get("ap03_display_mode", AP03_MODE_ALL_UNPAID))
    display_df = make_display_df(raw_df)
    display_df = apply_action_to_df(display_df)

    hidden_cols = {"ap_id", "supplier_id", "payment_id", "supplier_bank_account_id", "bank_account_id"}
    to_display_cols, to_internal_cols = build_display_i18n_maps(display_df, protected_cols=hidden_cols)
    display_df_i18n = display_df.rename(columns=to_display_cols)

    col_select = to_display_cols["勾選"]
    col_light = to_display_cols["燈號"]
    col_payment_status = to_display_cols["付款狀態"]
    col_receipt = to_display_cols["入庫單號"]
    col_supplier_name = to_display_cols["供應商名稱"]
    col_order = to_display_cols["訂單號碼"]
    col_invoice = to_display_cols["供應商發票號碼"]
    col_due = to_display_cols["應付日期"]
    col_payable_total = to_display_cols["應付總額"]
    col_paid_total = to_display_cols["已付金額"]
    col_total = to_display_cols["金額總計"]
    col_method = to_display_cols["付款方式"]
    col_supplier_bank_name = to_display_cols["供應商銀行名稱"]
    col_supplier_bank_code = to_display_cols["供應商銀行代號"]
    col_supplier_account_name = to_display_cols["供應商帳戶名"]
    col_supplier_account = to_display_cols["供應商帳號"]
    col_our_bank_name = to_display_cols["我方銀行名稱"]
    col_our_bank_code = to_display_cols["我方銀行代號"]
    col_our_account_name = to_display_cols["我方帳戶名"]
    col_our_account = to_display_cols["我方帳號"]
    col_created_by = to_display_cols["建檔人員"]
    col_created_at = to_display_cols["建檔時間"]
    col_updated_by = to_display_cols["最後修改人"]
    col_updated_at = to_display_cols["修改時間"]

    editor_df_i18n = st.data_editor(
        display_df_i18n,
        hide_index=True,
        height=220,
        use_container_width=True,
        key=f"ap03_editor_{st.session_state['ap03_editor_seed']}_{get_lang()}",
        column_config={
            col_select: st.column_config.CheckboxColumn(col_select, default=False, width="small"),
            col_light: st.column_config.TextColumn(col_light, disabled=True, width="small"),
            col_payment_status: st.column_config.TextColumn(col_payment_status, disabled=True),
            col_receipt: st.column_config.TextColumn(col_receipt, disabled=True),
            col_supplier_name: st.column_config.TextColumn(col_supplier_name, disabled=True),
            col_order: st.column_config.TextColumn(col_order, disabled=True),
            col_invoice: st.column_config.TextColumn(col_invoice, disabled=True),
            col_due: st.column_config.TextColumn(col_due, disabled=True),
            col_payable_total: st.column_config.NumberColumn(col_payable_total, format="%.2f", disabled=True),
            col_paid_total: st.column_config.NumberColumn(col_paid_total, format="%.2f", disabled=True),
            col_total: st.column_config.NumberColumn(col_total, format="%.2f", disabled=True),
            col_method: st.column_config.TextColumn(col_method, disabled=True),
            col_supplier_bank_name: st.column_config.TextColumn(col_supplier_bank_name, disabled=True),
            col_supplier_bank_code: st.column_config.TextColumn(col_supplier_bank_code, disabled=True),
            col_supplier_account_name: st.column_config.TextColumn(col_supplier_account_name, disabled=True),
            col_supplier_account: st.column_config.TextColumn(col_supplier_account, disabled=True),
            col_our_bank_name: st.column_config.TextColumn(col_our_bank_name, disabled=True),
            col_our_bank_code: st.column_config.TextColumn(col_our_bank_code, disabled=True),
            col_our_account_name: st.column_config.TextColumn(col_our_account_name, disabled=True),
            col_our_account: st.column_config.TextColumn(col_our_account, disabled=True),
            col_created_by: st.column_config.TextColumn(col_created_by, disabled=True),
            col_created_at: st.column_config.TextColumn(col_created_at, disabled=True),
            col_updated_by: st.column_config.TextColumn(col_updated_by, disabled=True),
            col_updated_at: st.column_config.TextColumn(col_updated_at, disabled=True),
            "ap_id": None,
            "supplier_id": None,
            "payment_id": None,
            "supplier_bank_account_id": None,
            "bank_account_id": None,
        },
    )

    editor_df = editor_df_i18n.rename(columns=to_internal_cols)
    selected_df = get_selected_rows(editor_df)
    total_amount = pd.to_numeric(selected_df["金額總計"], errors="coerce").fillna(0).sum() if not selected_df.empty else 0
    st.markdown(f"**{_t('金額總計：')}** {total_amount:,.2f}")
    st.divider()

    edit1, edit2 = st.columns([1, 1])
    with edit1:
        payment_date = st.date_input(_t("付款日期"), value=today, key="ap03_payment_date")
    with edit2:
        payment_method = st.selectbox(
            _t("付款方式"),
            PAYMENT_METHOD_OPTIONS,
            index=2 if "transfer" in PAYMENT_METHOD_OPTIONS else 0,
            format_func=lambda x: PAYMENT_METHOD_LABEL.get(x, x),
            key="ap03_payment_method",
        )

    st.markdown(f"**{_t('供應商銀行資訊')}**")
    supplier_bank_lookup_id, has_multi_supplier_selection = _selected_supplier_id_for_bank(selected_df, selected_supplier_id)
    if has_multi_supplier_selection:
        st.warning(_t("勾選資料包含多個供應商，請只選同一個供應商再選供應商銀行。"))

    supplier_bank_df = load_supplier_banks(supplier_bank_lookup_id)
    bank_name_options = [""] + supplier_bank_df["bank_name"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_supplier_bank_name", bank_name_options)
    sb1, sb2, sb3, sb4 = st.columns([1, 1, 1, 1.8])
    with sb1:
        selected_bank_name = st.selectbox(_t("付款銀行"), bank_name_options, key="ap03_supplier_bank_name")

    supplier_bank_filtered = supplier_bank_df.copy()
    if selected_bank_name:
        supplier_bank_filtered = supplier_bank_filtered.loc[
            supplier_bank_filtered["bank_name"].fillna("") == selected_bank_name
        ]

    bank_num_options = [""] + supplier_bank_filtered["bank_id"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_supplier_bank_num", bank_num_options)
    with sb2:
        selected_bank_num = st.selectbox(_t("銀行代碼"), bank_num_options, key="ap03_supplier_bank_num")
    if selected_bank_num:
        supplier_bank_filtered = supplier_bank_filtered.loc[
            supplier_bank_filtered["bank_id"].fillna("") == selected_bank_num
        ]

    account_name_options = [""] + supplier_bank_filtered["account_name"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_supplier_account_name", account_name_options)
    with sb3:
        selected_account_name = st.selectbox(_t("帳戶名稱"), account_name_options, key="ap03_supplier_account_name")
    if selected_account_name:
        supplier_bank_filtered = supplier_bank_filtered.loc[
            supplier_bank_filtered["account_name"].fillna("") == selected_account_name
        ]

    bank_account_options = [""] + supplier_bank_filtered["bank_account"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_supplier_bank_account", bank_account_options)
    with sb4:
        selected_bank_account = st.selectbox(_t("銀行帳號"), bank_account_options, key="ap03_supplier_bank_account")
    if selected_bank_account:
        supplier_bank_filtered = supplier_bank_filtered.loc[
            supplier_bank_filtered["bank_account"].fillna("") == selected_bank_account
        ]
    supplier_bank_row = supplier_bank_filtered.iloc[0] if not supplier_bank_filtered.empty else None

    st.markdown(f"**{_t('我方銀行資訊')}**")
    our_bank_df = load_our_banks()
    our_bank_name_options = [""] + our_bank_df["our_company_bank_name"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_our_bank_name", our_bank_name_options)
    ob1, ob2, ob3, ob4 = st.columns([1, 1, 1, 1.8])
    with ob1:
        selected_our_bank_name = st.selectbox(_t("我方銀行名稱"), our_bank_name_options, key="ap03_our_bank_name")

    our_bank_filtered = our_bank_df.copy()
    if selected_our_bank_name:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_bank_name"].fillna("") == selected_our_bank_name
        ]

    our_bank_num_options = [""] + our_bank_filtered["our_company_bank_num"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_our_bank_num", our_bank_num_options)
    with ob2:
        selected_our_bank_num = st.selectbox(_t("銀行代碼"), our_bank_num_options, key="ap03_our_bank_num")
    if selected_our_bank_num:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_bank_num"].fillna("") == selected_our_bank_num
        ]

    our_account_name_options = [""] + our_bank_filtered["our_company_account_name"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_our_account_name", our_account_name_options)
    with ob3:
        selected_our_account_name = st.selectbox(_t("帳戶名稱"), our_account_name_options, key="ap03_our_account_name")
    if selected_our_account_name:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_account_name"].fillna("") == selected_our_account_name
        ]

    our_bank_code_options = [""] + our_bank_filtered["our_company_account_code"].fillna("").drop_duplicates().tolist()
    _ensure_selectbox_value("ap03_our_bank_code", our_bank_code_options)
    with ob4:
        selected_our_bank_code = st.selectbox(_t("銀行帳號"), our_bank_code_options, key="ap03_our_bank_code")
    if selected_our_bank_code:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_account_code"].fillna("") == selected_our_bank_code
        ]
    our_bank_row = our_bank_filtered.iloc[0] if not our_bank_filtered.empty else None

    if st.button(_t("套用到勾選資料"), type="primary", use_container_width=True):
        try:
            upsert_batch_payment(selected_df, payment_date, payment_method, supplier_bank_row, our_bank_row)
            st.session_state["ap03_editor_seed"] += 1
            st.success(f"{_t('已成功套用到 ')}{len(selected_df)}{_t(' 筆付款紀錄。')}")
            force_refresh_batch_data()
            st.rerun()
        except Exception as exc:
            st.error(f"{_t('批量處理失敗：')}{exc}")


if __name__ == "__main__":
    main()
