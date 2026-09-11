# C01_material_fixed_final.py
# C01 | 原料主檔 + 採購單價歷史（material_unit_price）
# - 查詢區：上一頁 / 下一頁 + 每頁筆數（10~50）
# - 下方新增/編輯區：可按鈕收起/展開
# - 「設定採購單價」：50% 寬的彈窗（白底、遮罩），顯示歷史紀錄 + 新增單價（自動結束舊價）
#
# Streamlit 1.51.0

from __future__ import annotations

from compact_layout import apply_compact_layout

apply_compact_layout()

import os
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import streamlit as st

import auth
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from core.i18n import tr as _raw_tr
except Exception:
    def _raw_tr(s: str) -> str:
        return s

I18N_FALLBACK = {
    "C01 原料主檔": {"en": "C01 Material Master", "vi": "C01 Hồ sơ vật liệu"},
    "全部供應商": {"en": "All Suppliers", "vi": "Tất cả nhà cung cấp"},
    "全部類別": {"en": "All Categories", "vi": "Tất cả danh mục"},
    "全部": {"en": "All", "vi": "Tất cả"},
    "啟用": {"en": "Active", "vi": "Đang hoạt động"},
    "停用": {"en": "Inactive", "vi": "Ngừng hoạt động"},
    "查詢": {"en": "Search", "vi": "Tra cứu"},
    "關鍵字（料號/料名）": {"en": "Keyword (Item Code / Item Name)", "vi": "Từ khóa (Mã vật liệu / Tên vật liệu)"},
    "供應商": {"en": "Supplier", "vi": "Nhà cung cấp"},
    "公斤/PCS": {"en": "Kg / PCS", "vi": "Kg / PCS"},
    "狀態": {"en": "Status", "vi": "Trạng thái"},
    "類別": {"en": "Category", "vi": "Danh mục"},
    "上一頁": {"en": "Previous", "vi": "Trang trước"},
    "下一頁": {"en": "Next", "vi": "Trang sau"},
    "每頁筆數": {"en": "Rows per page", "vi": "Số dòng mỗi trang"},
    "共 {total} 筆｜第 {page}/{max_page} 頁": {"en": "Total {total} records | Page {page}/{max_page}", "vi": "Tổng {total} dòng | Trang {page}/{max_page}"},
    "沒有符合條件的資料。": {"en": "No matching records.", "vi": "Không có dữ liệu phù hợp."},
    "設定採購單價": {"en": "Set Purchase Price", "vi": "Thiết lập đơn giá mua"},
    "請先在表格勾選一筆原料，再按設定單價。": {"en": "Please select one material first, then click Set Purchase Price.", "vi": "Vui lòng chọn một vật liệu trước rồi bấm Thiết lập đơn giá mua."},
    "展開新增/編輯區": {"en": "Expand Create/Edit", "vi": "Mở khu vực thêm/sửa"},
    "收起新增/編輯區": {"en": "Collapse Create/Edit", "vi": "Thu gọn khu vực thêm/sửa"},
    "新增 / 編輯原料": {"en": "Create / Edit Material", "vi": "Thêm / Sửa vật liệu"},
    "原料：{item_code}｜{item_name}": {"en": "Material: {item_code} | {item_name}", "vi": "Vật liệu: {item_code} | {item_name}"},
    "尚無採購單價紀錄；新增第一筆後會自動成為『目前採購單價』。": {"en": "No purchase price history yet. The first record will become the current purchase price automatically.", "vi": "Chưa có lịch sử đơn giá mua; sau khi thêm dòng đầu tiên sẽ tự động thành đơn giá mua hiện tại."},
    "新增／套用單價": {"en": "Add / Apply Price", "vi": "Thêm / Áp dụng đơn giá"},
    "新單價": {"en": "New Price", "vi": "Đơn giá mới"},
    "生效時間（開始）": {"en": "Effective Time (Start)", "vi": "Thời gian hiệu lực (bắt đầu)"},
    "停止時間（可空）": {"en": "End Time (Optional)", "vi": "Thời gian kết thúc (có thể bỏ trống)"},
    "新增後會自動關閉舊的『目前有效』單價（設定其 valid_to 並 current_flag=0），並插入新單價。": {"en": "After adding, the previous current price will be closed automatically, then the new price will be inserted.", "vi": "Sau khi thêm, đơn giá hiện tại cũ sẽ tự động kết thúc rồi chèn đơn giá mới."},
    "新增並套用": {"en": "Add and Apply", "vi": "Thêm và áp dụng"},
    "重新載入": {"en": "Reload", "vi": "Tải lại"},
    "重新整理": {"en": "Refresh", "vi": "Làm mới"},
    "已新增採購單價並套用。": {"en": "Purchase price added and applied.", "vi": "Đã thêm và áp dụng đơn giá mua."},
    "料號": {"en": "Item Code", "vi": "Mã vật liệu"},
    "料名": {"en": "Item Name", "vi": "Tên vật liệu"},
    "供應商簡稱": {"en": "Supplier Short Name", "vi": "Tên viết tắt NCC"},
    "供應商全名": {"en": "Supplier Name", "vi": "Tên đầy đủ NCC"},
    "供應商代碼": {"en": "Supplier Code", "vi": "Mã NCC"},
    "追蹤": {"en": "Tracking", "vi": "Theo dõi"},
    "原料種類": {"en": "Material Type", "vi": "Loại vật liệu"},
    "型制": {"en": "Type", "vi": "Kiểu"},
    "規格": {"en": "Specification", "vi": "Quy cách"},
    "規格單位": {"en": "Spec Unit", "vi": "Đơn vị quy cách"},
    "採購單位": {"en": "Purchase Unit", "vi": "Đơn vị mua"},
    "基礎單位": {"en": "Base Unit", "vi": "Đơn vị cơ bản"},
    "安全庫存": {"en": "Safety Stock", "vi": "Tồn kho an toàn"},
    "條碼": {"en": "Barcode", "vi": "Mã vạch"},
    "目前採購單價": {"en": "Current Purchase Price", "vi": "Đơn giá mua hiện tại"},
    "建檔人員": {"en": "Created By", "vi": "Người tạo"},
    "最後修改人": {"en": "Last Modified By", "vi": "Người sửa cuối"},
    "選取": {"en": "Select", "vi": "Chọn"},
    "勾選後可設定單價/編輯": {"en": "Select to set price or edit", "vi": "Chọn để thiết lập đơn giá hoặc chỉnh sửa"},
    "目前只支援一次選 1 筆來設定單價/編輯；已取第一筆。": {"en": "Only one row can be selected at a time; the first one has been used.", "vi": "Hiện chỉ hỗ trợ chọn 1 dòng mỗi lần; đã lấy dòng đầu tiên."},
    "料號與料名為必填。": {"en": "Item code and item name are required.", "vi": "Mã vật liệu và tên vật liệu là bắt buộc."},
    "新增成功": {"en": "Created successfully", "vi": "Thêm thành công"},
    "更新成功": {"en": "Updated successfully", "vi": "Cập nhật thành công"},
    "儲存": {"en": "Save", "vi": "Lưu"},
    "收起": {"en": "Collapse", "vi": "Thu gọn"},
    "追蹤模式": {"en": "Tracking Mode", "vi": "Chế độ theo dõi"},
    "主要供應商": {"en": "Main Supplier", "vi": "Nhà cung cấp chính"},
    "原料類別": {"en": "Material Category", "vi": "Danh mục vật liệu"},
    "型制(Type)": {"en": "Type", "vi": "Kiểu (Type)"},
}

def _get_lang() -> str:
    lang = st.session_state.get('lang') or st.session_state.get('language') or st.session_state.get('locale') or 'zh-TW'
    lang = str(lang)
    low = lang.lower()
    if low.startswith('en'):
        return 'en'
    if low.startswith('vi'):
        return 'vi'
    return 'zh-TW'


def _t(text: str, **kwargs: Any) -> str:
    lang = _get_lang()
    result = text
    try:
        raw = _raw_tr(text)
        if isinstance(raw, str) and raw and not raw.startswith('[MISS:'):
            result = raw
        else:
            fallback = I18N_FALLBACK.get(text)
            if fallback and lang in fallback:
                result = fallback[lang]
    except Exception:
        fallback = I18N_FALLBACK.get(text)
        if fallback and lang in fallback:
            result = fallback[lang]
    if kwargs:
        try:
            result = result.format(**kwargs)
        except Exception:
            pass
    return result


# =========================
# Config
# =========================
DEFAULT_USER_ID = 1  # TODO: replace with login session user id
PAGE_KEY = "C01_material"
PAGE_SIZE_OPTIONS = [10, 20, 30, 50, 100]
DEFAULT_PAGE_SIZE = 20

st.set_page_config(page_title=_t("C01 原料主檔"), layout="wide")

# 權限守門：可看見
auth.require_read(PAGE_KEY)
USER_ID = int(st.session_state.get("user_id", DEFAULT_USER_ID))


# Page background + modal CSS
st.markdown(
    """
<style>
  
  @import url('https://fonts.googleapis.com/css2?family=Libre+Barcode+39+Text&display=swap');
.stApp { background: #e9f4ff; }
  .section-title { font-size: 1rem; font-weight: 600; margin: 0.25rem 0 0.5rem 0; }

  /* Modal overlay + box */
  .ordo-modal-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.35);
    z-index: 10000;
  }
  .ordo-modal {
    position: fixed;
    top: 8vh;
    left: 25vw;
    width: 50vw;
    max-height: 84vh;
    overflow-y: auto;
    background: #ffffff;
    border-radius: 14px;
    padding: 18px 18px 6px 18px;
    z-index: 10001;
    box-shadow: 0 12px 32px rgba(0,0,0,0.25);
  }
  @media (max-width: 1100px) {
    .ordo-modal { left: 6vw; width: 88vw; }
  }

  /* Keep the master-list work area inside one desktop viewport.  Records
     scroll within the editor; the application page itself stays compact. */
  div[data-testid="stDataEditor"] {
    border: 1px solid rgba(49, 51, 63, 0.16);
    border-radius: 8px;
    overflow: hidden;
  }
</style>
    """,
    unsafe_allow_html=True,
)


# =========================
# DB helpers
# =========================
@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    """Prefer project db.py:get_engine(), fallback to env MYSQL_*"""
    try:
        from db import get_engine as _get_engine  # type: ignore

        eng = _get_engine()
        if eng is not None:
            return eng
    except Exception:
        pass

    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "")

    if not database:
        raise RuntimeError(
            "找不到 MySQL 設定：請確認專案根目錄有 db.py（含 get_engine），或設定 MYSQL_DATABASE 環境變數。"
        )

    from urllib.parse import quote_plus

    pwd = quote_plus(password)
    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def fetch_df(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    eng = get_engine()
    with eng.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def fetch_scalar(sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
    eng = get_engine()
    with eng.connect() as conn:
        res = conn.execute(text(sql), params or {})
        row = res.first()
        return None if row is None else row[0]


def exec_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> int:
    eng = get_engine()
    with eng.begin() as conn:
        res = conn.execute(text(sql), params or {})
        return int(getattr(res, "rowcount", 0) or 0)


def force_refresh_c01_material_table() -> None:
    """Clear C01 cached lookup/table state and reset master-table widget state."""
    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.session_state.c01_selected_item_id = None
    st.session_state.c01_price_dialog_open = False
    st.session_state.pop("c01_price_item_id", None)
    st.session_state.c01_last_sig = None
    st.session_state["c01_table_seed"] = int(st.session_state.get("c01_table_seed", 0)) + 1


# =========================
# Lookups
# =========================
@st.cache_data(show_spinner=False, ttl=300)
def load_suppliers() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT supplier_id, supplier_name, supplier_code, supplier_shortname
        FROM supplier
        WHERE is_active = 1
        ORDER BY supplier_shortname, supplier_name
        """
    )


@st.cache_data(show_spinner=False, ttl=300)
def load_material_categories() -> pd.DataFrame:
    return fetch_df(
        """
        SELECT material_category_id, material_name
        FROM material_categories
        ORDER BY material_category_id
        """
    )


# =========================
# Schema helpers (ENUM / SET)
# =========================
@st.cache_data(show_spinner=False, ttl=300)
def load_enum_meta(table_name: str, column_name: str) -> Tuple[list[str], bool]:
    """Return (enum_values, is_nullable). If not enum/set or not found, returns ([], True)."""
    try:
        meta = fetch_df(
            """
            SELECT COLUMN_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :t
              AND COLUMN_NAME = :c
            """,
            {"t": table_name, "c": column_name},
        )
        if meta.empty:
            return [], True

        col_type = str(meta.iloc[0]["COLUMN_TYPE"] or "")
        is_nullable = str(meta.iloc[0]["IS_NULLABLE"] or "YES").upper() == "YES"

        m = re.match(r"^(enum|set)\((.*)\)$", col_type, flags=re.IGNORECASE)
        if not m:
            return [], is_nullable

        inner = m.group(2).strip()

        values: list[str] = []
        buf = ""
        in_quote = False
        i = 0
        while i < len(inner):
            ch = inner[i]
            if ch == "'" and (i == 0 or inner[i - 1] != "\\"):
                in_quote = not in_quote
                i += 1
                continue
            if ch == "," and not in_quote:
                v = buf.strip()
                if v:
                    values.append(v)
                buf = ""
                i += 1
                continue
            buf += ch
            i += 1
        tail = buf.strip()
        if tail:
            values.append(tail)

        clean: list[str] = []
        for v in values:
            v2 = v.strip()
            if len(v2) >= 2 and v2[0] == "'" and v2[-1] == "'":
                v2 = v2[1:-1]
            clean.append(v2)
        return clean, is_nullable
    except Exception:
        return [], True


@st.cache_data(show_spinner=False, ttl=300)
def load_distinct_values(table_name: str, column_name: str) -> list[str]:
    """Fallback when column is not ENUM/SET in schema."""
    try:
        dfv = fetch_df(
            f"SELECT DISTINCT {column_name} AS v FROM {table_name} WHERE {column_name} IS NOT NULL ORDER BY {column_name}",
        )
        vals = [str(x) for x in dfv["v"].tolist() if x is not None and str(x).strip() != ""]
        return vals
    except Exception:
        return []
# =========================
# Materials queries
# =========================
def build_where(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    where = ["1=1"]
    params: Dict[str, Any] = {}

    kw = (filters.get("keyword") or "").strip()
    if kw:
        where.append("(m.item_code LIKE :kw OR m.item_name LIKE :kw)")
        params["kw"] = f"%{kw}%"

    supplier_id = filters.get("supplier_id")
    if supplier_id:
        where.append("m.supplier_id = :supplier_id")
        params["supplier_id"] = supplier_id

    tracking = filters.get("tracking")
    if tracking and tracking != "全部":
        where.append("m.TrackingMod = :tracking")
        params["tracking"] = tracking

    statute = filters.get("statute")
    if statute and statute != "全部":
        where.append("m.statute = :statute")
        params["statute"] = 1 if statute == "啟用" else 0

    cat_id = filters.get("material_category_id")
    if cat_id:
        where.append("m.material_category = :cat_id")
        params["cat_id"] = cat_id

    return " AND ".join(where), params


def count_materials(filters: Dict[str, Any]) -> int:
    where_sql, params = build_where(filters)
    n = fetch_scalar(
        f"""
        SELECT COUNT(*)
        FROM material m
        LEFT JOIN supplier s ON s.supplier_id = m.supplier_id
        LEFT JOIN material_categories mc ON mc.material_category_id = m.material_category
        WHERE {where_sql}
        """,
        params,
    )
    return int(n or 0)


def load_materials_page(filters: Dict[str, Any], limit: int, offset: int) -> pd.DataFrame:
    where_sql, params = build_where(filters)
    params.update({"limit": int(limit), "offset": int(offset)})

    return fetch_df(
        f"""
        SELECT
          m.item_id,
          m.item_code,
          m.item_name,
          m.material_type,
          m.Type,
          m.specification,
          m.specification_unit,
          m.TrackingMod,
          m.purchase_unit,
          m.base_unit,
          m.safety_stock,
          m.material_barcode,
          m.statute,
          mc.material_name AS material_category_name,
          s.supplier_shortname,
          s.supplier_name,
          s.supplier_code,
          mup.material_unit_price AS current_purchase_price,
          COALESCE(creator_stuff.stuff_name, creator_user.user_code, CONCAT('User#', m.created_by_id)) AS created_by_name,
          CASE
            WHEN m.updated_by_id IS NULL OR m.updated_at IS NULL THEN ''
            ELSE COALESCE(updater_stuff.stuff_name, updater_user.user_code, CONCAT('User#', m.updated_by_id))
          END AS updated_by_name
        FROM material m
        LEFT JOIN supplier s ON s.supplier_id = m.supplier_id
        LEFT JOIN material_categories mc ON mc.material_category_id = m.material_category
        LEFT JOIN material_unit_price mup
               ON mup.material_item_id = m.item_id AND mup.valid_to IS NULL
        LEFT JOIN `user` creator_user ON creator_user.user_id = m.created_by_id
        LEFT JOIN stuff creator_stuff ON creator_stuff.stuff_id = creator_user.stuff_id
        LEFT JOIN `user` updater_user ON updater_user.user_id = m.updated_by_id
        LEFT JOIN stuff updater_stuff ON updater_stuff.stuff_id = updater_user.stuff_id
        WHERE {where_sql}
        ORDER BY m.item_id ASC
        LIMIT :limit OFFSET :offset
        """,
        params,
    )


# =========================
# Price history
# =========================
def load_price_history(material_item_id: int) -> pd.DataFrame:
    return fetch_df(
        """
        SELECT
          mup.material_price_id,
          mup.material_unit_price,
          mup.valid_from,
          mup.valid_to,
          mup.created_at,
          u.user_code AS created_by
        FROM material_unit_price mup
        LEFT JOIN user u ON u.user_id = mup.created_by
        WHERE mup.material_item_id = :mid
        ORDER BY mup.valid_from DESC, mup.material_price_id DESC
        """,
        {"mid": int(material_item_id)},
    )


def set_purchase_price(
    material_item_id: int,
    unit_price: Decimal,
    valid_from_dt: datetime,
    user_id: int,
    valid_to_dt: Optional[datetime] = None,
) -> None:
    """Set purchase unit price with history.

    Rules:
      1) If there is a current price (current_flag=1), close it by setting valid_to=valid_from_dt and current_flag=0.
      2) Insert the new price as current (current_flag=1, valid_to NULL).

    This design matches P01 behavior and works with UNIQUE(material_item_id, current_flag) when current_flag=1.
    """
    eng = get_engine()
    now = datetime.now()

    with eng.begin() as conn:
        # Try update with current_flag (preferred). If the column does not exist, fallback to valid_to IS NULL.
        try:
            conn.execute(
                text(
                    """
                    UPDATE material_unit_price
                    SET valid_to = :new_start,
                        current_flag = 0
                    WHERE material_item_id = :mid
                      AND current_flag = 1
                    """
                ),
                {"new_start": valid_from_dt, "mid": int(material_item_id)},
            )
        except Exception:
            # Fallback for older schema
            conn.execute(
                text(
                    """
                    UPDATE material_unit_price
                    SET valid_to = :new_start
                    WHERE material_item_id = :mid AND valid_to IS NULL
                    """
                ),
                {"new_start": valid_from_dt, "mid": int(material_item_id)},
            )

        # Insert new price
        # If valid_to_dt is provided, treat it as a closed (non-current) record.
        current_flag_val = 1 if valid_to_dt is None else 0

        # Prefer including current_flag if column exists.
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO material_unit_price (
                      material_item_id, material_unit_price, created_at, created_by, valid_from, valid_to, current_flag
                    ) VALUES (
                      :mid, :price, :created_at, :created_by, :valid_from, :valid_to, :current_flag
                    )
                    """
                ),
                {
                    "mid": int(material_item_id),
                    "price": unit_price,
                    "created_at": now,
                    "created_by": int(user_id),
                    "valid_from": valid_from_dt,
                    "valid_to": valid_to_dt,
                    "current_flag": int(current_flag_val),
                },
            )
        except Exception:
            conn.execute(
                text(
                    """
                    INSERT INTO material_unit_price (
                      material_item_id, material_unit_price, created_at, created_by, valid_from, valid_to
                    ) VALUES (
                      :mid, :price, :created_at, :created_by, :valid_from, :valid_to
                    )
                    """
                ),
                {
                    "mid": int(material_item_id),
                    "price": unit_price,
                    "created_at": now,
                    "created_by": int(user_id),
                    "valid_from": valid_from_dt,
                    "valid_to": valid_to_dt,
                },
            )

        # 設定採購單價也視為原料主檔被異動，更新最後修改人。
        conn.execute(
            text(
                """
                UPDATE material
                SET updated_by_id = :user_id,
                    updated_at = :updated_at
                WHERE item_id = :mid
                """
            ),
            {"user_id": int(user_id), "updated_at": now, "mid": int(material_item_id)},
        )


# =========================
# UI utils
# =========================
def _filters_signature(filters: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        (filters.get("keyword") or "").strip(),
        filters.get("supplier_id") or 0,
        filters.get("tracking") or "",
        filters.get("statute") or "",
        filters.get("material_category_id") or 0,
    )


def _parse_decimal(x: Any) -> Decimal:
    if x is None:
        raise InvalidOperation
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


def _supplier_options(suppliers_df: pd.DataFrame) -> Tuple[list[str], Dict[str, int]]:
    options = ["全部供應商"]
    mapping: Dict[str, int] = {}

    if suppliers_df is None or suppliers_df.empty:
        return options, mapping

    # Robust: accept supplier_shortname / supplier_name missing, avoid KeyError
    for r in suppliers_df.itertuples(index=False):
        sid = getattr(r, "supplier_id", None)
        if sid is None:
            continue
        name = getattr(r, "supplier_shortname", None) or getattr(r, "supplier_name", None) or f"Supplier {sid}"
        code = getattr(r, "supplier_code", None)
        label = f"{name} ({code})" if code else str(name)
        options.append(label)
        mapping[label] = int(sid)

    return options, mapping


def _ensure_price_dialog_css() -> None:
    """Try to force st.dialog to ~50vw width.

    Streamlit's dialog size API is limited; this CSS is best-effort.
    """
    st.markdown(
        """
        <style>
        /* Backdrop: darker so user knows background is disabled */
        div[data-testid="stDialog"]::backdrop { background: rgba(0,0,0,0.45); }

        /* Dialog container width */
        div[data-testid="stDialog"] > div[role="dialog"] {
            width: 50vw !important;
            max-width: 50vw !important;
            min-width: 50vw !important;
        }

        /* Content area spacing */
        div[data-testid="stDialog"] .stMarkdown { margin-bottom: 0.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.dialog(_t("設定採購單價"), width="large")
def show_price_dialog(material_row: Dict[str, Any]) -> None:
    """Modal dialog for price history & create new price."""
    _ensure_price_dialog_css()

    item_id = int(material_row.get("item_id"))
    item_code = _safe_str(material_row.get("item_code"))
    item_name = _safe_str(material_row.get("item_name"))

    st.markdown(f"**原料：{item_code}｜{item_name}**")

    # -------- history --------
    hist = load_price_history(item_id)
    if hist.empty:
        st.info(_t("尚無採購單價紀錄；新增第一筆後會自動成為『目前採購單價』。"))
    else:
        show_cols = []
        for c in ["material_unit_price", "valid_from", "valid_to", "created_at", "created_by"]:
            if c in hist.columns:
                show_cols.append(c)
        view = hist[show_cols].copy() if show_cols else hist.copy()
        view = view.rename(columns={
            "material_unit_price": "採購單價",
            "valid_from": "起始時間",
            "valid_to": "停止時間",
            "created_at": "建立時間",
            "created_by": "建立者",
        })
        st.dataframe(view, use_container_width=True, height=220)

    st.markdown("---")
    st.subheader(_t("新增／套用單價"))

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        new_price = st.number_input(
            _t("新單價"),
            min_value=0.0,
            value=0.0,
            step=1.0,
            format="%.2f",
            help="將寫入 material_unit_price.material_unit_price (DECIMAL 10,2)",
        )
    with col2:
        start_dt = st.text_input(
            _t("生效時間（開始）"),
            value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            help="預設為現在。格式：YYYY-MM-DD HH:MM:SS",
        )
    with col3:
        stop_dt = st.text_input(
            _t("停止時間（可空）"),
            value="",
            help="留空代表目前有效。若填入，將寫入 valid_to。",
        )

    hint = "新增後會自動關閉舊的『目前有效』單價（設定其 valid_to 並 current_flag=0），並插入新單價。"
    st.caption(_t("新增後會自動關閉舊的『目前有效』單價（設定其 valid_to 並 current_flag=0），並插入新單價。"))

    cbtn1, cbtn2, cbtn3 = st.columns([1.2, 1.0, 2.0])
    with cbtn1:
        apply_clicked = st.button(_t("新增並套用"), type="primary", use_container_width=True)
    with cbtn2:
        reload_clicked = st.button(_t("重新載入"), use_container_width=True)

    if reload_clicked:
        st.rerun()

    if apply_clicked:
        try:
            if new_price is None:
                raise ValueError("新單價不可為空")
            unit_price = Decimal(str(new_price))
            valid_from = datetime.strptime(start_dt.strip(), "%Y-%m-%d %H:%M:%S")
            stop_val = stop_dt.strip()
            valid_to = None
            if stop_val:
                valid_to = datetime.strptime(stop_val, "%Y-%m-%d %H:%M:%S")
                if valid_to <= valid_from:
                    raise ValueError("停止時間必須晚於生效時間")

            # 先關閉舊價，再插入新價（若 new 有停止時間，則不設為 current）
            set_purchase_price(material_item_id=item_id, unit_price=unit_price, valid_from_dt=valid_from, user_id=USER_ID, valid_to_dt=valid_to)

            st.success(_t("已新增採購單價並套用。"))
            # Close dialog by clearing selection and rerun
            st.session_state.pop("c01_price_item_id", None)
            st.rerun()
        except Exception as e:
            st.error(f"設定採購單價失敗：{e}")


# =========================
# Main
# =========================
def main() -> None:
    # Session init
    if "c01_page" not in st.session_state:
        st.session_state.c01_page = 1
    if "c01_page_size" not in st.session_state:
        st.session_state.c01_page_size = DEFAULT_PAGE_SIZE
    if "c01_last_sig" not in st.session_state:
        st.session_state.c01_last_sig = None
    if "c01_selected_item_id" not in st.session_state:
        st.session_state.c01_selected_item_id = None
    if "c01_price_dialog_open" not in st.session_state:
        st.session_state.c01_price_dialog_open = False
    if "c01_form_open" not in st.session_state:
        st.session_state.c01_form_open = False
    if "c01_table_seed" not in st.session_state:
        st.session_state.c01_table_seed = 0
    # 新增成功後用 seed 換掉新增表單的 widget key，避免 Streamlit 沿用舊的料號/料名。
    # 料號產生規則仍維持 get_next_material_code()：M00001、M00002...
    if "c01_new_form_seed" not in st.session_state:
        st.session_state.c01_new_form_seed = 0

    st.title(_t("C01 原料主檔"))

    suppliers_df = load_suppliers()
    cats_df = load_material_categories()

    supplier_options, supplier_map = _supplier_options(suppliers_df)
    cat_options = ["全部類別"]
    cat_map: Dict[str, int] = {}
    if cats_df is not None and not cats_df.empty:
        for r in cats_df.itertuples(index=False):
            cid = getattr(r, "material_category_id", None)
            name = getattr(r, "material_name", None)
            if cid is None or name is None:
                continue
            label = f"{name} ({cid})"
            cat_options.append(label)
            cat_map[label] = int(cid)

    # =========================
    # Query panel
    # =========================
    with st.container():
        st.markdown(f"<div class='section-title'>{_t('查詢')}</div>", unsafe_allow_html=True)
        q1, q2, q3, q4, q5 = st.columns([0.32, 0.22, 0.16, 0.16, 0.14])
        with q1:
            keyword = st.text_input(_t("關鍵字（料號/料名）"), value=st.session_state.get("c01_kw", ""))
        with q2:
            supplier_label = st.selectbox(
                _t("供應商"),
                supplier_options,
                index=supplier_options.index(st.session_state.get("c01_supplier", "全部供應商"))
                if st.session_state.get("c01_supplier", "全部供應商") in supplier_options
                else 0,
            )
        with q3:
            tracking = st.selectbox(
                _t("公斤/PCS"),
                ["全部", "公斤", "PCS"],
                index=["全部", "weight", "PCS"].index(st.session_state.get("c01_tracking", "全部"))
                if st.session_state.get("c01_tracking", "全部") in ["全部", "weight", "PCS"]
                else 0,
            )
        with q4:
            statute = st.selectbox(
                _t("狀態"),
                ["全部", "啟用", "停用"],
                index=["全部", "啟用", "停用"].index(st.session_state.get("c01_statute", "全部"))
                if st.session_state.get("c01_statute", "全部") in ["全部", "啟用", "停用"]
                else 0,
            )
        with q5:
            cat_label = st.selectbox(
                _t("類別"),
                cat_options,
                index=cat_options.index(st.session_state.get("c01_cat", "全部類別"))
                if st.session_state.get("c01_cat", "全部類別") in cat_options
                else 0,
            )

        # store filters
        st.session_state.c01_kw = keyword
        st.session_state.c01_supplier = supplier_label
        st.session_state.c01_tracking = tracking
        st.session_state.c01_statute = statute
        st.session_state.c01_cat = cat_label

        supplier_id = supplier_map.get(supplier_label)
        cat_id = cat_map.get(cat_label)

        filters = {
            "keyword": keyword,
            "supplier_id": supplier_id,
            "tracking": tracking,
            "statute": statute,
            "material_category_id": cat_id,
        }

        # reset page when filters change
        sig = _filters_signature(filters)
        if st.session_state.c01_last_sig != sig:
            st.session_state.c01_last_sig = sig
            st.session_state.c01_page = 1
        # pagination controls（每頁筆數放在上一頁、下一頁中間）
        _sp, p1, p2, p3 = st.columns([0.52, 0.14, 0.16, 0.14], vertical_alignment="bottom")
        with _sp:
            st.empty()
        with p1:
            if st.button(_t("上一頁"), use_container_width=True):
                st.session_state.c01_page = max(1, int(st.session_state.c01_page) - 1)
        with p2:
            page_size = st.selectbox(
                _t("每頁筆數"),
                PAGE_SIZE_OPTIONS,
                index=PAGE_SIZE_OPTIONS.index(int(st.session_state.c01_page_size))
                if int(st.session_state.c01_page_size) in PAGE_SIZE_OPTIONS
                else PAGE_SIZE_OPTIONS.index(DEFAULT_PAGE_SIZE),
            )
            if int(page_size) != int(st.session_state.c01_page_size):
                st.session_state.c01_page_size = int(page_size)
                st.session_state.c01_page = 1
        with p3:
            if st.button(_t("下一頁"), use_container_width=True):
                st.session_state.c01_page = int(st.session_state.c01_page) + 1

    st.divider()

    # =========================
    # Materials table
    # =========================
    total = count_materials(filters)
    page = int(st.session_state.c01_page)
    limit = int(st.session_state.c01_page_size)
    max_page = max(1, (total + limit - 1) // limit)
    if page > max_page:
        st.session_state.c01_page = max_page
        page = max_page

    offset = (page - 1) * limit
    df = load_materials_page(filters, limit=limit, offset=offset)

    st.caption(_t("共 {total} 筆｜第 {page}/{max_page} 頁", total=total, page=page, max_page=max_page))

    if df.empty:
        st.info(_t("沒有符合條件的資料。"))
    else:
        show = df.copy()
        if "選取" not in show.columns:
            show.insert(0, "選取", False)

        # friendly column names (translated headers)
        # Keep the checkbox column name in a variable, because after language switching
        # the dataframe column is no longer literally "選取".
        select_col = _t("選取")

        show.rename(
            columns={
                "選取": select_col,
                "item_code": _t("料號"),
                "item_name": _t("料名"),
                "supplier_shortname": _t("供應商簡稱"),
                "supplier_name": _t("供應商全名"),
                "supplier_code": _t("供應商代碼"),
                "TrackingMod": _t("追蹤"),
                "material_type": _t("原料種類"),
                "Type": _t("型制"),
                "specification": _t("規格"),
                "specification_unit": _t("規格單位"),
                "purchase_unit": _t("採購單位"),
                "base_unit": _t("基礎單位"),
                "safety_stock": _t("安全庫存"),
                "material_barcode": _t("條碼"),
                "material_category_name": _t("類別"),
                "statute": _t("狀態"),
                "current_purchase_price": _t("目前採購單價"),
                "created_by_name": _t("建檔人員"),
                "updated_by_name": _t("最後修改人"),
            },
            inplace=True,
        )

        # status mapping (value text follows current language too)
        status_col = _t("狀態")
        if status_col in show.columns:
            show[status_col] = show[status_col].map(lambda v: _t("啟用") if int(v or 0) == 1 else _t("停用"))

        # Use item_id as hidden index for selection tracking (avoid showing item_id twice)
        if "item_id" in show.columns:
            show.index = df["item_id"].astype(int)
            show.index.name = "item_id"
            show.drop(columns=["item_id"], inplace=True)

        # Defensive: if any duplicated translated columns exist, keep the first.
        # This prevents PyArrow / Streamlit from crashing when translation terms collide.
        if show.columns.duplicated().any():
            show = show.loc[:, ~show.columns.duplicated()].copy()

        # Audit columns must always be the final two visible columns in the master table.
        # This keeps responsibility tracking in a fixed position: second-last = creator, last = last editor.
        audit_cols = [_t("建檔人員"), _t("最後修改人")]
        for audit_col in audit_cols:
            if audit_col not in show.columns:
                show[audit_col] = ""
            show[audit_col] = show[audit_col].fillna("")
        non_audit_cols = [c for c in show.columns if c not in audit_cols]
        show = show[non_audit_cols + audit_cols]

        edited = st.data_editor(
            show,
            use_container_width=True,
            hide_index=True,
            height=360,
            disabled=[c for c in show.columns if c != select_col],
            column_config={
                select_col: st.column_config.CheckboxColumn(select_col, help=_t("勾選後可設定單價/編輯")),
            },
            key=f"c01_table_{st.session_state.get('c01_table_seed', 0)}_{_get_lang()}",
        )

        selected_ids = edited.index[edited[select_col] == True].tolist()  # noqa: E712
        if len(selected_ids) == 0:
            st.session_state.c01_selected_item_id = None
        else:
            # only take first
            st.session_state.c01_selected_item_id = int(selected_ids[0])
            if len(selected_ids) > 1:
                st.warning("目前只支援一次選 1 筆來設定單價/編輯；已取第一筆。")


    # action buttons under table
    b1, b2, b3, _bsp = st.columns([0.18, 0.14, 0.22, 0.46])
    with b1:
        if st.button(_t("設定採購單價"), type="primary", use_container_width=True):
            auth.require_edit(PAGE_KEY)
            if not st.session_state.c01_selected_item_id:
                st.warning(_t("請先在表格勾選一筆原料，再按設定單價。"))
            else:
                st.session_state.c01_price_item_id = int(st.session_state.c01_selected_item_id)
                st.session_state.c01_price_dialog_open = True
    with b2:
        if st.button(_t("重新整理"), key="c01_refresh_master_table", use_container_width=True):
            force_refresh_c01_material_table()
            st.rerun()
    with b3:
        label = _t("收起新增/編輯區") if st.session_state.c01_form_open else _t("展開新增/編輯區")
        if st.button(label, use_container_width=True):
            st.session_state.c01_form_open = not st.session_state.c01_form_open

    # =========================
    # Price dialog
    # =========================
    # NOTE:
    # Streamlit 的 st.dialog 關閉（右上角 X）不會自動把 session_state 的旗標清掉。
    # 如果我們讓 c01_price_dialog_open 持續為 True，下一次你只是「勾選原料」觸發 rerun，
    # 也會被誤判為要再次開啟對話框（看起來像「一勾就跳」）。
    # 解法：對話框只開「一次」，開啟後立刻把旗標清回 False。
    if st.session_state.get("c01_price_dialog_open") and st.session_state.get("c01_selected_item_id"):
        # auto-reset: only open once per click
        st.session_state.c01_price_dialog_open = False

        mid = int(st.session_state.c01_selected_item_id)
        # locate row (may be off current page)
        row_df = df[df["item_id"].astype(int) == mid]
        if row_df.empty:
            row_df = fetch_df(
                """
                SELECT item_id, item_code, item_name
                FROM material
                WHERE item_id = :mid
                """,
                {"mid": mid},
            )
        material_row = row_df.iloc[0].to_dict() if not row_df.empty else {"item_id": mid}
        show_price_dialog(material_row)

    st.divider()

    # =========================
    # Create/Edit form (collapsible)
    # =========================
    if st.session_state.c01_form_open:
        st.markdown(f"<div class='section-title'>{_t('新增 / 編輯原料')}</div>", unsafe_allow_html=True)

        selected_id = st.session_state.c01_selected_item_id
        is_edit = bool(selected_id)
        default: Dict[str, Any] = {}
        if is_edit:
            d0 = fetch_df(
                """
                SELECT * FROM material WHERE item_id = :mid
                """,
                {"mid": int(selected_id)},
            )
            if not d0.empty:
                default = d0.iloc[0].to_dict()

        def get_next_material_code() -> str:
            # 只取符合 M00001 這種格式的最大值
            max_n = fetch_scalar(
                r"""
                SELECT MAX(CAST(SUBSTRING(item_code, 2, 5) AS UNSIGNED))
                FROM material
                WHERE item_code REGEXP '^M[0-9]{5}$'
                """
            )
            n = int(max_n or 0) + 1
            return f"M{n:05d}"

        if is_edit:
            mode_key = f"edit_{int(selected_id)}"
        else:
            mode_key = f"new_{int(st.session_state.get('c01_new_form_seed', 0))}"
            default = {"item_code": get_next_material_code(), "item_name": ""}

        # supplier pick
        supplier_opts_form, supplier_map_form = _supplier_options(suppliers_df)
        supplier_opts_form = [o for o in supplier_opts_form if o != "全部供應商"]
        if not supplier_opts_form:
            supplier_opts_form = ["(無供應商資料)"]
            supplier_map_form = {}

        # category pick
        cat_opts_form = [o for o in cat_options if o != "全部類別"]
        if not cat_opts_form:
            cat_opts_form = ["(無類別資料)"]
            cat_map_form: Dict[str, int] = {}
        else:
            cat_map_form = {k: v for k, v in cat_map.items()}

        item_code_default = _safe_str(default.get("item_code"))
        f1, f2, f3, f4 = st.columns([0.22, 0.32, 0.23, 0.23])
        with f1:
            item_code = st.text_input("料號 *", value=item_code_default, disabled=(not is_edit), key=f"c01_item_code_{mode_key}")
        with f2:
            item_name = st.text_input("料名 *", value=_safe_str(default.get("item_name")), key=f"c01_item_name_{mode_key}")
        with f3:
            track = st.selectbox(
                "追蹤模式",
                ["weight", "PCS"],
                index=0 if _safe_str(default.get("TrackingMod")) != "PCS" else 1,
            )
        with f4:
            statute_label = st.selectbox(
                _t("狀態"),
                ["啟用", "停用"],
                index=0 if int(default.get("statute") or 1) == 1 else 1,
            )
            statute_val = 1 if statute_label == "啟用" else 0

        g1, g2, g3, g4 = st.columns([0.26, 0.26, 0.24, 0.24])
        with g1:
            supplier_label_form = st.selectbox(
                "主要供應商",
                supplier_opts_form,
                index=0,
            )
            supplier_id_form = supplier_map_form.get(supplier_label_form)
        with g2:
            cat_label_form = st.selectbox(
                "原料類別",
                cat_opts_form,
                index=0,
            )
            cat_id_form = cat_map_form.get(cat_label_form)
        with g3:
            material_type = st.text_input("原料種類", value=_safe_str(default.get("material_type")))
        with g4:
            type_ = st.text_input("型制(Type)", value=_safe_str(default.get("Type")))

        # ---- ENUM dropdown options (規格單位 / 採購單位 / 基礎單位) ----
        spec_unit_vals, spec_unit_nullable = load_enum_meta("material", "specification_unit")
        if not spec_unit_vals:
            spec_unit_vals = ["mm", "cm"]

        purchase_unit_vals, purchase_unit_nullable = load_enum_meta("material", "purchase_unit")
        if not purchase_unit_vals:
            purchase_unit_vals = load_distinct_values("material", "purchase_unit")

        base_unit_vals, base_unit_nullable = load_enum_meta("material", "base_unit")
        if not base_unit_vals:
            base_unit_vals = load_distinct_values("material", "base_unit")

        def _enum_select(
            label: str,
            values: list[str],
            default_value: Any,
            nullable: bool,
            key: str,
        ) -> Optional[str]:
            opts = values.copy()
            blank_label = "（空白）"
            if nullable:
                opts = [blank_label] + opts

            dv = None if default_value is None else str(default_value)
            if nullable and (dv is None or dv.strip() == ""):
                idx = 0
            else:
                try:
                    idx = opts.index(dv)
                except Exception:
                    idx = 0 if nullable else 0

            sel = st.selectbox(label, opts, index=idx, key=key)
            if nullable and sel == blank_label:
                return None
            return str(sel)

        h1, h2, h3, h4 = st.columns([0.28, 0.18, 0.27, 0.27])
        with h1:
            spec = st.text_input("規格", value=_safe_str(default.get("specification")))
        with h2:
            specification_unit = _enum_select(
                "規格單位",
                spec_unit_vals,
                default.get("specification_unit"),
                nullable=spec_unit_nullable,
                key=f"c01_spec_unit_{mode_key}",
            )
        with h3:
            purchase_unit = _enum_select(
                "採購單位",
                purchase_unit_vals,
                default.get("purchase_unit"),
                nullable=purchase_unit_nullable,
                key=f"c01_purchase_unit_{mode_key}",
            )
        with h4:
            base_unit = _enum_select(
                "基礎單位",
                base_unit_vals,
                default.get("base_unit"),
                nullable=base_unit_nullable,
                key=f"c01_base_unit_{mode_key}",
            )

        i1, i2 = st.columns([0.24, 0.76])
        with i1:
            safety_stock = st.number_input(
                "安全庫存",
                min_value=0.0,
                value=float(default.get("safety_stock") or 0.0),
                step=1.0,
            )


        # 條碼預覽（置於儲存按鈕上方）
        def _normalize_code39(raw: str) -> str:
            c = (raw or "").strip()
            # 使用者或舊資料若存成 *CODE*，預覽與儲存時一律去掉首尾 *
            if len(c) >= 2 and c.startswith("*") and c.endswith("*"):
                c = c[1:-1].strip()
            return c


        def _to_code39_storage(raw_code: str) -> Optional[str]:
            code = _normalize_code39(raw_code)
            return f"*{code}*" if code else None


        preview_item_code = _normalize_code39(item_code)

        def _render_code39(code: str, font_size: int = 52):
            # Libre Barcode 39 Text 需要起訖 * 才能正確顯示 Code39/3 of 9
            disp = f"*{code}*"
            st.markdown(
                f"<div style='margin-top:6px; font-family:\"Libre Barcode 39 Text\"; font-size:{font_size}px; line-height:1;'>{disp}</div>"
                f"<div style='margin-top:-10px; opacity:0.7;'>{code}</div>",
                unsafe_allow_html=True,
            )

        # 只顯示一個條碼：有填「條碼」就顯示條碼；否則顯示料號
        code_to_show = preview_item_code
        if code_to_show:
            _render_code39(code_to_show, font_size=54)

        action1, action2 = st.columns([0.5, 0.5])
        with action1:
            if st.button(_t("儲存"), type="primary", use_container_width=True):
                auth.require_edit(PAGE_KEY)
                try:
                    if not item_code.strip() or not item_name.strip():
                        st.error(_t("料號與料名為必填。"))
                        st.stop()

                    if not is_edit:
                        exec_sql(
                            """
                            INSERT INTO material (
                              item_code, item_name, supplier_id,
                              Type, material_type, specification, specification_unit,
                              TrackingMod, material_category,
                              material_barcode, safety_stock,
                              statute, created_by_id, updated_by_id,
                              purchase_unit, base_unit
                            ) VALUES (
                              :item_code, :item_name, :supplier_id,
                              :Type, :material_type, :specification, :specification_unit,
                              :TrackingMod, :material_category,
                              :material_barcode, :safety_stock,
                              :statute, :created_by_id, :updated_by_id,
                              :purchase_unit, :base_unit
                            )
                            """,
                            {
                                "item_code": item_code.strip(),
                                "item_name": item_name.strip(),
                                "supplier_id": supplier_id_form,
                                "Type": type_.strip() or None,
                                "material_type": material_type.strip() or None,
                                "specification": spec.strip() or None,
                                "specification_unit": specification_unit,
                                "TrackingMod": track,
                                "material_category": cat_id_form,
                                "material_barcode": _to_code39_storage(item_code),
                                "safety_stock": Decimal(str(safety_stock)),
                                "statute": statute_val,
                                "created_by_id": USER_ID,
                                "updated_by_id": None,
                                "purchase_unit": purchase_unit.strip() or None,
                                "base_unit": base_unit.strip() or None,
                            },
                        )
                        # 新增成功後：
                        # 1) 清除表格勾選，避免下一輪被誤判為編輯模式。
                        # 2) 換掉新增表單 widget key，讓料名清空，料號重新依原本邏輯抓下一號。
                        # 3) 重置主表 key，讓新增資料與勾選狀態乾淨刷新。
                        st.session_state.c01_selected_item_id = None
                        st.session_state.c01_new_form_seed = int(st.session_state.get("c01_new_form_seed", 0)) + 1
                        st.session_state.c01_table_seed = int(st.session_state.get("c01_table_seed", 0)) + 1
                        st.success(_t("新增成功"))
                    else:
                        exec_sql(

                            """
                            UPDATE material
                            SET
                              item_code = :item_code,
                              item_name = :item_name,
                              supplier_id = :supplier_id,
                              Type = :Type,
                              material_type = :material_type,
                              specification = :specification,
                              specification_unit = :specification_unit,
                              TrackingMod = :TrackingMod,
                              material_category = :material_category,
                              material_barcode = :material_barcode,
                              safety_stock = :safety_stock,
                              statute = :statute,
                              updated_by_id = :updated_by_id,
                              updated_at = :updated_at,
                              purchase_unit = :purchase_unit,
                              base_unit = :base_unit
                            WHERE item_id = :item_id
                            """,
                            {
                                "item_id": int(selected_id),
                                "item_code": item_code.strip(),
                                "item_name": item_name.strip(),
                                "supplier_id": supplier_id_form,
                                "Type": type_.strip() or None,
                                "material_type": material_type.strip() or None,
                                "specification": spec.strip() or None,
                                "specification_unit": specification_unit,
                                "TrackingMod": track,
                                "material_category": cat_id_form,
                                "material_barcode": _to_code39_storage(item_code),
                                "safety_stock": Decimal(str(safety_stock)),
                                "statute": statute_val,
                                "updated_by_id": USER_ID,
                                "updated_at": datetime.now(),
                                "purchase_unit": purchase_unit.strip() or None,
                                "base_unit": base_unit.strip() or None,
                            },
                        )
                        st.success(_t("更新成功"))

                    # refresh list
                    st.session_state.c01_last_sig = None
                    st.rerun()

                except Exception as e:
                    st.error(f"儲存失敗：{e}")

        with action2:
            if st.button(_t("收起"), use_container_width=True):
                st.session_state.c01_form_open = False
                st.rerun()


if __name__ == "__main__":
    main()
