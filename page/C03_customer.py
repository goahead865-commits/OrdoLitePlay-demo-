"""
C03 Customer Management Module
此模組處理客戶主檔及其相關子表（送貨地址、聯絡人、業務配置）的 CRUD 操作。
"""

import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd
import re
from sqlalchemy import text
from splitter_component import render_vertical_splitter

apply_compact_layout()
from typing import Optional, List, Tuple, Any

# =========================================
# I18N Helper
# =========================================
LANGUAGES = {
    "zh": "中文",
    "vi": "Tiếng Việt",
    "en": "English",
}

TRANSLATIONS = {
    "C03 客戶主檔（表單模式）": {"vi": "C03 Hồ sơ khách hàng (chế độ biểu mẫu)", "en": "C03 Customer Master (Form Mode)"},
    "客戶清單": {"vi": "Danh sách khách hàng", "en": "Customer List"},
    "建檔人員": {"vi": "Người tạo", "en": "Created By"},
    "最後修改人": {"vi": "Người sửa cuối", "en": "Last Modified By"},
    "資訊區": {"vi": "Khu vực thông tin", "en": "Information Section"},
    "主要資料": {"vi": "Dữ liệu chính", "en": "Main Information"},
    "送貨地址": {"vi": "Địa chỉ giao hàng", "en": "Delivery Address"},
    "客戶聯絡人": {"vi": "Người liên hệ khách hàng", "en": "Customer Contacts"},
    "負責業務": {"vi": "Nhân viên kinh doanh phụ trách", "en": "Assigned Sales"},
    "客戶銀行資料": {"vi": "Thông tin ngân hàng của khách hàng", "en": "Customer Bank Information"},
    "新增客戶類型": {"vi": "Thêm loại khách hàng", "en": "Add Customer Type"},
    "搜尋（代碼/名稱/簡稱）": {"vi": "Tìm kiếm (Mã / Tên / Tên viết tắt)", "en": "Search (Code / Name / Short Name)"},
    "例如：C0001 / 凱勝": {"vi": "Ví dụ: C0001 / Kai Sheng", "en": "e.g. C0001 / Kai Sheng"},
    "客戶類型": {"vi": "Loại khách hàng", "en": "Customer Type"},
    "每頁筆數": {"vi": "Số dòng mỗi trang", "en": "Rows per page"},
    "上一頁": {"vi": "Trang trước", "en": "Previous Page"},
    "下一頁": {"vi": "Trang sau", "en": "Next Page"},
    "選取": {"vi": "Chọn", "en": "Select"},
    "選一筆資料來修改（或選新增模式）": {"vi": "Chọn một dữ liệu để chỉnh sửa (hoặc chọn chế độ thêm mới)", "en": "Select a record to edit (or choose Add New mode)"},
    "取消選取（回新增）": {"vi": "Bỏ chọn (quay về chế độ thêm mới)", "en": "Clear Selection (Back to Add New mode)"},
    "取消選取": {"vi": "Bỏ chọn", "en": "Clear Selection"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "客戶代碼": {"vi": "Mã khách hàng", "en": "Customer Code"},
    "客戶代碼（系統自動）": {"vi": "Mã khách hàng (hệ thống tự động)", "en": "Customer Code (Auto Generated)"},
    "客戶名稱": {"vi": "Tên khách hàng", "en": "Customer Name"},
    "客戶簡稱": {"vi": "Tên viết tắt khách hàng", "en": "Customer Short Name"},
    "電話": {"vi": "Điện thoại", "en": "Phone"},
    "Email": {"vi": "Email", "en": "Email"},
    "統編/稅號": {"vi": "Mã số thuế", "en": "Tax ID / Registration No."},
    "地址": {"vi": "Địa chỉ", "en": "Address"},
    "負責人": {"vi": "Người phụ trách", "en": "Person in Charge"},
    "負責人電話": {"vi": "SĐT người phụ trách", "en": "Person in Charge Phone"},
    "結帳日": {"vi": "Ngày chốt công nợ", "en": "Closing Day"},
    "付款天數": {"vi": "Số ngày thanh toán", "en": "Payment Term (Days)"},
    "備註": {"vi": "Ghi chú", "en": "Remarks"},
    "客戶類型名稱": {"vi": "Tên loại khách hàng", "en": "Customer Type Name"},
    "儲存客戶類型": {"vi": "Lưu loại khách hàng", "en": "Save Customer Type"},
    "儲存主資料": {"vi": "Lưu dữ liệu chính", "en": "Save Main Data"},
    "回新增模式": {"vi": "Quay về chế độ thêm mới", "en": "Back to Add New Mode"},
    "儲存": {"vi": "Lưu", "en": "Save"},
    "刪除": {"vi": "Xóa", "en": "Delete"},
    "代碼": {"vi": "Mã", "en": "Code"},
    "收貨窗口": {"vi": "Người nhận hàng", "en": "Receiving Contact"},
    "距離(km)": {"vi": "Khoảng cách (km)", "en": "Distance (km)"},
    "啟用": {"vi": "Kích hoạt", "en": "Active"},
    "聯絡人": {"vi": "Người liên hệ", "en": "Contact Person"},
    "部門": {"vi": "Bộ phận", "en": "Department"},
    "職稱": {"vi": "Chức vụ", "en": "Title"},
    "業務人員": {"vi": "Nhân viên kinh doanh", "en": "Salesperson"},
    "起始日": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日": {"vi": "Ngày kết thúc", "en": "End Date"},
    "銀行代號": {"vi": "Mã ngân hàng", "en": "Bank Code"},
    "銀行名稱": {"vi": "Tên ngân hàng", "en": "Bank Name"},
    "戶名": {"vi": "Tên tài khoản", "en": "Account Name"},
    "銀行帳號": {"vi": "Số tài khoản ngân hàng", "en": "Bank Account Number"},
    "目前沒有資料。": {"vi": "Hiện chưa có dữ liệu.", "en": "No data available."},
    "查無資料。你可以直接在下方新增客戶。": {"vi": "Không tìm thấy dữ liệu. Bạn có thể thêm khách hàng mới bên dưới.", "en": "No records found. You can add a new customer below."},
    "目前是新增模式。請在上方清單勾選一個客戶，或直接填寫下方資料新增。": {"vi": "Hiện đang ở chế độ thêm mới. Vui lòng chọn khách hàng ở danh sách phía trên hoặc nhập dữ liệu bên dưới để thêm mới.", "en": "Currently in Add New mode. Please select a customer from the list above or enter data below to add a new one."},
    "請先在上方清單勾選一個客戶。": {"vi": "Vui lòng chọn một khách hàng ở danh sách phía trên trước.", "en": "Please select a customer from the list above first."},
    "請先選擇客戶。": {"vi": "Vui lòng chọn khách hàng trước.", "en": "Please select a customer first."},
    "新增後會自動回寫到客戶類型下拉選單。": {"vi": "Sau khi thêm, hệ thống sẽ tự động cập nhật vào danh sách chọn loại khách hàng.", "en": "After saving, it will be automatically added to the customer type dropdown."},
    "新增模式無法刪除。": {"vi": "Chế độ thêm mới không thể xóa.", "en": "Cannot delete in Add New mode."},
    "無法刪除。": {"vi": "Không thể xóa.", "en": "Cannot delete."},
    "此表無 Primary Key。": {"vi": "Bảng này không có khóa chính (Primary Key).", "en": "This table has no Primary Key."},
    "找不到該客戶資料，可能已被刪除。": {"vi": "Không tìm thấy dữ liệu khách hàng này, có thể đã bị xóa.", "en": "Customer record not found. It may have been deleted."},
    "找不到 customer 表，請確認資料庫結構。": {"vi": "Không tìm thấy bảng customer, vui lòng kiểm tra cấu trúc cơ sở dữ liệu.", "en": "customer table not found. Please check the database schema."},
    "找不到 db.py，請確認檔案是否存在。": {"vi": "Không tìm thấy db.py, vui lòng kiểm tra lại tệp.", "en": "db.py not found. Please make sure the file exists."},
    "此客戶類型已存在": {"vi": "Loại khách hàng này đã tồn tại", "en": "This customer type already exists"},
    "客戶類型名稱不可空白": {"vi": "Tên loại khách hàng không được để trống", "en": "Customer type name cannot be blank"},
    "客戶類型名稱不可超過 32 字": {"vi": "Tên loại khách hàng không được vượt quá 32 ký tự", "en": "Customer type name must not exceed 32 characters"},
    "已新增客戶類型：": {"vi": "Đã thêm loại khách hàng: ", "en": "Customer type added: "},
    "新增失敗：": {"vi": "Thêm mới thất bại: ", "en": "Create failed: "},
    "儲存失敗：": {"vi": "Lưu thất bại: ", "en": "Save failed: "},
    "刪除失敗：": {"vi": "Xóa thất bại: ", "en": "Delete failed: "},
    "(全部)": {"vi": "(Tất cả)", "en": "(All)"},
    "(新增模式)": {"vi": "(Chế độ thêm mới)", "en": "(Add New Mode)"},
    "(未指定)": {"vi": "(Chưa chỉ định)", "en": "(Unassigned)"},
    "未指定": {"vi": "Chưa chỉ định", "en": "Unassigned"},
    "請確認資料庫結構。": {"vi": "Vui lòng kiểm tra cấu trúc cơ sở dữ liệu.", "en": "Please check the database schema."},
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


# =========================================
# Database Connection Handling
# =========================================
try:
    from db import get_engine
except ImportError:
    def get_engine():
        st.error(_t("找不到 db.py，請確認檔案是否存在。"))
        return None



# =========================================
# Permission Guard
# =========================================
import auth
PAGE_KEY = "C03_customer"
auth.require_read(PAGE_KEY)

# =========================================
# Database Helper Functions
# =========================================
def qdf(engine, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    """執行 SQL 查詢並回傳 DataFrame"""
    if params is None:
        params = {}
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def exec_sql(engine, sql: str, params: Optional[dict] = None) -> None:
    """執行 DML (Insert/Update/Delete)"""
    if params is None:
        params = {}
    with engine.begin() as conn:
        conn.execute(text(sql), params)


def exec_scalar(engine, sql: str, params: Optional[dict] = None) -> Any:
    """執行 SQL 並取得單一純量值 (Scalar)"""
    if params is None:
        params = {}
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def get_engine_url(engine) -> str:
    """取得 Engine URL 字串 (用於快取雜湊鍵值)"""
    return str(engine.url)


# =========================================
# Schema Metadata Cache
# =========================================
@st.cache_data(ttl=3600)
def table_exists(_engine_url: str, table_name: str) -> bool:
    """檢查資料表是否存在於資料庫中"""
    engine = get_engine()
    if engine is None:
        return False
    sql = """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = :t
    """
    result = exec_scalar(engine, sql, {"t": table_name})
    return (result or 0) > 0


@st.cache_data(ttl=3600)
def get_table_columns(_engine_url: str, table_name: str) -> List[str]:
    """取得資料表的所有欄位名稱列表"""
    engine = get_engine()
    if engine is None:
        return []

    if not table_exists(_engine_url, table_name):
        return []

    sql = """
        SELECT COLUMN_NAME
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = :t
        ORDER BY ORDINAL_POSITION
    """
    with engine.connect() as conn:
        res = conn.execute(text(sql), {"t": table_name}).fetchall()
        # res: List[Row] -> 每列第一個欄位就是 COLUMN_NAME
        return [r[0] for r in res]


@st.cache_data(ttl=3600)
def get_pk_column(_engine_url: str, table_name: str) -> Optional[str]:
    """取得資料表的 Primary Key 欄位名稱"""
    engine = get_engine()
    if engine is None:
        return None

    if not table_exists(_engine_url, table_name):
        return None

    sql = """
        SELECT k.COLUMN_NAME
        FROM information_schema.table_constraints t
        JOIN information_schema.key_column_usage k
          ON t.CONSTRAINT_NAME = k.CONSTRAINT_NAME
         AND t.TABLE_SCHEMA = k.TABLE_SCHEMA
         AND t.TABLE_NAME = k.TABLE_NAME
        WHERE t.TABLE_SCHEMA = DATABASE()
          AND t.TABLE_NAME = :t
          AND t.CONSTRAINT_TYPE = 'PRIMARY KEY'
        ORDER BY k.ORDINAL_POSITION
        LIMIT 1
    """
    return exec_scalar(engine, sql, {"t": table_name})


# =========================================
# Utility Functions
# =========================================
def na_to_none(value: Any) -> Any:
    """將 pandas 的 NA/NaN 轉換為 Python 的 None"""
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def to_int_or_none(value: Any) -> Optional[int]:
    """安全地將值轉換為整數，失敗則回傳 None"""
    value = na_to_none(value)
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def to_float_or_none(value: Any) -> Optional[float]:
    """安全地將值轉換為浮點數，失敗則回傳 None"""
    value = na_to_none(value)
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# =========================================
# Constants & Mappings
# =========================================
COLUMN_MAP = {
    # Customer Main
    "customer_code": _t("客戶代碼"),
    "customer_name": _t("客戶名稱"),
    "customer_shortname": _t("客戶簡稱"),
    "customer_phone": _t("電話"),
    "customer_email": _t("Email"),
    "customer_tax_id": _t("統編/稅號"),
    "customer_address": _t("地址"),
    "boss_name": _t("負責人"),
    "boss_phone": _t("負責人電話"),
    "checkout_day": _t("結帳日"),
    "payment_term": _t("付款天數"),
    "note": _t("備註"),
    "customer_category": _t("客戶類型"),
    "customer_category_name": _t("客戶類型"),
    "our_sales_name": _t("負責業務"),
    "our_sales_display": _t("負責業務"),
    "created_by_display": _t("建檔人員"),
    "updated_by_display": _t("最後修改人"),
    "__pick__": _t("選取"),
    # Child Tables Common
    "code": _t("代碼"),
    "note2": _t("備註"),
    # Receiving Address
    "receiving_add": _t("送貨地址"),
    "warehouse_contact_person": _t("收貨窗口"),
    "tel": _t("電話"),
    "km": _t("距離(km)"),
    "is_active": _t("啟用"),
    # Contact Person
    "contact_person_name": _t("聯絡人"),
    "phone": _t("電話"),
    "email": _t("Email"),
    "department": _t("部門"),
    "title": _t("職稱"),
    # Sales
    "stuff_name": _t("業務人員"),
    "beginning_date": _t("起始日"),
    "begining_date": _t("起始日"),
    "end_date": _t("結束日"),
    # Customer Bank
    "customer_bank_num": _t("銀行代號"),
    "customer_bank_name": _t("銀行名稱"),
    "customer_account_name": _t("戶名"),
    "customer_bank_code": _t("銀行帳號"),
}


def current_user_id() -> int:
    """取得目前登入使用者 ID；若 session 沒有 user_id，才退回 1。"""
    try:
        return int(st.session_state.get("user_id") or 1)
    except Exception:
        return 1


def _user_display_sql(alias: str, fallback_prefix: str = "User#") -> str:
    """SQL 片段：使用 stuff_name 優先，沒有則顯示 user_code / User#id。"""
    return (
        f"COALESCE(NULLIF(s_{alias}.stuff_name, ''), "
        f"NULLIF(u_{alias}.user_code, ''), "
        f"CONCAT('{fallback_prefix}', c.{alias}_by_id))"
    )



# =========================================
# Data Loading (Cached)
# =========================================
@st.cache_data(ttl=30)
def load_category(engine_url_key: str) -> pd.DataFrame:
    """載入客戶類型清單"""
    if not table_exists(engine_url_key, "customer_category"):
        return pd.DataFrame(columns=["customer_category_id", "customer_category_name"])

    engine = get_engine()
    if engine is None:
        return pd.DataFrame(columns=["customer_category_id", "customer_category_name"])

    cols = get_table_columns(engine_url_key, "customer_category")
    required = {"customer_category_id", "customer_category_name"}
    if not required.issubset(set(cols)):
        return pd.DataFrame(columns=["customer_category_id", "customer_category_name"])

    return qdf(engine, """
        SELECT customer_category_id, customer_category_name
        FROM customer_category
        ORDER BY customer_category_id
    """)


def get_next_customer_category_code(engine) -> int:
    """取得下一個 customer_category.customer_code"""
    try:
        next_code = exec_scalar(engine, "SELECT COALESCE(MAX(customer_code), 0) + 1 FROM customer_category")
        return int(next_code or 1)
    except Exception:
        return 1


def create_customer_category(engine, category_name: str) -> Tuple[bool, str, Optional[int]]:
    """新增客戶類型，回傳 (成功, 訊息, 新ID)"""
    category_name = (category_name or "").strip()
    if not category_name:
        return False, _t("客戶類型名稱不可空白"), None

    if len(category_name) > 32:
        return False, _t("客戶類型名稱不可超過 32 字"), None

    try:
        existing = exec_scalar(
            engine,
            "SELECT customer_category_id FROM customer_category WHERE customer_category_name = :n LIMIT 1",
            {"n": category_name},
        )
        if existing:
            return False, _t("此客戶類型已存在"), int(existing)

        next_code = get_next_customer_category_code(engine)
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO customer_category (customer_code, customer_category_name)
                    VALUES (:code, :name)
                """),
                {"code": next_code, "name": category_name},
            )
            new_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        load_category.clear()
        return True, f"{_t('已新增客戶類型：')}{category_name}", int(new_id) if new_id else None
    except Exception as e:
        return False, f"{_t('新增失敗：')}{e}", None


@st.cache_data(ttl=30)
def load_staff(engine_url_key: str) -> pd.DataFrame:
    """載入員工(業務)清單"""
    if not table_exists(engine_url_key, "stuff"):
        return pd.DataFrame(columns=["stuff_id", "stuff_name"])

    engine = get_engine()
    if engine is None:
        return pd.DataFrame(columns=["stuff_id", "stuff_name"])

    cols = get_table_columns(engine_url_key, "stuff")
    required = {"stuff_id", "stuff_name"}
    if not required.issubset(set(cols)):
        return pd.DataFrame(columns=["stuff_id", "stuff_name"])

    return qdf(engine, """
        SELECT stuff_id, stuff_name
        FROM stuff
        ORDER BY stuff_name
    """)


# =========================================
# Business Logic
# =========================================
def generate_customer_code(engine) -> str:
    """產生下一組客戶代碼 (C0001...)"""
    mx = exec_scalar(engine, "SELECT MAX(customer_code) FROM customer WHERE customer_code LIKE 'C%'")
    if mx is None or str(mx).strip() == "":
        return "C0001"

    s_val = str(mx).strip()
    digits = "".join([ch for ch in s_val if ch.isdigit()])
    try:
        num = int(digits or "0")
    except ValueError:
        num = 0
    return f"C{num + 1:04d}"


def insert_record(engine, table: str, data: dict) -> Optional[int]:
    auth.require_edit(PAGE_KEY)
    """通用新增函式，自動處理時間戳記與建檔人。

    注意：新增時不自動寫入 updated_by / updated_by_id，
    讓「最後修改人」在尚未修改前保持空白。
    """
    engine_url_key = get_engine_url(engine)
    cols = get_table_columns(engine_url_key, table)
    if not cols:
        raise RuntimeError(f"找不到 {table} 欄位")

    clean_data = {k: v for k, v in data.items() if k in cols}

    uid = current_user_id()
    if "created_by_id" in cols and "created_by_id" not in clean_data:
        clean_data["created_by_id"] = uid
    if "created_by" in cols and "created_by" not in clean_data:
        clean_data["created_by"] = uid

    # 自動填入時間欄位；新增時 create/update 時間可以都記錄，
    # 但最後修改人仍空白，畫面就能判斷「尚未修改」。
    time_cols = []
    for col in ["create_at", "created_at", "update_at", "updated_at"]:
        if col in cols and col not in clean_data:
            time_cols.append(col)

    insert_cols = []
    value_placeholders = []
    params = {}

    for col in cols:
        if col in clean_data:
            insert_cols.append(col)
            value_placeholders.append(f":{col}")
            params[col] = na_to_none(clean_data[col])

    for col in time_cols:
        insert_cols.append(col)
        value_placeholders.append("NOW()")

    if not insert_cols:
        raise RuntimeError("沒有可新增的欄位")

    sql = f"INSERT INTO {table} ({', '.join(insert_cols)}) VALUES ({', '.join(value_placeholders)})"

    with engine.begin() as conn:
        res = conn.execute(text(sql), params)
        try:
            return int(res.lastrowid)
        except Exception:
            return None


def update_record(engine, table: str, pk_info: Tuple[str, int], data: dict) -> None:
    auth.require_edit(PAGE_KEY)
    """通用更新函式，自動更新時間戳記與最後修改人"""
    engine_url_key = get_engine_url(engine)
    cols = get_table_columns(engine_url_key, table)
    pk_col, pk_val = pk_info

    if not cols or pk_col not in cols:
        raise RuntimeError(f"{table} 欄位或 Primary Key 設定不正確")

    clean_data = {k: v for k, v in data.items() if k in cols and k != pk_col}

    uid = current_user_id()
    if "updated_by_id" in cols:
        clean_data["updated_by_id"] = uid
    if "updated_by" in cols:
        clean_data["updated_by"] = uid

    set_clauses = []
    params = {}

    for k, v in clean_data.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = na_to_none(v)

    for col in ["update_at", "updated_at"]:
        if col in cols:
            set_clauses.append(f"{col} = NOW()")

    if not set_clauses:
        return

    params["__pk__"] = pk_val
    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {pk_col} = :__pk__"
    exec_sql(engine, sql, params)


@st.cache_data(ttl=60)
def load_customer_list(engine_url_key: str, filters: dict) -> pd.DataFrame:
    """讀取客戶列表 (支援搜尋過濾)，並在最右側顯示建檔人 / 最後修改人。"""
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()

    cols = get_table_columns(engine_url_key, "customer")
    if "customer_id" not in cols:
        raise RuntimeError("customer 表缺少 customer_id")

    target_cols = [
        "customer_id", "customer_code", "customer_name", "customer_shortname",
        "customer_phone", "boss_name", "checkout_day", "payment_term", "note",
        "customer_category"
    ]
    pick_cols = [c for c in target_cols if c in cols]

    select_parts = [f"c.{c}" for c in pick_cols]
    sales_expr = build_customer_sales_expr(engine_url_key)
    select_parts.append(f"{sales_expr} AS our_sales_name")
    joins = []

    if "created_by_id" in cols:
        select_parts.append(
            "COALESCE(NULLIF(s_created.stuff_name, ''), "
            "NULLIF(u_created.user_code, ''), "
            "CONCAT('User#', c.created_by_id)) AS created_by_display"
        )
        joins.append("LEFT JOIN `user` u_created ON u_created.user_id = c.created_by_id")
        joins.append("LEFT JOIN stuff s_created ON s_created.stuff_id = u_created.stuff_id")
    else:
        select_parts.append("'' AS created_by_display")

    if "updated_by_id" in cols:
        if ("create_at" in cols and "update_at" in cols):
            not_modified_condition = (
                "c.updated_by_id IS NULL OR "
                "(c.created_by_id = c.updated_by_id "
                "AND c.create_at IS NOT NULL AND c.update_at IS NOT NULL "
                "AND ABS(TIMESTAMPDIFF(SECOND, c.create_at, c.update_at)) <= 2)"
            )
        elif ("created_at" in cols and "updated_at" in cols):
            not_modified_condition = (
                "c.updated_by_id IS NULL OR "
                "(c.created_by_id = c.updated_by_id "
                "AND c.created_at IS NOT NULL AND c.updated_at IS NOT NULL "
                "AND ABS(TIMESTAMPDIFF(SECOND, c.created_at, c.updated_at)) <= 2)"
            )
        else:
            not_modified_condition = "c.updated_by_id IS NULL"

        select_parts.append(
            "CASE WHEN " + not_modified_condition + " THEN '' ELSE "
            "COALESCE(NULLIF(s_updated.stuff_name, ''), "
            "NULLIF(u_updated.user_code, ''), "
            "CONCAT('User#', c.updated_by_id)) END AS updated_by_display"
        )
        joins.append("LEFT JOIN `user` u_updated ON u_updated.user_id = c.updated_by_id")
        joins.append("LEFT JOIN stuff s_updated ON s_updated.stuff_id = u_updated.stuff_id")
    else:
        select_parts.append("'' AS updated_by_display")

    sql = f"""
        SELECT {', '.join(select_parts)}
        FROM customer c
        {' '.join(joins)}
        WHERE 1=1
    """
    params = {}

    kw = (filters.get("kw") or "").strip()
    if kw:
        sql += " AND (c.customer_code LIKE :kw OR c.customer_name LIKE :kw OR c.customer_shortname LIKE :kw)"
        params["kw"] = f"%{kw}%"

    if filters.get("category_id") is not None and "customer_category" in cols:
        sql += " AND c.customer_category = :cat"
        params["cat"] = int(filters["category_id"])

    if filters.get("sales_id") is not None:
        sql += f" AND ({sales_expr}) = :sid"
        params["sid"] = int(filters["sales_id"])

    sql += " ORDER BY c.customer_code"
    return qdf(engine, sql, params)


def load_customer_detail(engine, customer_id: int) -> dict:
    """讀取單一客戶詳細資料"""
    df = qdf(engine, "SELECT * FROM customer WHERE customer_id = :cid", {"cid": customer_id})
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def get_current_customer_sales_id(engine, customer_id: int) -> Optional[int]:
    """
    取得客戶目前負責業務。

    設計原則：
    - C03 主資料不再寫入 customer.our_sales_name。
    - 負責業務以 customer_our_sales 分頁/子表為主。
    - 若舊資料庫尚未建立 customer_our_sales，才退回 customer.our_sales_name。
    """
    engine_url_key = get_engine_url(engine)

    if table_exists(engine_url_key, "customer_our_sales"):
        os_cols = get_table_columns(engine_url_key, "customer_our_sales")
        if {"customer_id", "stuff_name"}.issubset(set(os_cols)):
            pk_col = get_pk_column(engine_url_key, "customer_our_sales") or "customer_our_sales_id"
            begin_col = "beginning_date" if "beginning_date" in os_cols else ("begining_date" if "begining_date" in os_cols else None)

            order_parts = []
            if "end_date" in os_cols:
                order_parts.append("CASE WHEN end_date IS NULL OR end_date >= CURDATE() THEN 0 ELSE 1 END")
            if begin_col:
                order_parts.append(f"COALESCE({begin_col}, '1000-01-01') DESC")
            if pk_col in os_cols:
                order_parts.append(f"{pk_col} DESC")

            order_sql = ", ".join(order_parts) if order_parts else "stuff_name"
            sid = exec_scalar(
                engine,
                f"""
                SELECT stuff_name
                FROM customer_our_sales
                WHERE customer_id = :cid
                ORDER BY {order_sql}
                LIMIT 1
                """,
                {"cid": int(customer_id)},
            )
            return to_int_or_none(sid)

    # 兼容舊欄位：只有在沒有 customer_our_sales 可用時才讀母表。
    customer_cols = get_table_columns(engine_url_key, "customer")
    if "our_sales_name" in customer_cols:
        sid = exec_scalar(engine, "SELECT our_sales_name FROM customer WHERE customer_id = :cid", {"cid": int(customer_id)})
        return to_int_or_none(sid)

    return None


def build_customer_sales_expr(engine_url_key: str) -> str:
    """回傳 SQL 片段：從 customer_our_sales 取得目前負責業務，必要時退回舊欄位。"""
    customer_cols = get_table_columns(engine_url_key, "customer")
    fallback_expr = "c.our_sales_name" if "our_sales_name" in customer_cols else "NULL"

    if not table_exists(engine_url_key, "customer_our_sales"):
        return fallback_expr

    os_cols = get_table_columns(engine_url_key, "customer_our_sales")
    if not {"customer_id", "stuff_name"}.issubset(set(os_cols)):
        return fallback_expr

    pk_col = get_pk_column(engine_url_key, "customer_our_sales") or "customer_our_sales_id"
    begin_col = "beginning_date" if "beginning_date" in os_cols else ("begining_date" if "begining_date" in os_cols else None)

    order_parts = []
    if "end_date" in os_cols:
        order_parts.append("CASE WHEN cos.end_date IS NULL OR cos.end_date >= CURDATE() THEN 0 ELSE 1 END")
    if begin_col:
        order_parts.append(f"COALESCE(cos.{begin_col}, '1000-01-01') DESC")
    if pk_col in os_cols:
        order_parts.append(f"cos.{pk_col} DESC")

    order_sql = ", ".join(order_parts) if order_parts else "cos.stuff_name"
    return f"COALESCE((SELECT cos.stuff_name FROM customer_our_sales cos WHERE cos.customer_id = c.customer_id ORDER BY {order_sql} LIMIT 1), {fallback_expr})"


def load_child_table(
    engine,
    table: str,
    customer_id: int,
    wanted_cols: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, Optional[str]]:
    """讀取子表資料"""
    engine_url_key = get_engine_url(engine)
    if not table_exists(engine_url_key, table):
        return pd.DataFrame(), None

    cols = get_table_columns(engine_url_key, table)
    pk = get_pk_column(engine_url_key, table)

    if "customer_id" not in cols:
        return pd.DataFrame(), pk

    if wanted_cols:
        select_cols = []
        if pk and pk in cols:
            select_cols.append(pk)
        select_cols.append("customer_id")
        for c in wanted_cols:
            if c in cols and c not in select_cols:
                select_cols.append(c)
    else:
        select_cols = cols[:]

    sql = f"SELECT {', '.join(select_cols)} FROM {table} WHERE customer_id = :cid"
    df = qdf(engine, sql, {"cid": customer_id})

    if pk and pk in df.columns:
        df = df.set_index(pk, drop=True)
    return df, pk


def find_code_column(engine, table: str) -> Optional[str]:
    """尋找代碼欄位名稱 (code 或 xxx_code)"""
    engine_url_key = get_engine_url(engine)
    cols = get_table_columns(engine_url_key, table)
    for c in cols:
        if c.lower() == "code":
            return c
    for c in cols:
        if c.lower().endswith("_code"):
            return c
    return None


def generate_child_code(engine, table: str, code_col: str, prefix: str = "", width: int = 4) -> str:
    """產生子表代碼"""
    sql = f"SELECT MAX({code_col}) FROM {table} WHERE {code_col} IS NOT NULL"
    mx = exec_scalar(engine, sql)

    if mx is None or str(mx).strip() == "":
        base = 1
        return f"{prefix}{base:0{width}d}" if prefix else f"{base:0{width}d}"

    s_val = str(mx).strip()
    digits = "".join([ch for ch in s_val if ch.isdigit()])
    try:
        num = int(digits or "0") + 1
    except ValueError:
        num = 1

    use_prefix = prefix if prefix else "".join([ch for ch in s_val if ch.isalpha()])
    return f"{use_prefix}{num:0{width}d}" if use_prefix else f"{num:0{width}d}"


def delete_record(engine, table: str, pk_col: str, pk_val: int) -> None:
    auth.require_delete(PAGE_KEY)
    """刪除資料"""
    sql = f"DELETE FROM {table} WHERE {pk_col} = :id"
    exec_sql(engine, sql, {"id": int(pk_val)})


# =========================================
# State Management
# =========================================
def init_session_state():
    """初始化 Session State"""
    defaults = {
        "selected_customer_id": None,
        "loaded_customer_id_for_form": None,
        "main_form_widget_nonce": 0,
        "customer_list_editor_nonce": 0,
        "f_customer_id": None,
        "f_customer_name": "",
        "f_customer_shortname": "",
        "f_customer_phone": "",
        "f_customer_email": "",
        "f_customer_tax_id": "",
        "f_boss_name": "",
        "f_boss_phone": "",
        "f_customer_address": "",
        "f_checkout_day": 0,
        "f_payment_term": 0,
        "f_note": "",
        "f_customer_category": None,
        "pick_receiving_pk": None,
        "pick_contact_pk": None,
        "pick_os_pk": None
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)



def normalize_payment_term(value) -> Optional[int]:
    """
    payment_term 在 DB 中是 int（付款天數）。
    - None/"" -> None
    - 數字/可轉 int -> int
    - '60天'/'NET60' -> 60
    - '匯款/轉帳/現金/支票' 等付款方式文字 -> 0（兼容舊習慣，避免直接炸）
    """
    if value is None:
        return None
    if isinstance(value, (int,)):
        return int(value)
    # Streamlit number_input 有時回傳 float
    if isinstance(value, float):
        return int(value)
    s = str(value).strip()
    if s == "":
        return None

    # 抽出字串中的數字（例如 60天 / NET60）
    m = re.search(r"(\d+)", s)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass

    # 常見付款方式文字：當成 0 天（你要更精準就應新增 payment_method 欄位）
    payment_words = {"匯款", "轉帳", "現金", "支票", "刷卡", "月結", "到付"}
    if any(w in s for w in payment_words):
        return 0

    raise ValueError(f"付款天數(payment_term) 必須是整數天數，但收到：{s}")


def fill_form_from_db(row: Optional[dict]):
    """將資料庫取出的資料填入表單 State"""
    row = row or {}
    st.session_state["f_customer_id"] = row.get("customer_id")
    st.session_state["f_customer_name"] = row.get("customer_name") or ""
    st.session_state["f_customer_shortname"] = row.get("customer_shortname") or ""
    st.session_state["f_customer_phone"] = row.get("customer_phone") or ""
    st.session_state["f_customer_email"] = row.get("customer_email") or ""
    st.session_state["f_customer_tax_id"] = row.get("customer_tax_id") or ""
    st.session_state["f_boss_name"] = row.get("boss_name") or ""
    st.session_state["f_boss_phone"] = row.get("boss_phone") or ""
    st.session_state["f_customer_address"] = row.get("customer_address") or ""

    try:
        st.session_state["f_checkout_day"] = int(row.get("checkout_day") or 0)
    except (ValueError, TypeError):
        st.session_state["f_checkout_day"] = 0

    try:
        st.session_state["f_payment_term"] = int(row.get("payment_term") or 0)
    except (ValueError, TypeError):
        st.session_state["f_payment_term"] = 0

    st.session_state["f_note"] = row.get("note") or ""
    st.session_state["f_customer_category"] = to_int_or_none(row.get("customer_category"))


def reset_form_state():
    """重置表單為新增模式（注意：請只在按鈕 on_click callback 內呼叫）"""
    # 文字欄位 -> ""；數字欄位 -> 0；選項欄位/PK -> None
    defaults = {
        "f_customer_id": None,
        "selected_customer_id": None,
        "loaded_customer_id_for_form": None,
        "main_form_widget_nonce": int(st.session_state.get("main_form_widget_nonce", 0)) + 1,
        "f_customer_name": "",
        "f_customer_shortname": "",
        "f_customer_phone": "",
        "f_customer_email": "",
        "f_customer_tax_id": "",
        "f_boss_name": "",
        "f_boss_phone": "",
        "f_customer_address": "",
        "f_checkout_day": 0,
        "f_payment_term": 0,
        "f_note": "",
        "f_customer_category": None,
        "pick_receiving_pk": None,
        "pick_contact_pk": None,
        "pick_os_pk": None,
    }
    for k, v in defaults.items():
        st.session_state[k] = v
    st.session_state["f_checkout_day"] = 0
    str_fields = [
        "f_customer_name", "f_customer_shortname", "f_customer_phone",
        "f_customer_email", "f_customer_tax_id", "f_boss_name",
        "f_boss_phone", "f_customer_address", "f_note"
    ]
    for k in str_fields:
        st.session_state[k] = ""

    # 讓上方客戶清單 data_editor 換 key 重建，勾選格才會真的取消。
    # 只清 selected_customer_id 不夠，因為 data_editor 會保存自己的勾選狀態。
    st.session_state["customer_list_editor_nonce"] = int(st.session_state.get("customer_list_editor_nonce", 0)) + 1


# =========================================
# UI Components
# =========================================

def sanitize_numeric_form_state():
    try:
        st.session_state["f_checkout_day"] = int(st.session_state.get("f_checkout_day") or 0)
    except (ValueError, TypeError):
        st.session_state["f_checkout_day"] = 0

    try:
        st.session_state["f_payment_term"] = int(st.session_state.get("f_payment_term") or 0)
    except (ValueError, TypeError):
        st.session_state["f_payment_term"] = 0

def render_child_picker(df: pd.DataFrame, label_func, key: str):
    """渲染子表選擇下拉選單"""
    if df.empty:
        return None

    valid_indices = [int(i) for i in df.index.tolist() if to_int_or_none(i) is not None]
    options = [None] + valid_indices

    def format_option(x):
        if x is None:
            return _t("(新增模式)")
        try:
            row = df.loc[int(x)]
            return label_func(int(x), row)
        except KeyError:
            return str(x)

    return st.selectbox(_t("選一筆資料來修改（或選新增模式）"), options=options, format_func=format_option, key=key)


def render_readonly_table(df: pd.DataFrame, col_map: Optional[dict] = None):
    """渲染唯讀表格"""
    if df.empty:
        st.info(_t("目前沒有資料。"))
        return

    hide_cols = {"customer_id", "create_at", "created_at", "update_at", "updated_at"}
    visible_cols = [c for c in df.columns if c not in hide_cols]
    view_df = df[visible_cols].copy()

    if col_map:
        view_df = view_df.rename(columns=col_map)

    st.dataframe(view_df, use_container_width=True, hide_index=True)


# =========================================
# Main Application
# =========================================
def main():
    sanitize_numeric_form_state()
    st.subheader(_t("C03 客戶主檔（表單模式）"))
    st.session_state.setdefault("c03_top_height", 260)
    st.markdown(
        """
        <style>
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
          min-height: 1.55rem !important; padding-top: .1rem !important; padding-bottom: .1rem !important;
        }
        [data-testid="stTextInput"], [data-testid="stNumberInput"], [data-testid="stSelectbox"] { margin-bottom: 0 !important; }
        hr { margin: .25rem 0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    engine = get_engine()
    if engine is None:
        return

    engine_url_key = get_engine_url(engine)

    if not table_exists(engine_url_key, "customer"):
        st.error(_t("找不到 customer 表，請確認資料庫結構。"))
        return

    init_session_state()

    # 載入選項資料
    cat_df = load_category(engine_url_key)
    staff_df = load_staff(engine_url_key)

    cat_map = {}
    if not cat_df.empty:
        cat_map = {int(r["customer_category_id"]): r["customer_category_name"] for _, r in cat_df.iterrows()}

    staff_map = {}
    staff_name_to_id = {}
    if not staff_df.empty:
        staff_map = {int(r["stuff_id"]): r["stuff_name"] for _, r in staff_df.iterrows()}
        staff_name_to_id = {v: k for k, v in staff_map.items()}

    # --- 搜尋 / 分頁控制區塊 ---
    col_search_1, col_search_2, col_search_3, col_prev, col_page_size, col_next = st.columns([2.6, 1.5, 1.5, 0.9, 1.0, 0.9], vertical_alignment="bottom")
    with col_search_1:
        search_kw = st.text_input(_t("搜尋（代碼/名稱/簡稱）"), placeholder=_t("例如：C0001 / 凱勝"), key="search_kw")
    with col_search_2:
        cat_options = [None] + ([] if cat_df.empty else cat_df["customer_category_id"].astype(int).tolist())
        search_cat_id = st.selectbox(
            _t("客戶類型"),
            options=cat_options,
            format_func=lambda x: _t("(全部)") if x is None else f"{int(x):02d} - {cat_map.get(int(x), '')}",
            key="search_category"
        )
    with col_search_3:
        staff_options = [None] + ([] if staff_df.empty else staff_df["stuff_id"].astype(int).tolist())
        search_sales_id = st.selectbox(
            _t("負責業務"),
            options=staff_options,
            format_func=lambda x: _t("(全部)") if x is None else staff_map.get(int(x), str(x)),
            key="search_sales"
        )
    with col_prev:
        prev_placeholder = st.empty()
    with col_page_size:
        page_size = st.selectbox(
            _t("每頁筆數"),
            options=[10, 20, 30, 50, 100],
            index=[10, 20, 30, 50, 100].index(int(st.session_state.get("c03_page_size", 10))) if int(st.session_state.get("c03_page_size", 10)) in [10, 20, 30, 50, 100] else 0,
            key="c03_page_size_select"
        )
        st.session_state["c03_page_size"] = int(page_size)
    with col_next:
        next_placeholder = st.empty()

    # --- 列表區塊 ---
    st.markdown(f"#### {_t('客戶清單')}")
    df_list = load_customer_list(engine_url_key, {"kw": search_kw, "category_id": search_cat_id, "sales_id": search_sales_id})

    filter_sig = f"{search_kw.strip()}|{search_cat_id}|{search_sales_id}|{st.session_state['c03_page_size']}"
    if st.session_state.get("c03_filter_sig") != filter_sig:
        st.session_state["c03_filter_sig"] = filter_sig
        st.session_state["c03_page"] = 1

    total_rows = len(df_list)
    page_size = int(st.session_state.get("c03_page_size", 10))
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = max(1, min(int(st.session_state.get("c03_page", 1)), total_pages))
    st.session_state["c03_page"] = page

    with prev_placeholder:
        if st.button(_t("上一頁"), use_container_width=True, disabled=(page <= 1), key="c03_prev_page"):
            st.session_state["c03_page"] = max(1, page - 1)
            st.rerun()

    with next_placeholder:
        if st.button(_t("下一頁"), use_container_width=True, disabled=(page >= total_pages), key="c03_next_page"):
            st.session_state["c03_page"] = min(total_pages, page + 1)
            st.rerun()

    if not df_list.empty:
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_list = df_list.iloc[start_idx:end_idx].copy()

    if df_list.empty:
        st.info(_t("查無資料。你可以直接在下方新增客戶。"))

    # 顯示欄位加工
    if not df_list.empty:
        if "customer_category" in df_list.columns:
            df_list["customer_category_name"] = df_list["customer_category"].apply(
                lambda x: cat_map.get(to_int_or_none(x), None)
            )
        if "our_sales_name" in df_list.columns:
            df_list["our_sales_display"] = df_list["our_sales_name"].apply(
                lambda x: staff_map.get(to_int_or_none(x), None)
            )

    display_cols = [c for c in [
        "customer_code", "customer_name", "customer_shortname",
        "customer_category_name", "our_sales_display", "customer_phone",
        "boss_name", "checkout_day", "payment_term", "note",
        # 稽核欄位固定放在母表最右邊：倒數第二欄與倒數第一欄
        "created_by_display", "updated_by_display"
    ] if (not df_list.empty and c in df_list.columns)]

    if df_list.empty:
        grid_df = pd.DataFrame(columns=["__pick__"])
    else:
        grid_df = df_list[["customer_id"] + display_cols].copy().set_index("customer_id", drop=True)
        grid_df.insert(0, "__pick__", False)

    grid_df = grid_df.rename(columns={c: COLUMN_MAP.get(c, c) for c in grid_df.columns})

    edited_grid = st.data_editor(
        grid_df,
        use_container_width=True,
        height=int(st.session_state["c03_top_height"]),
        hide_index=True,
        num_rows="fixed",
        key=f"customer_list_editor_{st.session_state.get('customer_list_editor_nonce', 0)}",
        column_config={COLUMN_MAP["__pick__"]: st.column_config.CheckboxColumn(COLUMN_MAP["__pick__"], default=False)}
    )

    # 母表重新整理：清掉快取與目前勾選，並讓 data_editor 換 key 重建，避免吃到舊狀態。
    refresh_col, _refresh_spacer = st.columns([1.2, 6.8])
    with refresh_col:
        if st.button(f"🔄 {_t('重新整理')}", use_container_width=True, key="c03_refresh_master_table"):
            st.cache_data.clear()
            reset_form_state()
            st.session_state["selected_customer_id"] = None
            st.session_state["pick_receiving_pk"] = None
            st.session_state["picked_receiving_pk"] = None
            st.session_state["pick_contact_pk"] = None
            st.session_state["pick_os_pk"] = None
            st.session_state["customer_bank_picker_reset_token"] = int(st.session_state.get("customer_bank_picker_reset_token", 0)) + 1
            st.rerun()

    prev_selected = st.session_state.get("selected_customer_id")
    picked_ids: List[int] = []

    if not edited_grid.empty:
        for idx, row in edited_grid.iterrows():
            val = row.get(COLUMN_MAP["__pick__"], False)
            if bool(val):
                try:
                    picked_ids.append(int(idx))
                except Exception:
                    pass

    if len(picked_ids) > 1:
        st.warning(f"{_t('你勾了 ')}{len(picked_ids)}{_t(' 筆，我只會取第一筆：')}{picked_ids[0]}")
    if picked_ids:
        # 使用者真的在母表勾選某筆時，才切換 selected_customer_id。
        # Streamlit data_editor 在其他 widget 觸發 rerun 時，有時會短暫回傳未勾選狀態；
        # 若這時直接 reset_form_state()，下方表單就會被重新載入，造成下拉選單看起來改不了。
        st.session_state["selected_customer_id"] = picked_ids[0]
    else:
        # 不要因為 data_editor 一次 rerun 沒回傳勾選，就立刻清掉正在編輯的客戶。
        # 若要回新增模式，請使用下方「回新增模式」按鈕，狀態會比較穩。
        if prev_selected is not None:
            st.session_state["selected_customer_id"] = prev_selected

    selected_cid = st.session_state.get("selected_customer_id")
    _c03_splitter_result = render_vertical_splitter(
        int(st.session_state["c03_top_height"]),
        key="c03_vertical_splitter_control",
        min_top=150,
        max_top=430,
    )
    if isinstance(_c03_splitter_result, dict) and "top_height" in _c03_splitter_result:
        _c03_next_height = max(150, min(430, int(_c03_splitter_result["top_height"])))
        if _c03_next_height != int(st.session_state["c03_top_height"]):
            st.session_state["c03_top_height"] = _c03_next_height
            st.rerun()
    st.markdown("---")

    # --- 詳細資料區塊 ---
    st.markdown(f"#### {_t('資訊區')}")

    current_customer_data = {}
    if selected_cid is None:
        st.info(_t("目前是新增模式。請在上方清單勾選一個客戶，或直接填寫下方資料新增。"))
    else:
        current_customer_data = load_customer_detail(engine, int(selected_cid))
        if not current_customer_data:
            st.warning(_t("找不到該客戶資料，可能已被刪除。"))
            selected_cid = None
            st.session_state["loaded_customer_id_for_form"] = None
        else:
            c_code = current_customer_data.get("customer_code", "")
            c_name = current_customer_data.get("customer_name", "")
            c_short = current_customer_data.get("customer_shortname", "")
            c_cat = cat_map.get(to_int_or_none(current_customer_data.get("customer_category")), _t("未指定"))
            current_sales_id = get_current_customer_sales_id(engine, int(selected_cid))
            c_sales = staff_map.get(current_sales_id, _t("未指定"))

            st.write(f"**{c_code}** ｜ **{c_name}** （{c_short}）")
            st.caption(f"{_t('客戶類型')}：{c_cat} ｜ {_t('負責業務')}：{c_sales}")

            # 只在「剛選到這個客戶」時，才把 DB 資料灌進表單。
            # 若每次 rerun 都 fill_form_from_db()，Streamlit selectbox 一改值就會被 DB 原值覆蓋，
            # 造成修改模式下「客戶類型」點選後立刻跳回原類型。
            if st.session_state.get("loaded_customer_id_for_form") != int(selected_cid):
                fill_form_from_db(current_customer_data)
                st.session_state["loaded_customer_id_for_form"] = int(selected_cid)
                # 換一個 widget key，讓這次選到的客戶使用 DB 初始值建立表單；
                # 之後同一筆客戶編輯期間不再更換 key，使用者選的值才不會被吃掉。
                st.session_state["main_form_widget_nonce"] = int(st.session_state.get("main_form_widget_nonce", 0)) + 1

    st.markdown("---")
    tabs = st.tabs([_t("主要資料"), _t("送貨地址"), _t("客戶聯絡人"), _t("負責業務"), _t("客戶銀行資料")])

    # --- Tab 1: 主要資料 ---
    with tabs[0]:
        is_new = st.session_state.get("f_customer_id") is None
        auto_code = generate_customer_code(engine) if is_new else (current_customer_data.get("customer_code", "") or "")

        st.text_input(_t("客戶代碼（系統自動）"), value=str(auto_code), disabled=True)

        r1_c1, r1_c2, r1_c3 = st.columns([2, 2, 2])
        with r1_c1:
            st.text_input(_t("客戶名稱"), key="f_customer_name")
        with r1_c2:
            st.text_input(_t("客戶簡稱"), key="f_customer_shortname")
        with r1_c3:
            st.text_input(_t("電話"), key="f_customer_phone")

        r2_c1, r2_c2, r2_c3 = st.columns([2, 2, 2])
        with r2_c1:
            st.text_input(_t("Email"), key="f_customer_email")
        with r2_c2:
            st.text_input(_t("統編/稅號"), key="f_customer_tax_id")
        with r2_c3:
            st.text_input(_t("負責人"), key="f_boss_name")

        r3_c1, r3_c2, r3_c3 = st.columns([2, 2, 2])
        with r3_c1:
            st.text_input(_t("負責人電話"), key="f_boss_phone")
        with r3_c2:
            st.number_input(_t("結帳日"), min_value=0, max_value=31, key="f_checkout_day")
        with r3_c3:
            st.markdown("<div style='height: 0.45rem;'></div>", unsafe_allow_html=True)
            with st.popover(f"➕ {_t('新增客戶類型')}", use_container_width=True):
                st.markdown(f"##### {_t('新增客戶類型')}")
                st.caption(_t("新增後會自動回寫到客戶類型下拉選單。"))
                new_cat_name = st.text_input(_t("客戶類型名稱"), key="new_customer_category_name")
                if st.button(_t("儲存客戶類型"), key="btn_save_customer_category", use_container_width=True):
                    ok, msg, new_cat_id = create_customer_category(engine, new_cat_name)
                    if ok:
                        st.session_state["f_customer_category"] = new_cat_id
                        st.session_state["main_form_widget_nonce"] = int(st.session_state.get("main_form_widget_nonce", 0)) + 1
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        r4_c1, r4_c2 = st.columns([2, 2])
        with r4_c1:
            st.number_input(_t("付款天數"), min_value=0, max_value=365, step=1, key="f_payment_term")
        with r4_c2:
            # 注意：這裡不要直接用 key="f_customer_category"。
            # 原因是修改模式下，表單 state 與 widget state 混在一起時，
            # Streamlit rerun 很容易把 DB 原值重新套回去，造成下拉選單跳回舊值。
            current_cat_id = to_int_or_none(st.session_state.get("f_customer_category"))
            if current_cat_id not in cat_options:
                current_cat_id = None
            cat_index = cat_options.index(current_cat_id) if current_cat_id in cat_options else 0
            cat_widget_key = f"w_f_customer_category_{st.session_state.get('selected_customer_id') or 'new'}_{st.session_state.get('main_form_widget_nonce', 0)}"
            selected_cat_id = st.selectbox(
                _t("客戶類型"),
                options=cat_options,
                index=cat_index,
                format_func=lambda x: _t("(未指定)") if x is None else f"{int(x):02d} - {cat_map.get(int(x), '')}",
                key=cat_widget_key
            )
            st.session_state["f_customer_category"] = selected_cat_id

        st.text_input(_t("地址"), key="f_customer_address")
        st.text_area(_t("備註"), height=90, key="f_note")

        
        # --- callbacks (避免在 widget instantiate 後修改同名 session_state key) ---
        def _get_existing_customer_code(_cid: int) -> str:
            try:
                with engine.connect() as conn:
                    r = conn.execute(text("SELECT customer_code FROM customer WHERE customer_id = :cid"), {"cid": int(_cid)}).mappings().first()
                return (r.get("customer_code") if r else "") or ""
            except Exception:
                return ""

        def on_save_main():
            try:
                cid = st.session_state.get("f_customer_id")
                is_new_local = cid is None

                customer_code = generate_customer_code(engine) if is_new_local else _get_existing_customer_code(int(cid))
                if not customer_code:
                    # 保底：避免 update 時把代碼寫成空字串
                    customer_code = generate_customer_code(engine) if is_new_local else ""

                payment_term_int = normalize_payment_term(st.session_state.get("f_payment_term"))

                payload = {
                    "customer_code": customer_code,
                    "customer_name": st.session_state.get("f_customer_name"),
                    "customer_shortname": st.session_state.get("f_customer_shortname"),
                    "customer_phone": st.session_state.get("f_customer_phone") or None,
                    "customer_email": st.session_state.get("f_customer_email") or None,
                    "customer_tax_id": st.session_state.get("f_customer_tax_id") or None,
                    "boss_name": st.session_state.get("f_boss_name") or None,
                    "boss_phone": st.session_state.get("f_boss_phone") or None,
                    "customer_address": st.session_state.get("f_customer_address") or None,
                    "checkout_day": int(st.session_state.get("f_checkout_day") or 0),
                    "payment_term": payment_term_int,
                    "note": st.session_state.get("f_note") or None,
                    "customer_category": st.session_state.get("f_customer_category"),
                }

                if cid:
                    update_record(engine, "customer", ("customer_id", int(cid)), payload)
                else:
                    insert_record(engine, "customer", payload)

                reset_form_state()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"{_t('儲存失敗：')}{e}")

        def on_back_new():
            reset_form_state()
            st.rerun()

        btn_col_1, btn_col_2 = st.columns([1, 1])
        with btn_col_1:
            st.button(f"💾 {_t('儲存主資料')}", use_container_width=True, on_click=on_save_main)

        with btn_col_2:
            st.button(f"↩️ {_t('回新增模式')}", use_container_width=True, on_click=on_back_new)

    # --- Tab 2: 送貨地址 ---
    with tabs[1]:
        st.markdown(f"##### {_t('送貨地址')}")
        if selected_cid is None:
            st.info(_t("請先在上方清單勾選一個客戶。"))
        else:
            ra_table = "customer_receiving_add"
            if not table_exists(engine_url_key, ra_table):
                st.warning(f"找不到 {ra_table} 表。")
            else:
                ra_cols = ["code", "receiving_add", "warehouse_contact_person", "tel", "km", "is_active", "note"]
                df_ra, ra_pk = load_child_table(engine, ra_table, int(selected_cid), wanted_cols=ra_cols)

                if ra_pk is None:
                    st.error(_t("此表無 Primary Key。"))
                else:
                    render_readonly_table(df_ra, col_map={c: COLUMN_MAP.get(c, c) for c in df_ra.columns})

                    def label_ra(pid, row):
                        addr = str(row.get("receiving_add", "") or "")
                        who = str(row.get("warehouse_contact_person", "") or "")
                        return f"{pid} ｜ {addr[:30]} ｜ {who[:15]}"

                    pick_state_key = "picked_receiving_pk"
                    st.session_state.setdefault(pick_state_key, None)

                    pick_val = render_child_picker(df_ra, label_ra, key="pick_receiving_pk")
                    if pick_val != st.session_state.get(pick_state_key):
                        st.session_state[pick_state_key] = pick_val

                    if st.button(_t("取消選取（回新增）"), key="btn_clear_ra"):
                        st.session_state[pick_state_key] = None
                        st.rerun()

                    current_pick = st.session_state.get(pick_state_key)
                    ra_row = {}
                    if current_pick is not None and not df_ra.empty:
                        try:
                            ra_row = df_ra.loc[int(current_pick)].to_dict()
                        except KeyError:
                            pass

                    ra_code_col = find_code_column(engine, ra_table)
                    ra_auto_code = ""
                    if ra_code_col:
                        ra_auto_code = generate_child_code(engine, ra_table, ra_code_col, prefix="RA")

                    with st.form(f"form_ra_{selected_cid}", clear_on_submit=False):
                        if ra_code_col:
                            st.text_input(_t("代碼"), value=str(ra_row.get(ra_code_col) or ra_auto_code), disabled=True)

                        st.text_input(_t("送貨地址"), value=str(ra_row.get("receiving_add") or ""), key="f_ra_addr")

                        ra_c1, ra_c2, ra_c3 = st.columns([2, 2, 1])
                        with ra_c1:
                            st.text_input(_t("收貨窗口"), value=str(ra_row.get("warehouse_contact_person") or ""), key="f_ra_person")
                        with ra_c2:
                            st.text_input(_t("電話"), value=str(ra_row.get("tel") or ""), key="f_ra_tel")
                        with ra_c3:
                            st.number_input(
                                _t("距離(km)"),
                                min_value=0.0,
                                step=0.5,
                                value=float(to_float_or_none(ra_row.get("km")) or 0.0),
                                key="f_ra_km"
                            )

                        ra_c4, ra_c5 = st.columns([1, 3])
                        with ra_c4:
                            st.checkbox(_t("啟用"), value=(bool(int(ra_row.get("is_active") or 1)) if ra_row else True), key="f_ra_active")
                        with ra_c5:
                            st.text_area(_t("備註"), height=80, value=str(ra_row.get("note") or ""), key="f_ra_note")

                        ra_b1, ra_b2 = st.columns([1, 1])
                        btn_ra_save = ra_b1.form_submit_button(f"💾 {_t('儲存')}", use_container_width=True)
                        btn_ra_del = ra_b2.form_submit_button(f"🗑️ {_t('刪除')}", use_container_width=True)

                    if btn_ra_save:
                        try:
                            payload = {
                                "customer_id": int(selected_cid),
                                "receiving_add": st.session_state.get("f_ra_addr") or None,
                                "warehouse_contact_person": st.session_state.get("f_ra_person") or None,
                                "tel": st.session_state.get("f_ra_tel") or None,
                                "km": to_float_or_none(st.session_state.get("f_ra_km")),
                                "is_active": 1 if st.session_state.get("f_ra_active") else 0,
                                "note": st.session_state.get("f_ra_note") or None,
                            }
                            if ra_code_col:
                                payload[ra_code_col] = ra_row.get(ra_code_col) if current_pick else ra_auto_code

                            if current_pick is None:
                                insert_record(engine, ra_table, payload)
                            else:
                                update_record(engine, ra_table, (ra_pk, int(current_pick)), payload)

                            st.session_state[pick_state_key] = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"{_t('儲存失敗：')}{e}")

                    if btn_ra_del:
                        if current_pick is None:
                            st.warning(_t("新增模式無法刪除。"))
                        else:
                            try:
                                delete_record(engine, ra_table, ra_pk, int(current_pick))
                                st.session_state[pick_state_key] = None
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"{_t('刪除失敗：')}{e}")

    # --- Tab 3: 聯絡人 ---
    with tabs[2]:
        st.markdown(f"##### {_t('客戶聯絡人')}")
        if selected_cid is None:
            st.info(_t("請先選擇客戶。"))
        else:
            ct_table = "customer_contact"
            if not table_exists(engine_url_key, ct_table):
                st.warning(f"找不到 {ct_table} 表。")
            else:
                ct_code_col = find_code_column(engine, ct_table)
                ct_cols = []
                if ct_code_col:
                    ct_cols.append(ct_code_col)
                ct_cols += ["contact_person_name", "phone", "email", "department", "title", "note"]

                df_ct, ct_pk = load_child_table(engine, ct_table, int(selected_cid), wanted_cols=ct_cols)

                if ct_pk is None:
                    st.error(_t("此表無 Primary Key。"))
                else:
                    render_readonly_table(df_ct, col_map={c: COLUMN_MAP.get(c, c) for c in df_ct.columns})

                    def label_ct(pid, row):
                        nm = str(row.get("contact_person_name", "") or "")
                        ph = str(row.get("phone", "") or "")
                        return f"{pid} ｜ {nm[:20]} ｜ {ph[:15]}"

                    ct_pick_key = "pick_contact_pk"
                    ct_pick_val = render_child_picker(df_ct, label_ct, key=ct_pick_key)

                    sp_prefix = f"ct_{int(selected_cid)}"
                    ct_keys = {
                        "last": f"{sp_prefix}_last",
                        "code": f"{sp_prefix}_code",
                        "name": f"{sp_prefix}_name",
                        "phone": f"{sp_prefix}_phone",
                        "email": f"{sp_prefix}_email",
                        "dept": f"{sp_prefix}_dept",
                        "title": f"{sp_prefix}_title",
                        "note": f"{sp_prefix}_note"
                    }
                    for k in ct_keys.values():
                        st.session_state.setdefault(k, None)

                    ct_row = {}
                    if ct_pick_val is not None and not df_ct.empty:
                        try:
                            ct_row = df_ct.loc[int(ct_pick_val)].to_dict()
                        except Exception:
                            pass

                    if st.session_state[ct_keys["last"]] != ct_pick_val:
                        if ct_pick_val is None:
                            st.session_state[ct_keys["code"]] = generate_child_code(engine, ct_table, ct_code_col) if ct_code_col else ""
                            st.session_state[ct_keys["name"]] = ""
                            st.session_state[ct_keys["phone"]] = ""
                            st.session_state[ct_keys["email"]] = ""
                            st.session_state[ct_keys["dept"]] = ""
                            st.session_state[ct_keys["title"]] = ""
                            st.session_state[ct_keys["note"]] = ""
                        else:
                            if ct_code_col:
                                st.session_state[ct_keys["code"]] = str(ct_row.get(ct_code_col) or "")
                            st.session_state[ct_keys["name"]] = str(ct_row.get("contact_person_name") or "")
                            st.session_state[ct_keys["phone"]] = str(ct_row.get("phone") or "")
                            st.session_state[ct_keys["email"]] = str(ct_row.get("email") or "")
                            st.session_state[ct_keys["dept"]] = str(ct_row.get("department") or "")
                            st.session_state[ct_keys["title"]] = str(ct_row.get("title") or "")
                            st.session_state[ct_keys["note"]] = str(ct_row.get("note") or "")
                        st.session_state[ct_keys["last"]] = ct_pick_val

                    if st.button(_t("取消選取"), key="btn_clear_ct"):
                        st.session_state[ct_pick_key] = None
                        st.session_state[ct_keys["last"]] = None
                        st.rerun()

                    with st.form(f"form_ct_{selected_cid}", clear_on_submit=False):
                        if ct_code_col:
                            st.text_input(_t("代碼"), key=ct_keys["code"], disabled=True)
                        c1, c2 = st.columns(2)
                        with c1:
                            st.text_input(_t("聯絡人"), key=ct_keys["name"])
                        with c2:
                            st.text_input(_t("電話"), key=ct_keys["phone"])
                        c3, c4, c5 = st.columns(3)
                        with c3:
                            st.text_input(_t("Email"), key=ct_keys["email"])
                        with c4:
                            st.text_input(_t("部門"), key=ct_keys["dept"])
                        with c5:
                            st.text_input(_t("職稱"), key=ct_keys["title"])
                        st.text_area(_t("備註"), height=80, key=ct_keys["note"])

                        b1, b2 = st.columns(2)
                        btn_ct_save = b1.form_submit_button(f"💾 {_t('儲存')}", use_container_width=True)
                        btn_ct_del = b2.form_submit_button(f"🗑️ {_t('刪除')}", use_container_width=True)

                    if btn_ct_save:
                        try:
                            payload = {
                                "customer_id": int(selected_cid),
                                "contact_person_name": st.session_state.get(ct_keys["name"]) or None,
                                "phone": st.session_state.get(ct_keys["phone"]) or None,
                                "email": st.session_state.get(ct_keys["email"]) or None,
                                "department": st.session_state.get(ct_keys["dept"]) or None,
                                "title": st.session_state.get(ct_keys["title"]) or None,
                                "note": st.session_state.get(ct_keys["note"]) or None,
                            }
                            if ct_code_col:
                                if ct_pick_val is None:
                                    payload[ct_code_col] = st.session_state.get(ct_keys["code"]) or generate_child_code(engine, ct_table, ct_code_col)
                                else:
                                    payload[ct_code_col] = ct_row.get(ct_code_col)

                            if ct_pick_val is None:
                                insert_record(engine, ct_table, payload)
                            else:
                                update_record(engine, ct_table, (ct_pk, int(ct_pick_val)), payload)

                            st.session_state[ct_pick_key] = None
                            st.session_state[ct_keys["last"]] = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"{_t('儲存失敗：')}{e}")

                    if btn_ct_del:
                        if ct_pick_val is None:
                            st.warning(_t("無法刪除。"))
                        else:
                            try:
                                delete_record(engine, ct_table, ct_pk, int(ct_pick_val))
                                st.session_state[ct_pick_key] = None
                                st.session_state[ct_keys["last"]] = None
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"{_t('刪除失敗：')}{e}")

    # --- Tab 4: 負責業務 ---
    with tabs[3]:
        st.markdown(f"##### {_t('負責業務')}")
        if selected_cid is None:
            st.info(_t("請先選擇客戶。"))
        else:
            os_table = "customer_our_sales"
            if not table_exists(engine_url_key, os_table):
                st.warning(f"找不到 {os_table} 表。")
            else:
                os_cols = get_table_columns(engine_url_key, os_table)
                os_pk = get_pk_column(engine_url_key, os_table)

                if os_pk is None:
                    st.error(_t("此表無 Primary Key。"))
                else:
                    begin_col = "beginning_date" if "beginning_date" in os_cols else ("begining_date" if "begining_date" in os_cols else None)

                    wanted = []
                    if "stuff_name" in os_cols:
                        wanted.append("stuff_name")
                    if begin_col:
                        wanted.append(begin_col)
                    if "end_date" in os_cols:
                        wanted.append("end_date")

                    df_os, _ = load_child_table(engine, os_table, int(selected_cid), wanted_cols=wanted)

                    df_os_view = df_os.copy()
                    if not df_os_view.empty and "stuff_name" in df_os_view.columns:
                        df_os_view["stuff_name"] = df_os_view["stuff_name"].apply(
                            lambda x: staff_map.get(to_int_or_none(x), str(x) if x is not None else "")
                        )
                    render_readonly_table(df_os_view, col_map={c: COLUMN_MAP.get(c, c) for c in df_os_view.columns})

                    def label_os(pid, row):
                        sid = to_int_or_none(row.get("stuff_name"))
                        nm = staff_map.get(sid, "")
                        b_date = str(row.get(begin_col) or "") if begin_col else ""
                        e_date = str(row.get("end_date") or "")
                        return f"{pid} ｜ {nm} ｜ {b_date} ~ {e_date}"

                    os_pick_key = "pick_os_pk"
                    os_pick_val = render_child_picker(df_os, label_os, key=os_pick_key)

                    sp_os = f"os_{int(selected_cid)}"
                    os_keys = {
                        "last": f"{sp_os}_last",
                        "staff": f"{sp_os}_staff",
                        "begin": f"{sp_os}_begin",
                        "end": f"{sp_os}_end"
                    }
                    for k in os_keys.values():
                        st.session_state.setdefault(k, None)

                    os_row = {}
                    if os_pick_val is not None and not df_os.empty:
                        try:
                            os_row = df_os.loc[int(os_pick_val)].to_dict()
                        except Exception:
                            pass

                    if st.session_state[os_keys["last"]] != os_pick_val:
                        if os_pick_val is None:
                            st.session_state[os_keys["staff"]] = _t("(未指定)")
                            st.session_state[os_keys["begin"]] = None
                            st.session_state[os_keys["end"]] = None
                        else:
                            sid = to_int_or_none(os_row.get("stuff_name"))
                            st.session_state[os_keys["staff"]] = staff_map.get(sid, _t("(未指定)"))
                            st.session_state[os_keys["begin"]] = os_row.get(begin_col) if begin_col else None
                            st.session_state[os_keys["end"]] = os_row.get("end_date")
                        st.session_state[os_keys["last"]] = os_pick_val

                    if st.button(_t("取消選取"), key="btn_clear_os"):
                        st.session_state[os_pick_key] = None
                        st.session_state[os_keys["last"]] = None
                        st.rerun()

                    staff_names = [_t("(未指定)")] + list(staff_name_to_id.keys())

                    with st.form(f"form_os_{selected_cid}", clear_on_submit=False):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.selectbox(_t("業務人員"), options=staff_names, key=os_keys["staff"])
                        with c2:
                            if begin_col:
                                st.date_input(_t("起始日"), key=os_keys["begin"])
                            else:
                                st.empty()
                        with c3:
                            if "end_date" in os_cols:
                                st.date_input(_t("結束日"), key=os_keys["end"])
                            else:
                                st.empty()

                        b1, b2 = st.columns(2)
                        btn_os_save = b1.form_submit_button(f"💾 {_t('儲存')}", use_container_width=True)
                        btn_os_del = b2.form_submit_button(f"🗑️ {_t('刪除')}", use_container_width=True)

                    if btn_os_save:
                        try:
                            s_name = st.session_state.get(os_keys["staff"])
                            s_id = None if s_name in (None, "", _t("(未指定)")) else staff_name_to_id.get(s_name)

                            payload = {"customer_id": int(selected_cid), "stuff_name": s_id}
                            if begin_col:
                                payload[begin_col] = st.session_state.get(os_keys["begin"])
                            if "end_date" in os_cols:
                                payload["end_date"] = st.session_state.get(os_keys["end"])

                            if os_pick_val is None:
                                insert_record(engine, os_table, payload)
                            else:
                                update_record(engine, os_table, (os_pk, int(os_pick_val)), payload)

                            st.session_state[os_pick_key] = None
                            st.session_state[os_keys["last"]] = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"{_t('儲存失敗：')}{e}")

                    if btn_os_del:
                        if os_pick_val is None:
                            st.warning(_t("無法刪除。"))
                        else:
                            try:
                                delete_record(engine, os_table, os_pk, int(os_pick_val))
                                st.session_state[os_pick_key] = None
                                st.session_state[os_keys["last"]] = None
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"{_t('刪除失敗：')}{e}")



    # --- Tab 5: 客戶銀行資料 ---
    with tabs[4]:
        st.markdown(f"##### {_t('客戶銀行資料')}")
        if selected_cid is None:
            st.info(_t("請先選擇客戶。"))
        else:
            cb_table = "customer_bank"
            if not table_exists(engine_url_key, cb_table):
                st.warning(f"找不到 {cb_table} 表。")
            else:
                cb_cols = ["customer_bank_num", "customer_bank_name", "customer_account_name", "customer_bank_code"]
                df_cb, cb_pk = load_child_table(engine, cb_table, int(selected_cid), wanted_cols=cb_cols)

                if cb_pk is None:
                    st.error(_t("此表無 Primary Key。"))
                else:
                    render_readonly_table(df_cb, col_map={c: COLUMN_MAP.get(c, c) for c in df_cb.columns})

                    def label_cb(pid, row):
                        bank_no = str(row.get("customer_bank_num", "") or "")
                        bank_name = str(row.get("customer_bank_name", "") or "")
                        account_no = str(row.get("customer_bank_code", "") or "")
                        return f"{pid} ｜ {bank_no} ｜ {bank_name[:20]} ｜ {account_no[:12]}"

                    cb_reset_token_key = "customer_bank_picker_reset_token"
                    st.session_state.setdefault(cb_reset_token_key, 0)
                    cb_pick_key = f"pick_customer_bank_pk_{st.session_state[cb_reset_token_key]}"
                    cb_pick_val = render_child_picker(df_cb, label_cb, key=cb_pick_key)

                    sp_cb = f"cb_{int(selected_cid)}"
                    cb_keys = {
                        "last": f"{sp_cb}_last",
                        "num": f"{sp_cb}_num",
                        "name": f"{sp_cb}_name",
                        "account_name": f"{sp_cb}_account_name",
                        "code": f"{sp_cb}_code",
                    }
                    for k in cb_keys.values():
                        st.session_state.setdefault(k, None)

                    cb_row = {}
                    if cb_pick_val is not None and not df_cb.empty:
                        try:
                            cb_row = df_cb.loc[int(cb_pick_val)].to_dict()
                        except Exception:
                            pass

                    if st.session_state[cb_keys["last"]] != cb_pick_val:
                        if cb_pick_val is None:
                            st.session_state[cb_keys["num"]] = ""
                            st.session_state[cb_keys["name"]] = ""
                            st.session_state[cb_keys["account_name"]] = ""
                            st.session_state[cb_keys["code"]] = ""
                        else:
                            st.session_state[cb_keys["num"]] = str(cb_row.get("customer_bank_num") or "")
                            st.session_state[cb_keys["name"]] = str(cb_row.get("customer_bank_name") or "")
                            st.session_state[cb_keys["account_name"]] = str(cb_row.get("customer_account_name") or "")
                            st.session_state[cb_keys["code"]] = str(cb_row.get("customer_bank_code") or "")
                        st.session_state[cb_keys["last"]] = cb_pick_val

                    if st.button(_t("取消選取"), key="btn_clear_cb"):
                        st.session_state[cb_keys["last"]] = None
                        st.session_state[cb_reset_token_key] += 1
                        st.rerun()

                    with st.form(f"form_cb_{selected_cid}", clear_on_submit=False):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.text_input(_t("銀行代號"), key=cb_keys["num"])
                        with c2:
                            st.text_input(_t("銀行名稱"), key=cb_keys["name"])

                        c3, c4 = st.columns(2)
                        with c3:
                            st.text_input(_t("戶名"), key=cb_keys["account_name"])
                        with c4:
                            st.text_input(_t("銀行帳號"), key=cb_keys["code"])

                        b1, b2 = st.columns(2)
                        btn_cb_save = b1.form_submit_button(f"💾 {_t('儲存')}", use_container_width=True)
                        btn_cb_del = b2.form_submit_button(f"🗑️ {_t('刪除')}", use_container_width=True)

                    if btn_cb_save:
                        try:
                            payload = {
                                "customer_id": int(selected_cid),
                                "customer_bank_num": st.session_state.get(cb_keys["num"]) or None,
                                "customer_bank_name": st.session_state.get(cb_keys["name"]) or None,
                                "customer_account_name": st.session_state.get(cb_keys["account_name"]) or None,
                                "customer_bank_code": st.session_state.get(cb_keys["code"]) or None,
                            }

                            if cb_pick_val is None:
                                insert_record(engine, cb_table, payload)
                            else:
                                update_record(engine, cb_table, (cb_pk, int(cb_pick_val)), payload)

                                st.session_state[cb_keys["last"]] = None
                            st.session_state[cb_reset_token_key] += 1
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"{_t('儲存失敗：')}{e}")

                    if btn_cb_del:
                        if cb_pick_val is None:
                            st.warning(_t("新增模式無法刪除。"))
                        else:
                            try:
                                delete_record(engine, cb_table, cb_pk, int(cb_pick_val))
                                st.session_state[cb_keys["last"]] = None
                                st.session_state[cb_reset_token_key] += 1
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"{_t('刪除失敗：')}{e}")


if __name__ == "__main__":
    main()





















