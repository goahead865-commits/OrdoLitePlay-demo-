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
    "全部供應商": {"vi": "Tất cả nhà cung cấp", "en": "All Suppliers"},
    "全選所有顯示資料": {"vi": "Chọn tất cả dữ liệu đang hiển thị", "en": "Select All Displayed Rows"},
    "刪除勾選": {"vi": "Bỏ chọn đã chọn", "en": "Clear Selected"},
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
    "批量處理客戶收款紀錄": {"vi": "Xử lý hàng loạt phiếu thu khách hàng", "en": "Batch Process Customer Receipt Records"},
    "客戶": {"vi": "Khách hàng", "en": "Customer"},
    "全部客戶": {"vi": "Tất cả khách hàng", "en": "All Customers"},
    "燈號": {"vi": "Đèn trạng thái", "en": "Status Light"},
    "收款狀況": {"vi": "Tình trạng thu tiền", "en": "Receipt Status"},
    "未收款": {"vi": "Chưa thu", "en": "Unpaid"},
    "部分收款": {"vi": "Thu một phần", "en": "Partially Received"},
    "已收款": {"vi": "Đã thu", "en": "Received"},
    "應收總額": {"vi": "Tổng phải thu", "en": "Receivable Total"},
    "已收金額": {"vi": "Số tiền đã thu", "en": "Received Amount"},
    "客戶銀行資訊": {"vi": "Thông tin ngân hàng khách hàng", "en": "Customer Bank Information"},
    "客戶銀行名稱": {"vi": "Tên ngân hàng khách hàng", "en": "Customer Bank Name"},
    "客戶銀行代號": {"vi": "Mã ngân hàng khách hàng", "en": "Customer Bank Code"},
    "客戶帳戶名": {"vi": "Tên tài khoản khách hàng", "en": "Customer Account Name"},
    "客戶帳號": {"vi": "Số tài khoản khách hàng", "en": "Customer Bank Account"},
    "顯示模式": {"vi": "Chế độ hiển thị", "en": "Display Mode"},
    "顯示所有AR資料": {"vi": "Hiển thị tất cả dữ liệu AR", "en": "Show All AR Records"},
    "顯示所有未收款": {"vi": "Hiển thị tất cả khoản chưa thu", "en": "Show All Unpaid Receivables"},
    "顯示已到期未收款": {"vi": "Hiển thị khoản quá hạn chưa thu", "en": "Show Overdue Receivables"},
    "依應收日期區間": {"vi": "Theo khoảng ngày phải thu", "en": "By Receivable Due Date Range"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
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


PAGE_KEY = "AR03_batch_processing_customer_payment_records"
auth.require_read(PAGE_KEY)

AR03_MODE_ALL_AR = "all_ar"
AR03_MODE_ALL_UNPAID = "all_unpaid"
AR03_MODE_OVERDUE_UNPAID = "overdue_unpaid"
AR03_MODE_BY_DUE_DATE = "by_due_date"

def ar03_mode_options() -> dict[str, str]:
    return {
        AR03_MODE_ALL_AR: _t("顯示所有AR資料"),
        AR03_MODE_ALL_UNPAID: _t("顯示所有未收款"),
        AR03_MODE_OVERDUE_UNPAID: _t("顯示已到期未收款"),
        AR03_MODE_BY_DUE_DATE: _t("依應收日期區間"),
    }

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

def _sql_col(alias: str, col: Optional[str], fallback: str = "NULL") -> str:
    if col:
        return f"{alias}.`{col}`"
    return fallback


def _quote_table(table_name: str) -> str:
    return "`" + str(table_name).replace("`", "``") + "`"


def _first_existing_table(candidates: list[str]) -> Optional[str]:
    for table_name in candidates:
        if _table_columns(table_name):
            return table_name
    return None


def _build_audit_name_expr(
    *,
    user_alias: Optional[str],
    user_table: Optional[str],
    stuff_alias: Optional[str],
    stuff_table: Optional[str],
    fallback_expr: str,
) -> str:
    """Build a safe SQL display-name expression for audit user fields.

    Priority:
    1) user.stuff_id -> stuff.stuff_name
    2) user display/name fields
    3) raw user id

    Login/account/code columns are intentionally last because the UI should show
    the real person name whenever the DB schema can provide it.
    """
    parts: list[str] = []

    user_cols = set(_table_columns(user_table)) if user_table else set()
    stuff_cols = set(_table_columns(stuff_table)) if stuff_table else set()

    if stuff_alias and stuff_table:
        for col in ["stuff_name", "staff_name", "employee_name", "name", "full_name"]:
            if col in stuff_cols:
                parts.append(f"NULLIF({stuff_alias}.`{col}`, '')")
                break

    if user_alias and user_table:
        for col in [
            "display_name", "full_name", "real_name", "name",
            "user_name", "username", "login_name", "account", "user_code",
        ]:
            if col in user_cols:
                parts.append(f"NULLIF({user_alias}.`{col}`, '')")

    if fallback_expr:
        parts.append(f"CAST({fallback_expr} AS CHAR)")

    if not parts:
        return "''"
    return "COALESCE(" + ", ".join(parts) + ")"


def _build_ar_head_audit_sql(alias: str = "h") -> tuple[str, str]:
    """Return (audit_select_sql, audit_join_sql) for ar_statement_head.

    The function is schema-aware so the page will still run in older databases
    that do not have every audit column yet.
    """
    head_cols = set(_table_columns("ar_statement_head"))
    created_by_col = next((c for c in ["created_by", "created_by_id", "creadted_by", "create_by"] if c in head_cols), None)
    updated_by_col = next((c for c in ["updated_by", "updated_by_id", "modified_by", "modify_by"] if c in head_cols), None)
    created_at_col = next((c for c in ["created_at", "create_at", "created_time"] if c in head_cols), None)
    updated_at_col = next((c for c in ["updated_at", "pudated_at", "update_at", "modified_at", "modified_time"] if c in head_cols), None)

    user_table = _first_existing_table(["user", "users", "app_user", "system_user"])
    stuff_table = _first_existing_table(["stuff", "staff", "employee", "employees"])

    user_cols = set(_table_columns(user_table)) if user_table else set()
    stuff_cols = set(_table_columns(stuff_table)) if stuff_table else set()

    user_id_col = next((c for c in ["user_id", "id"] if c in user_cols), None)
    user_stuff_col = next((c for c in ["stuff_id", "staff_id", "employee_id"] if c in user_cols), None)
    stuff_id_col = next((c for c in ["stuff_id", "staff_id", "employee_id", "id"] if c in stuff_cols), None)

    joins: list[str] = []
    created_user_alias = None
    updated_user_alias = None
    created_stuff_alias = None
    updated_stuff_alias = None

    if user_table and user_id_col and created_by_col:
        created_user_alias = "u_created"
        joins.append(
            f"LEFT JOIN {_quote_table(user_table)} {created_user_alias} "
            f"ON {created_user_alias}.`{user_id_col}` = {alias}.`{created_by_col}`"
        )
        if stuff_table and user_stuff_col and stuff_id_col:
            created_stuff_alias = "s_created"
            joins.append(
                f"LEFT JOIN {_quote_table(stuff_table)} {created_stuff_alias} "
                f"ON {created_stuff_alias}.`{stuff_id_col}` = {created_user_alias}.`{user_stuff_col}`"
            )

    if user_table and user_id_col and updated_by_col:
        updated_user_alias = "u_updated"
        joins.append(
            f"LEFT JOIN {_quote_table(user_table)} {updated_user_alias} "
            f"ON {updated_user_alias}.`{user_id_col}` = {alias}.`{updated_by_col}`"
        )
        if stuff_table and user_stuff_col and stuff_id_col:
            updated_stuff_alias = "s_updated"
            joins.append(
                f"LEFT JOIN {_quote_table(stuff_table)} {updated_stuff_alias} "
                f"ON {updated_stuff_alias}.`{stuff_id_col}` = {updated_user_alias}.`{user_stuff_col}`"
            )

    created_by_expr = _build_audit_name_expr(
        user_alias=created_user_alias,
        user_table=user_table,
        stuff_alias=created_stuff_alias,
        stuff_table=stuff_table,
        fallback_expr=f"{alias}.`{created_by_col}`" if created_by_col else "''",
    )
    updated_by_raw_expr = _build_audit_name_expr(
        user_alias=updated_user_alias,
        user_table=user_table,
        stuff_alias=updated_stuff_alias,
        stuff_table=stuff_table,
        fallback_expr=f"{alias}.`{updated_by_col}`" if updated_by_col else "''",
    )

    created_at_expr = f"{alias}.`{created_at_col}`" if created_at_col else "NULL"
    updated_at_expr = f"{alias}.`{updated_at_col}`" if updated_at_col else "NULL"

    blank_conditions: list[str] = []
    if updated_by_col:
        blank_conditions.append(f"({alias}.`{updated_by_col}` IS NULL OR {alias}.`{updated_by_col}` = 0)")
    if updated_at_col:
        blank_conditions.append(f"{alias}.`{updated_at_col}` IS NULL")
    if updated_at_col and created_at_col:
        same_time = f"{alias}.`{updated_at_col}` = {alias}.`{created_at_col}`"
        if updated_by_col and created_by_col:
            same_time = f"({same_time} AND COALESCE({alias}.`{updated_by_col}`, 0) = COALESCE({alias}.`{created_by_col}`, 0))"
        blank_conditions.append(same_time)
    if not updated_by_col and not updated_at_col:
        blank_conditions.append("1=1")

    blank_when = " OR ".join(blank_conditions) if blank_conditions else "1=0"

    select_sql = f"""
            {created_by_expr} AS audit_created_by_name,
            {created_at_expr} AS audit_created_at,
            CASE WHEN {blank_when} THEN '' ELSE {updated_by_raw_expr} END AS audit_updated_by_name,
            CASE WHEN {blank_when} THEN NULL ELSE {updated_at_expr} END AS audit_updated_at
    """
    join_sql = "\n        ".join(joins)
    return select_sql, join_sql

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


def _current_user_id() -> Optional[int]:
    try:
        user_id = st.session_state.get("user_id")
        if user_id:
            return int(user_id)
    except Exception:
        pass

    try:
        if hasattr(auth, "get_current_user"):
            user = auth.get_current_user() or {}
            user_id = user.get("user_id")
            if user_id:
                return int(user_id)
    except Exception:
        pass

    return None


def _is_admin_user() -> bool:
    try:
        if bool(st.session_state.get("is_admin")):
            return True
    except Exception:
        pass

    try:
        if hasattr(auth, "get_current_user"):
            user = auth.get_current_user() or {}
            return bool(user.get("is_admin"))
    except Exception:
        pass

    return False


@st.cache_data(ttl=30, show_spinner=False)
def _load_ar03_permission(user_id: int) -> dict:
    """
    直接查 Z99 權限設定，避免 auth.require_edit 與欄位命名不一致時誤擋。
    """
    sql = """
        SELECT
            COALESCE(upo.can_read, 0) AS can_read,
            COALESCE(upo.can_create, 0) AS can_create,
            COALESCE(upo.can_update, 0) AS can_update,
            COALESCE(upo.can_delete, 0) AS can_delete,
            COALESCE(upo.can_approve, 0) AS can_approve
        FROM permission_resource pr
        LEFT JOIN user_permission_override upo
               ON upo.resource_id = pr.resource_id
              AND upo.user_id = :user_id
        WHERE pr.resource_code = :page_key
          AND COALESCE(pr.is_active, 1) = 1
        LIMIT 1
    """
    try:
        with get_db_engine().connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"user_id": int(user_id), "page_key": PAGE_KEY})
        if df.empty:
            return {"can_read": 0, "can_create": 0, "can_update": 0, "can_delete": 0, "can_approve": 0}
        row = df.iloc[0].to_dict()
        return {k: int(row.get(k) or 0) for k in ["can_read", "can_create", "can_update", "can_delete", "can_approve"]}
    except Exception:
        return {"can_read": 0, "can_create": 0, "can_update": 0, "can_delete": 0, "can_approve": 0}


def _can_edit_page() -> bool:
    if _is_admin_user():
        return True

    user_id = _current_user_id()
    if not user_id:
        return False

    p = _load_ar03_permission(int(user_id))
    return any(bool(p.get(k)) for k in ["can_create", "can_update", "can_approve"])


def _require_edit_page() -> None:
    """
    AR03 寫入收款資料前的真正權限檢查。
    """
    if _can_edit_page():
        return

    # 若本地檢查失敗，再交給原 auth，看是否有其他權限來源。
    if hasattr(auth, "require_edit"):
        auth.require_edit(PAGE_KEY)
        return

    raise PermissionError("你沒有權限編輯此頁：AR03_batch_processing_customer_payment_records")


@st.cache_data(ttl=300)
def load_supplier_master() -> pd.DataFrame:
    # AR03：沿用原本 supplier_master 變數名稱，但實際改抓 customer。
    sql = """
        SELECT
            customer_id AS supplier_id,
            customer_name AS supplier_name,
            customer_shortname AS supplier_shortname,
            checkout_day AS checkout_date,
            payment_term AS payment_days,
            1 AS is_active
        FROM customer
        ORDER BY customer_name
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


@st.cache_data(ttl=300)
def load_suppliers_with_ap(start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    # AR03：客戶下拉列出所有有 AR 對帳資料的客戶，不被日期卡住。
    sql = """
        SELECT DISTINCT
            h.customer_id AS supplier_id,
            COALESCE(c.customer_name, h.customer_name, CONCAT('Customer#', h.customer_id)) AS supplier_name
        FROM ar_statement_head h
        LEFT JOIN customer c ON c.customer_id = h.customer_id
        WHERE h.customer_id IS NOT NULL
          AND COALESCE(h.status, 'draft') <> 'cancelled'
        ORDER BY supplier_name
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


@st.cache_data(ttl=300)
def load_supplier_banks(supplier_id: Optional[int]) -> pd.DataFrame:
    # AR03：沿用 supplier_bank 內部名稱，但實際改抓 customer_bank。
    if not supplier_id:
        return pd.DataFrame(columns=[
            "Supplier_bank_account_id", "bank_id", "bank_name", "account_name", "bank_account", "is_default", "status"
        ])

    sql = """
        SELECT
            customer_bank_id AS Supplier_bank_account_id,
            customer_bank_num AS bank_id,
            customer_bank_name AS bank_name,
            customer_account_name AS account_name,
            customer_bank_code AS bank_account,
            1 AS is_default,
            'active' AS status
        FROM customer_bank
        WHERE customer_id = :customer_id
        ORDER BY customer_bank_name, customer_bank_num, customer_account_name, customer_bank_code
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params={"customer_id": int(supplier_id)})


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


@st.cache_data(ttl=300)
def fetch_ap_rows(
    start_date: dt.date,
    end_date: dt.date,
    supplier_id: Optional[int],
    display_mode: str = AR03_MODE_ALL_AR,
) -> pd.DataFrame:
    # AR03 正式資料源：
    # Head: ar_statement_head
    # Line: ar_statement_line
    # Payment: ar_apyable_payment（資料庫原本表名如此，先沿用）
    params = {}
    customer_clause = ""
    if supplier_id:
        customer_clause = " AND h.customer_id = :customer_id "
        params["customer_id"] = int(supplier_id)

    # AR03 金額總計來源：
    # 只以 ar_statement_head.final_total 為準。
    # final_total 應由 AR01 / 對帳單主檔寫入，內容已包含折讓與稅率。
    # 這裡不再 fallback 回 amount_total，避免畫面又顯示未計折讓 / 稅率的原始金額。
    receivable_amount_expr = """
        COALESCE(h.final_total, 0)
    """

    effective_date_expr = """
        COALESCE(
            DATE(h.ar_due_date),
            DATE(h.deliver_date),
            DATE(h.created_at)
        )
    """

    audit_select_sql, audit_join_sql = _build_ar_head_audit_sql("h")

    where_parts = [
        "COALESCE(h.status, 'draft') <> 'cancelled'"
    ]

    if display_mode == AR03_MODE_ALL_UNPAID:
        where_parts.append(f"""
            GREATEST(
                {receivable_amount_expr}
                - (
                    SELECT COALESCE(SUM(p.actual_amount_paid), 0)
                    FROM ar_apyable_payment p
                    WHERE p.ar_id = h.statement_id
                      AND COALESCE(p.status, 'unpaid') <> 'void'
                ),
                0
            ) > 0
        """)
    elif display_mode == AR03_MODE_OVERDUE_UNPAID:
        where_parts.append(f"""
            GREATEST(
                {receivable_amount_expr}
                - (
                    SELECT COALESCE(SUM(p.actual_amount_paid), 0)
                    FROM ar_apyable_payment p
                    WHERE p.ar_id = h.statement_id
                      AND COALESCE(p.status, 'unpaid') <> 'void'
                ),
                0
            ) > 0
        """)
        where_parts.append(f"{effective_date_expr} <= CURRENT_DATE()")
    elif display_mode == AR03_MODE_BY_DUE_DATE:
        where_parts.append(f"{effective_date_expr} BETWEEN :start_date AND :end_date")
        params["start_date"] = start_date
        params["end_date"] = end_date

    where_sql = " AND ".join(where_parts)

    sql = f"""
        WITH latest_payment AS (
            SELECT p.*
            FROM ar_apyable_payment p
            INNER JOIN (
                SELECT ar_id, MAX(ar_payment_id) AS max_payment_id
                FROM ar_apyable_payment
                GROUP BY ar_id
            ) x ON x.max_payment_id = p.ar_payment_id
        ),
        paid_sum AS (
            SELECT
                ar_id,
                COALESCE(SUM(actual_amount_paid), 0) AS paid_amount
            FROM ar_apyable_payment
            WHERE COALESCE(status, 'unpaid') <> 'void'
            GROUP BY ar_id
        )
        SELECT
            h.statement_id AS ap_id,
            h.statement_code AS ap_code,
            h.customer_id AS supplier_id,
            COALESCE(c.customer_name, h.customer_name, CONCAT('Customer#', h.customer_id)) AS supplier_name,
            h.delivery_code AS delivery_no,
            h.customer_order_number AS order_no,
            h.our_invoice_number AS supplier_invoice_no,
            h.our_invoice_date AS supplier_invoice_date,
            h.deliver_date AS checkout_date,
            {effective_date_expr} AS due_date,
            CAST({receivable_amount_expr} AS DECIMAL(18,2)) AS receivable_total,
            CAST(COALESCE(ps.paid_amount, 0) AS DECIMAL(18,2)) AS paid_amount,
            CASE
                WHEN COALESCE({receivable_amount_expr}, 0) > 0
                 AND COALESCE(ps.paid_amount, 0) >= COALESCE({receivable_amount_expr}, 0) THEN 'paid'
                WHEN COALESCE(ps.paid_amount, 0) > 0 THEN 'partial'
                ELSE 'unpaid'
            END AS payment_status,
            CASE
                WHEN COALESCE({receivable_amount_expr}, 0) > 0
                 AND COALESCE(ps.paid_amount, 0) >= COALESCE({receivable_amount_expr}, 0) THEN '🟢'
                WHEN COALESCE(ps.paid_amount, 0) > 0 THEN '🟡'
                ELSE '🔴'
            END AS payment_light,
            CAST(
                GREATEST(
                    {receivable_amount_expr} - COALESCE(ps.paid_amount, 0),
                    0
                ) AS DECIMAL(18,2)
            ) AS payment_total,
            COALESCE(lp.ar_payment_method, '') AS payment_method,
            COALESCE(lp.ar_payment_date, NULL) AS payment_date,
            COALESCE(lp.our_bank_account_code, '') AS payment_reference,
            COALESCE(lp.ar_voucher_no, '') AS voucher_no,
            COALESCE(lp.actual_amount_paid, GREATEST({receivable_amount_expr} - COALESCE(ps.paid_amount, 0), 0)) AS payment_amount,
            COALESCE(lp.ar_our_bank_id, NULL) AS bank_account_id,
            COALESCE(lp.ar_customer_bank_account_id, NULL) AS supplier_bank_account_id,
            COALESCE(lp.ar_customer_bank_code, '') AS supplier_bank_account,
            COALESCE(ob.our_company_bank_name, lp.our_bank_account_name, '') AS our_bank_name,
            COALESCE(ob.our_company_bank_num, lp.our_bank_num, '') AS our_bank_num,
            COALESCE(ob.our_company_account_name, lp.ar_our_bank_account_name, '') AS our_account_name,
            COALESCE(ob.our_company_account_code, lp.our_bank_account_code, '') AS our_bank_code,
            COALESCE(cb.customer_bank_name, lp.ar_customer_bank_name, '') AS supplier_bank_name,
            COALESCE(cb.customer_bank_num, lp.ar_customer_bank_num, '') AS supplier_bank_num,
            COALESCE(cb.customer_account_name, lp.ar_customer_account_name, '') AS supplier_account_name,
            COALESCE(cb.customer_bank_code, lp.ar_customer_bank_code, '') AS supplier_bank_account_code,
            lp.ar_payment_id AS payment_id,
            {audit_select_sql}
        FROM ar_statement_head h
        LEFT JOIN customer c ON c.customer_id = h.customer_id
        LEFT JOIN latest_payment lp ON lp.ar_id = h.statement_id
        LEFT JOIN paid_sum ps ON ps.ar_id = h.statement_id
        LEFT JOIN our_bank ob ON ob.our_bank_id = lp.ar_our_bank_id
        LEFT JOIN customer_bank cb ON cb.customer_bank_id = lp.ar_customer_bank_account_id
        {audit_join_sql}
        WHERE {where_sql}
        {customer_clause}
        ORDER BY
            {effective_date_expr} IS NULL,
            {effective_date_expr},
            h.statement_id DESC
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
    st.session_state.setdefault("ap03_display_mode", AR03_MODE_ALL_AR)
    st.session_state.setdefault("ap03_editor_seed", 0)
    st.session_state.setdefault("ap03_action", None)


def trigger_select_all():
    st.session_state["ap03_action"] = "select_all"


def trigger_clear_all():
    st.session_state["ap03_action"] = "clear_all"


def handle_supplier_change():
    supplier_name = st.session_state.get("ap03_supplier_name_widget", "全部客戶")
    supplier_master = load_supplier_master()
    selected_supplier_id = None
    if supplier_name != _t("全部客戶"):
        match = supplier_master.loc[supplier_master["supplier_name"] == supplier_name, "supplier_id"]
        if not match.empty:
            selected_supplier_id = int(match.iloc[0])

    st.session_state["ap03_supplier_id"] = selected_supplier_id
    end_date = st.session_state.get("ap03_end_date", dt.date.today())
    st.session_state["ap03_start_date"] = compute_default_start_date(selected_supplier_id, end_date)


def make_display_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame(columns=[
            "勾選", "燈號", "收款狀況", "入庫單號", "訂單號碼", "供應商發票號碼", "應付日期",
            "應收總額", "已收金額", "金額總計", "付款方式",
            "客戶銀行名稱", "客戶銀行代號", "客戶帳戶名", "客戶帳號",
            "我方銀行名稱", "我方銀行代號", "我方帳戶名", "我方帳號",
            "建檔人員", "建檔時間", "最後修改人", "修改時間",
            "ap_id", "supplier_id", "payment_id", "supplier_bank_account_id", "bank_account_id"
        ])

    df = raw_df.copy()
    df["勾選"] = False
    df["應付日期"] = pd.to_datetime(df["due_date"]).dt.strftime("%Y-%m-%d").fillna("")
    status_label_map = {
        "paid": _t("已收款"),
        "partial": _t("部分收款"),
        "unpaid": _t("未收款"),
    }
    display_df = pd.DataFrame({
        "勾選": df["勾選"],
        "燈號": df.get("payment_light", pd.Series(["🔴"] * len(df))).fillna("🔴"),
        "收款狀況": df.get("payment_status", pd.Series(["unpaid"] * len(df))).fillna("unpaid").map(status_label_map).fillna(_t("未收款")),
        "入庫單號": df["delivery_no"].fillna(""),
        "訂單號碼": df["order_no"].fillna(""),
        "供應商發票號碼": df["supplier_invoice_no"].fillna(""),
        "應付日期": df["應付日期"],
        "應收總額": pd.to_numeric(df.get("receivable_total", 0), errors="coerce").fillna(0.0),
        "已收金額": pd.to_numeric(df.get("paid_amount", 0), errors="coerce").fillna(0.0),
        "金額總計": pd.to_numeric(df["payment_total"], errors="coerce").fillna(0.0),
        "付款方式": df["payment_method"].fillna(""),
        "客戶銀行名稱": df["supplier_bank_name"].fillna(""),
        "客戶銀行代號": df["supplier_bank_num"].fillna(""),
        "客戶帳戶名": df["supplier_account_name"].fillna(""),
        "客戶帳號": df["supplier_bank_account_code"].fillna(""),
        "我方銀行名稱": df["our_bank_name"].fillna(""),
        "我方銀行代號": df["our_bank_num"].fillna(""),
        "我方帳戶名": df["our_account_name"].fillna(""),
        "我方帳號": df["our_bank_code"].fillna(""),
        "建檔人員": df.get("audit_created_by_name", pd.Series([""] * len(df))).fillna(""),
        "建檔時間": pd.to_datetime(df.get("audit_created_at", pd.Series([None] * len(df))), errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna(""),
        "最後修改人": df.get("audit_updated_by_name", pd.Series([""] * len(df))).fillna(""),
        "修改時間": pd.to_datetime(df.get("audit_updated_at", pd.Series([None] * len(df))), errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna(""),
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


def upsert_batch_payment(
    selected_df: pd.DataFrame,
    payment_date: dt.date,
    payment_method: str,
    supplier_bank_row: Optional[pd.Series],
    our_bank_row: Optional[pd.Series],
):
    _require_edit_page()

    if selected_df.empty:
        raise ValueError("請先勾選至少一筆資料。")
    if not payment_method:
        raise ValueError("請選擇付款方式。")

    customer_bank_id = None
    customer_bank_num = ""
    customer_bank_name = ""
    customer_account_name = ""
    customer_bank_code = ""
    if supplier_bank_row is not None and not supplier_bank_row.empty:
        customer_bank_id = int(supplier_bank_row["Supplier_bank_account_id"])
        customer_bank_num = str(supplier_bank_row["bank_id"] or "")
        customer_bank_name = str(supplier_bank_row["bank_name"] or "")
        customer_account_name = str(supplier_bank_row["account_name"] or "")
        customer_bank_code = str(supplier_bank_row["bank_account"] or "")

    our_bank_id = None
    our_bank_name = ""
    our_bank_num = ""
    our_account_name = ""
    our_bank_code = ""
    if our_bank_row is not None and not our_bank_row.empty:
        our_bank_id = int(our_bank_row["our_bank_id"])
        our_bank_name = str(our_bank_row["our_company_bank_name"] or "")
        our_bank_num = str(our_bank_row["our_company_bank_num"] or "")
        our_account_name = str(our_bank_row["our_company_account_name"] or "")
        our_bank_code = str(our_bank_row["our_company_account_code"] or "")

    user_id = int(st.session_state.get("user_id", 1) or 1)

    update_sql = text("""
        UPDATE ar_apyable_payment
        SET final_total = :final_total,
            actual_amount_paid = :actual_amount_paid,
            balance = :balance,
            ar_payment_date = :payment_date,
            ar_payment_method = :payment_method,
            ar_our_bank_id = :our_bank_id,
            our_bank_account_name = :our_bank_name,
            our_bank_num = :our_bank_num,
            our_bank_account_code = :our_bank_code,
            ar_our_bank_account_name = :our_account_name,
            ar_customer_bank_account_id = :customer_bank_id,
            ar_customer_bank_num = :customer_bank_num,
            ar_customer_bank_name = :customer_bank_name,
            ar_customer_account_name = :customer_account_name,
            ar_customer_bank_code = :customer_bank_code,
            status = CASE WHEN :balance <= 0 THEN 'settled' ELSE 'partial' END,
            pudated_at = NOW(),
            updated_by = :user_id
        WHERE ar_payment_id = :payment_id
    """)

    insert_sql = text("""
        INSERT INTO ar_apyable_payment (
            ar_id,
            final_total,
            actual_amount_paid,
            balance,
            ar_payment_date,
            ar_payment_method,
            ar_our_bank_id,
            our_bank_account_name,
            our_bank_num,
            our_bank_account_code,
            ar_our_bank_account_name,
            ar_customer_bank_account_id,
            ar_customer_bank_num,
            ar_customer_bank_name,
            ar_customer_account_name,
            ar_customer_bank_code,
            status,
            created_at,
            created_by
        ) VALUES (
            :ar_id,
            :final_total,
            :actual_amount_paid,
            :balance,
            :payment_date,
            :payment_method,
            :our_bank_id,
            :our_bank_name,
            :our_bank_num,
            :our_bank_code,
            :our_account_name,
            :customer_bank_id,
            :customer_bank_num,
            :customer_bank_name,
            :customer_account_name,
            :customer_bank_code,
            CASE WHEN :balance <= 0 THEN 'settled' ELSE 'partial' END,
            NOW(),
            :user_id
        )
    """)

    with get_db_engine().begin() as conn:
        for _, row in selected_df.iterrows():
            ar_id = int(row["ap_id"])
            # 存檔前重新讀一次 DB，避免母表或快取殘留造成重複收款。
            chk = conn.execute(text("""
                SELECT
                    COALESCE(h.final_total, 0) AS receivable_total,
                    COALESCE((
                        SELECT SUM(p.actual_amount_paid)
                        FROM ar_apyable_payment p
                        WHERE p.ar_id = h.statement_id
                          AND COALESCE(p.status, 'unpaid') <> 'void'
                    ), 0) AS paid_amount
                FROM ar_statement_head h
                WHERE h.statement_id = :ar_id
                LIMIT 1
            """), {"ar_id": ar_id}).mappings().first()
            if not chk:
                raise ValueError(f"找不到 AR 資料：{ar_id}")
            receivable_total = float(chk.get("receivable_total") or 0.0)
            paid_amount = float(chk.get("paid_amount") or 0.0)
            receivable_balance = max(receivable_total - paid_amount, 0.0)
            if receivable_total > 0 and paid_amount >= receivable_total:
                raise ValueError(f"AR 已收款完成，不能重複收款：{row.get('入庫單號', ar_id)}")
            if receivable_balance <= 0:
                raise ValueError(f"剩餘應收金額為 0，不能新增收款：{row.get('入庫單號', ar_id)}")

            actual_amount_paid = receivable_balance
            balance_after = max(receivable_balance - actual_amount_paid, 0.0)

            payload = {
                "payment_id": None,
                "ar_id": ar_id,
                "final_total": str(receivable_balance),
                "actual_amount_paid": actual_amount_paid,
                "balance": balance_after,
                "payment_date": payment_date,
                "payment_method": payment_method,
                "our_bank_id": our_bank_id,
                "our_bank_name": our_bank_name,
                "our_bank_num": our_bank_num,
                "our_bank_code": our_bank_code,
                "our_account_name": our_account_name,
                "customer_bank_id": customer_bank_id,
                "customer_bank_num": customer_bank_num,
                "customer_bank_name": customer_bank_name,
                "customer_account_name": customer_account_name,
                "customer_bank_code": customer_bank_code,
                "user_id": user_id,
            }

            if payload["payment_id"]:
                conn.execute(update_sql, payload)
            else:
                conn.execute(insert_sql, payload)

            # 同步更新 AR statement 狀態。
            conn.execute(text("""
                UPDATE ar_statement_head
                SET status = CASE
                    WHEN (
                        SELECT COALESCE(SUM(actual_amount_paid), 0)
                        FROM ar_apyable_payment
                        WHERE ar_id = :ar_id
                          AND COALESCE(status, 'unpaid') <> 'void'
                    ) >= COALESCE(final_total, 0) THEN 'closed'
                    WHEN (
                        SELECT COALESCE(SUM(actual_amount_paid), 0)
                        FROM ar_apyable_payment
                        WHERE ar_id = :ar_id
                          AND COALESCE(status, 'unpaid') <> 'void'
                    ) > 0 THEN 'confirmed'
                    ELSE COALESCE(status, 'draft')
                END,
                updated_at = NOW(),
                updated_by = :user_id
                WHERE statement_id = :ar_id
            """), {"ar_id": ar_id, "user_id": user_id})


def main():
    init_state()
    st.title(_t("批量處理客戶收款紀錄"))
    CAN_EDIT_PAGE = _can_edit_page()
    if not CAN_EDIT_PAGE:
        st.warning(_t("你目前只有查看權限，不能套用收款資料。請到 Z99 開啟 AR03 的可編輯權限。"))

    today = dt.date.today()
    supplier_master = load_supplier_master()

    top1, top2, top3, top4 = st.columns([1, 1, 1.25, 1.35])
    with top1:
        start_date = st.date_input(_t("開始日期"), key="ap03_start_date")
    with top2:
        end_date = st.date_input(_t("結束日期"), key="ap03_end_date")
    with top3:
        mode_map = ar03_mode_options()
        display_mode = st.selectbox(
            _t("顯示模式"),
            options=list(mode_map.keys()),
            format_func=lambda x: mode_map.get(x, x),
            key="ap03_display_mode",
        )
    with top4:
        suppliers_df = load_suppliers_with_ap(start_date, end_date)
        supplier_options = [_t("全部客戶")] + suppliers_df["supplier_name"].dropna().tolist()
        current_supplier_name = _t("全部客戶")
        if st.session_state.get("ap03_supplier_id"):
            row = supplier_master.loc[supplier_master["supplier_id"] == st.session_state["ap03_supplier_id"]]
            if not row.empty and row.iloc[0]["supplier_name"] in supplier_options:
                current_supplier_name = row.iloc[0]["supplier_name"]
        if "ap03_supplier_name_widget" not in st.session_state:
            st.session_state["ap03_supplier_name_widget"] = current_supplier_name
        elif st.session_state["ap03_supplier_name_widget"] not in supplier_options:
            st.session_state["ap03_supplier_name_widget"] = current_supplier_name

        st.selectbox(
            _t("客戶"),
            supplier_options,
            key="ap03_supplier_name_widget",
            on_change=handle_supplier_change,
        )

    selected_supplier_id = st.session_state.get("ap03_supplier_id")

    b1, b2, b3 = st.columns([1, 1.2, 1])
    with b1:
        st.button(_t("全選所有顯示資料"), on_click=trigger_select_all, use_container_width=True, disabled=not CAN_EDIT_PAGE)
    with b2:
        st.button(_t("刪除勾選"), on_click=trigger_clear_all, use_container_width=True, disabled=not CAN_EDIT_PAGE)
    with b3:
        if st.button(_t("重新整理"), key="ar03_force_refresh", use_container_width=True):
            force_refresh_batch_data()
            st.rerun()

    raw_df = fetch_ap_rows(start_date, end_date, selected_supplier_id, st.session_state.get("ap03_display_mode", AR03_MODE_ALL_AR))
    display_df = make_display_df(raw_df)
    display_df = apply_action_to_df(display_df)

    # Keep the DataFrame's original Chinese keys for business logic,
    # but translate the visible column labels through column_config.
    # Do NOT rename display_df itself here, because later code reads keys like "勾選" and "金額總計".
    editor_df = st.data_editor(
        display_df,
        hide_index=True,
        height=220,
        use_container_width=True,
        key=f"ap03_editor_{st.session_state['ap03_editor_seed']}",
        disabled=(not CAN_EDIT_PAGE),
        column_config={
            "勾選": st.column_config.CheckboxColumn(_t("勾選"), default=False, width="small"),
            "燈號": st.column_config.TextColumn(_t("燈號"), disabled=True, width="small"),
            "收款狀況": st.column_config.TextColumn(_t("收款狀況"), disabled=True),
            "入庫單號": st.column_config.TextColumn(_t("入庫單號"), disabled=True),
            "訂單號碼": st.column_config.TextColumn(_t("訂單號碼"), disabled=True),
            "供應商發票號碼": st.column_config.TextColumn(_t("供應商發票號碼"), disabled=True),
            "應付日期": st.column_config.TextColumn(_t("應付日期"), disabled=True),
            "應收總額": st.column_config.NumberColumn(_t("應收總額"), format="%.2f", disabled=True),
            "已收金額": st.column_config.NumberColumn(_t("已收金額"), format="%.2f", disabled=True),
            "金額總計": st.column_config.NumberColumn(_t("金額總計"), format="%.2f", disabled=True),
            "付款方式": st.column_config.TextColumn(_t("付款方式"), disabled=True),
            "客戶銀行名稱": st.column_config.TextColumn(_t("客戶銀行名稱"), disabled=True),
            "客戶銀行代號": st.column_config.TextColumn(_t("客戶銀行代號"), disabled=True),
            "客戶帳戶名": st.column_config.TextColumn(_t("客戶帳戶名"), disabled=True),
            "客戶帳號": st.column_config.TextColumn(_t("客戶帳號"), disabled=True),
            "我方銀行名稱": st.column_config.TextColumn(_t("我方銀行名稱"), disabled=True),
            "我方銀行代號": st.column_config.TextColumn(_t("我方銀行代號"), disabled=True),
            "我方帳戶名": st.column_config.TextColumn(_t("我方帳戶名"), disabled=True),
            "我方帳號": st.column_config.TextColumn(_t("我方帳號"), disabled=True),
            "建檔人員": st.column_config.TextColumn(_t("建檔人員"), disabled=True),
            "建檔時間": st.column_config.TextColumn(_t("建檔時間"), disabled=True),
            "最後修改人": st.column_config.TextColumn(_t("最後修改人"), disabled=True),
            "修改時間": st.column_config.TextColumn(_t("修改時間"), disabled=True),
            "ap_id": None,
            "supplier_id": None,
            "payment_id": None,
            "supplier_bank_account_id": None,
            "bank_account_id": None,
        },
    )

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

    # 客戶銀行資料來源：customer_bank。
    # 若上方篩選不是單一客戶，但使用者在母表只勾選同一個客戶，也要能帶出該客戶銀行資料。
    selected_customer_for_bank = selected_supplier_id
    if not selected_customer_for_bank and not selected_df.empty and "supplier_id" in selected_df.columns:
        unique_customer_ids = selected_df["supplier_id"].dropna().astype(int).unique().tolist()
        if len(unique_customer_ids) == 1:
            selected_customer_for_bank = int(unique_customer_ids[0])

    st.markdown(f"**{_t('客戶銀行資訊')}**")
    supplier_bank_df = load_supplier_banks(selected_customer_for_bank)
    bank_name_options = [""] + supplier_bank_df["bank_name"].fillna("").drop_duplicates().tolist()
    sb1, sb2, sb3, sb4 = st.columns([1, 1, 1, 1.8])
    with sb1:
        selected_bank_name = st.selectbox(_t("付款銀行"), bank_name_options, key="ap03_supplier_bank_name")

    supplier_bank_filtered = supplier_bank_df.copy()
    if selected_bank_name:
        supplier_bank_filtered = supplier_bank_filtered.loc[
            supplier_bank_filtered["bank_name"].fillna("") == selected_bank_name
        ]

    bank_num_options = [""] + supplier_bank_filtered["bank_id"].fillna("").drop_duplicates().tolist()
    with sb2:
        selected_bank_num = st.selectbox(_t("銀行代碼"), bank_num_options, key="ap03_supplier_bank_num")
    if selected_bank_num:
        supplier_bank_filtered = supplier_bank_filtered.loc[
            supplier_bank_filtered["bank_id"].fillna("") == selected_bank_num
        ]

    account_name_options = [""] + supplier_bank_filtered["account_name"].fillna("").drop_duplicates().tolist()
    with sb3:
        selected_account_name = st.selectbox(_t("帳戶名稱"), account_name_options, key="ap03_supplier_account_name")
    if selected_account_name:
        supplier_bank_filtered = supplier_bank_filtered.loc[
            supplier_bank_filtered["account_name"].fillna("") == selected_account_name
        ]

    bank_account_options = [""] + supplier_bank_filtered["bank_account"].fillna("").drop_duplicates().tolist()
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
    ob1, ob2, ob3, ob4 = st.columns([1, 1, 1, 1.8])
    with ob1:
        selected_our_bank_name = st.selectbox(_t("我方銀行名稱"), our_bank_name_options, key="ap03_our_bank_name")

    our_bank_filtered = our_bank_df.copy()
    if selected_our_bank_name:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_bank_name"].fillna("") == selected_our_bank_name
        ]

    our_bank_num_options = [""] + our_bank_filtered["our_company_bank_num"].fillna("").drop_duplicates().tolist()
    with ob2:
        selected_our_bank_num = st.selectbox(_t("銀行代碼"), our_bank_num_options, key="ap03_our_bank_num")
    if selected_our_bank_num:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_bank_num"].fillna("") == selected_our_bank_num
        ]

    our_account_name_options = [""] + our_bank_filtered["our_company_account_name"].fillna("").drop_duplicates().tolist()
    with ob3:
        selected_our_account_name = st.selectbox(_t("帳戶名稱"), our_account_name_options, key="ap03_our_account_name")
    if selected_our_account_name:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_account_name"].fillna("") == selected_our_account_name
        ]

    our_bank_code_options = [""] + our_bank_filtered["our_company_account_code"].fillna("").drop_duplicates().tolist()
    with ob4:
        selected_our_bank_code = st.selectbox(_t("銀行帳號"), our_bank_code_options, key="ap03_our_bank_code")
    if selected_our_bank_code:
        our_bank_filtered = our_bank_filtered.loc[
            our_bank_filtered["our_company_account_code"].fillna("") == selected_our_bank_code
        ]
    our_bank_row = our_bank_filtered.iloc[0] if not our_bank_filtered.empty else None

    if st.button(_t("套用到勾選資料"), type="primary", use_container_width=True, disabled=not CAN_EDIT_PAGE):
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
