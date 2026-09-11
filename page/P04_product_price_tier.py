import streamlit as st
from compact_layout import apply_compact_layout
import auth
from splitter_component import apply_vertical_splitter
import pandas as pd
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Tuple

apply_compact_layout()

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from core.i18n import init_language, tr as _core_tr
try:
    from core.i18n import get_language
except Exception:  # pragma: no cover
    def get_language() -> str:
        return str(st.session_state.get("language", "zh"))


P04_TRANSLATIONS = {
    "P04 產品價格級距設定": {
        "en": "P04 Product Price Tier Settings",
        "vi": "P04 Thiết lập bậc giá sản phẩm",
    },
    "此頁維護 customer_product_price_tier。E01 會依客戶、商品與訂購總量自動套用價格。": {
        "en": "This page maintains customer_product_price_tier. E01 will automatically apply prices based on customer, product, and total order quantity.",
        "vi": "Trang này dùng để quản lý customer_product_price_tier. E01 sẽ tự động áp dụng giá theo khách hàng, sản phẩm và tổng số lượng đặt hàng.",
    },
    "查詢區": {"en": "Search", "vi": "Khu vực tìm kiếm"},
    "客戶": {"en": "Customer", "vi": "Khách hàng"},
    "重新整理": {"en": "Refresh", "vi": "Làm mới"},
    "搜尋產品": {"en": "Search Product", "vi": "Tìm sản phẩm"},
    "輸入客戶料號、本公司品號、品名": {"en": "Enter customer product code, our product code, or product name", "vi": "Nhập mã hàng khách, mã hàng nội bộ hoặc tên sản phẩm"},
    "產品清單": {"en": "Product List", "vi": "Danh sách sản phẩm"},
    "此客戶目前沒有可設定的產品。": {
        "en": "This customer currently has no products available for tier pricing.",
        "vi": "Khách hàng này hiện chưa có sản phẩm nào có thể thiết lập bậc giá.",
    },
    "選取": {"en": "Select", "vi": "Chọn"},
    "勾選一個產品後，在下方設定級距": {
        "en": "Select one product, then set price tiers below.",
        "vi": "Chọn một sản phẩm, sau đó thiết lập bậc giá bên dưới.",
    },
    "本公司品號": {"en": "Our Product Code", "vi": "Mã sản phẩm nội bộ"},
    "客戶品號": {"en": "Customer Product Code", "vi": "Mã sản phẩm khách hàng"},
    "品名": {"en": "Product Name", "vi": "Tên sản phẩm"},
    "規格": {"en": "Specification", "vi": "Quy cách"},
    "規格單位": {"en": "Spec Unit", "vi": "Đơn vị quy cách"},
    "單位": {"en": "Unit", "vi": "Đơn vị"},
    "目前基礎價格": {"en": "Current Base Price", "vi": "Giá cơ bản hiện tại"},
    "啟用級距數": {"en": "Active Tier Count", "vi": "Số bậc giá đang bật"},
    "目前級距範圍": {"en": "Current Tier Range", "vi": "Phạm vi bậc giá hiện tại"},
    "請先在產品清單勾選一個產品。": {
        "en": "Please select one product from the product list first.",
        "vi": "Vui lòng chọn một sản phẩm trong danh sách trước.",
    },
    "目前一次只支援設定一個產品，系統會使用第一筆勾選資料。": {
        "en": "Only one product can be configured at a time. The system will use the first selected product.",
        "vi": "Hiện tại chỉ hỗ trợ thiết lập một sản phẩm mỗi lần. Hệ thống sẽ dùng sản phẩm được chọn đầu tiên.",
    },
    "級距設定": {"en": "Tier Settings", "vi": "Thiết lập bậc giá"},
    "目前選取產品": {"en": "Currently Selected Product", "vi": "Sản phẩm hiện đang chọn"},
    "目前啟用級距": {"en": "Currently Active Tiers", "vi": "Bậc giá hiện đang bật"},
    "此產品目前尚未設定客戶級距價格。": {
        "en": "This product currently has no customer price tiers.",
        "vi": "Sản phẩm này hiện chưa thiết lập bậc giá khách hàng.",
    },
    "輸入級距": {"en": "Enter Price Tiers", "vi": "Nhập bậc giá"},
    "資料庫只會儲存數量起點與價格。E01 會依訂購總量抓小於等於該數量的最高起點價格。": {
        "en": "The database only stores the quantity threshold and unit price. E01 will use the total order quantity to select the highest threshold price that is less than or equal to that quantity.",
        "vi": "Cơ sở dữ liệu chỉ lưu số lượng bắt đầu và đơn giá. E01 sẽ căn cứ vào tổng số lượng đặt hàng để lấy mức giá có số lượng bắt đầu cao nhất nhưng nhỏ hơn hoặc bằng số lượng đó.",
    },
    "資料庫只會儲存數量起點與價格。E01 會依訂購總量抓小於等於該數量的最高起點價格": {
        "en": "The database only stores the quantity threshold and unit price. E01 will use the total order quantity to select the highest threshold price that is less than or equal to that quantity.",
        "vi": "Cơ sở dữ liệu chỉ lưu số lượng bắt đầu và đơn giá. E01 sẽ căn cứ vào tổng số lượng đặt hàng để lấy mức giá có số lượng bắt đầu cao nhất nhưng nhỏ hơn hoặc bằng số lượng đó.",
    },
    "幣別": {"en": "Currency", "vi": "Tiền tệ"},
    "生效日": {"en": "Effective Date", "vi": "Ngày hiệu lực"},
    "起始時間": {"en": "Start Time", "vi": "Thời gian bắt đầu"},
    "設定失效日": {"en": "Set End Date", "vi": "Đặt ngày hết hiệu lực"},
    "失效日": {"en": "End Date", "vi": "Ngày hết hiệu lực"},
    "失效日不可早於生效日。": {
        "en": "The end date cannot be earlier than the start date.",
        "vi": "Ngày hết hiệu lực không được sớm hơn ngày bắt đầu.",
    },
    "備註": {"en": "Note", "vi": "Ghi chú"},
    "可填寫此批價格規則的說明": {
        "en": "You may enter notes for this price rule batch.",
        "vi": "Có thể nhập ghi chú cho nhóm quy tắc giá này.",
    },
    "列": {"en": "No.", "vi": "Dòng"},
    "數量起點": {"en": "Quantity Threshold", "vi": "Số lượng bắt đầu"},
    "級距單價": {"en": "Tier Unit Price", "vi": "Đơn giá theo bậc"},
    "單價": {"en": "Unit Price", "vi": "Đơn giá"},
    "刪除": {"en": "Delete", "vi": "Xóa"},
    "刪除所有級距": {"en": "Delete All Tiers", "vi": "Xóa tất cả bậc giá"},
    "儲存級距": {"en": "Save Tiers", "vi": "Lưu bậc giá"},
    "停用目前級距": {"en": "Deactivate Current Tiers", "vi": "Tắt bậc giá hiện tại"},
    "儲存時會先停用此客戶與此產品目前啟用中的舊級距，再建立新的級距資料；歷史資料不會被刪除。": {
        "en": "When saving, the currently active tiers for this customer and product will be deactivated first, then new tiers will be created. Historical records will not be deleted.",
        "vi": "Khi lưu, các bậc giá đang bật của khách hàng và sản phẩm này sẽ được tắt trước, sau đó tạo bậc giá mới. Dữ liệu lịch sử sẽ không bị xóa.",
    },
    "沒有可儲存的級距。": {"en": "No tiers to save.", "vi": "Không có bậc giá nào để lưu."},
    "DB 連線失敗。": {"en": "Database connection failed.", "vi": "Kết nối CSDL thất bại."},
    "已儲存 {len(tiers)} 筆級距價格。": {"en": "Saved {len(tiers)} price tier(s).", "vi": "Đã lưu {len(tiers)} bậc giá."},
    "儲存失敗：{e}": {"en": "Save failed: {e}", "vi": "Lưu thất bại: {e}"},
    "已停用 {affected} 筆目前啟用的級距。": {"en": "Deactivated {affected} currently active tier(s).", "vi": "Đã tắt {affected} bậc giá đang bật."},
    "停用失敗：{e}": {"en": "Deactivate failed: {e}", "vi": "Tắt bậc giá thất bại: {e}"},
    "第一列必須輸入數量起點與價格。": {
        "en": "The first row must include both quantity threshold and price.",
        "vi": "Dòng đầu tiên phải nhập số lượng bắt đầu và đơn giá.",
    },
    "請至少輸入一筆級距價格。": {
        "en": "Please enter at least one price tier.",
        "vi": "Vui lòng nhập ít nhất một bậc giá.",
    },
    "第一列數量起點必須為 1。": {
        "en": "The first quantity threshold must be 1.",
        "vi": "Số lượng bắt đầu của dòng đầu tiên phải là 1.",
    },
    "級距起點不可重複。": {
        "en": "Quantity thresholds cannot be duplicated.",
        "vi": "Số lượng bắt đầu không được trùng lặp.",
    },
    "OK": {"en": "OK", "vi": "OK"},
}


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
    """P04 local i18n wrapper.

    It first uses the global term dictionary. If the dictionary has not yet been
    updated and returns [MISS:...], it falls back to P04_TRANSLATIONS so this
    page can still switch Chinese / Vietnamese / English correctly.
    """
    try:
        value = _core_tr(text)
        if isinstance(value, str) and value and not value.startswith("[MISS:"):
            return value
    except Exception:
        pass
    return P04_TRANSLATIONS.get(text, {}).get(_lang_key(), text)


# =============================================================================
# P04 - 產品價格級距設定
#   - product_unit_price：產品基礎價格 / 主要價格
#   - customer_product_price_tier：客戶 + 商品 + 數量起點級距價格
#
# 設計原則：
# 1) 使用者在 UI 看到「數量起點 / 價格」
# 2) 資料庫只存 qty_threshold（起點）與 unit_price
# 3) E01 依 customer_id + product_id + 下單總數量，抓符合的最高 qty_threshold
# =============================================================================


# ---------------------------
# DB connection
# ---------------------------
def _fallback_get_connection():
    import os
    import mysql.connector
    from mysql.connector import Error

    cfg = {
        "host": os.getenv("ORDO_DB_HOST", "localhost"),
        "port": int(os.getenv("ORDO_DB_PORT", "3306")),
        "user": os.getenv("ORDO_DB_USER", "root"),
        "password": os.getenv("ORDO_DB_PASSWORD", ""),
        "database": os.getenv("ORDO_DB_NAME", "ordotest"),
    }
    try:
        return mysql.connector.connect(**cfg)
    except Error as e:
        st.error(f"DB connect error: {e}")
        return None


try:
    from db import get_connection  # type: ignore
except Exception:  # pragma: no cover
    try:
        from db import get_engine  # type: ignore

        def get_connection():  # type: ignore
            eng = get_engine()
            return eng.raw_connection()

    except Exception:  # pragma: no cover
        get_connection = _fallback_get_connection  # type: ignore


# ---------------------------
# Helpers
# ---------------------------
def _current_user_id(default: int = 1) -> int:
    try:
        return int(st.session_state.get("user_id") or default)
    except Exception:
        return int(default)


def _to_decimal(value, default: Optional[Decimal] = None) -> Optional[Decimal]:
    if value is None:
        return default
    text = str(value).strip().replace(",", "")
    if text == "":
        return default
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


def _fmt_money(v) -> str:
    try:
        if v is None or pd.isna(v):
            return ""
        d = Decimal(str(v))
        if d == d.to_integral():
            return f"{int(d):,}"
        return f"{d:,.4f}".rstrip("0").rstrip(".")
    except Exception:
        return str(v or "")


def _fmt_qty(v) -> str:
    try:
        if v is None or pd.isna(v):
            return ""
        d = Decimal(str(v))
        if d == d.to_integral():
            return str(int(d))
        return str(d.normalize())
    except Exception:
        return str(v or "")


# ---------------------------
# Queries
# ---------------------------
@st.cache_data(show_spinner=False, ttl=30)
def fetch_customers() -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    sql = """
        SELECT customer_id, customer_code, customer_name, customer_shortname, is_active
        FROM customer
        WHERE COALESCE(is_active, 1) = 1
        ORDER BY customer_name ASC, customer_id ASC
    """
    df = pd.read_sql(sql, conn)
    try:
        conn.close()
    except Exception:
        pass
    return df


@st.cache_data(show_spinner=False, ttl=30)
def fetch_products_by_customer(customer_id: int) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    sql = """
        SELECT
            p.product_id,
            p.product_code,
            p.customer_production_id AS customer_product_id,
            p.product_name,
            p.Specification AS specification,
            p.Specification_unit AS specification_unit,
            p.unit,
            COALESCE(
                (
                    SELECT pup.unit_price
                    FROM product_unit_price pup
                    WHERE pup.product_unit_price_id = p.product_id
                      AND pup.is_active = 1
                      AND pup.valid_from <= NOW()
                      AND (pup.valid_to IS NULL OR pup.valid_to >= NOW())
                    ORDER BY pup.valid_from DESC, pup.price_id DESC
                    LIMIT 1
                ),
                (
                    SELECT pup2.unit_price
                    FROM product_unit_price pup2
                    WHERE pup2.product_unit_price_id = p.product_id
                      AND pup2.is_active = 1
                    ORDER BY pup2.valid_from DESC, pup2.price_id DESC
                    LIMIT 1
                ),
                p.unit_price
            ) AS base_unit_price,
            COALESCE(tier_stat.active_tier_count, 0) AS active_tier_count,
            tier_stat.min_threshold,
            tier_stat.max_threshold
        FROM product p
        LEFT JOIN (
            SELECT
                product_id,
                COUNT(*) AS active_tier_count,
                MIN(qty_threshold) AS min_threshold,
                MAX(qty_threshold) AS max_threshold
            FROM customer_product_price_tier
            WHERE customer_id = %s
              AND is_active = 1
              AND (effective_from IS NULL OR effective_from <= CURDATE())
              AND (effective_to IS NULL OR effective_to >= CURDATE())
            GROUP BY product_id
        ) tier_stat
            ON tier_stat.product_id = p.product_id
        WHERE p.customer_id = %s
          AND COALESCE(p.is_active, 1) = 1
        ORDER BY p.product_code ASC, p.product_name ASC, p.product_id ASC
    """
    df = pd.read_sql(sql, conn, params=[int(customer_id), int(customer_id)])
    try:
        conn.close()
    except Exception:
        pass
    return df


@st.cache_data(show_spinner=False, ttl=15)
def fetch_active_tiers(customer_id: int, product_id: int) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    sql = """
        SELECT
            price_tier_id,
            customer_id,
            product_id,
            qty_threshold,
            unit_price,
            currency,
            effective_from,
            effective_to,
            is_active,
            note,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM customer_product_price_tier
        WHERE customer_id = %s
          AND product_id = %s
          AND is_active = 1
          AND (effective_from IS NULL OR effective_from <= CURDATE())
          AND (effective_to IS NULL OR effective_to >= CURDATE())
        ORDER BY qty_threshold ASC, price_tier_id ASC
    """
    df = pd.read_sql(sql, conn, params=[int(customer_id), int(product_id)])
    try:
        conn.close()
    except Exception:
        pass
    return df


def save_price_tiers(
    customer_id: int,
    product_id: int,
    tiers: List[Dict],
    currency: str,
    effective_from: Optional[date],
    effective_to: Optional[date],
    note: str,
    user_id: int,
) -> Tuple[bool, str]:
    """Replace current active tiers for customer+product with the submitted tiers.

    Historical rows are not deleted. Existing active rows are set inactive first.
    """
    auth.require_edit(PAGE_KEY)

    if not tiers:
        return False, "沒有可儲存的級距。"

    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗。"

    try:
        cur = conn.cursor()

        # 停用舊級距，保留歷史資料。
        cur.execute(
            """
            UPDATE customer_product_price_tier
            SET is_active = 0,
                effective_to = COALESCE(effective_to, CURDATE()),
                updated_by = %s,
                updated_at = NOW()
            WHERE customer_id = %s
              AND product_id = %s
              AND is_active = 1
            """,
            (int(user_id), int(customer_id), int(product_id)),
        )

        for row in tiers:
            cur.execute(
                """
                INSERT INTO customer_product_price_tier
                (customer_id, product_id, qty_threshold, unit_price, currency,
                 effective_from, effective_to, is_active, note,
                 created_by, created_at, updated_by, updated_at)
                VALUES
                (%s, %s, %s, %s, %s,
                 %s, %s, 1, %s,
                 %s, NOW(), NULL, NULL)
                """,
                (
                    int(customer_id),
                    int(product_id),
                    str(row["qty_threshold"]),
                    str(row["unit_price"]),
                    str(currency or "VND"),
                    effective_from,
                    effective_to,
                    str(note or ""),
                    int(user_id),
                ),
            )

        conn.commit()
        return True, f"已儲存 {len(tiers)} 筆級距價格。"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"儲存失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def deactivate_price_tiers(customer_id: int, product_id: int, user_id: int) -> Tuple[bool, str]:
    auth.require_edit(PAGE_KEY)
    conn = get_connection()
    if conn is None:
        return False, "DB 連線失敗。"
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE customer_product_price_tier
            SET is_active = 0,
                effective_to = COALESCE(effective_to, CURDATE()),
                updated_by = %s,
                updated_at = NOW()
            WHERE customer_id = %s
              AND product_id = %s
              AND is_active = 1
            """,
            (int(user_id), int(customer_id), int(product_id)),
        )
        affected = cur.rowcount
        conn.commit()
        return True, f"已停用 {affected} 筆目前啟用的級距。"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"停用失敗：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def build_default_tier_inputs(tiers_df: pd.DataFrame, base_price) -> List[Dict[str, str]]:
    """Build 10 UI rows from active threshold-only DB rows.

    DB stores qty_threshold as the quantity starting point.
    The UI also uses quantity starting point directly.
    """
    defaults: List[Dict[str, str]] = []
    if tiers_df is not None and not tiers_df.empty:
        rows = tiers_df.sort_values(["qty_threshold", "price_tier_id"]).to_dict("records")
        for r in rows[:10]:
            defaults.append({
                "start": _fmt_qty(r.get("qty_threshold")),
                "price": _fmt_money(r.get("unit_price")),
            })

    if not defaults:
        defaults.append({"start": "1", "price": _fmt_money(base_price)})

    while len(defaults) < 10:
        defaults.append({"start": "", "price": ""})
    return defaults[:10]


def clear_tier_input_state(prefix: str) -> None:
    for k in list(st.session_state.keys()):
        if k.startswith(prefix):
            st.session_state.pop(k, None)


def delete_tier_input_row(row_index: int, row_count: int = 10) -> None:
    """Delete one input row and shift rows below upward.

    This avoids blank gaps. parse_tier_rows stops at the first blank row, so
    leaving a hole would accidentally ignore later tiers.
    """
    try:
        idx = int(row_index)
    except Exception:
        return

    for i in range(idx, row_count - 1):
        st.session_state[f"p04_tier_input_start_{i}"] = st.session_state.get(f"p04_tier_input_start_{i + 1}", "")
        st.session_state[f"p04_tier_input_price_{i}"] = st.session_state.get(f"p04_tier_input_price_{i + 1}", "")

    st.session_state[f"p04_tier_input_start_{row_count - 1}"] = ""
    st.session_state[f"p04_tier_input_price_{row_count - 1}"] = ""


def clear_all_tier_input_rows(row_count: int = 10) -> None:
    """Clear all tier input textboxes in the current editing area."""
    for i in range(row_count):
        st.session_state[f"p04_tier_input_start_{i}"] = ""
        st.session_state[f"p04_tier_input_price_{i}"] = ""


def apply_pending_tier_input_ops(row_count: int = 10) -> None:
    """Apply delayed textbox changes before Streamlit instantiates the widgets.

    Streamlit does not allow modifying a widget key after the widget has already
    been created in the same run. Row delete / clear-all buttons are rendered
    after the textboxes, so the buttons only set a pending operation and rerun.
    This function is called before the textboxes are rendered on the next run.
    """
    if st.session_state.pop("p04_pending_clear_all_tiers", False):
        clear_all_tier_input_rows(row_count)
        return

    pending_delete = st.session_state.pop("p04_pending_delete_row", None)
    if pending_delete is not None:
        try:
            delete_tier_input_row(int(pending_delete), row_count=row_count)
        except Exception:
            pass


def parse_tier_rows(row_inputs: List[Dict]) -> Tuple[bool, str, List[Dict]]:
    tiers: List[Dict] = []

    for row in row_inputs:
        start_text = str(row.get("start") or "").strip().replace(",", "")
        price_text = str(row.get("price") or "").strip().replace(",", "")
        row_no = int(row.get("row_no") or 0)

        # 空白列：表示輸入到此結束。
        if start_text == "" and price_text == "":
            if row_no == 1:
                return False, "第一列必須輸入數量起點與價格。", []
            break

        if start_text == "":
            return False, f"第 {row_no} 列已有價格，但數量起點空白。", []

        if price_text == "":
            return False, f"第 {row_no} 列已有數量起點，但價格空白。", []

        start_qty = _to_decimal(start_text)
        if start_qty is None or start_qty <= 0:
            return False, f"第 {row_no} 列數量起點格式錯誤，且必須大於 0。", []

        price = _to_decimal(price_text)
        if price is None or price < 0:
            return False, f"第 {row_no} 列價格格式錯誤。", []

        tiers.append({
            "qty_threshold": start_qty,
            "unit_price": price,
        })

    if not tiers:
        return False, "請至少輸入一筆級距價格。", []

    # 防止重複起點，也避免輸入順序混亂。
    starts = [x["qty_threshold"] for x in tiers]
    if len([str(x) for x in starts]) != len(set(str(x) for x in starts)):
        return False, "級距起點不可重複。", []

    for idx in range(1, len(starts)):
        if starts[idx] <= starts[idx - 1]:
            return False, f"第 {idx + 1} 列數量起點必須大於上一列。", []

    return True, "OK", tiers


# =============================================================================
# UI
# =============================================================================
st.set_page_config(page_title=_t("P04 產品價格級距設定"), layout="wide")

PAGE_KEY = "P04_product_price_tier"
auth.require_read(PAGE_KEY)
init_language()
st.session_state.setdefault("p04_top_height", 260)

st.markdown(
    """
    <style>
      .block-container { padding-top: 0 !important; padding-bottom: 0.65rem; max-width: 100% !important; padding-left: 1rem; padding-right: 1rem; }
      .ordo-panel {
        background: #f5f9ff;
        border: 1px solid #d7e3f4;
        border-radius: 8px;
        padding: 6px 8px;
        margin: 4px 0 6px 0;
      }
      .ordo-section-title { font-size: 0.92rem; font-weight: 700; margin: 0 0 3px 0; }
      .ordo-muted { color: #6b7280; font-size: 0.78rem; }
      div[data-testid="stDataEditor"] { border-radius: 10px; overflow: hidden; }
      div[data-testid="stHorizontalBlock"] button[kind="secondary"], div[data-testid="stHorizontalBlock"] button[kind="primary"] { min-height: 28px; padding-top: 0.1rem; padding-bottom: 0.1rem; }
      [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input { min-height: 1.55rem !important; padding-top: 0.1rem !important; padding-bottom: 0.1rem !important; }
      [data-testid="stTextInput"], [data-testid="stNumberInput"], [data-testid="stSelectbox"], [data-testid="stDateInput"] { margin-bottom: 0 !important; }
      [data-testid="stDataFrame"] { margin: 0.15rem 0 !important; }
      hr { margin: 0.25rem 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(_t("P04 產品價格級距設定"))
st.caption(_t("此頁維護 customer_product_price_tier。E01 會依客戶、商品與訂購總量自動套用價格。"))

cust_df = fetch_customers()
if cust_df is None or cust_df.empty:
    st.error(_t("找不到客戶資料。"))
    st.stop()

cust_df = cust_df.copy()
cust_df["customer_id"] = cust_df["customer_id"].astype(int)
cust_ids = cust_df["customer_id"].tolist()
cust_labels = {
    int(r["customer_id"]): f'{r["customer_name"]} | {r["customer_code"]} | {r["customer_shortname"]} | ID:{int(r["customer_id"])}'
    for _, r in cust_df.iterrows()
}

st.markdown(f"### {_t('查詢區')}")
q1, q2, q3 = st.columns([3.0, 2.2, 1.0], vertical_alignment="bottom")
with q1:
    selected_customer_id = st.selectbox(
        _t("客戶"),
        options=cust_ids,
        index=0,
        format_func=lambda x: cust_labels.get(int(x), str(x)),
        key="p04_customer_id",
    )
with q2:
    product_keyword = st.text_input(
        _t("搜尋產品"),
        value="",
        key="p04_product_keyword",
        placeholder=_t("輸入客戶料號、本公司品號、品名"),
    )
with q3:
    if st.button(_t("重新整理"), use_container_width=True, key="p04_refresh"):
        st.cache_data.clear()
        st.rerun()

selected_customer_id = int(selected_customer_id)

products_df = fetch_products_by_customer(selected_customer_id)
products_df = products_df if products_df is not None else pd.DataFrame()

# Product keyword filter: customer product code, our product code, or product name.
if not products_df.empty and str(product_keyword or "").strip():
    kw = str(product_keyword or "").strip().lower()
    mask = (
        products_df.get("customer_product_id", pd.Series("", index=products_df.index)).fillna("").astype(str).str.lower().str.contains(kw, na=False)
        | products_df.get("product_code", pd.Series("", index=products_df.index)).fillna("").astype(str).str.lower().str.contains(kw, na=False)
        | products_df.get("product_name", pd.Series("", index=products_df.index)).fillna("").astype(str).str.lower().str.contains(kw, na=False)
    )
    products_df = products_df[mask].copy()

st.markdown(f"### {_t('產品清單')}")
if products_df.empty:
    st.info(_t("此客戶目前沒有可設定的產品。"))
    st.stop()

show_products = products_df.copy()
show_products.insert(0, "select", False)
show_products["base_unit_price"] = pd.to_numeric(show_products["base_unit_price"], errors="coerce")
show_products["active_tier_count"] = pd.to_numeric(show_products["active_tier_count"], errors="coerce").fillna(0).astype(int)
show_products["tier_range"] = show_products.apply(
    lambda r: "" if int(r.get("active_tier_count") or 0) == 0 else f'{_fmt_qty(r.get("min_threshold"))} 起 / 最高 {_fmt_qty(r.get("max_threshold"))} 起',
    axis=1,
)
show_products = show_products.set_index("product_id", drop=True)

list_cols = [
    "select",
    "product_code",
    "customer_product_id",
    "product_name",
    "specification",
    "specification_unit",
    "unit",
    "base_unit_price",
    "active_tier_count",
    "tier_range",
]
list_cols = [c for c in list_cols if c in show_products.columns]

products_editor = st.data_editor(
    show_products[list_cols],
    use_container_width=True,
    hide_index=True,
    disabled=[c for c in list_cols if c != "select"],
    height=int(st.session_state["p04_top_height"]),
    column_config={
        "select": st.column_config.CheckboxColumn(_t("選取"), help=_t("勾選一個產品後，在下方設定級距"), default=False),
        "product_code": st.column_config.TextColumn(_t("本公司品號"), width="small", disabled=True),
        "customer_product_id": st.column_config.TextColumn(_t("客戶品號"), width="medium", disabled=True),
        "product_name": st.column_config.TextColumn(_t("品名"), width="large", disabled=True),
        "specification": st.column_config.TextColumn(_t("規格"), width="medium", disabled=True),
        "specification_unit": st.column_config.TextColumn(_t("規格單位"), width="small", disabled=True),
        "unit": st.column_config.TextColumn(_t("單位"), width="small", disabled=True),
        "base_unit_price": st.column_config.NumberColumn(_t("目前基礎價格"), width="small", disabled=True),
        "active_tier_count": st.column_config.NumberColumn(_t("啟用級距數"), width="small", disabled=True),
        "tier_range": st.column_config.TextColumn(_t("目前級距範圍"), width="medium", disabled=True),
    },
    key=f"p04_products_editor_{selected_customer_id}",
)

picked_products = products_editor[products_editor["select"] == True] if "select" in products_editor.columns else pd.DataFrame()
picked_product_ids = [int(x) for x in picked_products.index.tolist()] if picked_products is not None and not picked_products.empty else []

if not picked_product_ids:
    apply_vertical_splitter("p04_top_height", "p04_vertical_splitter_control", min_top=150, max_top=430)
    st.info(_t("請先在產品清單勾選一個產品。"))
    st.stop()

if len(picked_product_ids) > 1:
    st.warning(_t("目前一次只支援設定一個產品，系統會使用第一筆勾選資料。"))

apply_vertical_splitter("p04_top_height", "p04_vertical_splitter_control", min_top=150, max_top=430)

product_id = int(picked_product_ids[0])
product_row = products_df.loc[products_df["product_id"] == product_id].iloc[0].to_dict()
base_price = product_row.get("base_unit_price")

st.divider()
st.markdown(f"### {_t('級距設定')}")
st.markdown(
    f"""
    <div class='ordo-panel'>
      <div class='ordo-section-title'>{_t('目前選取產品')}</div>
      <div>{_t('本公司品號')}：<b>{product_row.get('product_code') or ''}</b></div>
      <div>{_t('客戶品號')}：<b>{product_row.get('customer_product_id') or ''}</b></div>
      <div>{_t('品名')}：<b>{product_row.get('product_name') or ''}</b></div>
      <div>{_t('目前基礎價格')}：<b>{_fmt_money(base_price)}</b></div>
    </div>
    """,
    unsafe_allow_html=True,
)

active_tiers_df = fetch_active_tiers(selected_customer_id, product_id)

if active_tiers_df is not None and not active_tiers_df.empty:
    st.markdown(f"<div class='ordo-section-title'>{_t('目前啟用級距')}</div>", unsafe_allow_html=True)
    view_df = active_tiers_df.copy()
    view_df = view_df.sort_values("qty_threshold")
    view_df["start_qty"] = view_df["qty_threshold"]
    active_show_df = view_df[["start_qty", "unit_price", "currency", "effective_from", "effective_to", "note"]].copy()
    active_show_df = active_show_df.rename(columns={
        "start_qty": _t("數量起點"),
        "unit_price": _t("級距單價"),
        "currency": _t("幣別"),
        "effective_from": _t("起始時間"),
        "effective_to": _t("失效日"),
        "note": _t("備註"),
    })
    st.dataframe(
        active_show_df,
        use_container_width=True,
        hide_index=True,
        height=110,
    )
else:
    st.info(_t("此產品目前尚未設定客戶級距價格。"))

# Product change: initialize ten input rows from current active tiers.
_state_identity = f"{selected_customer_id}_{product_id}"
if st.session_state.get("p04_current_identity") != _state_identity:
    clear_tier_input_state("p04_tier_input_")
    st.session_state["p04_current_identity"] = _state_identity
    defaults = build_default_tier_inputs(active_tiers_df, base_price)
    for i, row in enumerate(defaults):
        st.session_state[f"p04_tier_input_start_{i}"] = row.get("start", "")
        st.session_state[f"p04_tier_input_price_{i}"] = row.get("price", "")

# Apply delayed delete / clear operations before the tier textboxes are instantiated.
apply_pending_tier_input_ops(row_count=10)

st.markdown(f"<div class='ordo-section-title'>{_t('輸入級距')}</div>", unsafe_allow_html=True)
st.caption(_t("資料庫只會儲存數量起點與價格。E01 會依訂購總量抓小於等於該數量的最高起點價格。"))

meta1, meta2, meta3, meta4 = st.columns([1.0, 1.0, 1.0, 2.0], vertical_alignment="bottom")
with meta1:
    currency = st.selectbox(_t("幣別"), options=["VND", "TWD", "USD", "CNY"], index=0, key="p04_currency")
with meta2:
    effective_from = st.date_input(_t("起始時間"), value=date.today(), key="p04_effective_from")
with meta3:
    # 預設空白：使用者未填失效日，就寫入 NULL，表示此級距一直有效。
    # 使用新 key 避免舊版 session_state 裡殘留的日期自動帶入。
    try:
        effective_to = st.date_input(_t("失效日"), value=None, key="p04_effective_to_nullable")
    except Exception:
        # 舊版 Streamlit 若不支援 value=None，退回文字輸入；空白一樣視為 NULL。
        _effective_to_text = st.text_input(_t("失效日"), value="", key="p04_effective_to_text", placeholder="YYYY-MM-DD")
        effective_to = pd.to_datetime(_effective_to_text, errors="coerce").date() if str(_effective_to_text or "").strip() else None
with meta4:
    note = st.text_input(_t("備註"), value="", key="p04_note")

if effective_to is not None and effective_from is not None and effective_to < effective_from:
    st.warning(_t("失效日不可早於生效日。"))

# Header row
h1, h2, h3, h4 = st.columns([0.16, 1.64, 1.45, 0.65], gap="small")
with h1:
    st.markdown(_t("列"))
with h2:
    st.markdown(_t("數量起點"))
with h3:
    st.markdown(_t("級距單價"))
with h4:
    st.markdown("&nbsp;", unsafe_allow_html=True)

row_inputs: List[Dict] = []

for i in range(10):
    row_no = i + 1

    c1, c2, c3, c4 = st.columns([0.16, 1.64, 1.45, 0.65], gap="small", vertical_alignment="center")
    with c1:
        st.markdown(f"<div style='text-align:center;font-weight:700;'>{row_no}</div>", unsafe_allow_html=True)
    with c2:
        start_text = st.text_input(
            "",
            key=f"p04_tier_input_start_{i}",
            placeholder=_t("數量起點"),
            label_visibility="collapsed",
        )
    with c3:
        price_text = st.text_input(
            "",
            key=f"p04_tier_input_price_{i}",
            placeholder=_t("單價"),
            label_visibility="collapsed",
        )
    with c4:
        if st.button(_t("刪除"), key=f"p04_btn_delete_row_{i}", use_container_width=True):
            st.session_state["p04_pending_delete_row"] = int(i)
            st.rerun()

    row_inputs.append({
        "row_no": row_no,
        "start": start_text,
        "price": price_text,
    })

btn1, btn2, btn_clear, btn3 = st.columns([1.4, 1.4, 1.4, 3.6], vertical_alignment="bottom")
with btn1:
    if st.button(_t("儲存級距"), type="primary", use_container_width=True, key="p04_btn_save_tiers"):
        if effective_to is not None and effective_from is not None and effective_to < effective_from:
            st.warning(_t("失效日不可早於生效日。"))
        else:
            ok_parse, msg_parse, parsed_tiers = parse_tier_rows(row_inputs)
            if not ok_parse:
                st.warning(msg_parse)
            else:
                ok, msg = save_price_tiers(
                    customer_id=int(selected_customer_id),
                    product_id=int(product_id),
                    tiers=parsed_tiers,
                    currency=str(currency or "VND"),
                    effective_from=effective_from,
                    effective_to=effective_to,
                    note=str(note or ""),
                    user_id=_current_user_id(),
                )
                if ok:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)

with btn2:
    if st.button(_t("停用目前級距"), use_container_width=True, key="p04_btn_deactivate_tiers"):
        ok, msg = deactivate_price_tiers(
            customer_id=int(selected_customer_id),
            product_id=int(product_id),
            user_id=_current_user_id(),
        )
        if ok:
            st.success(msg)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(msg)

with btn_clear:
    if st.button(_t("刪除所有級距"), use_container_width=True, key="p04_btn_clear_all_tiers"):
        st.session_state["p04_pending_clear_all_tiers"] = True
        st.rerun()

with btn3:
    st.caption(_t("儲存時會先停用此客戶與此產品目前啟用中的舊級距，再建立新的級距資料；歷史資料不會被刪除。"))
