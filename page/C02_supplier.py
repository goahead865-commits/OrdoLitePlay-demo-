import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd
import math

apply_compact_layout()
from typing import Optional, List


# ---- i18n helpers ----
try:
    from core.i18n import tr  # type: ignore
except Exception:
    def tr(key: str) -> str:
        return key

def _get_lang() -> str:
    for k in ("lang", "language", "ui_lang"):
        v = st.session_state.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return "zh-TW"

_FALLBACK = {
    "operator (user_id)": {"en": "Operator (user_id)", "vi": "Người thao tác (user_id)"},
    "本次操作人員": {"en": "Current Operator", "vi": "Người thao tác hiện tại"},
    "搜尋（供應商代號/簡稱/全名/電話/統編）": {"en": "Search (Supplier Code / Short Name / Full Name / Phone / Tax ID)", "vi": "Tìm kiếm (Mã NCC / Tên ngắn / Tên đầy đủ / Điện thoại / MST)"},
    "供應商分類": {"en": "Supplier Category", "vi": "Phân loại nhà cung cấp"},
    "供應商大類": {"en": "Supplier Main Category", "vi": "Nhóm chính nhà cung cấp"},
    "供應商細類": {"en": "Supplier Subcategory", "vi": "Nhóm chi tiết nhà cung cấp"},
    "管理供應商大類": {"en": "Manage Supplier Main Categories", "vi": "Quản lý nhóm chính NCC"},
    "➕ 管理供應商大類": {"en": "➕ Manage Main Categories", "vi": "➕ Quản lý nhóm chính"},
    "管理供應商細類": {"en": "Manage Supplier Subcategories", "vi": "Quản lý nhóm chi tiết NCC"},
    "➕ 管理供應商細類": {"en": "➕ Manage Subcategories", "vi": "➕ Quản lý nhóm chi tiết"},
    "新增供應商大類": {"en": "Add Supplier Main Category", "vi": "Thêm nhóm chính NCC"},
    "供應商大類名稱": {"en": "Supplier Main Category Name", "vi": "Tên nhóm chính NCC"},
    "儲存供應商大類": {"en": "Save Supplier Main Category", "vi": "Lưu nhóm chính NCC"},
    "請輸入供應商大類名稱。": {"en": "Enter a supplier main category name.", "vi": "Vui lòng nhập tên nhóm chính NCC."},
    "已新增供應商大類：": {"en": "Added supplier main category: ", "vi": "Đã thêm nhóm chính NCC: "},
    "新增供應商大類失敗：": {"en": "Failed to add supplier main category: ", "vi": "Thêm nhóm chính NCC thất bại: "},
    "目前沒有可管理的分類。": {"en": "There are no categories to manage.", "vi": "Không có phân loại để quản lý."},
    "確認刪除此分類（無法復原）": {"en": "Confirm deleting this category (cannot be undone)", "vi": "Xác nhận xóa phân loại này (không thể hoàn tác)"},
    "請先勾選確認刪除。": {"en": "Select the confirmation checkbox before deleting.", "vi": "Vui lòng tích xác nhận trước khi xóa."},
    "此分類仍有供應商使用，無法刪除。": {"en": "This category is still used by suppliers and cannot be deleted.", "vi": "Phân loại này vẫn đang được nhà cung cấp sử dụng, không thể xóa."},
    "關閉": {"en": "Close", "vi": "Đóng"},
    "修改": {"en": "Edit", "vi": "Chỉnh sửa"},
    "供應商大類會保留原料、物料（輔料）、設備、生產工具、模具等上層分類；原本的供應商細類不會改變。": {"en": "Main categories cover Raw Materials, Materials (Auxiliary), Equipment, Production Tools and Molds; existing subcategories remain unchanged.", "vi": "Nhóm chính gồm Nguyên liệu, Vật liệu (phụ trợ), Thiết bị, Công cụ sản xuất và Khuôn; các nhóm chi tiết hiện có không thay đổi."},
    "狀態": {"en": "Status", "vi": "Trạng thái"},
    "(全部)": {"en": "(All)", "vi": "(Tất cả)"},
    "合作中": {"en": "Active", "vi": "Đang hợp tác"},
    "停止合作": {"en": "Inactive", "vi": "Ngừng hợp tác"},
    "供應商清單": {"en": "Supplier List", "vi": "Danh sách nhà cung cấp"},
    "上一頁": {"en": "Previous", "vi": "Trang trước"},
    "下一頁": {"en": "Next", "vi": "Trang sau"},
    "每頁筆數": {"en": "Rows per page", "vi": "Số dòng mỗi trang"},
    "重新整理": {"en": "Refresh", "vi": "Làm mới"},
    "選取": {"en": "Select", "vi": "Chọn"},
    "代號": {"en": "Code", "vi": "Mã"},
    "簡稱": {"en": "Short Name", "vi": "Tên ngắn"},
    "全名": {"en": "Full Name", "vi": "Tên đầy đủ"},
    "分類": {"en": "Category", "vi": "Phân loại"},
    "電話": {"en": "Phone", "vi": "Điện thoại"},
    "統編/稅號": {"en": "Tax ID", "vi": "MST"},
    "聯絡人": {"en": "Contact Person", "vi": "Người liên hệ"},
    "聯絡人電話": {"en": "Contact Phone", "vi": "Điện thoại liên hệ"},
    "結帳日": {"en": "Closing Day", "vi": "Ngày chốt sổ"},
    "付款天數": {"en": "Payment Days", "vi": "Số ngày thanh toán"},
    "本公司採購": {"en": "Our Buyer", "vi": "Nhân viên mua hàng"},
    "建立時間": {"en": "Created At", "vi": "Thời gian tạo"},
    "建立者": {"en": "Created By", "vi": "Người tạo"},
    "更新時間": {"en": "Updated At", "vi": "Thời gian cập nhật"},
    "更新者": {"en": "Updated By", "vi": "Người cập nhật"},
    "新增/編輯": {"en": "Create/Edit", "vi": "Thêm/Sửa"},
    "銀行帳戶": {"en": "Bank Accounts", "vi": "Tài khoản ngân hàng"},
    "目前是新增模式：請在上方清單勾選一筆即可進入編輯。": {"en": "Create mode: select one supplier above to enter edit mode.", "vi": "Hiện đang ở chế độ thêm mới: hãy chọn một nhà cung cấp phía trên để vào chế độ chỉnh sửa."},
    "目前是編輯模式：supplier_id = ": {"en": "Edit mode: supplier_id = ", "vi": "Hiện đang ở chế độ chỉnh sửa: supplier_id = "},
    "供應商代碼（自動編號）*": {"en": "Supplier Code (Auto Numbering) *", "vi": "Mã nhà cung cấp (tự động) *"},
    "供應商簡稱（簡稱）*": {"en": "Supplier Short Name *", "vi": "Tên ngắn NCC *"},
    "供應商名稱（全名）*": {"en": "Supplier Full Name *", "vi": "Tên đầy đủ NCC *"},
    "供應商類別（分類）*": {"en": "Supplier Category *", "vi": "Phân loại NCC *"},
    "➕ 新增供應商類別": {"en": "➕ Add Supplier Category", "vi": "➕ Thêm phân loại NCC"},
    "新增後會自動刷新並選到新類別": {"en": "After adding, it will refresh and select the new category automatically.", "vi": "Sau khi thêm sẽ tự động làm mới và chọn phân loại mới."},
    "供應商類別名稱": {"en": "Supplier Category Name", "vi": "Tên phân loại NCC"},
    "儲存供應商類別": {"en": "Save Supplier Category", "vi": "Lưu phân loại NCC"},
    "請輸入供應商類別名稱。": {"en": "Please enter a supplier category name.", "vi": "Vui lòng nhập tên phân loại NCC."},
    "已新增供應商類別：": {"en": "Added supplier category: ", "vi": "Đã thêm phân loại NCC: "},
    "新增供應商類別失敗：": {"en": "Failed to add supplier category: ", "vi": "Thêm phân loại NCC thất bại: "},
    "供應商電話": {"en": "Supplier Phone", "vi": "Điện thoại NCC"},
    "供應商信箱": {"en": "Supplier Email", "vi": "Email NCC"},
    "供應商地址": {"en": "Supplier Address", "vi": "Địa chỉ NCC"},
    "老闆姓名": {"en": "Boss Name", "vi": "Tên chủ doanh nghiệp"},
    "老闆電話": {"en": "Boss Phone", "vi": "Điện thoại chủ doanh nghiệp"},
    "聯絡人信箱": {"en": "Contact Email", "vi": "Email liên hệ"},
    "結帳日期": {"en": "Closing Date", "vi": "Ngày chốt sổ"},
    "付款天數": {"en": "Payment Days", "vi": "Số ngày thanh toán"},
    "稅率(%)": {"en": "Tax Rate (%)", "vi": "Thuế suất (%)"},
    "本公司採購": {"en": "Our Buyer", "vi": "Nhân viên mua hàng"},
    "備註": {"en": "Note", "vi": "Ghi chú"},
    "新增": {"en": "Create", "vi": "Thêm mới"},
    "新增失敗：": {"en": "Create failed: ", "vi": "Thêm mới thất bại: "},
    "新增成功": {"en": "Created successfully", "vi": "Tạo thành công"},
    "已新增：": {"en": "Created: ", "vi": "Đã tạo: "},
    "供應商代碼（不可改）*": {"en": "Supplier Code (Read-only) *", "vi": "Mã NCC (không sửa được) *"},
    "儲存修改": {"en": "Save Changes", "vi": "Lưu thay đổi"},
    "↩️ 回新增模式": {"en": "↩️ Back to Create Mode", "vi": "↩️ Quay lại chế độ thêm mới"},
    "已更新。": {"en": "Updated.", "vi": "Đã cập nhật."},
    "更新失敗：": {"en": "Update failed: ", "vi": "Cập nhật thất bại: "},
    "刪除（慎用）": {"en": "Delete (Use with caution)", "vi": "Xóa (thận trọng)"},
    "若供應商已被其他資料（例如採購、收貨、對帳）參照，刪除會被外鍵擋下。": {"en": "If this supplier is referenced by other records (e.g. purchasing, receiving, reconciliation), deletion will be blocked by foreign keys.", "vi": "Nếu nhà cung cấp này đã được tham chiếu bởi dữ liệu khác (ví dụ: mua hàng, nhập hàng, đối chiếu), việc xóa sẽ bị khóa ngoại chặn lại."},
    "刪除這筆 supplier": {"en": "Delete this supplier", "vi": "Xóa nhà cung cấp này"},
    "已刪除。": {"en": "Deleted.", "vi": "Đã xóa."},
    "刪除失敗：": {"en": "Delete failed: ", "vi": "Xóa thất bại: "},
    "請先在第一頁勾選一筆供應商，這裡才有對應的銀行帳戶可以維護。": {"en": "Please select one supplier on the first tab before maintaining bank accounts here.", "vi": "Vui lòng chọn một nhà cung cấp ở tab đầu tiên trước khi quản lý tài khoản ngân hàng tại đây."},
    "供應商：": {"en": "Supplier: ", "vi": "Nhà cung cấp: "},
    "此供應商已停止合作（停用）。銀行帳戶僅供查閱，禁止新增/修改/刪除。": {"en": "This supplier is inactive. Bank accounts are view-only; create/update/delete is disabled.", "vi": "Nhà cung cấp này đã ngừng hợp tác. Tài khoản ngân hàng chỉ để xem; không cho phép thêm/sửa/xóa."},
    "銀行帳戶清單": {"en": "Bank Account List", "vi": "Danh sách tài khoản ngân hàng"},
    "目前沒有任何銀行帳戶。請先新增一筆（建議至少一筆預設帳戶）。": {"en": "There are no bank accounts yet. Please add one first (it is recommended to have at least one default account).", "vi": "Hiện chưa có tài khoản ngân hàng nào. Vui lòng thêm một tài khoản trước (khuyến nghị có ít nhất một tài khoản mặc định)."},
    "銀行代碼": {"en": "Bank Code", "vi": "Mã ngân hàng"},
    "銀行名稱": {"en": "Bank Name", "vi": "Tên ngân hàng"},
    "戶名": {"en": "Account Name", "vi": "Tên tài khoản"},
    "帳號": {"en": "Bank Account", "vi": "Số tài khoản"},
    "預設": {"en": "Default", "vi": "Mặc định"},
    "新增銀行帳戶": {"en": "Add Bank Account", "vi": "Thêm tài khoản ngân hàng"},
    "設為預設帳戶": {"en": "Set as default account", "vi": "Đặt làm tài khoản mặc định"},
    "編輯/動作": {"en": "Edit / Actions", "vi": "Chỉnh sửa / Thao tác"},
    "請在上方清單勾選一筆銀行帳戶，才能在這裡設預設 / 停用 / 修改。": {"en": "Select one bank account above to set default / deactivate / edit here.", "vi": "Hãy chọn một tài khoản ngân hàng phía trên để đặt mặc định / ngừng dùng / chỉnh sửa tại đây."},
    "找不到該筆銀行帳戶，可能已被刪除。": {"en": "This bank account could not be found; it may have been deleted.", "vi": "Không tìm thấy tài khoản ngân hàng này; có thể đã bị xóa."},
    "只設預設": {"en": "Set Default Only", "vi": "Chỉ đặt mặc định"},
    "已設為預設帳戶。": {"en": "Set as default account.", "vi": "Đã đặt làm tài khoản mặc định."},
    "設定失敗：": {"en": "Setting failed: ", "vi": "Thiết lập thất bại: "},
    "停用 / 刪除（慎用）": {"en": "Deactivate / Delete (Use with caution)", "vi": "Ngừng dùng / Xóa (thận trọng)"},
    "停用": {"en": "Deactivate", "vi": "Ngừng dùng"},
    "啟用": {"en": "Activate", "vi": "Kích hoạt"},
    "已": {"en": "", "vi": "Đã "},
    "失敗：": {"en": " failed: ", "vi": " thất bại: "},
}

def _t(key: str) -> str:
    try:
        res = tr(key)
        if isinstance(res, str) and res:
            if not res.startswith("[MISS:"):
                return res
    except Exception:
        pass
    lang = _get_lang().lower()
    fb = _FALLBACK.get(key)
    if fb:
        if lang.startswith("en"):
            return fb.get("en", key)
        if lang.startswith("vi"):
            return fb.get("vi", key)
        return key
    return f"[MISS:{key}]"

import auth
from splitter_component import render_vertical_splitter

# 盡量相容你目前專案的 db.py（沿用 P01_product.py 的寫法）：
# - 優先用 get_connection()
# - 若沒有 get_connection，退回用 get_engine().raw_connection()
try:
    from db import get_connection  # type: ignore
except Exception:  # pragma: no cover
    try:
        from db import get_engine  # type: ignore

        def get_connection():  # type: ignore
            eng = get_engine()
            if eng is None:
                return None
            return eng.raw_connection()

    except Exception:
        def get_connection():  # type: ignore
            st.error("找不到 db.get_connection / db.get_engine，請確認 db.py。")
            return None




def parse_int_or_none(v) -> Optional[int]:
    """允許空白；輸入轉 int，失敗回 None。"""
    try:
        s = str(v).strip()
        if s == "":
            return None
        return int(float(s))
    except Exception:
        return None

# ================== 基本設定 ==================
st.set_page_config(page_title=_t("供應商清單"), layout="wide")

PAGE_KEY = "C02_supplier"
auth.require_read(PAGE_KEY)


TABLE_SUPPLIER = "supplier"
TABLE_SUPPLIER_CATEGORY = "supplier_category"
TABLE_SUPPLIER_MAJOR_CATEGORY = "supplier_major_category"
TABLE_SUPPLIER_BANK = "supplier_bank_account"
TABLE_USER = "user"
TABLE_STUFF = "stuff"

PK_BANK = "Supplier_bank_account_id"  # 注意：你目前 schema 的 PK 是這個大小寫


# ================== DB 小工具 ==================
def read_df(sql: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def exec_sql(sql: str, params=None) -> None:
    conn = get_connection()
    if conn is None:
        raise RuntimeError("get_connection() 回傳 None，無法寫入 DB。")
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
    finally:
        cur.close()
        conn.close()


def exec_sql_returning_id(sql: str, params=None) -> int:
    """INSERT 後回傳 lastrowid（MySQL connector / pymysql 都支援）。"""
    conn = get_connection()
    if conn is None:
        raise RuntimeError("get_connection() 回傳 None，無法寫入 DB。")
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
        try:
            return int(getattr(cur, "lastrowid", 0) or 0)
        except Exception:
            return 0
    finally:
        cur.close()
        conn.close()


def exec_tx(statements: List[tuple]) -> None:
    """
    簡單 transaction helper：
    statements: [(sql, params), ...]
    """
    conn = get_connection()
    if conn is None:
        raise RuntimeError("get_connection() 回傳 None，無法寫入 DB。")
    cur = conn.cursor()
    try:
        for sql, params in statements:
            cur.execute(sql, params or ())
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        cur.close()
        conn.close()


# ================== Lookup ==================
def get_supplier_categories() -> pd.DataFrame:
    return read_df(f"""
        SELECT supplier_category_id, supplier_category_name AS label
        FROM {TABLE_SUPPLIER_CATEGORY}
        ORDER BY supplier_category_name
    """)


def insert_supplier_category(category_name: str) -> int:
    sql = f"""
        INSERT INTO {TABLE_SUPPLIER_CATEGORY} (
            supplier_category_name
        ) VALUES (
            %s
        )
    """
    return exec_sql_returning_id(sql, ((category_name or "").strip(),))


def get_supplier_major_categories() -> pd.DataFrame:
    return read_df(f"""
        SELECT supplier_major_category_id, supplier_major_category_name AS label
        FROM {TABLE_SUPPLIER_MAJOR_CATEGORY}
        WHERE is_active = 1
        ORDER BY supplier_major_category_name
    """)


def insert_supplier_major_category(category_name: str) -> int:
    sql = f"""
        INSERT INTO {TABLE_SUPPLIER_MAJOR_CATEGORY} (supplier_major_category_name)
        VALUES (%s)
    """
    return exec_sql_returning_id(sql, ((category_name or "").strip(),))


def update_supplier_category(category_id: int, category_name: str) -> None:
    exec_sql(
        f"UPDATE {TABLE_SUPPLIER_CATEGORY} SET supplier_category_name=%s WHERE supplier_category_id=%s",
        ((category_name or "").strip(), int(category_id)),
    )


def delete_supplier_category(category_id: int) -> None:
    exec_sql(
        f"DELETE FROM {TABLE_SUPPLIER_CATEGORY} WHERE supplier_category_id=%s",
        (int(category_id),),
    )


def update_supplier_major_category(category_id: int, category_name: str) -> None:
    exec_sql(
        f"UPDATE {TABLE_SUPPLIER_MAJOR_CATEGORY} SET supplier_major_category_name=%s WHERE supplier_major_category_id=%s",
        ((category_name or "").strip(), int(category_id)),
    )


def delete_supplier_major_category(category_id: int) -> None:
    exec_sql(
        f"DELETE FROM {TABLE_SUPPLIER_MAJOR_CATEGORY} WHERE supplier_major_category_id=%s",
        (int(category_id),),
    )


def supplier_category_usage_count(category_id: int) -> int:
    df = read_df(
        f"SELECT COUNT(*) AS cnt FROM {TABLE_SUPPLIER} WHERE supplier_category=%s",
        (int(category_id),),
    )
    return int(df.iloc[0]["cnt"] or 0) if not df.empty else 0


def supplier_major_category_usage_count(category_id: int) -> int:
    df = read_df(
        f"SELECT COUNT(*) AS cnt FROM {TABLE_SUPPLIER} WHERE supplier_major_category_id=%s",
        (int(category_id),),
    )
    return int(df.iloc[0]["cnt"] or 0) if not df.empty else 0


def get_users_with_stuff() -> pd.DataFrame:
    """
    created_by_id / updated_by_id 顯示 stuff_name
    supplier.created_by_id -> user.user_id -> user.stuff_id -> stuff.stuff_name
    """
    return read_df(f"""
        SELECT
            u.user_id,
            COALESCE(s.stuff_name, u.user_code, CAST(u.user_id AS CHAR)) AS label
        FROM {TABLE_USER} u
        LEFT JOIN {TABLE_STUFF} s ON s.stuff_id = u.stuff_id
        ORDER BY label
    """)


@st.cache_data(ttl=60)
def cached_categories() -> pd.DataFrame:
    return get_supplier_categories()


@st.cache_data(ttl=60)
def cached_major_categories() -> pd.DataFrame:
    return get_supplier_major_categories()


@st.cache_data(ttl=60)
def cached_users() -> pd.DataFrame:
    return get_users_with_stuff()


categories = cached_categories()
major_categories = cached_major_categories()
users = cached_users()

cat_map = dict(zip(categories["supplier_category_id"], categories["label"])) if not categories.empty else {}
major_cat_map = dict(zip(major_categories["supplier_major_category_id"], major_categories["label"])) if not major_categories.empty else {}
user_map = dict(zip(users["user_id"], users["label"])) if not users.empty else {}

# NOT NULL created_by_id：沿用 P01 的做法，讓你每次操作可選操作人員
st.sidebar.subheader(_t("本次操作人員"))
if users.empty:
    st.sidebar.error("user / stuff 查不到資料：無法寫入 created_by_id / updated_by_id。")
    st.stop()

operator_id = st.sidebar.selectbox(
    _t("operator (user_id)"),
    options=users["user_id"].tolist(),
    format_func=lambda x: user_map.get(x, str(x)),
    index=0,
)


# ================== supplier_code 自動編號 ==================
def get_next_supplier_code(prefix: str = "S", width: int = 4) -> str:
    """
    規則：S0001、S0002... 依此類推（S + 4 位數字）
    取號邏輯：掃描目前最大的 supplier_code（只接受 S+純數字），取 MAX + 1。
    """
    df = read_df(f"""
        SELECT MAX(CAST(SUBSTRING(TRIM(supplier_code), 2) AS UNSIGNED)) AS max_n
        FROM {TABLE_SUPPLIER}
        WHERE TRIM(supplier_code) REGEXP CONCAT('^', %s, '[0-9]+$')
    """, params=(prefix,))

    max_n = 0
    if not df.empty and df.iloc[0, 0] is not None:
        try:
            max_n = int(df.iloc[0, 0])
        except Exception:
            max_n = 0

    next_n = max_n + 1
    if next_n > (10 ** width - 1):
        raise ValueError(f"supplier_code 已達上限：{prefix}{str(10 ** width - 1).zfill(width)}，請擴充編碼規則。")

    return f"{prefix}{str(next_n).zfill(width)}"


# ================== 查詢/載入 ==================
def search_suppliers(
    keyword: str,
    category_id: Optional[int],
    is_active: Optional[int],
    limit: Optional[int] = None,
    offset: int = 0,
) -> pd.DataFrame:
    kw = (keyword or "").strip()
    where = []
    params = []

    if kw:
        where.append("""
            (
                s.supplier_code LIKE %s OR
                s.supplier_shortname LIKE %s OR
                s.supplier_name LIKE %s OR
                s.supplier_phone LIKE %s OR
                s.supplier_tax_id LIKE %s
            )
        """)
        like = f"%{kw}%"
        params += [like, like, like, like, like]

    if category_id:
        where.append("s.supplier_category = %s")
        params.append(int(category_id))
    if is_active is not None:
        where.append("s.is_active = %s")
        params.append(int(is_active))

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT %s OFFSET %s"
        params.append(int(limit))
        params.append(int(max(offset, 0)))

    sql = f"""
        SELECT
            s.supplier_id,
            s.supplier_code,
            s.supplier_shortname,
            s.supplier_name,
            smc.supplier_major_category_name AS supplier_major_category_name,
            sc.supplier_category_name AS supplier_category_name,
            s.supplier_phone,
            s.supplier_tax_id,
            s.is_active,
            s.contact_person,
            s.contact_person_phone,
            s.checkout_date,
            s.payment_days,
            s.our_buyer,
            s.created_at,
            s.created_by_id,
            s1.stuff_name AS created_by_name,
            s.updated_at,
            s.updated_by_id,
            s2.stuff_name AS updated_by_name
        FROM {TABLE_SUPPLIER} s
        LEFT JOIN {TABLE_SUPPLIER_MAJOR_CATEGORY} smc ON smc.supplier_major_category_id = s.supplier_major_category_id
        LEFT JOIN {TABLE_SUPPLIER_CATEGORY} sc ON sc.supplier_category_id = s.supplier_category
        LEFT JOIN {TABLE_USER} u1 ON u1.user_id = s.created_by_id
        LEFT JOIN {TABLE_STUFF} s1 ON s1.stuff_id = u1.stuff_id
        LEFT JOIN {TABLE_USER} u2 ON u2.user_id = s.updated_by_id
        LEFT JOIN {TABLE_STUFF} s2 ON s2.stuff_id = u2.stuff_id
        {where_sql}
        ORDER BY s.supplier_id ASC
        {limit_sql}
    """
    return read_df(sql, params=params)


def count_suppliers(keyword: str, category_id: Optional[int], is_active: Optional[int]) -> int:
    kw = (keyword or "").strip()
    where = []
    params = []

    if kw:
        where.append("""
            (
                s.supplier_code LIKE %s OR
                s.supplier_shortname LIKE %s OR
                s.supplier_name LIKE %s OR
                s.supplier_phone LIKE %s OR
                s.supplier_tax_id LIKE %s
            )
        """)
        like = f"%{kw}%"
        params += [like, like, like, like, like]

    if category_id:
        where.append("s.supplier_category = %s")
        params.append(int(category_id))
    if is_active is not None:
        where.append("s.is_active = %s")
        params.append(int(is_active))

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    df = read_df(f"""
        SELECT COUNT(*) AS cnt
        FROM {TABLE_SUPPLIER} s
        {where_sql}
    """, params=params)
    if df.empty:
        return 0
    return int(df.iloc[0, 0] or 0)


@st.cache_data(ttl=30)
def cached_supplier_count(keyword: str, category_id: Optional[int], is_active: Optional[int]) -> int:
    return count_suppliers(keyword=keyword, category_id=category_id, is_active=is_active)


@st.cache_data(ttl=30)
def cached_search_suppliers(keyword: str, category_id: Optional[int], is_active: Optional[int], limit: int, offset: int) -> pd.DataFrame:
    return search_suppliers(keyword=keyword, category_id=category_id, is_active=is_active, limit=limit, offset=offset)


def load_supplier(supplier_id: int) -> dict:
    df = read_df(f"SELECT * FROM {TABLE_SUPPLIER} WHERE supplier_id=%s", params=[supplier_id])
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


# ================== 寫入 ==================
def insert_supplier(data: dict) -> int:
    sql = f"""
        INSERT INTO {TABLE_SUPPLIER} (
            supplier_code, supplier_shortname, supplier_phone, supplier_address, supplier_tax_id,
            supplier_major_category_id, supplier_category, contact_person, contact_person_phone, supplier_name, is_active,
            boss_name, boss_phone, supplier_email, contact_person_email,
            checkout_date, payment_days, tax_rate,
            our_buyer, note, created_by_id, updated_by_id
        ) VALUES (
            %s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,
            %s,%s,%s,
            %s,%s,%s,%s
        )
    """
    params = (
        data["supplier_code"],
        data["supplier_shortname"],
        data.get("supplier_phone"),
        data.get("supplier_address"),
        data.get("supplier_tax_id"),
        data.get("supplier_major_category_id"),
        data["supplier_category"],
        data.get("contact_person"),
        data.get("contact_person_phone"),
        data["supplier_name"],
        int(data.get("is_active", 1) or 0),
        data.get("boss_name"),
        data.get("boss_phone"),
        data.get("supplier_email"),
        data.get("contact_person_email"),
        data.get("checkout_date"),
        data.get("payment_days"),
        data.get("tax_rate"),
        data.get("our_buyer"),
        data.get("note"),
        data["created_by_id"],
        data.get("updated_by_id"),
    )
    return exec_sql_returning_id(sql, params)


def update_supplier(supplier_id: int, data: dict) -> None:
    sql = f"""
        UPDATE {TABLE_SUPPLIER}
        SET
            supplier_shortname=%s,
            supplier_phone=%s,
            supplier_address=%s,
            supplier_tax_id=%s,
            supplier_major_category_id=%s,
            supplier_category=%s,
            contact_person=%s,
            contact_person_phone=%s,
            supplier_name=%s,
            is_active=%s,
            boss_name=%s,
            boss_phone=%s,
            supplier_email=%s,
            contact_person_email=%s,
            checkout_date=%s,
            payment_days=%s,
            tax_rate=%s,
            our_buyer=%s,
            note=%s,
            updated_by_id=%s
        WHERE supplier_id=%s
    """
    params = (
        data["supplier_shortname"],
        data.get("supplier_phone"),
        data.get("supplier_address"),
        data.get("supplier_tax_id"),
        data.get("supplier_major_category_id"),
        data["supplier_category"],
        data.get("contact_person"),
        data.get("contact_person_phone"),
        data["supplier_name"],
        int(data.get("is_active", 1) or 0),
        data.get("boss_name"),
        data.get("boss_phone"),
        data.get("supplier_email"),
        data.get("contact_person_email"),
        data.get("checkout_date"),
        data.get("payment_days"),
        data.get("tax_rate"),
        data.get("our_buyer"),
        data.get("note"),
        data.get("updated_by_id"),
        supplier_id,
    )
    exec_sql(sql, params)


def delete_supplier(supplier_id: int) -> None:
    exec_sql(f"DELETE FROM {TABLE_SUPPLIER} WHERE supplier_id=%s", (supplier_id,))


# ================== Bank Accounts ==================
def get_bank_accounts(supplier_id: int) -> pd.DataFrame:
    return read_df(f"""
        SELECT
            {PK_BANK} AS bank_account_id,
            supplier_id,
            bank_id,
            bank_name,
            account_name,
            bank_account,
            COALESCE(is_default, 0) AS is_default,
            COALESCE(status, 'active') AS status
        FROM {TABLE_SUPPLIER_BANK}
        WHERE supplier_id=%s
        ORDER BY COALESCE(is_default, 0) DESC, {PK_BANK} ASC
    """, params=[supplier_id])


@st.cache_data(ttl=15)
def cached_bank_accounts(supplier_id: int) -> pd.DataFrame:
    return get_bank_accounts(int(supplier_id))


def insert_bank_account(data: dict) -> int:
    sql = f"""
        INSERT INTO {TABLE_SUPPLIER_BANK} (
            supplier_id, bank_id, bank_name, account_name, bank_account, is_default, status
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s
        )
    """
    params = (
        int(data["supplier_id"]),
        data["bank_id"],
        data["bank_name"],
        data.get("account_name"),
        data["bank_account"],
        int(data.get("is_default", 0)),
        data.get("status", "active"),
    )
    return exec_sql_returning_id(sql, params)


def update_bank_account(bank_account_id: int, data: dict) -> None:
    sql = f"""
        UPDATE {TABLE_SUPPLIER_BANK}
        SET
            bank_id=%s,
            bank_name=%s,
            account_name=%s,
            bank_account=%s,
            is_default=%s,
            status=%s
        WHERE {PK_BANK}=%s
    """
    params = (
        data["bank_id"],
        data["bank_name"],
        data.get("account_name"),
        data["bank_account"],
        int(data.get("is_default", 0)),
        data.get("status", "active"),
        int(bank_account_id),
    )
    exec_sql(sql, params)


def set_default_bank_account(supplier_id: int, bank_account_id: int) -> None:
    # 交易：先清掉同 supplier 的 default，再把指定那筆設 default
    exec_tx([
        (f"UPDATE {TABLE_SUPPLIER_BANK} SET is_default=0 WHERE supplier_id=%s", (int(supplier_id),)),
        (f"UPDATE {TABLE_SUPPLIER_BANK} SET is_default=1 WHERE {PK_BANK}=%s AND supplier_id=%s", (int(bank_account_id), int(supplier_id))),
    ])


def toggle_bank_account_status(bank_account_id: int, new_status: str) -> None:
    exec_sql(f"UPDATE {TABLE_SUPPLIER_BANK} SET status=%s WHERE {PK_BANK}=%s", (new_status, int(bank_account_id)))


def delete_bank_account(bank_account_id: int) -> None:
    exec_sql(f"DELETE FROM {TABLE_SUPPLIER_BANK} WHERE {PK_BANK}=%s", (int(bank_account_id),))


# ================== UI State ==================
def init_c02_state() -> None:
    st.session_state.setdefault("c02_selected_supplier_id", None)
    st.session_state.setdefault("c02_prev_selected_supplier_id", None)
    st.session_state.setdefault("c02_page", 1)
    st.session_state.setdefault("c02_last_filters", None)
    # data_editor 會記住勾選狀態；換 key 才能真正取消上方勾選
    st.session_state.setdefault("c02_supplier_editor_nonce", 0)


def reset_to_new_mode() -> None:
    """
    回到新增模式：
    1. 清掉目前選取的 supplier_id
    2. 讓上方供應商清單 data_editor 換一個新 key
       這樣 Streamlit 會重建表格，勾選格才會真的取消
    """
    st.session_state["c02_selected_supplier_id"] = None
    st.session_state["c02_prev_selected_supplier_id"] = None

    old_key = f"c02_supplier_list_editor_{st.session_state.get('c02_supplier_editor_nonce', 0)}"
    st.session_state.pop(old_key, None)

    st.session_state["c02_supplier_editor_nonce"] = int(st.session_state.get("c02_supplier_editor_nonce", 0)) + 1


def force_refresh_c02_master() -> None:
    """清除 C02 母表快取與勾選狀態，避免 data_editor 或 cache 吃到舊資料。"""
    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.session_state["c02_selected_supplier_id"] = None
    st.session_state["c02_prev_selected_supplier_id"] = None

    old_supplier_key = f"c02_supplier_list_editor_{st.session_state.get('c02_supplier_editor_nonce', 0)}"
    st.session_state.pop(old_supplier_key, None)
    st.session_state.pop("c02_bank_list_editor", None)

    st.session_state["c02_supplier_editor_nonce"] = int(st.session_state.get("c02_supplier_editor_nonce", 0)) + 1


def fill_edit_state(row: dict) -> None:
    st.session_state["e_supplier_code"] = row.get("supplier_code") or ""
    st.session_state["e_supplier_shortname"] = row.get("supplier_shortname") or ""
    st.session_state["e_supplier_name"] = row.get("supplier_name") or ""
    major_category_id = row.get("supplier_major_category_id")
    st.session_state["e_supplier_major_category_id"] = int(major_category_id) if pd.notna(major_category_id) else None
    st.session_state["e_is_active"] = (_t("合作中") if int(row.get("is_active", 1) or 0) == 1 else _t("停止合作"))
    st.session_state["e_supplier_category"] = int(row.get("supplier_category") or 0)
    st.session_state["e_supplier_phone"] = row.get("supplier_phone") or ""
    st.session_state["e_supplier_email"] = row.get("supplier_email") or ""
    st.session_state["e_supplier_tax_id"] = row.get("supplier_tax_id") or ""
    st.session_state["e_supplier_address"] = row.get("supplier_address") or ""
    st.session_state["e_contact_person"] = row.get("contact_person") or ""
    st.session_state["e_contact_person_phone"] = row.get("contact_person_phone") or ""
    st.session_state["e_contact_person_email"] = row.get("contact_person_email") or ""
    st.session_state["e_checkout_date"] = ("" if row.get("checkout_date") is None else str(int(row.get("checkout_date"))))
    st.session_state["e_payment_days"] = ("" if row.get("payment_days") is None else str(int(row.get("payment_days"))))
    st.session_state["e_tax_rate"] = ("" if row.get("tax_rate") is None else str(int(row.get("tax_rate"))))
    st.session_state["e_boss_name"] = row.get("boss_name") or ""
    st.session_state["e_boss_phone"] = row.get("boss_phone") or ""
    st.session_state["e_our_buyer"] = row.get("our_buyer") or ""
    st.session_state["e_note"] = row.get("note") or ""


init_c02_state()

# 套用「新增供應商類別」後待回填的分類 id（必須在 widget 建立前處理）
if st.session_state.get("c02_pending_new_supplier_category_id_new") is not None:
    st.session_state["n_supplier_category"] = int(st.session_state.pop("c02_pending_new_supplier_category_id_new"))
if st.session_state.get("c02_pending_new_supplier_category_id_edit") is not None:
    st.session_state["e_supplier_category"] = int(st.session_state.pop("c02_pending_new_supplier_category_id_edit"))
if st.session_state.get("c02_pending_new_supplier_major_category_id_new") is not None:
    st.session_state["n_supplier_major_category_id"] = int(st.session_state.pop("c02_pending_new_supplier_major_category_id_new"))
if st.session_state.get("c02_pending_new_supplier_major_category_id_edit") is not None:
    st.session_state["e_supplier_major_category_id"] = int(st.session_state.pop("c02_pending_new_supplier_major_category_id_edit"))

@st.dialog(_t("管理供應商大類"), width="small")
def _show_supplier_major_category_dialog() -> None:
    st.caption(_t("供應商大類會保留原料、物料（輔料）、設備、生產工具、模具等上層分類；原本的供應商細類不會改變。"))
    _render_supplier_category_manager("major")


@st.dialog(_t("管理供應商細類"), width="small")
def _show_supplier_category_dialog() -> None:
    _render_supplier_category_manager("subcategory")


def _close_category_manager() -> None:
    st.session_state.pop("c02_category_manager_kind", None)
    st.session_state.pop("c02_category_manager_target", None)
    cached_categories.clear()
    cached_major_categories.clear()
    st.cache_data.clear()
    st.rerun()


def _render_supplier_category_manager(kind: str) -> None:
    """Shared add / rename / safe-delete dialog for supplier category lookups."""
    is_major = kind == "major"
    category_df = get_supplier_major_categories() if is_major else get_supplier_categories()
    id_column = "supplier_major_category_id" if is_major else "supplier_category_id"
    name_label = _t("供應商大類名稱") if is_major else _t("供應商類別名稱")
    kind_label = _t("供應商大類") if is_major else _t("供應商細類")
    caller_target = st.session_state.get("c02_category_manager_target", "new")

    st.subheader(_t("新增") + kind_label)
    with st.form(f"c02_add_{kind}_category_form", clear_on_submit=True):
        new_name = st.text_input(name_label, key=f"c02_add_{kind}_category_name")
        create_clicked = st.form_submit_button(_t("新增"), type="primary", use_container_width=True)
    if create_clicked:
        name = (new_name or "").strip()
        if not name:
            st.error(_t("請輸入供應商大類名稱。") if is_major else _t("請輸入供應商類別名稱。"))
        else:
            try:
                auth.require_edit(PAGE_KEY)
                new_id = insert_supplier_major_category(name) if is_major else insert_supplier_category(name)
                if is_major:
                    st.session_state[f"c02_pending_new_supplier_major_category_id_{caller_target}"] = int(new_id)
                else:
                    st.session_state[f"c02_pending_new_supplier_category_id_{caller_target}"] = int(new_id)
                _close_category_manager()
            except Exception as e:
                st.error(f"{_t('新增失敗：')}{e}")

    st.divider()
    st.subheader(_t("修改") + " / " + _t("刪除（慎用）"))
    if category_df.empty:
        st.info(_t("目前沒有可管理的分類。"))
    else:
        category_ids = [int(value) for value in category_df[id_column].tolist()]
        label_map = dict(zip(category_ids, category_df["label"].astype(str).tolist()))
        selected_id = st.selectbox(
            kind_label,
            options=category_ids,
            format_func=lambda value: label_map.get(int(value), str(value)),
            key=f"c02_manage_{kind}_category_id",
        )
        current_name = label_map[int(selected_id)]
        with st.form(f"c02_edit_{kind}_category_form_{selected_id}"):
            edited_name = st.text_input(name_label, value=current_name, key=f"c02_edit_{kind}_category_name_{selected_id}")
            delete_confirmed = st.checkbox(
                _t("確認刪除此分類（無法復原）"),
                key=f"c02_delete_{kind}_category_confirm_{selected_id}",
            )
            save_col, delete_col = st.columns(2)
            save_clicked = save_col.form_submit_button(_t("儲存修改"), use_container_width=True)
            delete_clicked = delete_col.form_submit_button(_t("刪除（慎用）"), use_container_width=True)

        if save_clicked:
            name = (edited_name or "").strip()
            if not name:
                st.error(_t("請輸入供應商大類名稱。") if is_major else _t("請輸入供應商類別名稱。"))
            else:
                try:
                    auth.require_edit(PAGE_KEY)
                    if is_major:
                        update_supplier_major_category(int(selected_id), name)
                    else:
                        update_supplier_category(int(selected_id), name)
                    _close_category_manager()
                except Exception as e:
                    st.error(f"{_t('更新失敗：')}{e}")

        if delete_clicked:
            if not delete_confirmed:
                st.error(_t("請先勾選確認刪除。"))
            else:
                try:
                    auth.require_edit(PAGE_KEY)
                    usage_count = (
                        supplier_major_category_usage_count(int(selected_id))
                        if is_major
                        else supplier_category_usage_count(int(selected_id))
                    )
                    if usage_count:
                        st.error(_t("此分類仍有供應商使用，無法刪除。") + f"（{usage_count}）")
                    else:
                        if is_major:
                            delete_supplier_major_category(int(selected_id))
                        else:
                            delete_supplier_category(int(selected_id))
                        _close_category_manager()
                except Exception as e:
                    st.error(f"{_t('刪除失敗：')}{e}")

    if st.button(_t("關閉"), use_container_width=True, key=f"c02_close_{kind}_category_manager"):
        _close_category_manager()


def _request_category_manager(kind: str, target: str) -> None:
    st.session_state["c02_category_manager_kind"] = kind
    st.session_state["c02_category_manager_target"] = target
    st.rerun()


manager_kind = st.session_state.get("c02_category_manager_kind")
if manager_kind == "major":
    _show_supplier_major_category_dialog()
elif manager_kind == "subcategory":
    _show_supplier_category_dialog()


st.title("C02_supplier — " + _t("供應商清單"))

st.session_state.setdefault("c02_top_height", 260)

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

if st.session_state.get("c02_new_category_success"):
    st.success(st.session_state.pop("c02_new_category_success"))

col_search_1, col_search_2, col_search_3 = st.columns([2, 2, 1])
with col_search_1:
    kw = st.text_input(_t("搜尋（供應商代號/簡稱/全名/電話/統編）"), key="c02_kw", placeholder="例如：S0001 / 台塑 / 23456789")
with col_search_2:
    cat_sel = st.selectbox(
        _t("供應商分類"),
        options=[None] + (categories["supplier_category_id"].tolist() if not categories.empty else []),
        format_func=lambda x: _t("(全部)") if x is None else cat_map.get(x, str(x)),
        index=0,
        key="c02_cat",
    )


with col_search_3:
    is_active_sel = st.selectbox(
        _t("狀態"),
        options=[None, 1, 0],
        format_func=lambda x: _t("(全部)") if x is None else (_t("合作中") if int(x) == 1 else _t("停止合作")),
        index=0,
        key="c02_is_active",
    )
st.markdown("#### " + _t("供應商清單"))

# --- 分頁查詢（沿用 P01 的 UX：任何條件變更就回第 1 頁）---
filters = ((kw or "").strip(), cat_sel)
if st.session_state.get("c02_last_filters") != filters:
    st.session_state["c02_page"] = 1
    st.session_state["c02_last_filters"] = filters

# --- 分頁工具列（每頁筆數置中於上一頁 / 下一頁）---
def _c02_prev_page():
    st.session_state["c02_page"] = max(1, int(st.session_state.get("c02_page", 1)) - 1)

def _c02_next_page(total_pages: int):
    st.session_state["c02_page"] = min(int(total_pages), int(st.session_state.get("c02_page", 1)) + 1)

page_size_options = [10, 20, 30, 50, 100]
current_page_size = int(st.session_state.get("c02_page_size", 20))
if current_page_size not in page_size_options:
    current_page_size = 20
page_size = current_page_size

total_rows = cached_supplier_count(keyword=kw, category_id=cat_sel, is_active=is_active_sel)
total_pages = max(1, int(math.ceil(total_rows / max(int(page_size), 1))))

# clamp page（避免超出頁碼）
if st.session_state["c02_page"] > total_pages:
    st.session_state["c02_page"] = total_pages
if st.session_state["c02_page"] < 1:
    st.session_state["c02_page"] = 1

toolbar_left, toolbar_spacer, toolbar_right = st.columns([3.8, 2.2, 3.0])
with toolbar_left:
    st.caption(f"共 {total_rows} 筆｜第 {st.session_state['c02_page']} / {total_pages} 頁")

with toolbar_right:
    c_prev, c_size, c_next = st.columns([1.0, 1.0, 1.0], vertical_alignment="bottom")
    with c_prev:
        st.button(_t("上一頁"), disabled=(st.session_state["c02_page"] <= 1), use_container_width=True, on_click=_c02_prev_page)
    with c_size:
        page_size = st.selectbox(
            _t("每頁筆數"),
            options=page_size_options,
            index=page_size_options.index(current_page_size),
            key="c02_page_size",
        )
    with c_next:
        st.button(_t("下一頁"), disabled=(st.session_state["c02_page"] >= total_pages), use_container_width=True, on_click=_c02_next_page, kwargs={"total_pages": total_pages})

offset = (int(st.session_state["c02_page"]) - 1) * int(page_size)
df = cached_search_suppliers(keyword=kw, category_id=cat_sel, is_active=is_active_sel, limit=int(page_size), offset=int(offset))

# ---- 清單用 DataEditor（P01 同邏輯：勾一筆 => 編輯模式；不勾 => 新增模式）----
if df.empty:
    st.info("查無資料。你可以直接在下方新增供應商。")
    grid_df = pd.DataFrame(columns=["__pick__"])
else:
    display_cols = [
        "supplier_code", "supplier_shortname", "supplier_name", "supplier_major_category_name", "supplier_category_name",
        "supplier_phone", "supplier_tax_id", "is_active",
        "contact_person", "contact_person_phone",
        "checkout_date", "payment_days",
        "our_buyer",
        "created_at", "created_by_name", "updated_at", "updated_by_name",
    ]
    grid_df = df[["supplier_id"] + display_cols].copy().set_index("supplier_id", drop=True)
    grid_df.insert(0, "__pick__", False)

    # NULL 顯示處理
    def _fmt_int_no_decimal(x):
        if x is None:
            return ""
        try:
            # pandas 可能給 float / numpy types
            if isinstance(x, float) and math.isnan(x):
                return ""
        except Exception:
            pass
        s = str(x).strip()
        if s == "":
            return ""
        try:
            return str(int(float(s)))
        except Exception:
            return s

    for col in ["supplier_major_category_name", "supplier_category_name", "created_by_name", "updated_by_name", "our_buyer"]:
        if col in grid_df.columns:
            grid_df[col] = grid_df[col].fillna("")

    # 這兩欄是整數顯示，不要出現 .0
    for col in ["checkout_date", "payment_days"]:
        if col in grid_df.columns:
            grid_df[col] = grid_df[col].apply(_fmt_int_no_decimal)
col_map = {
    "__pick__": _t("選取"),
    "supplier_code": _t("代號"),
    "supplier_shortname": _t("簡稱"),
    "supplier_name": _t("全名"),
    "supplier_major_category_name": _t("供應商大類"),
    "supplier_category_name": _t("分類"),
    "supplier_phone": _t("電話"),
    "supplier_tax_id": _t("統編/稅號"),
    "is_active": _t("合作中"),
    "contact_person": _t("聯絡人"),
    "contact_person_phone": _t("聯絡人電話"),
    "checkout_date": _t("結帳日"),
    "payment_days": _t("付款天數"),
    "our_buyer": _t("本公司採購"),
    "created_at": _t("建立時間"),
    "created_by_name": _t("建立者"),
    "updated_at": _t("更新時間"),
    "updated_by_name": _t("更新者"),
}

if not grid_df.empty:
    grid_df = grid_df.rename(columns={k: col_map.get(k, k) for k in grid_df.columns})

editor_height = int(st.session_state["c02_top_height"])
edited_grid = st.data_editor(
    grid_df,
    use_container_width=True,
    height=editor_height,
    hide_index=True,
    num_rows="fixed",
    disabled=[c for c in grid_df.columns if c != col_map["__pick__"]],
    key=f"c02_supplier_list_editor_{st.session_state.get('c02_supplier_editor_nonce', 0)}",
    column_config={
        col_map["__pick__"]: st.column_config.CheckboxColumn(col_map["__pick__"], default=False),
        col_map.get("is_active", "啟用"): st.column_config.CheckboxColumn(col_map.get("is_active", "啟用"), default=True),
    },
)

refresh_col, _refresh_spacer = st.columns([1.1, 5.5], vertical_alignment="center")
with refresh_col:
    if st.button(_t("重新整理"), key="c02_refresh_supplier_master", use_container_width=True):
        force_refresh_c02_master()
        st.rerun()

prev_selected = st.session_state.get("c02_selected_supplier_id")
picked_ids: List[int] = []
if edited_grid is not None and not edited_grid.empty:
    for idx, row in edited_grid.iterrows():
        if bool(row.get(col_map["__pick__"], False)):
            try:
                picked_ids.append(int(idx))
            except Exception:
                pass

if len(picked_ids) > 1:
    st.warning(f"你勾了 {len(picked_ids)} 筆，我只會取第一筆：{picked_ids[0]}")

if picked_ids:
    st.session_state["c02_selected_supplier_id"] = picked_ids[0]
else:
    # 從有選取 -> 取消選取：回新增模式
    if prev_selected is not None:
        reset_to_new_mode()
        st.cache_data.clear()
        st.rerun()

_c02_splitter_result = render_vertical_splitter(
    int(st.session_state["c02_top_height"]),
    key="c02_vertical_splitter_control",
    min_top=150,
    max_top=430,
)
if isinstance(_c02_splitter_result, dict) and "top_height" in _c02_splitter_result:
    _c02_next_height = max(150, min(430, int(_c02_splitter_result["top_height"])))
    if _c02_next_height != int(st.session_state["c02_top_height"]):
        st.session_state["c02_top_height"] = _c02_next_height
        st.rerun()


lower_tabs = st.tabs([_t("新增/編輯"), _t("銀行帳戶")])

with lower_tabs[0]:
    selected_sid = st.session_state.get("c02_selected_supplier_id")

    st.markdown("---")
    st.markdown("#### " + _t("新增/編輯"))

    # 選取變更：灌入 session_state
    if selected_sid is not None and st.session_state.get("c02_prev_selected_supplier_id") != selected_sid:
        row = load_supplier(int(selected_sid))
        if row:
            fill_edit_state(row)
            st.session_state["c02_prev_selected_supplier_id"] = selected_sid

    if selected_sid is None:
        st.info(_t("目前是新增模式：請在上方清單勾選一筆即可進入編輯。"))

        with st.form("c02_new_supplier_form", clear_on_submit=True):

            # ===== 區塊 1：供應商代碼/簡稱/全名 =====
            r1 = st.columns([1, 1, 1])
            with r1[0]:
                auto_code = get_next_supplier_code()
                st.text_input(_t("供應商代碼（自動編號）*"), value=auto_code, disabled=True)
                supplier_code = auto_code
            with r1[1]:
                supplier_shortname = st.text_input(_t("供應商簡稱（簡稱）*"), value="", key="n_supplier_shortname")
            with r1[2]:
                supplier_name = st.text_input(_t("供應商名稱（全名）*"), value="", key="n_supplier_name")

            st.divider()

            # ===== 區塊 2：供應商大類 + 既有細類 / 電話 / 統編 / 信箱 / 地址 =====
            r_major = st.columns([2.2, 1.1], vertical_alignment="bottom")
            with r_major[0]:
                supplier_major_category_id = st.selectbox(
                    _t("供應商大類"),
                    options=[None] + (major_categories["supplier_major_category_id"].tolist() if not major_categories.empty else []),
                    format_func=lambda x: "—" if x is None else major_cat_map.get(x, str(x)),
                    key="n_supplier_major_category_id",
                )
            with r_major[1]:
                manage_major_clicked = st.form_submit_button(_t("➕ 管理供應商大類"), use_container_width=True)
            if manage_major_clicked:
                _request_category_manager("major", "new")

            r2 = st.columns([2.2, 1.1], vertical_alignment="bottom")
            with r2[0]:
                supplier_category = st.selectbox(
                    _t("供應商細類") + " *",
                    options=categories["supplier_category_id"].tolist() if not categories.empty else [],
                    format_func=lambda x: cat_map.get(x, str(x)),
                    key="n_supplier_category",
                )
            with r2[1]:
                manage_subcategory_clicked = st.form_submit_button(_t("➕ 管理供應商細類"), use_container_width=True)
            if manage_subcategory_clicked:
                _request_category_manager("subcategory", "new")

            r2b = st.columns([1, 1])
            with r2b[0]:
                supplier_phone = st.text_input(_t("供應商電話"), value="", key="n_supplier_phone")
            with r2b[1]:
                supplier_tax_id = st.text_input(_t("統編/稅號"), value="", key="n_supplier_tax_id")

            r3 = st.columns([1, 2])
            with r3[0]:
                supplier_email = st.text_input(_t("供應商信箱"), value="", key="n_supplier_email")
            with r3[1]:
                supplier_address = st.text_input(_t("供應商地址"), value="", key="n_supplier_address")

            st.divider()

            # ===== 區塊 3：老闆/聯絡人 =====
            # ===== 區塊 3：老闆/聯絡人 =====
            r4 = st.columns([1, 1])
            with r4[0]:
                boss_name = st.text_input(_t("老闆姓名"), value="", key="n_boss_name")
            with r4[1]:
                boss_phone = st.text_input(_t("老闆電話"), value="", key="n_boss_phone")

            r5 = st.columns([1, 1, 2])
            with r5[0]:
                contact_person = st.text_input(_t("聯絡人"), value="", key="n_contact_person")
            with r5[1]:
                contact_person_phone = st.text_input(_t("聯絡人電話"), value="", key="n_contact_person_phone")
            with r5[2]:
                contact_person_email = st.text_input(_t("聯絡人信箱"), value="", key="n_contact_person_email")
            st.markdown('<hr style="border:0;border-top:1px solid #B0B0B0;margin:6px 0 12px 0;" />', unsafe_allow_html=True)
            r5b = st.columns([1, 1, 1])
            with r5b[0]:
                checkout_date_txt = st.text_input(_t("結帳日期"), value="", key="n_checkout_date", placeholder="例如：25（每月25日結帳）")
            with r5b[1]:
                payment_days_txt = st.text_input(_t("付款天數"), value="", key="n_payment_days", placeholder="例如：30（結帳後30天付款）")
            with r5b[2]:
                tax_rate_txt = st.text_input(_t("稅率(%)"), value="", key="n_tax_rate", placeholder="例如：10")

            st.markdown('<hr style="border:0;border-top:1px solid #B0B0B0;margin:12px 0 12px 0;" />', unsafe_allow_html=True)

            # ===== 區塊 4：本公司採購 / 合作中 =====
            r6 = st.columns([2, 1])
            with r6[0]:
                our_buyer = st.text_input(_t("本公司採購"), value="", key="n_our_buyer")
            with r6[1]:
                coop_status = st.selectbox(_t("合作中"), options=[_t("合作中"), _t("停止合作")], index=0, key="n_is_active")

            note = st.text_area(_t("備註"), value="", key="n_note", height=90)

            submit = st.form_submit_button(_t("新增"), type="primary")

            if submit:

                auth.require_edit(PAGE_KEY)
                data = {
                    "supplier_code": supplier_code.strip(),
                    "supplier_shortname": (supplier_shortname or "").strip(),
                    "supplier_name": (supplier_name or "").strip(),
                    "is_active": 1 if (coop_status == _t("合作中")) else 0,
                    "supplier_major_category_id": supplier_major_category_id,
                    "supplier_category": int(supplier_category),
                    "supplier_phone": (supplier_phone.strip() or None),
                    "supplier_email": (supplier_email.strip() or None),
                    "supplier_tax_id": (supplier_tax_id.strip() or None),
                    "supplier_address": (supplier_address.strip() or None),
                    "contact_person": (contact_person.strip() or None),
                    "contact_person_phone": (contact_person_phone.strip() or None),
                    "contact_person_email": (contact_person_email.strip() or None),
                    "checkout_date": parse_int_or_none(st.session_state.get("n_checkout_date")),
                    "payment_days": parse_int_or_none(st.session_state.get("n_payment_days")),
                    "tax_rate": parse_int_or_none(st.session_state.get("n_tax_rate")),
                    "boss_name": (boss_name.strip() or None),
                    "boss_phone": (boss_phone.strip() or None),
                    "our_buyer": (our_buyer.strip() or None),
                    "note": (note.strip() or None),
                    "created_by_id": int(operator_id),
                    "updated_by_id": int(operator_id),
                }

                if not data["supplier_shortname"] or not data["supplier_name"]:
                    st.error("supplier_shortname / supplier_name 不能空。")
                else:
                    # 避免多人同時新增撞號：若 Duplicate，重新取號再試
                    last_err = None
                    base_data = dict(data)
                    for _ in range(3):
                        try:
                            base_data["supplier_code"] = get_next_supplier_code()
                            new_id = insert_supplier(base_data)
                            st.success(f"已新增：{base_data['supplier_code']}（supplier_id={new_id}）")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            last_err = e
                            msg = str(e)
                            if ("1062" in msg) or ("Duplicate" in msg) or ("duplicate" in msg):
                                continue
                            break
                    st.error(_t("新增失敗：") + f"{last_err}")

    else:
        row = load_supplier(int(selected_sid))
        if not row:
            st.warning("找不到該 supplier，可能已被刪除。")
            reset_to_new_mode()
            st.rerun()

        st.write(_t("目前是編輯模式：supplier_id = ") + f"**{int(selected_sid)}**")

        with st.form("c02_edit_supplier_form", clear_on_submit=False):

            # ===== 區塊 1：供應商代碼/簡稱/全名 =====
            r1 = st.columns([1, 1, 1])
            with r1[0]:
                supplier_code = st.text_input(_t("供應商代碼（不可改）*"), key="e_supplier_code", disabled=True)
            with r1[1]:
                supplier_shortname = st.text_input(_t("供應商簡稱（簡稱）*"), key="e_supplier_shortname")
            with r1[2]:
                supplier_name = st.text_input(_t("供應商名稱（全名）*"), key="e_supplier_name")

            st.divider()

            # ===== 區塊 2：供應商大類 + 既有細類 / 電話 / 統編 / 信箱 / 地址 =====
            r_major = st.columns([2.2, 1.1], vertical_alignment="bottom")
            with r_major[0]:
                supplier_major_category_id = st.selectbox(
                    _t("供應商大類"),
                    options=[None] + (major_categories["supplier_major_category_id"].tolist() if not major_categories.empty else []),
                    format_func=lambda x: "—" if x is None else major_cat_map.get(x, str(x)),
                    key="e_supplier_major_category_id",
                )
            with r_major[1]:
                manage_major_clicked = st.form_submit_button(_t("➕ 管理供應商大類"), use_container_width=True)
            if manage_major_clicked:
                _request_category_manager("major", "edit")

            r2 = st.columns([2.2, 1.1], vertical_alignment="bottom")
            with r2[0]:
                supplier_category = st.selectbox(
                    _t("供應商細類") + " *",
                    options=categories["supplier_category_id"].tolist() if not categories.empty else [],
                    format_func=lambda x: cat_map.get(x, str(x)),
                    key="e_supplier_category",
                )
            with r2[1]:
                manage_subcategory_clicked = st.form_submit_button(_t("➕ 管理供應商細類"), use_container_width=True)
            if manage_subcategory_clicked:
                _request_category_manager("subcategory", "edit")

            r2b = st.columns([1, 1])
            with r2b[0]:
                supplier_phone = st.text_input(_t("供應商電話"), key="e_supplier_phone")
            with r2b[1]:
                supplier_tax_id = st.text_input(_t("統編/稅號"), key="e_supplier_tax_id")

            r3 = st.columns([1, 2])
            with r3[0]:
                supplier_email = st.text_input(_t("供應商信箱"), key="e_supplier_email")
            with r3[1]:
                supplier_address = st.text_input(_t("供應商地址"), key="e_supplier_address")

            st.divider()

            # ===== 區塊 3：老闆/聯絡人 =====
            # ===== 區塊 3：老闆/聯絡人 =====
            r4 = st.columns([1, 1])
            with r4[0]:
                boss_name = st.text_input(_t("老闆姓名"), key="e_boss_name")
            with r4[1]:
                boss_phone = st.text_input(_t("老闆電話"), key="e_boss_phone")

            r5 = st.columns([1, 1, 2])
            with r5[0]:
                contact_person = st.text_input(_t("聯絡人"), key="e_contact_person")
            with r5[1]:
                contact_person_phone = st.text_input(_t("聯絡人電話"), key="e_contact_person_phone")
            with r5[2]:
                contact_person_email = st.text_input(_t("聯絡人信箱"), key="e_contact_person_email")
            st.markdown('<hr style="border:0;border-top:1px solid #B0B0B0;margin:6px 0 12px 0;" />', unsafe_allow_html=True)
            r5b = st.columns([1, 1, 1])
            with r5b[0]:
                checkout_date_txt = st.text_input(_t("結帳日期"), key="e_checkout_date", placeholder="例如：25（每月25日結帳）")
            with r5b[1]:
                payment_days_txt = st.text_input(_t("付款天數"), key="e_payment_days", placeholder="例如：30（結帳後30天付款）")
            with r5b[2]:
                tax_rate_txt = st.text_input(_t("稅率(%)"), key="e_tax_rate", placeholder="例如：10")
            st.markdown('<hr style="border:0;border-top:1px solid #B0B0B0;margin:12px 0 12px 0;" />', unsafe_allow_html=True)

            # ===== 區塊 4：本公司採購 / 合作中 =====
            r6 = st.columns([2, 1])
            with r6[0]:
                our_buyer = st.text_input(_t("本公司採購"), key="e_our_buyer")
            with r6[1]:
                coop_status = st.selectbox(_t("合作中"), options=[_t("合作中"), _t("停止合作")], key="e_is_active")

            note = st.text_area(_t("備註"), key="e_note", height=90)

            btn_save, btn_back = st.columns([1, 1])
            save = btn_save.form_submit_button(_t("儲存修改"), type="primary", use_container_width=True)
            back = btn_back.form_submit_button(_t("↩️ 回新增模式"), use_container_width=True)

            if back:
                reset_to_new_mode()
                st.rerun()

            if save:

                auth.require_edit(PAGE_KEY)
                data = {
                    "supplier_shortname": (supplier_shortname or "").strip(),
                    "supplier_name": (supplier_name or "").strip(),
                    "is_active": 1 if (coop_status == _t("合作中")) else 0,
                    "supplier_major_category_id": supplier_major_category_id,
                    "supplier_category": int(supplier_category),
                    "supplier_phone": ((supplier_phone or "").strip() or None),
                    "supplier_email": ((supplier_email or "").strip() or None),
                    "supplier_tax_id": ((supplier_tax_id or "").strip() or None),
                    "supplier_address": ((supplier_address or "").strip() or None),
                    "contact_person": ((contact_person or "").strip() or None),
                    "contact_person_phone": ((contact_person_phone or "").strip() or None),
                    "contact_person_email": ((contact_person_email or "").strip() or None),
                    "checkout_date": parse_int_or_none(st.session_state.get("e_checkout_date")),
                    "payment_days": parse_int_or_none(st.session_state.get("e_payment_days")),
                    "tax_rate": parse_int_or_none(st.session_state.get("e_tax_rate")),
                    "boss_name": ((boss_name or "").strip() or None),
                    "boss_phone": ((boss_phone or "").strip() or None),
                    "our_buyer": ((our_buyer or "").strip() or None),
                    "note": ((note or "").strip() or None),
                    "updated_by_id": int(operator_id),
                }

                if not data["supplier_shortname"] or not data["supplier_name"]:
                    st.error("supplier_shortname / supplier_name 不能空。")
                else:
                    try:
                        update_supplier(int(selected_sid), data)
                        st.success(_t("已更新。"))
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(_t("更新失敗：") + f"{e}")

        with st.expander(_t("刪除（慎用）"), expanded=False):
            st.warning(_t("若供應商已被其他資料（例如採購、收貨、對帳）參照，刪除會被外鍵擋下。"))
            if st.button(_t("刪除這筆 supplier"), type="secondary"):

                auth.require_delete(PAGE_KEY)
                try:
                    delete_supplier(int(selected_sid))
                    st.success(_t("已刪除。"))
                    st.cache_data.clear()
                    reset_to_new_mode()
                    st.rerun()
                except Exception as e:
                    st.error(_t("刪除失敗：") + f"{e}")




with lower_tabs[1]:
    selected_sid = st.session_state.get("c02_selected_supplier_id")
    if selected_sid is None:
        st.info(_t("請先在第一頁勾選一筆供應商，這裡才有對應的銀行帳戶可以維護。"))
        st.stop()

    sup = load_supplier(int(selected_sid))
    st.subheader(_t("供應商：") + f"{sup.get('supplier_shortname', '')}（{sup.get('supplier_code', '')}）")

    supplier_active = (int(sup.get("is_active", 1) or 0) == 1)
    lock_bank = (not supplier_active)
    if lock_bank:
        st.warning(_t("此供應商已停止合作（停用）。銀行帳戶僅供查閱，禁止新增/修改/刪除。"))

    # 讀取銀行帳戶
    bank_df = cached_bank_accounts(int(selected_sid))

    st.markdown("#### " + _t("銀行帳戶清單"))
    if bank_df.empty:
        st.info(_t("目前沒有任何銀行帳戶。請先新增一筆（建議至少一筆預設帳戶）。"))
        grid_b = pd.DataFrame(columns=["__pick__"])
    else:
        grid_b = bank_df.copy().set_index("bank_account_id", drop=True)
        grid_b.insert(0, "__pick__", False)

    bank_col_map = {
        "__pick__": _t("選取"),
        "bank_id": _t("銀行代碼"),
        "bank_name": _t("銀行名稱"),
        "account_name": _t("戶名"),
        "bank_account": _t("帳號"),
        "is_default": _t("預設"),
        "status": _t("狀態"),
    }

    if not grid_b.empty:
        grid_b = grid_b.rename(columns={k: bank_col_map.get(k, k) for k in grid_b.columns if k != "supplier_id"})

    editor_height_b = 240 if grid_b.empty else min(520, 36 * (len(grid_b) + 1) + 120)
    df_bank_editor = grid_b.drop(columns=[c for c in ["supplier_id"] if c in grid_b.columns], errors="ignore")
    disabled_bank_cols = (list(df_bank_editor.columns) if lock_bank else ([bank_col_map["is_default"]] if not grid_b.empty else []))

    edited_bank = st.data_editor(
        df_bank_editor,
        use_container_width=True,
        height=editor_height_b,
        hide_index=True,
        num_rows="fixed",
        key="c02_bank_list_editor",
        column_config={
            bank_col_map["__pick__"]: st.column_config.CheckboxColumn(bank_col_map["__pick__"], default=False),
            bank_col_map["is_default"]: st.column_config.CheckboxColumn(bank_col_map["is_default"], default=False),
        },
        disabled=disabled_bank_cols,  # 停用供應商時鎖定全部欄位；其他情況只鎖預設欄避免多筆 True
    )

    picked_bank_ids: List[int] = []
    if edited_bank is not None and not edited_bank.empty:
        for idx, row in edited_bank.iterrows():
            if bool(row.get(bank_col_map["__pick__"], False)):
                try:
                    picked_bank_ids.append(int(idx))
                except Exception:
                    pass

    if len(picked_bank_ids) > 1:
        st.warning(f"你勾了 {len(picked_bank_ids)} 筆，我只會取第一筆：{picked_bank_ids[0]}")

    selected_bank_id = picked_bank_ids[0] if picked_bank_ids else None

    st.markdown("---")
    left, right = st.columns([1.15, 1.0])

    # --- 新增 ---
    with left:
        st.markdown("#### " + _t("新增銀行帳戶"))
        existing_cnt = 0 if bank_df.empty else int(len(bank_df))
        force_default = (existing_cnt == 0)

        with st.form("c02_new_bank_form", clear_on_submit=True):
            c1 = st.columns(3)
            with c1[0]:
                bank_id = st.text_input("bank_id（銀行代碼）*", value="", key="nb_bank_id", placeholder="例如：004 / VCB / BIDV")
            with c1[1]:
                bank_name = st.text_input("bank_name（銀行名稱）*", value="", key="nb_bank_name", placeholder="例如：台灣銀行 / Vietcombank")
            with c1[2]:
                status = st.selectbox("status", options=["active", "inactive"], index=0, key="nb_status")

            c2 = st.columns(2)
            with c2[0]:
                account_name = st.text_input("account_name（戶名）", value="", key="nb_account_name")
            with c2[1]:
                bank_account = st.text_input("bank_account（帳號）*", value="", key="nb_bank_account")

            is_default = st.checkbox(_t("設為預設帳戶"), value=True if force_default else False, key="nb_is_default", disabled=force_default)

            submit = st.form_submit_button(_t("新增銀行帳戶"), type="primary", use_container_width=True, disabled=lock_bank)

            if submit:

                auth.require_edit(PAGE_KEY)
                data = {
                    "supplier_id": int(selected_sid),
                    "bank_id": (bank_id or "").strip(),
                    "bank_name": (bank_name or "").strip(),
                    "account_name": ((account_name or "").strip() or None),
                    "bank_account": (bank_account or "").strip(),
                    "is_default": 1 if is_default or force_default else 0,
                    "status": status,
                }
                if not data["bank_id"] or not data["bank_name"] or not data["bank_account"]:
                    st.error("bank_id / bank_name / bank_account 不能空。")
                else:
                    try:
                        new_id = insert_bank_account(data)
                        # 若是預設，確保唯一
                        if data["is_default"]:
                            set_default_bank_account(int(selected_sid), int(new_id))
                        st.success("已新增銀行帳戶。")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"新增失敗：{e}")

    # --- 編輯/動作 ---
    with right:
        st.markdown("#### " + _t("編輯/動作"))
        if selected_bank_id is None:
            st.info(_t("請在上方清單勾選一筆銀行帳戶，才能在這裡設預設 / 停用 / 修改。"))
        else:
            row = bank_df[bank_df["bank_account_id"] == selected_bank_id]
            if row.empty:
                st.warning(_t("找不到該筆銀行帳戶，可能已被刪除。"))
            else:
                r = row.iloc[0].to_dict()

                with st.form("c02_edit_bank_form", clear_on_submit=False):
                    bank_id = st.text_input("bank_id（銀行代碼）*", value=str(r.get("bank_id") or ""), key="eb_bank_id")
                    bank_name = st.text_input("bank_name（銀行名稱）*", value=str(r.get("bank_name") or ""), key="eb_bank_name")
                    account_name = st.text_input("account_name（戶名）", value=str(r.get("account_name") or ""), key="eb_account_name")
                    bank_account = st.text_input("bank_account（帳號）*", value=str(r.get("bank_account") or ""), key="eb_bank_account")
                    status = st.selectbox("status", options=["active", "inactive"], index=0 if (r.get("status") or "active") == "active" else 1, key="eb_status")

                    is_default_now = bool(int(r.get("is_default") or 0))
                    is_default = st.checkbox(_t("設為預設帳戶"), value=is_default_now, key="eb_is_default")

                    b_save, b_set_default = st.columns([1, 1])
                    save = b_save.form_submit_button("儲存修改", type="primary", use_container_width=True, disabled=lock_bank)
                    set_def = b_set_default.form_submit_button(_t("只設預設"), use_container_width=True, disabled=lock_bank)

                    if set_def:

                        auth.require_edit(PAGE_KEY)
                        try:
                            set_default_bank_account(int(selected_sid), int(selected_bank_id))
                            st.success(_t("已設為預設帳戶。"))
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(_t("設定失敗：") + f"{e}")

                    if save:

                        auth.require_edit(PAGE_KEY)
                        data = {
                            "bank_id": (bank_id or "").strip(),
                            "bank_name": (bank_name or "").strip(),
                            "account_name": ((account_name or "").strip() or None),
                            "bank_account": (bank_account or "").strip(),
                            "is_default": 1 if is_default else 0,
                            "status": status,
                        }
                        if not data["bank_id"] or not data["bank_name"] or not data["bank_account"]:
                            st.error("bank_id / bank_name / bank_account 不能空。")
                        else:
                            try:
                                update_bank_account(int(selected_bank_id), data)
                                if data["is_default"]:
                                    set_default_bank_account(int(selected_sid), int(selected_bank_id))
                                st.success(_t("已更新。"))
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(_t("更新失敗：") + f"{e}")

                with st.expander(_t("停用 / 刪除（慎用）"), expanded=False):
                    s1, s2 = st.columns(2)
                    with s1:
                        new_status = "inactive" if (r.get("status") or "active") == "active" else "active"
                        btn_label = "停用" if new_status == "inactive" else "啟用"
                        if st.button(_t(btn_label), use_container_width=True, disabled=lock_bank):

                            auth.require_edit(PAGE_KEY)
                            try:
                                toggle_bank_account_status(int(selected_bank_id), new_status)
                                st.success(_t("已") + _t(btn_label) + "。")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(_t(btn_label) + _t("失敗：") + f"{e}")
                    with s2:
                        if st.button("刪除這筆帳戶", type="secondary", use_container_width=True, disabled=lock_bank):

                            auth.require_delete(PAGE_KEY)
                            try:
                                delete_bank_account(int(selected_bank_id))
                                st.success(_t("已刪除。"))
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(_t("刪除失敗：") + f"{e}")
