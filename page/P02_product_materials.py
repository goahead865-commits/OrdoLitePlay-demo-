# -*- coding: utf-8 -*-
"""
P02｜產品所需物料（用料表）
- 用料表明細一定顯示在 BOM 區塊內（不再混入「統計概覽」造成誤會）
- 用料表表格：只允許「勾選」，不允許表格內編輯
- 勾選後在下方同一個「新增 / 修正」區塊編輯 / 刪除
"""

import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd

apply_compact_layout()
from datetime import date
from typing import Any, Dict, Optional

import auth
from splitter_component import apply_vertical_splitter

try:
    from core.i18n import tr  # type: ignore
except Exception:
    def tr(text: str) -> str:
        return text

PAGE_KEY = "P02_product_materials"

_FALLBACK_I18N = {
    "P02｜產品所需物料": {"en": "P02 | Product Materials", "vi": "P02 | Nguyên vật liệu sản phẩm"},
    "產品清單（勾選一筆後，於下方維護用料表）": {"en": "Product List (Select one item, then maintain the BOM below)", "vi": "Danh sách sản phẩm (Chọn 1 dòng rồi bảo trì BOM bên dưới)"},
    "搜尋（產品代碼 / 品名 / 客戶 / 客戶料號）": {"en": "Search (Product Code / Name / Customer / Customer Part No.)", "vi": "Tìm kiếm (Mã SP / Tên / Khách hàng / Mã hàng KH)"},
    "顯示範圍": {"en": "Display Range", "vi": "Phạm vi hiển thị"},
    "只顯示啟用產品": {"en": "Active Products Only", "vi": "Chỉ hiển thị sản phẩm đang hoạt động"},
    "顯示全部產品": {"en": "All Products", "vi": "Hiển thị tất cả sản phẩm"},
    "只顯示停用產品": {"en": "Inactive Products Only", "vi": "Chỉ hiển thị sản phẩm ngừng hoạt động"},
    "每頁筆數": {"en": "Rows per Page", "vi": "Số dòng mỗi trang"},
    "上一頁": {"en": "Previous", "vi": "Trang trước"},
    "下一頁": {"en": "Next", "vi": "Trang sau"},
    "重新整理": {"en": "Refresh", "vi": "Làm mới"},
    "共": {"en": "Total", "vi": "Tổng"},
    "筆": {"en": "records", "vi": "dòng"},
    "第": {"en": "Page", "vi": "Trang"},
    "頁": {"en": "", "vi": ""},
    "查無產品。": {"en": "No products found.", "vi": "Không tìm thấy sản phẩm."},
    "本頁無資料（可能剛好被刪除或條件變更）。": {"en": "No data on this page (it may have been deleted or the filter changed).", "vi": "Trang này không có dữ liệu (có thể đã bị xóa hoặc điều kiện đã thay đổi)."},
    "選取": {"en": "Select", "vi": "Chọn"},
    "產品代碼": {"en": "Product Code", "vi": "Mã sản phẩm"},
    "客戶": {"en": "Customer", "vi": "Khách hàng"},
    "產品名稱": {"en": "Product Name", "vi": "Tên sản phẩm"},
    "客戶料號": {"en": "Customer Part No.", "vi": "Mã hàng khách"},
    "規格": {"en": "Specification", "vi": "Quy cách"},
    "顏色": {"en": "Color", "vi": "Màu sắc"},
    "單位": {"en": "Unit", "vi": "Đơn vị"},
    "一箱數量": {"en": "Qty/Carton", "vi": "Số lượng/thùng"},
    "啟用": {"en": "Active", "vi": "Kích hoạt"},
    "一次只勾選 1 筆產品": {"en": "Select only one product at a time", "vi": "Mỗi lần chỉ chọn 1 sản phẩm"},
    "請先勾選一筆產品。": {"en": "Please select a product first.", "vi": "Vui lòng chọn một sản phẩm trước."},
    "找不到所選產品（可能已被刪除）。請重新選取。": {"en": "Selected product not found (it may have been deleted). Please select again.", "vi": "Không tìm thấy sản phẩm đã chọn (có thể đã bị xóa). Vui lòng chọn lại."},
    "用料表": {"en": "BOM", "vi": "Bảng định mức NVL"},
    "條件（原料類別 → 供應商）": {"en": "Conditions (Material Category → Supplier)", "vi": "Điều kiện (Loại NVL → Nhà cung cấp)"},
    "原料類別": {"en": "Material Category", "vi": "Loại nguyên liệu"},
    "供應商（合作中）": {"en": "Supplier (Active)", "vi": "Nhà cung cấp (đang hợp tác)"},
    "用料表維度為「產品 + 供應商」。切換供應商即可切換 BOM。": {"en": "The BOM dimension is 'Product + Supplier'. Switch supplier to switch BOM.", "vi": "BOM được xác định theo 'Sản phẩm + Nhà cung cấp'. Đổi nhà cung cấp sẽ đổi BOM."},
    "找不到原料類別（material_categories）。": {"en": "Material categories not found (material_categories).", "vi": "Không tìm thấy loại nguyên liệu (material_categories)."},
    "此類別沒有合作中供應商。": {"en": "There are no active suppliers for this category.", "vi": "Loại này không có nhà cung cấp đang hợp tác."},
    "用料表明細（這張才是明細，不是統計）": {"en": "BOM Details (This is the detail table, not a summary)", "vi": "Chi tiết BOM (Đây là bảng chi tiết, không phải thống kê)"},
    "此供應商維度尚無用料明細。請在下方新增第一筆。": {"en": "No BOM items for this supplier yet. Please add the first one below.", "vi": "Nhà cung cấp này chưa có chi tiết BOM. Hãy thêm dòng đầu tiên bên dưới."},
    "新增 / 修正（用料表）": {"en": "Add / Edit (BOM)", "vi": "Thêm / Sửa (BOM)"},
    "未勾選明細：此區為新增模式。": {"en": "No detail selected: this area is in add mode.", "vi": "Chưa chọn dòng chi tiết: khu vực này đang ở chế độ thêm mới."},
    "物料（依供應商/類別）": {"en": "Material (by Supplier/Category)", "vi": "Vật liệu (theo NCC/Loại)"},
    "物料名稱（自動帶出）": {"en": "Material Name (Auto)", "vi": "Tên vật liệu (tự động)"},
    "原料用量": {"en": "Usage Qty", "vi": "Lượng dùng"},
    "計量單位": {"en": "UOM", "vi": "Đơn vị tính"},
    "損耗率(%)": {"en": "Scrap Rate (%)", "vi": "Tỷ lệ hao hụt (%)"},
    "備註": {"en": "Note", "vi": "Ghi chú"},
    "排序": {"en": "Sort", "vi": "Thứ tự"},
    "新增到用料表": {"en": "Add to BOM", "vi": "Thêm vào BOM"},
    "已新增。": {"en": "Added.", "vi": "Đã thêm."},
    "已儲存。": {"en": "Saved.", "vi": "Đã lưu."},
    "儲存修改": {"en": "Save Changes", "vi": "Lưu thay đổi"},
    "刪除": {"en": "Delete", "vi": "Xóa"},
    "確認刪除": {"en": "Confirm Delete", "vi": "Xác nhận xóa"},
    "已刪除。": {"en": "Deleted.", "vi": "Đã xóa."},
    "若你無法勾選，通常是看到「統計」而不是「明細」。此版已移除統計表，明細一定在上方。": {"en": "If you cannot select a row, you were probably looking at a summary instead of details. This version removes the summary table; details are always above.", "vi": "Nếu bạn không thể chọn, thường là vì bạn đang xem bảng thống kê chứ không phải chi tiết. Bản này đã bỏ bảng thống kê; chi tiết luôn ở phía trên."},
    "請重新勾選。": {"en": "Please reselect.", "vi": "Vui lòng chọn lại."},
    "找不到所選用料資料。請重新勾選。": {"en": "Selected BOM item not found. Please select again.", "vi": "Không tìm thấy dữ liệu BOM đã chọn. Vui lòng chọn lại."},
    "供應商": {"en": "Supplier", "vi": "Nhà cung cấp"},
    "物料名稱": {"en": "Material Name", "vi": "Tên vật liệu"},
    "此供應商在該類別下沒有任何原料（material 主檔可能未建）。": {"en": "This supplier has no materials under the selected category (material master may be incomplete).", "vi": "Nhà cung cấp này không có vật liệu trong loại đã chọn (có thể chưa tạo master material)."},
    "計量單位已改為 enum 下拉：g / PCS。": {"en": "UOM has been changed to an enum dropdown: g / PCS.", "vi": "Đơn vị tính đã đổi thành danh sách chọn: g / PCS."},
    "此原料缺少 material_category，請先補齊 material.material_category。": {"en": "This material lacks material_category. Please complete material.material_category first.", "vi": "Vật liệu này thiếu material_category. Vui lòng bổ sung material.material_category trước."},
    "一次請只勾選 1 筆。": {"en": "Please select only one record at a time.", "vi": "Mỗi lần chỉ chọn 1 dòng."},
}

def _get_lang() -> str:
    for key in ("lang", "language", "locale"):
        val = st.session_state.get(key)
        if val:
            return str(val)
    return "zh-TW"

def _t(text: str) -> str:
    try:
        result = tr(text)
        if isinstance(result, str) and result and not result.startswith("[MISS:"):
            return result
    except Exception:
        pass

    lang = _get_lang().lower()
    item = _FALLBACK_I18N.get(text)
    if not item:
        return text
    if lang.startswith("en"):
        return item.get("en", text)
    if lang.startswith("vi"):
        return item.get("vi", text)
    return text

# ------------------------------
# DB helpers（盡量相容你專案）
# ------------------------------
SQLA_OK = False
try:
    from sqlalchemy import text  # type: ignore
    SQLA_OK = True
except Exception:
    SQLA_OK = False

_MODE = None  # "sqlalchemy" / "dbapi" / "none"


def _get_mode() -> str:
    global _MODE
    if _MODE is not None:
        return _MODE

    try:
        from db import get_engine  # type: ignore
        eng = get_engine()
        if eng is not None:
            _MODE = "sqlalchemy"
            return _MODE
    except Exception:
        pass

    try:
        from db import get_connection  # type: ignore
        conn = get_connection()
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            _MODE = "dbapi"
            return _MODE
    except Exception:
        pass

    _MODE = "none"
    return _MODE


def _df_from_sql(sql_s: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    params = params or {}
    mode = _get_mode()

    if mode == "sqlalchemy":
        from db import get_engine  # type: ignore
        eng = get_engine()
        if eng is None:
            return pd.DataFrame()
        with eng.connect() as conn:
            if SQLA_OK:
                return pd.read_sql(text(sql_s), conn, params=params)
            return pd.read_sql(sql_s, conn)

    if mode == "dbapi":
        if params:
            st.error("DBAPI 模式不支援帶參數查詢；請改用 SQLAlchemy engine。")
            return pd.DataFrame()
        from db import get_connection  # type: ignore
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
        try:
            return pd.read_sql(sql_s, conn)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    st.error("DB 連線不可用：找不到 db.get_engine() 或 db.get_connection()")
    return pd.DataFrame()


def _exec_sql(sql_s: str, params: Optional[Dict[str, Any]] = None) -> None:
    params = params or {}
    mode = _get_mode()

    if mode == "sqlalchemy":
        from db import get_engine  # type: ignore
        eng = get_engine()
        if eng is None:
            raise RuntimeError("DB engine is None")
        with eng.begin() as conn:
            if SQLA_OK:
                conn.execute(text(sql_s), params)
            else:
                conn.execute(sql_s)
        return

    if mode == "dbapi":
        if params:
            raise RuntimeError("DBAPI 模式不支援 named params，請改用 SQLAlchemy engine。")
        from db import get_connection  # type: ignore
        conn = get_connection()
        if conn is None:
            raise RuntimeError("DB connection is None")
        try:
            cur = conn.cursor()
            cur.execute(sql_s)
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return

    raise RuntimeError("DB mode unsupported")


# ------------------------------
# SQL
# ------------------------------
SQL_PRODUCTS_COUNT = """
SELECT COUNT(*) AS cnt
FROM product p
LEFT JOIN customer c ON c.customer_id = p.customer_id
WHERE (:kw IS NULL OR :kw = ''
       OR p.product_code LIKE :kw_like
       OR p.product_name LIKE :kw_like
       OR p.customer_production_id LIKE :kw_like
       OR c.customer_shortname LIKE :kw_like
       OR c.customer_name LIKE :kw_like)
  AND (
      :active_mode = 0
      OR (:active_mode = 1 AND p.is_active = 1)
      OR (:active_mode = -1 AND p.is_active = 0)
  )
"""

SQL_PRODUCTS_PAGED = """
SELECT
  p.product_id,
  p.product_code,
  c.customer_shortname AS customer,
  p.customer_production_id,
  p.product_name,
  p.Specification,
  p.color,
  p.unit,
  p.qty_per_carton,
  p.is_active
FROM product p
LEFT JOIN customer c ON c.customer_id = p.customer_id
WHERE (:kw IS NULL OR :kw = ''
       OR p.product_code LIKE :kw_like
       OR p.product_name LIKE :kw_like
       OR p.customer_production_id LIKE :kw_like
       OR c.customer_shortname LIKE :kw_like
       OR c.customer_name LIKE :kw_like)
  AND (
      :active_mode = 0
      OR (:active_mode = 1 AND p.is_active = 1)
      OR (:active_mode = -1 AND p.is_active = 0)
  )
ORDER BY p.product_code
LIMIT :limit OFFSET :offset
"""


SQL_MATERIAL_CATEGORIES = """
SELECT material_category_id, material_category_code, material_name
FROM material_categories
ORDER BY material_category_code
"""

SQL_SUPPLIERS_BY_CATEGORY = """
SELECT
  s.supplier_id,
  s.supplier_code,
  s.supplier_shortname,
  COALESCE(sc.supplier_category_name, '') AS supplier_category_name,
  COALESCE(mc.material_name, '') AS material_category_name,
  CASE
    WHEN EXISTS (
      SELECT 1
      FROM material m
      WHERE m.supplier_id = s.supplier_id
        AND m.material_category = :cat_id
    ) THEN 1
    ELSE 0
  END AS has_material
FROM supplier s
LEFT JOIN supplier_category sc
  ON sc.supplier_category_id = s.supplier_category
LEFT JOIN material_categories mc
  ON mc.material_category_id = :cat_id
WHERE COALESCE(s.is_active, 1) = 1
  AND (
      -- 已經在 C01 建過此原料類別的供應商，一定要顯示
      EXISTS (
        SELECT 1
        FROM material m
        WHERE m.supplier_id = s.supplier_id
          AND m.material_category = :cat_id
      )
      -- C02 供應商分類與 C01 原料類別是兩張表，ID 不一定相同。
      -- 因此改用名稱比對，例如 supplier_category.塑膠粒 對 material_categories.塑膠粒。
      OR REPLACE(COALESCE(sc.supplier_category_name, ''), ' ', '') = REPLACE(COALESCE(mc.material_name, ''), ' ', '')
      OR COALESCE(sc.supplier_category_name, '') LIKE CONCAT('%', COALESCE(mc.material_name, ''), '%')
      OR COALESCE(mc.material_name, '') LIKE CONCAT('%', COALESCE(sc.supplier_category_name, ''), '%')
  )
ORDER BY has_material DESC, s.supplier_code
"""

SQL_ACTIVE_SUPPLIERS = """
SELECT
  s.supplier_id,
  s.supplier_code,
  s.supplier_shortname,
  COALESCE(sc.supplier_category_name, '') AS supplier_category_name,
  '' AS material_category_name,
  0 AS has_material
FROM supplier s
LEFT JOIN supplier_category sc
  ON sc.supplier_category_id = s.supplier_category
WHERE COALESCE(s.is_active, 1) = 1
ORDER BY s.supplier_code
"""

SQL_MATERIALS_BY_SUPPLIER_AND_CAT = """
SELECT
  m.item_id,
  m.item_code,
  m.item_name,
  m.material_category,
  mc.material_name AS material_category_name
FROM material m
LEFT JOIN material_categories mc
  ON mc.material_category_id = m.material_category
WHERE m.supplier_id = :supplier_id
  AND m.material_category = :cat_id
ORDER BY m.item_code
"""

# ✅ 優先選「有 bom_item 的 header」
SQL_BOM_HEADERS_FOR_PRODUCT_SUPPLIER = """
SELECT
  bh.bom_id
FROM bom_header bh
LEFT JOIN (
  SELECT bom_id, COUNT(*) AS item_cnt
  FROM bom_item
  GROUP BY bom_id
) x ON x.bom_id = bh.bom_id
WHERE bh.product_id = :product_id
  AND bh.supplier_id = :supplier_id
ORDER BY COALESCE(x.item_cnt, 0) DESC, bh.is_active DESC, bh.effective_date DESC, bh.bom_id DESC
LIMIT 1
"""

SQL_INSERT_BOM_HEADER = """
INSERT INTO bom_header (
  product_id, bom_code, bom_name, is_active, effective_date, note,
  created_at, created_by, updated_at, updated_by, supplier_id
) VALUES (
  :product_id, :bom_code, :bom_name, 1, :effective_date, :note,
  NOW(), :user_id, NOW(), :user_id, :supplier_id
)
"""

SQL_BOM_ITEMS = """
SELECT
  bom_item_id,
  material_category_id,
  material_category_name,
  supplier_id,
  supplier_stort_name,
  material_id,
  material_name,
  qty_per_parent,
  uom,
  ScrapRate,
  note,
  sort_order
FROM bom_item
WHERE bom_id = :bom_id
ORDER BY COALESCE(sort_order, 999999), bom_item_id
"""

SQL_INSERT_BOM_ITEM = """
INSERT INTO bom_item (
  bom_id,
  supplier_id,
  supplier_stort_name,
  material_id,
  material_name,
  qty_per_parent,
  uom,
  ScrapRate,
  note,
  sort_order,
  material_category_id,
  material_category_name
) VALUES (
  :bom_id,
  :supplier_id,
  :supplier_shortname,
  :material_id,
  :material_name,
  :qty_per_parent,
  :uom,
  :scrap_rate,
  :note,
  :sort_order,
  :material_category_id,
  :material_category_name
)
"""

SQL_UPDATE_BOM_ITEM = """
UPDATE bom_item
SET
  qty_per_parent = :qty_per_parent,
  uom = :uom,
  ScrapRate = :scrap_rate,
  note = :note,
  sort_order = :sort_order
WHERE bom_item_id = :bom_item_id
  AND bom_id = :bom_id
"""

SQL_DELETE_BOM_ITEM = """
DELETE FROM bom_item
WHERE bom_item_id = :bom_item_id
  AND bom_id = :bom_id
"""


# ------------------------------
# helpers
# ------------------------------
def _safe_like(kw: str) -> str:
    return f"%{kw.strip()}%"


def _pick_one_index(df: pd.DataFrame, select_col: str = "_select") -> Optional[int]:
    if df is None or getattr(df, "empty", True) or select_col not in df.columns:
        return None
    picked_idx = df.index[df[select_col] == True].tolist()
    if not picked_idx:
        return None
    if len(picked_idx) > 1:
        st.warning("一次請只勾選 1 筆。")
        return None
    try:
        return int(picked_idx[0])
    except Exception:
        return None


def _bom_code_auto(product_id: int, supplier_id: int) -> str:
    base = f"BOM{product_id:04d}{supplier_id:04d}"
    existing = _df_from_sql(
        "SELECT bom_code FROM bom_header WHERE product_id=:product_id AND supplier_id=:supplier_id",
        {"product_id": product_id, "supplier_id": supplier_id},
    )
    used = set(existing["bom_code"].astype(str).tolist()) if not existing.empty else set()
    for seq in range(1, 100):
        code = f"{base}{seq:02d}"
        if code not in used:
            return code
    return f"{base}99"


def _get_or_create_bom_header(product_id: int, supplier_id: int, user_id: int = 1) -> int:
    hdr = _df_from_sql(SQL_BOM_HEADERS_FOR_PRODUCT_SUPPLIER, {"product_id": product_id, "supplier_id": supplier_id})
    if not hdr.empty:
        return int(hdr.iloc[0]["bom_id"])

    bom_code = _bom_code_auto(product_id, supplier_id)
    # 權限：建立 BOM Header 屬於編輯行為
    auth.require_edit(PAGE_KEY)
    _exec_sql(
        SQL_INSERT_BOM_HEADER,
        {
            "product_id": product_id,
            "supplier_id": supplier_id,
            "bom_code": bom_code,
            "bom_name": "AUTO",
            "effective_date": date.today(),
            "note": "auto-created by P02",
            "user_id": user_id,
        },
    )
    hdr2 = _df_from_sql(SQL_BOM_HEADERS_FOR_PRODUCT_SUPPLIER, {"product_id": product_id, "supplier_id": supplier_id})
    if hdr2.empty:
        raise RuntimeError("建立 BOM Header 失敗：未能取得 bom_id")
    return int(hdr2.iloc[0]["bom_id"])



def _force_refresh_p02() -> None:
    """Clear cached data and reset P02 editor selections.

    Incrementing p02_refresh_seed changes the product master data_editor key
    after rerun, so old checkbox/editor state cannot stick to freshly queried data.
    """
    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.session_state["p02_refresh_seed"] = int(st.session_state.get("p02_refresh_seed", 0)) + 1

    for key in [
        "p02_selected_bom_item_id",
        "p02_last_edit_bid",
        "p02_last_ctx",
    ]:
        st.session_state.pop(key, None)


def _render_splitter() -> None:
    """Render the draggable divider used by the two independently scrolling panes."""
    components.html(
        """
        <style>
          html, body { margin: 0; overflow: hidden; background: transparent; }
          #splitter {
            height: 14px; display: flex; align-items: center; justify-content: center;
            cursor: row-resize; user-select: none; touch-action: none;
          }
          #splitter::before { content: ''; width: 100%; border-top: 1px solid rgba(49,51,63,.28); }
          #grip {
            position: absolute; padding: 0 12px; color: #52657b; background: #e9f4ff;
            font-size: 12px; letter-spacing: 3px; line-height: 14px;
          }
        </style>
        <div id="splitter" title="拖曳調整上下區域高度"><span id="grip">•••</span></div>
        <script>
          const splitter = document.getElementById('splitter');
          const parentDoc = window.parent && window.parent.document;
          const findPane = (key) => {
            const host = parentDoc && parentDoc.querySelector('.st-key-' + key);
            return host && (host.querySelector('[data-testid="stVerticalBlockBorderWrapper"]') || host);
          };
          let dragging = false, startY = 0, startTop = 0;
          const resize = (event) => {
            if (!dragging) return;
            const top = findPane('p02_top_pane');
            const bottom = findPane('p02_bottom_pane');
            if (!top || !bottom) return;
            const delta = event.clientY - startY;
            const newTop = Math.max(150, Math.min(520, startTop + delta));
            const newBottom = Math.max(180, window.parent.innerHeight - newTop - 185);
            top.style.height = newTop + 'px';
            top.style.overflowY = 'auto';
            bottom.style.height = newBottom + 'px';
            bottom.style.overflowY = 'auto';
          };
          splitter.addEventListener('pointerdown', (event) => {
            const top = findPane('p02_top_pane');
            if (!top) return;
            dragging = true; startY = event.clientY; startTop = top.getBoundingClientRect().height;
            splitter.setPointerCapture(event.pointerId); event.preventDefault();
          });
          splitter.addEventListener('pointermove', resize);
          splitter.addEventListener('pointerup', () => { dragging = false; });
          splitter.addEventListener('pointercancel', () => { dragging = false; });
        </script>
        """,
        height=14,
        scrolling=False,
    )


def _render_splitter() -> None:
    """Use a bidirectional component so drag events update Streamlit state."""
    result = render_vertical_splitter(
        int(st.session_state["p02_top_height"]),
        key="p02_vertical_splitter_control",
    )
    if not isinstance(result, dict) or "top_height" not in result:
        return
    next_height = max(200, min(600, int(result["top_height"])))
    if next_height != int(st.session_state["p02_top_height"]):
        st.session_state["p02_top_height"] = next_height
        st.rerun()


# ------------------------------
# Page
# ------------------------------
st.set_page_config(page_title=_t("P02｜產品所需物料"), layout="wide")

st.markdown(
    """
    <style>
    /* Two-panel P02 workspace: keep both the product list and BOM editor visible. */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        min-height: 1.55rem !important;
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
    }
    [data-testid="stTextInput"],
    [data-testid="stNumberInput"],
    [data-testid="stSelectbox"] {
        margin-bottom: 0 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 0.45rem 0.6rem !important;
    }
    [data-testid="stMetricLabel"] { font-size: 0.72rem !important; }
    [data-testid="stMetricValue"] { font-size: 1rem !important; }
    hr { margin: 0.25rem 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

auth.require_read(PAGE_KEY)
USER_ID = int(st.session_state.get("user_id", 1))
st.session_state.setdefault("p02_top_height", 350)
top_pane_height = int(st.session_state["p02_top_height"])
bottom_pane_height = max(300, 900 - top_pane_height)

st.title(_t("P02｜產品所需物料"))

# -----------------------------
# 產品清單
# -----------------------------
with st.container(border=True, height=top_pane_height, key="p02_top_pane"):
    st.subheader(_t("產品清單（勾選一筆後，於下方維護用料表）"))
    c1, c2, c3, c4, c5 = st.columns([3.4, 2.0, 1.0, 1.0, 1.0], vertical_alignment="bottom")
    with c1:
        kw = st.text_input(_t("搜尋（產品代碼 / 品名 / 客戶 / 客戶料號）"), value="", key="p02_kw")
    with c2:
        active_mode_label = st.selectbox(
            _t("顯示範圍"),
            options=[_t("只顯示啟用產品"), _t("顯示全部產品"), _t("只顯示停用產品")],
            index=0,
            key="p02_active_mode",
        )
    with c3:
        prev_btn = st.empty()
    with c4:
        page_size = st.selectbox(_t("每頁筆數"), options=[10, 20, 30, 50, 100], index=2, key="p02_page_size")
    with c5:
        next_btn = st.empty()

    active_mode_map = {_t("只顯示啟用產品"): 1, _t("顯示全部產品"): 0, _t("只顯示停用產品"): -1}
    active_mode = int(active_mode_map.get(active_mode_label, 1))
    kw_like = _safe_like(kw) if (kw or "").strip() else ""

    # ---- 分頁狀態：只要查詢條件改變，就回到第 1 頁
    sig = (str((kw or "").strip()), int(active_mode), int(page_size))
    if st.session_state.get("p02_prod_sig") != sig:
        st.session_state["p02_prod_sig"] = sig
        st.session_state["p02_prod_page"] = 0

    page = int(st.session_state.get("p02_prod_page", 0))
    page_size = int(page_size)

    cnt_df = _df_from_sql(
        SQL_PRODUCTS_COUNT,
        {"kw": (kw or "").strip(), "kw_like": kw_like, "active_mode": active_mode},
    )
    total = int(cnt_df.iloc[0]["cnt"]) if (not cnt_df.empty and "cnt" in cnt_df.columns) else 0
    if total <= 0:
        st.info(_t("查無產品。"))
        st.stop()

    total_pages = max(1, (total + page_size - 1) // page_size)
    if page > total_pages - 1:
        page = total_pages - 1
        st.session_state["p02_prod_page"] = page

    def _prev_page():
        st.session_state["p02_prod_page"] = max(0, int(st.session_state.get("p02_prod_page", 0)) - 1)

    def _next_page():
        st.session_state["p02_prod_page"] = min(total_pages - 1, int(st.session_state.get("p02_prod_page", 0)) + 1)

    with prev_btn:
        st.button(_t("上一頁"), on_click=_prev_page, disabled=(page <= 0), use_container_width=True)
    with next_btn:
        st.button(_t("下一頁"), on_click=_next_page, disabled=(page >= total_pages - 1), use_container_width=True)

    st.caption(f"{_t('共')} {total} {_t('筆')}｜{_t('第')} {page + 1} / {total_pages} {_t('頁')}")

    offset = page * page_size
    products = _df_from_sql(
        SQL_PRODUCTS_PAGED,
        {"kw": (kw or "").strip(), "kw_like": kw_like, "active_mode": active_mode, "limit": page_size, "offset": offset},
    )
    if products.empty:
        st.info(_t("本頁無資料（可能剛好被刪除或條件變更）。"))
        st.stop()

    grid = products.set_index("product_id").copy()
    grid.insert(0, "_select", False)

    # 用 page/sig 當 key，避免換頁後 checkbox 狀態殘留到別頁
    refresh_seed = int(st.session_state.get("p02_refresh_seed", 0))
    grid_key = f"p02_products_grid_p{page}_s{page_size}_{refresh_seed}_{hash(sig)}"

    edited = st.data_editor(
        grid,
        hide_index=True,
        use_container_width=True,
        height=210,
        column_config={
            "_select": st.column_config.CheckboxColumn(_t("選取"), help=_t("一次只勾選 1 筆產品")),
            "product_code": st.column_config.TextColumn(_t("產品代碼"), disabled=True),
            "customer": st.column_config.TextColumn(_t("客戶"), disabled=True),
            "product_name": st.column_config.TextColumn(_t("產品名稱"), disabled=True),
            "customer_production_id": st.column_config.TextColumn(_t("客戶料號"), disabled=True),
            "Specification": st.column_config.TextColumn(_t("規格"), disabled=True),
            "color": st.column_config.TextColumn(_t("顏色"), disabled=True),
            "unit": st.column_config.TextColumn(_t("單位"), disabled=True),
            "qty_per_carton": st.column_config.NumberColumn(_t("一箱數量"), disabled=True),
            "is_active": st.column_config.CheckboxColumn(_t("啟用"), disabled=True),
        },
        disabled=[c for c in grid.columns if c != "_select"],
        key=grid_key,
    )

    refresh_col, _ = st.columns([1.1, 6.0], vertical_alignment="center")
    with refresh_col:
        if st.button(_t("重新整理"), key="p02_refresh_master_table", use_container_width=True):
            _force_refresh_p02()
            st.rerun()

    selected_pid = _pick_one_index(edited, "_select")
    if selected_pid is None:
        apply_vertical_splitter("p02_top_height", "p02_vertical_splitter_control", default=350, min_top=200, max_top=600)
        st.info(_t("請先勾選一筆產品。"))
        st.stop()

apply_vertical_splitter("p02_top_height", "p02_vertical_splitter_control", default=350, min_top=200, max_top=600)

sel_df = products.loc[products["product_id"] == int(selected_pid)]
if sel_df.empty:
    st.warning(_t("找不到所選產品（可能已被刪除）。請重新選取。"))
    st.stop()
sel_row = sel_df.iloc[0].to_dict()

# -----------------------------
# 用料表（BOM）
# -----------------------------
with st.container(border=True, height=bottom_pane_height, key="p02_bottom_pane"):
    st.subheader(_t("用料表"))
    a1, a2, a3, a4 = st.columns([1.1, 2.2, 1.4, 1.3])
    with a1:
        st.metric(_t("產品代碼"), str(sel_row.get("product_code") or ""))
    with a2:
        st.metric(_t("產品名稱"), str(sel_row.get("product_name") or ""))
    with a3:
        st.metric(_t("客戶料號"), str(sel_row.get("customer_production_id") or ""))
    with a4:
        st.metric(_t("一箱數量"), "" if sel_row.get("qty_per_carton") is None else str(sel_row.get("qty_per_carton")))

    st.divider()

    st.markdown(f"##### {_t('條件（原料類別 → 供應商）')}")
    b1, b2, b3 = st.columns([2.2, 2.2, 3.6])

    cat_df = _df_from_sql(SQL_MATERIAL_CATEGORIES, {})
    if cat_df.empty:
        st.error(_t("找不到原料類別（material_categories）。"))
        st.stop()

    cat_labels, cat_map = [], {}
    for _, r in cat_df.iterrows():
        cid = int(r["material_category_id"])
        label = f"{r['material_category_code']} - {r['material_name']}"
        cat_labels.append(label)
        cat_map[label] = cid

    with b1:
        cat_label = st.selectbox(_t("原料類別"), options=cat_labels, key=f"p02_cat_{selected_pid}")
        cat_id = int(cat_map[cat_label])

    sup_df = _df_from_sql(SQL_SUPPLIERS_BY_CATEGORY, {"cat_id": cat_id})
    if sup_df.empty:
        # 保底：如果 supplier_category 名稱與 material_categories 名稱沒有對上，仍顯示所有合作中供應商，
        # 不要讓使用者以為 C02 的供應商不見了。
        sup_df = _df_from_sql(SQL_ACTIVE_SUPPLIERS, {})
        if sup_df.empty:
            st.warning(_t("此類別沒有合作中供應商。"))
            st.stop()
        st.warning("此原料類別沒有對應到 C02 的供應商分類，已暫時顯示全部合作中供應商。")

    sup_labels, sup_map = [], {}
    for _, r in sup_df.iterrows():
        sid = int(r["supplier_id"])
        has_material = int(r.get("has_material") or 0)
        supplier_cat = str(r.get("supplier_category_name") or "").strip()
        note = "" if has_material else "（尚未建此類別原料）"
        cat_note = f"｜{supplier_cat}" if supplier_cat else ""
        label = f"{r['supplier_code']} - {r['supplier_shortname']}{cat_note}{note}"
        sup_labels.append(label)
        sup_map[label] = {
            "supplier_id": sid,
            "supplier_code": str(r["supplier_code"]),
            "supplier_shortname": str(r["supplier_shortname"]),
            "has_material": has_material,
        }

    with b2:
        sup_label = st.selectbox(_t("供應商（合作中）"), options=sup_labels, key=f"p02_sup_{selected_pid}_{cat_id}")
        supplier_id = int(sup_map[sup_label]["supplier_id"])
        supplier_shortname = str(sup_map[sup_label]["supplier_shortname"])
        supplier_has_material = int(sup_map[sup_label].get("has_material") or 0)

    with b3:
        st.caption(_t("用料表維度為「產品 + 供應商」。切換供應商即可切換 BOM。"))
        if not supplier_has_material:
            st.warning("此供應商已建立於 C02，但 C01 尚未建立此原料類別的原料；請先到 C01 補原料主檔，避免 P02 建出空 BOM。")

    # 只有當此供應商已經有該類別原料時，才自動建立 BOM Header。
    # 否則只是讓供應商出現在下拉，並提示回 C01 補原料，避免選一下就產生一堆空 BOM。
    existing_bom_df = _df_from_sql(
        SQL_BOM_HEADERS_FOR_PRODUCT_SUPPLIER,
        {"product_id": int(selected_pid), "supplier_id": int(supplier_id)},
    )
    if supplier_has_material:
        bom_id = _get_or_create_bom_header(int(selected_pid), int(supplier_id), user_id=USER_ID)
    elif not existing_bom_df.empty:
        bom_id = int(existing_bom_df.iloc[0]["bom_id"])
    else:
        st.stop()

    st.divider()
    st.markdown(f"##### {_t('用料表明細（這張才是明細，不是統計）')}")

    items_df = _df_from_sql(SQL_BOM_ITEMS, {"bom_id": bom_id})

    # 清掉跨 BOM 的選取狀態（避免切換供應商後還卡住舊選取）
    sel_key = "p02_selected_bom_item_id"
    last_ctx_key = "p02_last_ctx"
    ctx = f"{selected_pid}-{cat_id}-{supplier_id}-{bom_id}"
    if st.session_state.get(last_ctx_key) != ctx:
        st.session_state[last_ctx_key] = ctx
        st.session_state.pop(sel_key, None)
        st.session_state.pop("p02_last_edit_bid", None)

    if items_df.empty:
        st.info(_t("此供應商維度尚無用料明細。請在下方新增第一筆。"))
    else:
        view_df = items_df.set_index("bom_item_id").copy()
        view_df.insert(0, "_select", False)

        # 隱藏 id 欄位，但保留 material_name 等要看的欄位
        drop_cols = [c for c in ["material_category_id", "supplier_id", "material_id"] if c in view_df.columns]
        if drop_cols:
            view_df = view_df.drop(columns=drop_cols)

        desired_cols = [
            "_select",
            "material_category_name",
            "supplier_stort_name",
            "material_name",
            "qty_per_parent",
            "uom",
            "ScrapRate",
            "note",
            "sort_order",
        ]
        ordered = [c for c in desired_cols if c in view_df.columns] + [c for c in view_df.columns if c not in desired_cols]
        view_df = view_df[ordered]

        edited_view = st.data_editor(
            view_df,
            hide_index=True,
            use_container_width=True,
            height=190,
            column_config={
                "_select": st.column_config.CheckboxColumn(_t("選取"), help=_t("勾選後到下方「新增 / 修正」修改或刪除")),
                "material_category_name": st.column_config.TextColumn(_t("原料類別"), disabled=True),
                "supplier_stort_name": st.column_config.TextColumn(_t("供應商"), disabled=True),
                "material_name": st.column_config.TextColumn(_t("物料名稱"), disabled=True),
                "qty_per_parent": st.column_config.NumberColumn(_t("原料用量"), disabled=True),
                "uom": st.column_config.TextColumn(_t("計量單位"), disabled=True),
                "ScrapRate": st.column_config.NumberColumn(_t("損耗率(%)"), disabled=True),
                "note": st.column_config.TextColumn(_t("備註"), disabled=True),
                "sort_order": st.column_config.NumberColumn(_t("排序"), disabled=True),
            },
            disabled=[c for c in view_df.columns if c != "_select"],
            key=f"p02_bom_table_{bom_id}",
        )

        picked_bid = _pick_one_index(edited_view, "_select")
        if picked_bid is not None:
            st.session_state[sel_key] = int(picked_bid)
        else:
            st.session_state.pop(sel_key, None)

    st.divider()
    st.subheader(_t("新增 / 修正（用料表）"))

    bid = st.session_state.get(sel_key)
    edit_mode = bid is not None and not items_df.empty

    if edit_mode:
        row_df = items_df.loc[items_df["bom_item_id"] == int(bid)]
        if row_df.empty:
            st.warning(_t("找不到所選用料資料。請重新勾選。"))
            st.session_state.pop(sel_key, None)
            st.stop()
        row = row_df.iloc[0].to_dict()

        last_bid = st.session_state.get("p02_last_edit_bid")
        if last_bid != int(bid):
            st.session_state["p02_edit_qty"] = float(row.get("qty_per_parent") or 0.0)
            st.session_state["p02_edit_uom"] = str(row.get("uom") or "PCS")
            st.session_state["p02_edit_scrap"] = float(row.get("ScrapRate") or 0.0)
            st.session_state["p02_edit_note"] = "" if row.get("note") is None else str(row.get("note"))
            st.session_state["p02_edit_sort"] = int(row.get("sort_order") or 0)
            st.session_state["p02_last_edit_bid"] = int(bid)

        i1, i2, i3 = st.columns([2.4, 2.4, 3.2])
        with i1:
            st.text_input(_t("原料類別"), value=str(row.get("material_category_name") or ""), disabled=True)
        with i2:
            st.text_input(_t("供應商"), value=str(row.get("supplier_stort_name") or supplier_shortname), disabled=True)
        with i3:
            st.text_input(_t("物料名稱"), value=str(row.get("material_name") or ""), disabled=True)

        f1, f2, f3, f4, f5 = st.columns([1.4, 1.2, 1.2, 3.0, 1.0])
        with f1:
            qty = st.number_input(_t("原料用量"), min_value=0.0, step=0.1, key="p02_edit_qty")
        with f2:
            uom = st.selectbox(_t("計量單位"), options=["g", "PCS"], key="p02_edit_uom")
        with f3:
            scrap = st.number_input(_t("損耗率(%)"), min_value=0.0, step=0.1, key="p02_edit_scrap")
        with f4:
            note = st.text_input(_t("備註"), key="p02_edit_note")
        with f5:
            sort_order = st.number_input(_t("排序"), min_value=0, step=1, key="p02_edit_sort")

        cbtn1, cbtn2, cbtn3 = st.columns([1.4, 1.4, 7.2])
        with cbtn1:
            do_save = st.button(_t("儲存修改"), type="primary", key="p02_edit_save")
        with cbtn2:
            confirm_del = st.checkbox(_t("確認刪除"), value=False, key="p02_edit_del_confirm")
            do_del = st.button(_t("刪除"), disabled=not confirm_del, key="p02_edit_del")
        with cbtn3:
            st.caption(_t("若你無法勾選，通常是看到「統計」而不是「明細」。此版已移除統計表，明細一定在上方。"))

        if do_save:
            auth.require_edit(PAGE_KEY)
            _exec_sql(
                SQL_UPDATE_BOM_ITEM,
                {
                    "bom_id": bom_id,
                    "bom_item_id": int(bid),
                    "qty_per_parent": float(qty),
                    "uom": str(uom or "PCS"),
                    "scrap_rate": float(scrap),
                    "note": (str(note).strip() if str(note).strip() else None),
                    "sort_order": (int(sort_order) if int(sort_order) > 0 else None),
                },
            )
            st.success(_t("已儲存。"))
            st.rerun()

        if do_del and confirm_del:
            auth.require_delete(PAGE_KEY)
            _exec_sql(SQL_DELETE_BOM_ITEM, {"bom_id": bom_id, "bom_item_id": int(bid)})
            st.success(_t("已刪除。"))
            st.session_state.pop(sel_key, None)
            st.session_state.pop("p02_last_edit_bid", None)
            st.rerun()

    else:
        st.caption(_t("未勾選明細：此區為新增模式。"))

        mat_df = _df_from_sql(SQL_MATERIALS_BY_SUPPLIER_AND_CAT, {"supplier_id": supplier_id, "cat_id": cat_id})
        if mat_df.empty:
            st.warning(_t("此供應商在該類別下沒有任何原料（material 主檔可能未建）。"))
            st.stop()

        mat_labels, mat_map = [], {}
        for _, r in mat_df.iterrows():
            mid = int(r["item_id"])
            label = f"{r['item_code']} - {r['item_name']}"
            mat_labels.append(label)
            mat_map[label] = mid

        f1, f2, f3, f4, f5 = st.columns([3.0, 1.3, 1.2, 1.5, 2.5])
        with f1:
            mat_label = st.selectbox(_t("物料（依供應商/類別）"), options=mat_labels, key=f"p02_add_mat_{bom_id}")
            material_id = int(mat_map[mat_label])
            mat_row = mat_df.loc[mat_df["item_id"] == material_id].iloc[0]
            material_name = str(mat_row["item_name"])
            material_category_id = int(mat_row["material_category"]) if pd.notna(mat_row["material_category"]) else None
            material_category_name = str(mat_row["material_category_name"] or "")
            st.text_input(_t("物料名稱（自動帶出）"), value=material_name, disabled=True)

        with f2:
            qty = st.number_input(_t("原料用量"), min_value=0.0, value=1.0, step=0.1, key=f"p02_add_qty_{bom_id}")
        with f3:
            uom = st.selectbox(_t("計量單位"), options=["g", "PCS"], index=1, key=f"p02_add_uom_{bom_id}")
        with f4:
            scrap = st.number_input(_t("損耗率(%)"), min_value=0.0, value=0.0, step=0.1, key=f"p02_add_scrap_{bom_id}")
        with f5:
            note = st.text_input(_t("備註"), value="", key=f"p02_add_note_{bom_id}")

        g1, g2 = st.columns([1.2, 5.8])
        with g1:
            sort_order = st.number_input(_t("排序"), min_value=0, value=0, step=1, key=f"p02_add_sort_{bom_id}")
        with g2:
            st.caption(_t("計量單位已改為 enum 下拉：g / PCS。"))

        if material_category_id is None or not material_category_name:
            st.error(_t("此原料缺少 material_category，請先補齊 material.material_category。"))
            st.stop()

        if st.button(_t("新增到用料表"), type="primary", key=f"p02_add_btn_{bom_id}"):
            auth.require_edit(PAGE_KEY)
            _exec_sql(
                SQL_INSERT_BOM_ITEM,
                {
                    "bom_id": bom_id,
                    "supplier_id": supplier_id,
                    "supplier_shortname": supplier_shortname,
                    "material_id": material_id,
                    "material_name": material_name,
                    "qty_per_parent": float(qty),
                    "uom": str(uom or "PCS"),
                    "scrap_rate": float(scrap),
                    "note": note.strip() or None,
                    "sort_order": int(sort_order) if int(sort_order) > 0 else None,
                    "material_category_id": int(material_category_id),
                    "material_category_name": material_category_name,
                },
            )
            st.success(_t("已新增。"))
            st.rerun()
