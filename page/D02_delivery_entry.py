# -*- coding: utf-8 -*-
"""
D01 + D02 合併頁（以 D02 作入口）
- 上方：delivery_head 主表（可勾選）
- 勾選後：顯示 delivery_product 明細；並自動隱藏下方新增區
- 未勾選：顯示下方 D02 新建送貨單
"""
from __future__ import annotations

from compact_layout import apply_compact_layout

apply_compact_layout()
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List
import pandas as pd
import streamlit as st
import auth
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from core.i18n import init_language, tr as _t

init_language()


# ---------------------------
# D02 local table-label translations
# ---------------------------
# Some D02 grids were previously rendered directly from SQL column names
# (delivery_code, created_at, etc.).  These helpers keep the internal dataframe
# keys untouched for business logic, while showing user-facing headers in the
# current UI language.
D02_LOCAL_TRANSLATIONS = {
    "勾選": {"vi": "Chọn", "en": "Select"},
    "ID": {"vi": "ID", "en": "ID"},
    "送貨單號": {"vi": "Số phiếu giao hàng", "en": "Delivery No."},
    "狀態": {"vi": "Trạng thái", "en": "Status"},
    "客戶訂單號碼": {"vi": "Số đơn hàng khách", "en": "Customer Order No."},
    "車號": {"vi": "Số xe", "en": "Vehicle No."},
    "送貨日期": {"vi": "Ngày giao hàng", "en": "Delivery Date"},
    "建檔時間": {"vi": "Thời gian tạo", "en": "Created At"},
    "客戶名稱": {"vi": "Tên khách hàng", "en": "Customer Name"},
    "行號": {"vi": "Số dòng", "en": "Line No."},
    "客戶料號": {"vi": "Mã hàng khách", "en": "Customer Item Code"},
    "品名": {"vi": "Tên hàng", "en": "Product Name"},
    "數量": {"vi": "Số lượng", "en": "Quantity"},
    "規格": {"vi": "Quy cách", "en": "Specification"},
    "規格單位": {"vi": "Đơn vị quy cách", "en": "Spec Unit"},
    "顏色": {"vi": "Màu sắc", "en": "Color"},
    "每箱數量": {"vi": "Số lượng/thùng", "en": "Qty/Carton"},
    "單價": {"vi": "Đơn giá", "en": "Unit Price"},
    "金額": {"vi": "Thành tiền", "en": "Amount"},
    "選取": {"vi": "Chọn", "en": "Select"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "產品編號": {"vi": "Mã sản phẩm", "en": "Product Code"},
    "使用紙箱": {"vi": "Số thùng dùng", "en": "Cartons Used"},
    "備註": {"vi": "Ghi chú", "en": "Note"},
    "建立人員": {"vi": "Người tạo", "en": "Created By"},
    "系統會依目前登入者自動寫入 created_by，不可手動修改。": {"vi": "Hệ thống tự động ghi created_by theo người đăng nhập hiện tại, không thể chỉnh sửa thủ công.", "en": "The system records created_by from the current logged-in user and cannot be edited manually."},
    "建立人員會自動使用目前登入帳號；資料庫仍寫入 user_id。": {"vi": "Người tạo sẽ tự động dùng tài khoản đang đăng nhập; cơ sở dữ liệu vẫn lưu user_id.", "en": "The creator is taken from the current login account; the database still stores user_id."},
    "訂單類別": {"vi": "Loại đơn hàng", "en": "Order Category"},
    "一般訂單": {"vi": "Đơn hàng thông thường", "en": "General Order"},
    "補料單（要收款）": {"vi": "Đơn bù nguyên liệu (Cần thu tiền)", "en": "Material Replenishment Order (Receivable)"},
    "補料單（不收款）": {"vi": "Đơn bù nguyên liệu (Không thu tiền)", "en": "Material Replenishment Order (Non-Receivable)"},
    "本次送貨會建立應收帳款。": {"vi": "Lần giao hàng này sẽ tạo công nợ phải thu.", "en": "This delivery will create an AR record."},
    "本次送貨不會建立應收帳款（補料單不收款）。": {"vi": "Lần giao hàng này sẽ không tạo công nợ phải thu (đơn bù nguyên liệu không thu tiền).", "en": "This delivery will not create an AR record (non-receivable replenishment order)."},
    "來源單據": {"vi": "Chứng từ nguồn", "en": "Source Document"},
    "客戶訂單": {"vi": "Đơn hàng khách", "en": "Customer Order"},
    "樣品單": {"vi": "Đơn hàng mẫu", "en": "Sample Order"},
    "樣品單（要收款）": {"vi": "Đơn mẫu (Cần thu tiền)", "en": "Sample Order (Receivable)"},
    "樣品單（不收款）": {"vi": "Đơn mẫu (Không thu tiền)", "en": "Sample Order (Non-Receivable)"},
    "選擇來源單據": {"vi": "Chọn chứng từ nguồn", "en": "Select Source Document"},
    "選擇客戶訂單或樣品單；樣品不必先建立正式產品。": {"vi": "Chọn đơn hàng khách hoặc đơn mẫu; mẫu chưa cần tạo sản phẩm chính thức.", "en": "Select a customer or sample order; samples do not need a formal product first."},
    "本次送貨不會建立應收帳款（樣品不收款）。": {"vi": "Lần giao hàng này sẽ không tạo công nợ phải thu (mẫu không thu tiền).", "en": "This delivery will not create an AR record (non-receivable sample)."},
    "來源模組": {"vi": "Mô-đun nguồn", "en": "Source Module"},
    "E01 客戶訂單": {"vi": "E01 Đơn hàng khách", "en": "E01 Customer Order"},
    "SP01 樣品單": {"vi": "SP01 Đơn mẫu", "en": "SP01 Sample Order"},
    "單據類別": {"vi": "Loại chứng từ", "en": "Document Category"},
    "應收規則": {"vi": "Quy tắc công nợ phải thu", "en": "AR Rule"},
    "建立應收帳款": {"vi": "Tạo công nợ phải thu", "en": "Create AR"},
    "不建立應收帳款": {"vi": "Không tạo công nợ phải thu", "en": "Do Not Create AR"},
    "尚未選擇單據": {"vi": "Chưa chọn chứng từ", "en": "No document selected"},
}

D02_LINE_COLUMN_LABELS = {
    "_選取": "選取",
    "line_no": "行號",
    "product_code": "產品編號",
    "product_name": "品名",
    "customer_product_id": "客戶料號",
    "qty": "數量",
    "product_unit_price": "單價",
    "line_amount": "金額",
    "carton_used": "使用紙箱",
    "specification": "規格",
    "specification_unit": "規格單位",
    "color": "顏色",
    "note": "備註",
}

D02_MASTER_COLUMN_LABELS = {
    "_選取": "勾選",
    "delivery_note_id": "ID",
    "delivery_code": "送貨單號",
    "status": "狀態",
    "customer_order_no": "客戶訂單號碼",
    "vehicle_no": "車號",
    "delivery_date": "送貨日期",
    "created_at": "建檔時間",
    "customer_name": "客戶名稱",
}


def _d02_lang() -> str:
    lang = st.session_state.get("lang", st.session_state.get("language", "zh"))
    return lang if lang in {"zh", "vi", "en"} else "zh"


def _d02_t(text: str) -> str:
    translated = _t(text)
    # A missing dictionary entry is a sentinel, not a translated label.
    # Continue to the local translations for terms added by this page.
    if translated and translated != text and not translated.startswith("[MISS:"):
        return translated
    if _d02_lang() == "zh":
        return text
    return D02_LOCAL_TRANSLATIONS.get(text, {}).get(_d02_lang(), text)


CUSTOMER_ORDER_CATEGORY_GENERAL = "general"
CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_RECEIVABLE = "material_replenishment_receivable"
CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_NON_RECEIVABLE = "material_replenishment_non_receivable"
CUSTOMER_ORDER_CATEGORY_LABELS = {
    CUSTOMER_ORDER_CATEGORY_GENERAL: "一般訂單",
    CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_RECEIVABLE: "補料單（要收款）",
    CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_NON_RECEIVABLE: "補料單（不收款）",
}


def customer_order_category_label(category: str) -> str:
    return _d02_t(CUSTOMER_ORDER_CATEGORY_LABELS.get(
        str(category or "").strip(),
        CUSTOMER_ORDER_CATEGORY_LABELS[CUSTOMER_ORDER_CATEGORY_GENERAL],
    ))


def _translate_d02_columns(df: pd.DataFrame, label_map: Optional[dict[str, str]] = None) -> tuple[pd.DataFrame, dict[str, str]]:
    """Translate dataframe headers for display and return reverse map."""
    if df is None:
        return df, {}
    label_map = label_map or {}
    rename_map: dict[str, str] = {}
    reverse_map: dict[str, str] = {}
    used: set[str] = set()
    for col in df.columns:
        label_key = label_map.get(str(col), str(col))
        display_col = _d02_t(label_key)
        if display_col in used:
            display_col = f"{display_col} ({col})"
        rename_map[col] = display_col
        reverse_map[display_col] = col
        used.add(display_col)
    return df.rename(columns=rename_map), reverse_map


def _restore_d02_columns(df: pd.DataFrame, reverse_map: dict[str, str]) -> pd.DataFrame:
    if df is None or not reverse_map:
        return df
    return df.rename(columns={c: reverse_map.get(c, c) for c in df.columns})

import io, base64, os, threading, time, hashlib, socket, html as html_lib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PAGE_KEY = "D02_delivery_entry"


# ReportLab font metrics (needed for mixed CJK/Latin width calc)
try:
    from reportlab.pdfbase import pdfmetrics  # type: ignore
    from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
except Exception:  # ReportLab not installed or unavailable
    pdfmetrics = None  # type: ignore
    TTFont = None  # type: ignore


# ---------------------------
# Printing (PDF) helpers
# ---------------------------
def _reportlab_available() -> bool:
    try:
        import reportlab  # noqa
        return True
    except Exception:
        return False


def _register_font(font_name: str, font_path: str) -> bool:
    """Register a TTF/OTF/TTC font with ReportLab. Return True on success."""
    try:
        if not font_path:
            return False
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        return True
    except Exception:
        return False


def _get_pdf_cjk_font_name() -> str:
    """
    Font for CJK (Chinese).
    Priority:
      1) ORDO_PDF_CJK_FONT_PATH
      2) Common Windows fonts (Noto Sans TC, Microsoft JhengHei)
      3) Linux CJK fallback (AR PL UMing)
      4) Helvetica (will break Chinese)
    """
    env_path = os.environ.get("ORDO_PDF_CJK_FONT_PATH", "").strip()
    if env_path and _register_font("CJK", env_path):
        return "CJK"

    project_font_candidates = []
    try:
        here = Path(__file__).resolve().parent
        project_font_candidates = [
            here / "NotoSansTC-VariableFont_wght.ttf",
            here / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
            ROOT_DIR / "NotoSansTC-VariableFont_wght.ttf",
            ROOT_DIR / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
            Path.cwd() / "NotoSansTC-VariableFont_wght.ttf",
            Path.cwd() / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
        ]
    except Exception:
        project_font_candidates = []

    candidates = [str(x) for x in project_font_candidates] + [
        # Windows
        r"C:\Windows\Fonts\NotoSansTC-VariableFont_wght.ttf",
        r"C:\Windows\Fonts\NotoSansTC-Regular.otf",
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\msjhbd.ttc",
        # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    for p in candidates:
        if _register_font("CJK", p):
            return "CJK"
    return "Helvetica"


def _get_pdf_latin_font_name() -> str:
    """
    Font for Latin + Vietnamese diacritics.
    Priority:
      1) ORDO_PDF_LATIN_FONT_PATH
      2) Common Windows fonts (Noto Sans, Arial)
      3) Linux fallback (DejaVu Sans / Noto Sans)
      4) Helvetica
    """
    env_path = os.environ.get("ORDO_PDF_LATIN_FONT_PATH", "").strip()
    if env_path and _register_font("LAT", env_path):
        return "LAT"

    project_font_candidates = []
    try:
        here = Path(__file__).resolve().parent
        project_font_candidates = [
            here / "NotoSansTC-VariableFont_wght.ttf",
            here / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
            ROOT_DIR / "NotoSansTC-VariableFont_wght.ttf",
            ROOT_DIR / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
            Path.cwd() / "NotoSansTC-VariableFont_wght.ttf",
            Path.cwd() / "fonts" / "NotoSansTC-VariableFont_wght.ttf",
        ]
    except Exception:
        project_font_candidates = []

    candidates = [str(x) for x in project_font_candidates] + [
        # Windows
        r"C:\Windows\Fonts\NotoSans-Regular.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans.ttf",
    ]
    for p in candidates:
        if _register_font("LAT", p):
            return "LAT"
    return "Helvetica"


def _is_cjk_char(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF  # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF  # Extension A
        or 0xF900 <= cp <= 0xFAFF  # Compatibility Ideographs
        or 0x3000 <= cp <= 0x303F  # CJK Symbols/Punctuation
        or 0xFF00 <= cp <= 0xFFEF  # Halfwidth/Fullwidth forms
    )


def _split_runs(text: str) -> list[tuple[str, str]]:
    """Split text into runs of ('CJK'|'LAT', substring)."""
    if not text:
        return []
    runs: list[tuple[str, str]] = []
    cur_kind = "CJK" if _is_cjk_char(text[0]) else "LAT"
    buf = [text[0]]
    for ch in text[1:]:
        kind = "CJK" if _is_cjk_char(ch) else "LAT"
        if kind == cur_kind:
            buf.append(ch)
        else:
            runs.append((cur_kind, "".join(buf)))
            cur_kind = kind
            buf = [ch]
    runs.append((cur_kind, "".join(buf)))
    return runs


def _string_width_mixed(text: str, size: int | float, cjk_font: str, lat_font: str) -> float:
    if pdfmetrics is None:
        raise RuntimeError('ReportLab pdfmetrics is not available. Please install reportlab.')
    w = 0.0
    for kind, seg in _split_runs(text):
        font = cjk_font if kind == "CJK" else lat_font
        w += pdfmetrics.stringWidth(seg, font, size)
    return w


def _draw_mixed(c: canvas.Canvas, x: float, y: float, text: str, size: int | float, cjk_font: str, lat_font: str):
    """Draw left-aligned mixed CJK/Latin text."""
    if pdfmetrics is None:
        raise RuntimeError('ReportLab pdfmetrics is not available. Please install reportlab.')
    cur_x = x
    for kind, seg in _split_runs(text):
        font = cjk_font if kind == "CJK" else lat_font
        c.setFont(font, size)
        c.drawString(cur_x, y, seg)
        cur_x += pdfmetrics.stringWidth(seg, font, size)


def _draw_mixed_right(c: canvas.Canvas, x_right: float, y: float, text: str, size: int | float, cjk_font: str, lat_font: str):
    """Draw right-aligned mixed CJK/Latin text."""
    if pdfmetrics is None:
        raise RuntimeError('ReportLab pdfmetrics is not available. Please install reportlab.')
    w = _string_width_mixed(text, size, cjk_font, lat_font)
    _draw_mixed(c, x_right - w, y, text, size, cjk_font, lat_font)


def _wrap_text_mixed(text: str, max_width: float, size: int | float, cjk_font: str, lat_font: str, max_lines: int = 2) -> list[str]:
    """Wrap mixed CJK / Vietnamese / Latin text inside a PDF cell."""
    text = str(text or "").strip()
    if not text:
        return [""]

    lines: list[str] = []
    cur = ""
    for ch in text:
        trial = cur + ch
        if cur and _string_width_mixed(trial, size, cjk_font, lat_font) > max_width:
            lines.append(cur.rstrip())
            cur = ch.lstrip()
            if len(lines) >= max_lines:
                break
        else:
            cur = trial

    if len(lines) < max_lines and cur:
        lines.append(cur.rstrip())

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if lines:
        last = lines[-1]
        # Trim last line and add ellipsis if it still exceeds width.
        if _string_width_mixed(last, size, cjk_font, lat_font) > max_width:
            ell = "…"
            while last and _string_width_mixed(last + ell, size, cjk_font, lat_font) > max_width:
                last = last[:-1]
            lines[-1] = (last + ell) if last else ell
    return lines or [""]


def _draw_wrapped_cell_mixed(
    c: canvas.Canvas,
    x_left: float,
    x_right: float,
    y_top: float,
    text: str,
    size: int | float,
    cjk_font: str,
    lat_font: str,
    *,
    max_lines: int = 2,
    pad_x: float = 0,
    first_baseline_offset: float = 4.2,
    line_gap: float = 3.6,
):
    """Draw text in a cell with Excel-like wrap to second line."""
    from reportlab.lib.units import mm
    pad = pad_x if pad_x else 1.2 * mm
    available_w = max(1, (x_right - x_left) - 2 * pad)
    lines = _wrap_text_mixed(text, available_w, size, cjk_font, lat_font, max_lines=max_lines)
    for idx, line in enumerate(lines[:max_lines]):
        _draw_mixed(c, x_left + pad, y_top - (first_baseline_offset + idx * line_gap) * mm, line, size, cjk_font, lat_font)
def fetch_delivery_print_data(delivery_ids: list[int]) -> pd.DataFrame:
    """Fetch printable rows for selected delivery_head IDs."""
    if not delivery_ids:
        return pd.DataFrame()
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        ph = ",".join(["%s"] * len(delivery_ids))
        sql = f"""
            SELECT
                dh.delivery_note_id,
                dh.delivery_code,
                dh.delivery_date,
                dh.customer_order_no,
                c.customer_name,
                c.customer_address,
                dp.line_no,
                COALESCE(NULLIF(dp.customer_product_id, ''), NULLIF(p.customer_production_id, ''), p.product_code) AS product_code,
                COALESCE(dp.product_name, p.product_name) AS product_name,
                CAST(dp.qty AS DECIMAL(18,2)) AS qty_pcs,
                COALESCE(p.qty_per_carton, 0) AS qty_per_carton,
                COALESCE(dp.note, '') AS note,
                CASE
                  WHEN COALESCE(p.qty_per_carton,0) > 0 THEN CEIL(dp.qty / p.qty_per_carton)
                  ELSE 0
                END AS carton_qty
            FROM delivery_head dh
            JOIN customer c ON c.customer_id = dh.customer_id
            JOIN delivery_product dp ON dp.delivery_head_id = dh.delivery_note_id
            JOIN product p ON p.product_id = dp.product_id
            WHERE dh.delivery_note_id IN ({ph})
            ORDER BY dh.delivery_note_id, dp.line_no
        """
        df = pd.read_sql(sql, conn, params=[int(x) for x in delivery_ids])
        return df
    finally:
        try:
            conn.close()
        except Exception:
            pass

def build_delivery_pdf(delivery_ids: list[int]) -> bytes:
    """Generate a PDF for printing delivery notes.

    Paper size (landscape): width=186mm, height=139mm.
    """
    if not _reportlab_available():
        return b""

    df = fetch_delivery_print_data(delivery_ids)
    if df.empty:
        return b""

    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm

    # Landscape per user requirement
    page_w = 186 * mm
    page_h = 139 * mm
    margin = 6 * mm
    cjk_font = _get_pdf_cjk_font_name()
    lat_font = _get_pdf_latin_font_name()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    # group by delivery_note_id
    for dn_id, g in df.groupby("delivery_note_id", sort=False):
        g = g.copy()
        delivery_code = str(g["delivery_code"].iloc[0] or "")
        delivery_date = g["delivery_date"].iloc[0]
        date_str = delivery_date.strftime("%Y/%m/%d") if pd.notna(delivery_date) else ""
        customer_order_no = str(g["customer_order_no"].iloc[0] or "")
        customer_name = str(g["customer_name"].iloc[0] or "")
        customer_addr = str(g["customer_address"].iloc[0] or "")

        total_pcs = float(g["qty_pcs"].fillna(0).sum())
        total_carton = float(g["carton_qty"].fillna(0).sum())

        y = page_h - margin

        # Title
        c.setFont(cjk_font, 18)
        c.drawString(margin, y, "送貨單")
        c.setFont(lat_font, 18)
        c.drawString(margin + 28*mm, y, "Biên lai giao hàng")

        # Date / No
        c.setFont(lat_font, 11)
        c.drawRightString(page_w - margin, y, f"Ngày: {date_str}")
        y -= 7*mm
        c.drawRightString(page_w - margin, y, f"Số: {delivery_code}")

        # Customer / Address
        y -= 8*mm
        _draw_mixed(c, margin, y, f"客戶 / Khách hàng: {customer_name}", 10.5, cjk_font, lat_font)
        y -= 6*mm
        addr_text = customer_addr if customer_addr else "______________________________"
        _draw_mixed(c, margin, y, f"送貨地址 / Địa chỉ giao hàng: {addr_text}", 10.5, cjk_font, lat_font)

        # Table header (8 cols)
        y -= 7*mm
        header_h = 7*mm
        row_h = 10*mm  # data row: allow product name / note to wrap to a second line

        # Column widths (approx. match the sample layout)
        col_w = [20*mm, 20*mm, 40*mm, 12*mm, 10*mm, 12*mm, 14*mm, 25*mm]
        headers = ["訂單", "產品編號", "商品名稱", "數量", "PCS", "箱數", "PCS/箱", "備註"]

        # Use very thin grid lines (dot-matrix friendly)
        c.setLineWidth(0.3)

        # Pre-calc x boundaries
        x0 = margin
        xs = [x0]
        for w in col_w:
            xs.append(xs[-1] + w)

        # --- Draw header row box + vertical separators
        y_top = y
        y_bot = y - header_h
        c.rect(x0, y_bot, xs[-1] - x0, header_h, stroke=1, fill=0)
        for xi in xs[1:-1]:
            c.line(xi, y_bot, xi, y_top)

        # Header text centered in each cell
        c.setFont(cjk_font, 9)
        for i, htxt in enumerate(headers):
            cx = (xs[i] + xs[i+1]) / 2.0
            c.drawCentredString(cx, y_top - 5*mm, htxt)

        y -= header_h

        # --- Draw data rows with full grid (vertical + horizontal)
        max_rows = int((y - (margin + 24*mm)) // row_h)
        rows = g.to_dict("records")
        data_rows = rows[:max_rows]

        # Draw outer box for all data rows first
        table_h = row_h * max(1, len(data_rows))
        y_data_top = y
        y_data_bot = y - table_h
        c.rect(x0, y_data_bot, xs[-1] - x0, table_h, stroke=1, fill=0)

        # Vertical separators
        for xi in xs[1:-1]:
            c.line(xi, y_data_bot, xi, y_data_top)

        # Horizontal separators between rows
        for r_i in range(1, len(data_rows)):
            yy = y_data_top - row_h * r_i
            c.line(x0, yy, xs[-1], yy)

        # Text helper
        def _cell_text(x_left, x_right, y_top_cell, s, align="left", wrap=False):
            pad = 1.2 * mm
            if s is None:
                s = ""
            s = str(s)
            if wrap:
                _draw_wrapped_cell_mixed(
                    c, x_left, x_right, y_top_cell, s, 8.2, cjk_font, lat_font,
                    max_lines=2, pad_x=pad, first_baseline_offset=4.0, line_gap=3.6
                )
                return
            y_baseline = y_top_cell - 6.2*mm
            if align == "center":
                c.setFont(lat_font, 8.5)
                c.drawCentredString((x_left + x_right) / 2.0, y_baseline, s)
            elif align == "right":
                c.setFont(lat_font, 8.5)
                c.drawRightString(x_right - pad, y_baseline, s)
            else:
                _draw_mixed(c, x_left + pad, y_baseline, s, 8.5, cjk_font, lat_font)

        # Write each row
        c.setFont(lat_font, 8.5)
        for r_i, r in enumerate(data_rows):
            y_row_top = y_data_top - row_h * r_i

            vals = [
                customer_order_no,
                (r.get("product_code") or ""),  # customer product/material number for delivery note print
                (r.get("product_name") or ""),
                f'{float(r.get("qty_pcs") or 0):g}',
                "PCS",
                f'{float(r.get("carton_qty") or 0):g}',
                f'{float(r.get("qty_per_carton") or 0):g}',
                (r.get("note") or ""),
            ]

            # order no / product code / product name / note use wrapped drawing;
            # especially order no may be longer than the first column and must stay inside its own cell.
            aligns = ["left", "left", "left", "center", "center", "center", "center", "left"]
            wrap_cols = {0, 1, 2, 7}

            for i, (v, al) in enumerate(zip(vals, aligns)):
                _cell_text(xs[i], xs[i+1], y_row_top, v, align=al, wrap=(i in wrap_cols))

        y = y_data_bot

        # Totals
        y -= 4*mm
        c.setFont(cjk_font, 11)
        total_text = f"合計 {total_pcs:g} PCS    合計 {total_carton:g} 箱"
        _draw_mixed_right(c, page_w - margin, y, total_text, 11, cjk_font, lat_font)

        # Seller footer
        y -= 10*mm
        c.setFont(cjk_font, 12)
        c.drawString(margin, y, "香巴拉責任有限公司")
        y -= 6*mm
        c.setFont(cjk_font, 10)
        _draw_mixed(c, margin, y, "公司地址 / Địa chỉ công ty:", 10, cjk_font, lat_font)
        y -= 5*mm
        c.setFont("Helvetica", 9)
        c.setFont(lat_font, 10)
        c.drawString(margin, y, "Lô J1, Đường NA3-DA3, KCN Mỹ phước 2, P. Mỹ Phước, Tx. Bến Cát, T. Bình")
        y -= 4*mm
        c.setFont(lat_font, 10)
        c.drawString(margin, y, "Dương")
        c.setFont(cjk_font, 10)

        c.showPage()

    c.save()
    return buf.getvalue()

_PRINT_SERVER_PORT = int(os.environ.get("ORDO_PRINT_PORT", "8765"))
_PRINT_SERVER_THREAD = None
_PRINT_CACHE_DIR = ROOT_DIR / "_ordo_print_cache"


class _QuietPrintHandler(SimpleHTTPRequestHandler):
    """Simple PDF file server for OrdoLite print cache."""

    def log_message(self, format, *args):
        # Keep Streamlit console clean.
        return


def _ensure_print_server() -> tuple[bool, str, int]:
    """Start a tiny local HTTP server for printable PDFs.

    Why: Chrome often blocks / blanks data: or blob: PDF opened from Streamlit components.
    Serving a normal http://host:port/file.pdf is much more stable.
    """
    global _PRINT_SERVER_THREAD
    _PRINT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if _PRINT_SERVER_THREAD is not None and _PRINT_SERVER_THREAD.is_alive():
        return True, "", _PRINT_SERVER_PORT

    def _run_server():
        handler = lambda *args, **kwargs: _QuietPrintHandler(
            *args, directory=str(_PRINT_CACHE_DIR), **kwargs
        )
        httpd = ThreadingHTTPServer(("0.0.0.0", _PRINT_SERVER_PORT), handler)
        httpd.serve_forever()

    try:
        t = threading.Thread(target=_run_server, daemon=True)
        t.start()
        time.sleep(0.15)
        _PRINT_SERVER_THREAD = t
        return True, "", _PRINT_SERVER_PORT
    except OSError as e:
        if "address already in use" in str(e).lower() or getattr(e, "errno", None) in (48, 98, 10048):
            return True, "", _PRINT_SERVER_PORT
        return False, str(e), _PRINT_SERVER_PORT
    except Exception as e:
        return False, str(e), _PRINT_SERVER_PORT


def _write_print_pdf_file(pdf_bytes: bytes, delivery_ids: list[int]) -> str:
    """Write PDF bytes to print cache and return filename."""
    _PRINT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        now = time.time()
        for p in _PRINT_CACHE_DIR.glob("delivery_note_*.pdf"):
            if now - p.stat().st_mtime > 24 * 3600:
                p.unlink(missing_ok=True)
    except Exception:
        pass

    ids_text = "_".join(str(int(x)) for x in delivery_ids) if delivery_ids else "none"
    digest = hashlib.md5(pdf_bytes).hexdigest()[:10]
    filename = f"delivery_note_{ids_text}_{digest}.pdf"
    (_PRINT_CACHE_DIR / filename).write_bytes(pdf_bytes)
    return filename


def _get_print_host_candidates() -> tuple[str, str]:
    """Return (LAN/configured host, localhost) for the PDF print server."""
    forced = os.environ.get("ORDO_PRINT_HOST", "").strip()
    if forced:
        return forced, "localhost"

    lan_ip = "localhost"
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.connect(("8.8.8.8", 80))
        lan_ip = sock.getsockname()[0]
    except Exception:
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            lan_ip = "localhost"
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass

    return lan_ip, "localhost"


def render_delivery_print_page(delivery_ids: list[int]) -> None:
    st.subheader(f"🖨️ {_t('列印送貨單')}")

    c1, c2 = st.columns([1.0, 6.0])
    with c1:
        if st.button(f"⬅️ {_t('返回')}", use_container_width=True, key="d01_print_back"):
            st.session_state["d01_show_print_page"] = False
            st.rerun()

    pdf_bytes = build_delivery_pdf(delivery_ids)
    if not pdf_bytes:
        st.error(_t("PDF 生成失敗：請確認已安裝 reportlab，且有可列印資料。"))
        return

    st.download_button(
        f"📥 {_t('下載送貨單 PDF')}",
        data=pdf_bytes,
        file_name="delivery_note.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="d01_print_download",
    )

    filename = _write_print_pdf_file(pdf_bytes, delivery_ids)
    ok_server, server_msg, port = _ensure_print_server()

    if not ok_server:
        st.error(f"{_t('列印服務啟動失敗')}：{server_msg}")
        st.info(_t("請先使用『下載送貨單 PDF』列印。"))
        return

    btn_text = _t("開啟列印分頁（新分頁）")

    # 原本這裡用 st.components.v1.html() 包一段 HTML/JS 來開 PDF。
    # 問題：Streamlit components 本身會被放進 iframe；若 JS 的 window.open() 回傳 null，
    # 原程式會 fallback 到 window.location.href = pdfUrl，結果就是 PDF 被塞回原本頁面的 iframe，
    # Chrome 不能正常呈現時就會出現灰色「無法呈現」區塊。
    #
    # 修正：不要再用 components iframe 畫按鈕或導向 PDF。
    # 改用 Streamlit 原生 link_button，只在新分頁開啟 PDF，不在原頁嵌入任何 PDF/iframe。
    lan_host, local_host = _get_print_host_candidates()

    # 優先使用使用者目前連進 OrdoLite 的主機名稱/IP，避免其他電腦拿到 localhost。
    browser_host = ""
    try:
        headers = getattr(getattr(st, "context", None), "headers", None)
        if headers:
            browser_host = headers.get("host", "") or headers.get("Host", "") or ""
            browser_host = str(browser_host).split(":")[0].strip()
    except Exception:
        browser_host = ""

    if browser_host and browser_host not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        main_host = browser_host
    else:
        main_host = lan_host or local_host

    main_url = f"http://{main_host}:{port}/{filename}"
    local_url = f"http://{local_host}:{port}/{filename}"

    st.link_button(
        f"🧾 {btn_text}",
        main_url,
        use_container_width=True,
    )

    with st.expander(_t("PDF 連結備用")):
        st.caption(_t("如果新分頁打不開，再複製下方連結到瀏覽器。"))
        st.code(main_url)
        st.caption(_t("主機本機備用："))
        st.code(local_url)






# ---- DB connection helpers ----
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
        st.error(f"DB connect error (fallback): {e}")
        return None

try:
    from db import get_connection  # type: ignore
except Exception:
    try:
        from db import get_engine  # type: ignore
        def get_connection():  # type: ignore
            eng = get_engine()
            return eng.raw_connection()
    except Exception:
        get_connection = _fallback_get_connection  # type: ignore

@st.cache_data(show_spinner=False, ttl=30)
def fetch_customers() -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    sql = """
        SELECT c.customer_id, c.customer_name
        FROM customer c
        ORDER BY c.customer_name ASC
    """
    df = pd.read_sql(sql, conn)
    try: conn.close()
    except Exception: pass
    return df

def _head_where(customer_id: Optional[int], date_from: Optional[date], date_to: Optional[date], keyword: str) -> Tuple[str, list]:
    where=[]; params=[]
    if customer_id:
        where.append("dh.customer_id = %s"); params.append(int(customer_id))
    if date_from:
        where.append("dh.created_at >= %s"); params.append(datetime.combine(date_from, datetime.min.time()))
    if date_to:
        where.append("dh.created_at < %s"); params.append(datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    kw=(keyword or "").strip()
    if kw:
        where.append("(dh.delivery_code LIKE %s OR dh.customer_order_no LIKE %s OR c.customer_name LIKE %s)")
        like=f"%{kw}%"; params.extend([like, like, like])
    return ("WHERE " + " AND ".join(where)) if where else "", params

def count_delivery_heads(customer_id: Optional[int], date_from: Optional[date], date_to: Optional[date], keyword: str) -> int:
    conn=get_connection()
    if conn is None: return 0
    where_sql, params = _head_where(customer_id, date_from, date_to, keyword)
    sql=f"""SELECT COUNT(*) FROM delivery_head dh JOIN customer c ON c.customer_id=dh.customer_id {where_sql}"""
    cur=conn.cursor(); cur.execute(sql, params); row=cur.fetchone()
    try: cur.close(); conn.close()
    except Exception: pass
    return int(row[0] if row else 0)

def fetch_delivery_heads(customer_id: Optional[int], date_from: Optional[date], date_to: Optional[date], keyword: str, limit: int, offset: int) -> pd.DataFrame:
    conn=get_connection()
    if conn is None: return pd.DataFrame()
    where_sql, params = _head_where(customer_id, date_from, date_to, keyword)
    sql=f"""
        SELECT dh.delivery_note_id, dh.delivery_code, dh.status, dh.customer_order_no, dh.vehicle_no, dh.delivery_date, dh.created_at, c.customer_name
        FROM delivery_head dh
        JOIN customer c ON c.customer_id = dh.customer_id
        {where_sql}
        ORDER BY dh.created_at DESC, dh.delivery_note_id DESC
        LIMIT %s OFFSET %s
    """
    df=pd.read_sql(sql, conn, params=params+[int(limit), int(offset)])
    try: conn.close()
    except Exception: pass
    return df

def fetch_delivery_products(delivery_head_ids: List[int]) -> pd.DataFrame:
    if not delivery_head_ids: return pd.DataFrame()
    conn=get_connection()
    if conn is None: return pd.DataFrame()
    ph=",".join(["%s"]*len(delivery_head_ids))
    sql=f"""
        SELECT dh.delivery_code AS 送貨單號, dp.line_no AS 行號, dp.customer_product_id AS 客戶料號, dp.product_name AS 品名, dp.qty AS 數量,
               dp.specification AS 規格, dp.specification_unit AS 規格單位, dp.color AS 顏色, dp.qty_per_carton AS 每箱數量
        FROM delivery_product dp
        JOIN delivery_head dh ON dh.delivery_note_id = dp.delivery_head_id
        WHERE dp.delivery_head_id IN ({ph})
        ORDER BY dh.delivery_code ASC, dp.line_no ASC
    """
    df=pd.read_sql(sql, conn, params=[int(x) for x in delivery_head_ids])
    try: conn.close()
    except Exception: pass
    return df

def _placeholders(n:int)->str:
    return ",".join(["%s"]*max(1,n))

def _get_table_column_set(cur, table_name: str) -> set[str]:
    """Return columns for current DB table using the same transaction cursor."""
    try:
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            """,
            (table_name,),
        )
        return {str(r[0]) for r in (cur.fetchall() or []) if r and r[0] is not None}
    except Exception:
        return set()


def _qcol(col_name: str) -> str:
    """Backtick quote a MySQL column name."""
    return "`" + str(col_name).replace("`", "``") + "`"


def _ar_payment_blocking_reason(cur, stmt_ids: List[int]) -> Optional[str]:
    """Return a message when selected delivery's AR already has customer payment.

    D02 deletion currently hard-deletes delivery_head, delivery_product,
    product_stock_io_head/line, ar_statement_head/line, and ar_apyable_payment.
    Once AR has any received amount, the delivery note must not be hard-deleted;
    otherwise customer collection records disappear with it.
    """
    clean_stmt_ids = sorted({int(x) for x in (stmt_ids or []) if x not in (None, "")})
    if not clean_stmt_ids:
        return None

    sph = _placeholders(len(clean_stmt_ids))
    paid_msg = (
        "此送貨單已經有客戶收款紀錄，D02 不可刪除。"
        "若真的要更正，請先到 AR 收款頁面作廢/沖銷收款紀錄，再由管理者處理。"
    )

    # 1) AR head itself may store paid/received summary or status.
    ar_cols = _get_table_column_set(cur, "ar_statement_head")

    ar_amount_candidates = [
        "actual_amount_paid", "paid_amount", "paid_total", "total_paid_amount",
        "received_amount", "receipt_amount", "collection_amount", "amount_received",
    ]
    ar_amount_cols = [c for c in ar_amount_candidates if c in ar_cols]
    if ar_amount_cols:
        amount_expr = " + ".join([f"COALESCE({_qcol(c)}, 0)" for c in ar_amount_cols])
        cur.execute(
            f"""
            SELECT statement_id
            FROM ar_statement_head
            WHERE statement_id IN ({sph})
              AND ({amount_expr}) > 0
            LIMIT 1
            FOR UPDATE
            """,
            clean_stmt_ids,
        )
        if cur.fetchone():
            return paid_msg

    ar_status_candidates = ["status", "payment_status", "collection_status", "receipt_status", "ar_status"]
    ar_status_cols = [c for c in ar_status_candidates if c in ar_cols]
    paid_statuses = "'paid','settled','partial','partially_paid','received','collected','closed'"
    if ar_status_cols:
        status_cond = " OR ".join([
            f"LOWER(COALESCE({_qcol(c)}, '')) IN ({paid_statuses})"
            for c in ar_status_cols
        ])
        cur.execute(
            f"""
            SELECT statement_id
            FROM ar_statement_head
            WHERE statement_id IN ({sph})
              AND ({status_cond})
            LIMIT 1
            FOR UPDATE
            """,
            clean_stmt_ids,
        )
        if cur.fetchone():
            return paid_msg

    # 2) Payment table: if any non-void payment has amount > 0, block deletion.
    pay_cols = _get_table_column_set(cur, "ar_apyable_payment")
    if not pay_cols:
        return None

    ar_id_col = "ar_id" if "ar_id" in pay_cols else ("statement_id" if "statement_id" in pay_cols else None)
    if not ar_id_col:
        return None

    pay_amount_candidates = [
        "actual_amount_paid", "payment_amount", "paid_amount", "amount_paid",
        "received_amount", "receipt_amount", "collection_amount", "amount_received",
    ]
    pay_amount_cols = [c for c in pay_amount_candidates if c in pay_cols]
    pay_status_candidates = ["status", "payment_status", "collection_status", "receipt_status"]
    pay_status_cols = [c for c in pay_status_candidates if c in pay_cols]

    # Ignore clearly void/cancelled/deleted rows. If amount > 0 is present, draft is still blocked
    # because hard deletion would erase the user's entered collection data.
    invalid_statuses = "'void','cancelled','canceled','cancel','deleted'"
    valid_status_sql = ""
    if pay_status_cols:
        valid_status_sql = " AND " + " AND ".join([
            f"LOWER(COALESCE({_qcol(c)}, '')) NOT IN ({invalid_statuses})"
            for c in pay_status_cols
        ])

    if pay_amount_cols:
        amount_expr = " + ".join([f"COALESCE({_qcol(c)}, 0)" for c in pay_amount_cols])
        cur.execute(
            f"""
            SELECT {_qcol(ar_id_col)}
            FROM ar_apyable_payment
            WHERE {_qcol(ar_id_col)} IN ({sph})
              AND ({amount_expr}) > 0
              {valid_status_sql}
            LIMIT 1
            FOR UPDATE
            """,
            clean_stmt_ids,
        )
        if cur.fetchone():
            return paid_msg
    else:
        # If old schema has no amount column, treat any positive/posted/paid payment row as blocking.
        positive_statuses = "'posted','paid','settled','partial','partially_paid','received','collected','closed'"
        if pay_status_cols:
            positive_status_sql = " OR ".join([
                f"LOWER(COALESCE({_qcol(c)}, '')) IN ({positive_statuses})"
                for c in pay_status_cols
            ])
            cur.execute(
                f"""
                SELECT {_qcol(ar_id_col)}
                FROM ar_apyable_payment
                WHERE {_qcol(ar_id_col)} IN ({sph})
                  AND ({positive_status_sql})
                LIMIT 1
                FOR UPDATE
                """,
                clean_stmt_ids,
            )
        else:
            cur.execute(
                f"""
                SELECT {_qcol(ar_id_col)}
                FROM ar_apyable_payment
                WHERE {_qcol(ar_id_col)} IN ({sph})
                LIMIT 1
                FOR UPDATE
                """,
                clean_stmt_ids,
            )
        if cur.fetchone():
            return paid_msg

    return None


def _refresh_customer_order_status_after_delivery_change(cur, order_ids: List[int]) -> None:
    """Refresh E01 customer_order.order_status after D02 delivery changes.

    The database already has sp_refresh_customer_order_status(), but the old flow
    only refreshed status when product_stock_io_line was inserted. Deleting a
    delivery note removes OUT records, so we must call the same refresh logic
    after deletion; otherwise E01 keeps showing the old shipped status.
    """
    clean_ids = sorted({int(x) for x in (order_ids or []) if x not in (None, "")})
    for oid in clean_ids:
        try:
            cur.execute("CALL sp_refresh_customer_order_status(%s)", (int(oid),))
            # mysql-connector may keep empty result sets after CALL; consume them
            # so the same cursor can continue safely.
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass
        except Exception:
            # Fallback: if the stored procedure is missing in a test DB, keep the
            # essential D02/E01 behavior correct based on remaining OUT records.
            cur.execute(
                """
                SELECT COUNT(*)
                FROM product_stock_io_head
                WHERE customer_order_id = %s
                  AND io_type = 'OUT'
                  AND COALESCE(status, '') <> 'void'
                """,
                (int(oid),),
            )
            row = cur.fetchone()
            out_cnt = int(row[0] or 0) if row else 0
            cur.execute(
                """
                UPDATE customer_order
                SET order_status = CASE WHEN %s > 0 THEN 'shipped' ELSE 'not_in_stock' END,
                    updated_at = NOW()
                WHERE customer_order_id = %s
                """,
                (out_cnt, int(oid)),
            )


def hard_delete_deliveries(delivery_ids: List[int]) -> tuple[bool,str]:
    """Hard delete exactly one delivery note and all generated AR / stock-out records.

    Safety rule: one click deletes one delivery note only. After deleting the
    generated OUT records, recalculate the linked E01 customer order status.
    """
    auth.require_delete(PAGE_KEY)
    if not delivery_ids:
        return False, "未選取任何送貨單。"

    ids=[int(x) for x in delivery_ids]
    if len(ids) != 1:
        return False, "一次只能刪除一張送貨單。請取消其他勾選後再刪除。"

    delivery_id = ids[0]
    conn=get_connection()
    if conn is None: return False, "DB 連線失敗。"
    try:
        cur=conn.cursor()
        try: conn.start_transaction()
        except Exception: pass

        # Capture affected customer orders BEFORE deleting delivery/stock-out rows.
        affected_order_ids: List[int] = []
        cur.execute(
            """
            SELECT DISTINCT customer_order_id
            FROM delivery_head
            WHERE delivery_note_id = %s
              AND customer_order_id IS NOT NULL
            """,
            (delivery_id,),
        )
        affected_order_ids.extend([int(r[0]) for r in (cur.fetchall() or []) if r and r[0] is not None])

        cur.execute(
            """
            SELECT DISTINCT customer_order_id
            FROM product_stock_io_head
            WHERE delivery_head_id = %s
              AND customer_order_id IS NOT NULL
            """,
            (delivery_id,),
        )
        affected_order_ids.extend([int(r[0]) for r in (cur.fetchall() or []) if r and r[0] is not None])
        affected_order_ids = sorted(set(affected_order_ids))

        # 1) AR children -> AR head.
        #    Safety guard: if the customer has already paid/partially paid this AR,
        #    D02 must not hard-delete the delivery note. Otherwise AR collection
        #    records would disappear together with the delivery.
        cur.execute("SELECT statement_id FROM ar_statement_head WHERE delivery_id = %s FOR UPDATE", (delivery_id,))
        stmt_ids=[int(r[0]) for r in (cur.fetchall() or [])]
        block_msg = _ar_payment_blocking_reason(cur, stmt_ids)
        if block_msg:
            try: conn.rollback()
            except Exception: pass
            return False, block_msg

        if stmt_ids:
            sph=_placeholders(len(stmt_ids))
            cur.execute(f"DELETE FROM ar_statement_line WHERE statement_id IN ({sph})", stmt_ids)
            cur.execute(f"DELETE FROM ar_apyable_payment WHERE ar_id IN ({sph})", stmt_ids)
            cur.execute(f"DELETE FROM ar_statement_head WHERE statement_id IN ({sph})", stmt_ids)

        # 2) Product stock-out children -> stock-out head.
        cur.execute("SELECT psioh_id FROM product_stock_io_head WHERE delivery_head_id = %s", (delivery_id,))
        psioh_ids=[int(r[0]) for r in (cur.fetchall() or [])]
        if psioh_ids:
            pph=_placeholders(len(psioh_ids))
            cur.execute(f"DELETE FROM product_stock_io_line WHERE psioh_id IN ({pph})", psioh_ids)
            cur.execute(f"DELETE FROM product_stock_io_head WHERE psioh_id IN ({pph})", psioh_ids)

        # 3) Delivery detail -> delivery head.
        cur.execute("DELETE FROM delivery_product WHERE delivery_head_id = %s", (delivery_id,))
        cur.execute("DELETE FROM delivery_head WHERE delivery_note_id = %s", (delivery_id,))

        # 4) E01 status must be recalculated after OUT rows are gone.
        _refresh_customer_order_status_after_delivery_change(cur, affected_order_ids)

        try: conn.commit()
        except Exception: pass
        return True, "已刪除送貨單 1 筆（含相關庫存/AR 紀錄；E01訂單狀態已更新）。"
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"刪除失敗：{e}"
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


def _init_state():
    # Page initialization only needs read permission.
    # Delete permission is checked only when the user actually confirms deletion
    # inside hard_delete_deliveries().
    # If this is require_delete(), users who can read/edit but cannot delete
    # will be stopped before the D02 page can render.
    auth.require_read(PAGE_KEY)
    st.session_state.setdefault("d01_page", 0)
    st.session_state.setdefault("d01_filter_page_size", 20)
    st.session_state.setdefault("d01_selected_ids", [])
    st.session_state.setdefault("d01_head_ver", 0)
    st.session_state.setdefault("d01_keyword", "")
    st.session_state.setdefault("d01_customer_name", "全部")


def _refresh_d01_master_state() -> None:
    """Refresh D02 master table state and clear stale data_editor selections."""
    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.session_state["d01_selected_ids"] = []
    st.session_state["d01_head_ver"] = int(st.session_state.get("d01_head_ver", 0)) + 1
    st.session_state["d01_show_delete_dialog"] = False
    st.session_state["d01_show_print_page"] = False
    st.session_state.pop("d01_print_ids", None)

def render_d01_master_and_detail() -> List[int]:
    _init_state()
    st.title(_t("送貨單管理（查詢 + 新增）"))
    customers=fetch_customers()
    customer_options=[("全部", None)] + [(str(r["customer_name"]), int(r["customer_id"])) for _, r in customers.iterrows()]
    today=date.today(); default_from=today - timedelta(days=30)
    # 讓查詢列撐滿整個可用頁寬：保留目前各欄相對比例，但移除右側多餘留白欄。
    cols=st.columns([2.0,2.0,2.0,2.5,1.0,1.3,1.0,1.4], vertical_alignment="bottom")  # 起始/結束/客戶=2.0

    with cols[0]: date_from=st.date_input(_t("起始日期"), value=st.session_state.get("d01_filter_date_from", default_from), key="d01_filter_date_from")
    with cols[1]: date_to=st.date_input(_t("結束日期"), value=st.session_state.get("d01_filter_date_to", today), key="d01_filter_date_to")
    with cols[2]:
        customer_name=st.selectbox(_t("客戶名稱"), options=[x[0] for x in customer_options], index=0, key="d01_filter_customer_name")
        customer_id=dict(customer_options).get(customer_name)
    with cols[3]: keyword=st.text_input(_t("關鍵字"), value=st.session_state.get("d01_filter_keyword", ""), key="d01_filter_keyword", placeholder=_t("送貨單號/客戶單號/客戶"))
    filter_sig=(customer_id,str(date_from),str(date_to),(keyword or "").strip(), st.session_state.get("d01_filter_page_size"))
    if st.session_state.get("d01_filter_sig")!=filter_sig:
        st.session_state.d01_filter_sig=filter_sig
        st.session_state.d01_page=0
    total=count_delivery_heads(customer_id,date_from,date_to,keyword)
    page_size=int(st.session_state.d01_filter_page_size)
    offset=st.session_state.d01_page * page_size
    has_next=(offset + page_size) < total
    prev_disabled=st.session_state.d01_page<=0
    with cols[4]:
        if st.button(_t("上一頁"), disabled=prev_disabled, use_container_width=True, key="d01_prev"):
            st.session_state.d01_page=max(0, st.session_state.d01_page-1); st.rerun()
    with cols[5]:
        ps=st.selectbox(_t("顯示筆數"), options=[10,20,30,50,100], index=[10,20,30,50,100].index(page_size), key="d01_page_size_sel", label_visibility="collapsed")
        st.session_state.d01_filter_page_size=int(ps)
    with cols[6]:
        if st.button(_t("下一頁"), disabled=not has_next, use_container_width=True, key="d01_next"):
            st.session_state.d01_page += 1; st.rerun()
    with cols[7]:
        st.caption(f"{_t('共')} {total} {_t('筆')}（{_t('第')} {st.session_state.d01_page+1} {_t('頁')}）")

    st.subheader(_t("送貨單（主表）"))
    page_size=int(st.session_state.d01_filter_page_size)
    offset=st.session_state.d01_page*page_size
    head_df=fetch_delivery_heads(customer_id,date_from,date_to,keyword,page_size,offset)
    if head_df.empty:
        st.info(_t("沒有符合條件的送貨單。"))
        st.session_state.d01_selected_ids=[]
        empty_refresh_cols = st.columns([1.2, 6.8])
        with empty_refresh_cols[0]:
            if st.button(f"🔄 {_d02_t('重新整理')}", use_container_width=True, key="d01_refresh_empty_btn"):
                _refresh_d01_master_state()
                st.rerun()
        return []
    display=head_df.copy()
    display.insert(0,"_選取", False)

    display_i18n, display_reverse_map = _translate_d02_columns(display, D02_MASTER_COLUMN_LABELS)
    select_col = _d02_t("勾選")
    id_col = _d02_t("ID")

    edited_display=st.data_editor(
        display_i18n,
        hide_index=True,
        use_container_width=True,
        column_config={
            select_col: st.column_config.CheckboxColumn(""),
            id_col: st.column_config.NumberColumn(id_col, disabled=True),
        },
        disabled=[c for c in display_i18n.columns if c != select_col],
        key=f"d01_head_editor_{st.session_state.d01_head_ver}_{_d02_lang()}",
    )
    edited = _restore_d02_columns(edited_display, display_reverse_map)
    selected_ids=edited.loc[edited["_選取"]==True, "delivery_note_id"].astype(int).tolist()
    st.session_state.d01_selected_ids=selected_ids

    # actions
    action_cols=st.columns([0.9,0.9,1.0,3.8,1.3])
    with action_cols[0]:
        if st.button(f"🗑️ {_t('刪除')}", disabled=(len(selected_ids)==0), use_container_width=True, key="d01_delete_btn"):
            if len(selected_ids) != 1:
                st.warning(_t("一次只能勾選一張送貨單刪除。請取消其他勾選。"))
            else:
                st.session_state["d01_show_delete_dialog"]=True
    with action_cols[1]:
        if st.button(f"🖨️ {_t('列印')}", disabled=(len(selected_ids)==0), use_container_width=True, key="d01_print_btn"):
            st.session_state["d01_print_ids"]=selected_ids
            st.session_state["d01_show_print_page"]=True
            st.rerun()
    with action_cols[2]:
        if st.button(f"🔄 {_d02_t('重新整理')}", use_container_width=True, key="d01_refresh_btn"):
            _refresh_d01_master_state()
            st.rerun()

    with action_cols[3]:
        st.write("")
    with action_cols[4]:
        if st.button(_t("取消勾選"), disabled=(len(selected_ids)==0), use_container_width=True, key="d01_clear_sel_btn"):
            st.session_state.d01_selected_ids = []
            st.session_state.d01_head_ver += 1
            st.rerun()

    if st.session_state.get("d01_show_print_page", False):
        ids=st.session_state.get("d01_print_ids", [])
        render_delivery_print_page(ids)
        return selected_ids


    if st.session_state.get("d01_show_delete_dialog", False):
        codes=edited.loc[edited["_選取"]==True, "delivery_code"].astype(str).tolist()
        codes_text="\n".join([f"- {c}" for c in codes]) if codes else "(無)"
        try:
            @st.dialog("刪除確認")
            def _dlg():
                st.warning(_t("是否刪除以上送貨單資料？資料刪除後無法回復。"))
                st.markdown(codes_text)
                c1,c2=st.columns(2)
                with c1:
                    if st.button(_t("確認"), use_container_width=True):
                        ok,msg=hard_delete_deliveries(selected_ids)
                        if ok:
                            st.success(msg)
                            st.session_state["d01_show_delete_dialog"]=False
                            st.session_state.d01_selected_ids=[]
                            st.session_state.d01_head_ver += 1
                            st.cache_data.clear()
                            st.rerun()
                        else: st.error(msg)
                with c2:
                    if st.button(_t("取消"), use_container_width=True):
                        st.session_state["d01_show_delete_dialog"]=False; st.rerun()
            _dlg()
        except Exception:
            st.warning(_t("是否刪除以上送貨單資料？資料刪除後無法回復。"))
            st.markdown(codes_text)
            c1,c2=st.columns(2)
            with c1:
                if st.button(_t("確認刪除"), use_container_width=True, key="d01_confirm_delete"):
                    ok,msg=hard_delete_deliveries(selected_ids)
                    if ok: st.success(msg); st.session_state["d01_show_delete_dialog"]=False; st.session_state.d01_selected_ids=[]; st.session_state.d01_head_ver += 1; st.cache_data.clear(); st.rerun()
                    else: st.error(msg)
            with c2:
                if st.button(_t("取消"), use_container_width=True, key="d01_cancel_delete"):
                    st.session_state["d01_show_delete_dialog"]=False; st.rerun()

    st.subheader(_t("送貨單明細（delivery_product）"))
    if not selected_ids:
        st.caption(_t("在上方勾選送貨單後，這裡會顯示明細。"))
        return []
    dp_df=fetch_delivery_products(selected_ids)
    if dp_df.empty: st.info(_t("選取的送貨單沒有明細。"))
    else:
        dp_df_i18n, _ = _translate_d02_columns(dp_df)
        st.dataframe(dp_df_i18n, hide_index=True, use_container_width=True)
    return selected_ids

def render_delivery_entry_d02():
    import streamlit as st

    import pandas as pd
    import random
    import math
    from datetime import datetime
    from typing import Optional, Tuple, List, Dict, Any
    
    # =============================================================================
    # OrdoLite - D02 新建送貨單（Header + 明細逐筆新增）
    # 需求重點
    # - 不直接在 data_editor 內改（避免不確定性）
    # - 上方：客戶下拉、車號 TextBox、依客戶產生的可出貨訂單下拉
    # - 下方：逐筆輸入明細（TextBox/NumberInput）
    # - 儲存時：
    #   1) delivery_head / delivery_product 寫入
    #   2) product_stock_io 寫入 io_type = 'OUT'
    # =============================================================================
    
    # ---------------------------
    # DB connection helpers
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
            st.error(f"DB connect error (fallback): {e}")
            return None
    
    
    # 優先沿用你專案的 db.py：get_connection() 或 get_engine()
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
    # Schema helpers (avoid 1054 Unknown column in mixed DB schemas)
    # ---------------------------
    @st.cache_data(show_spinner=False, ttl=3600)
    def get_table_columns(table_name: str) -> set:
        """Return a set of column names for a table in the current DB."""
        conn = get_connection()
        if conn is None:
            return set()
        cols = set()
        try:
            cur = conn.cursor()
            cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
            rows = cur.fetchall()
            for r in rows:
                if r and len(r) >= 1:
                    cols.add(str(r[0]))
        except Exception:
            cols = set()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return cols
    
    # ---------------------------
    # Cacheable query helpers
    # ---------------------------
    
    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_customers() -> pd.DataFrame:
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
    
        sql = """
            SELECT
                c.customer_id,
                c.customer_code,
                c.customer_name,
                c.customer_shortname,
                c.is_active
            FROM customer c
            ORDER BY c.customer_name ASC
        """
        df = pd.read_sql(sql, conn)
        try:
            conn.close()
        except Exception:
            pass
        return df
    

    def _current_login_user_id(default: int = 1) -> int:
        """Return the current logged-in user_id from Streamlit session state."""
        try:
            return int(st.session_state.get("user_id") or default)
        except Exception:
            return int(default)


    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_login_user_profile(user_id: int) -> Dict[str, Any]:
        """Fetch current login user's display name.

        D02 must store created_by as user.user_id, but the UI should display the
        employee/staff name and must not let users change it manually.
        """
        conn = get_connection()
        if conn is None:
            return {
                "user_id": int(user_id),
                "username": str(st.session_state.get("username") or ""),
                "stuff_name": "",
                "display_name": str(st.session_state.get("username") or f"User {int(user_id)}"),
            }
        try:
            sql = """
                SELECT
                    u.user_id,
                    u.username,
                    u.user_code,
                    COALESCE(s.stuff_name, '') AS stuff_name
                FROM `user` u
                LEFT JOIN stuff s
                  ON s.stuff_id = u.stuff_id
                WHERE u.user_id = %s
                LIMIT 1
            """
            df = pd.read_sql(sql, conn, params=[int(user_id)])
            if df is None or df.empty:
                username = str(st.session_state.get("username") or "")
                display_name = username or f"User {int(user_id)}"
                return {
                    "user_id": int(user_id),
                    "username": username,
                    "stuff_name": "",
                    "display_name": display_name,
                }

            row = df.iloc[0]
            username = str(row.get("username") or "").strip()
            stuff_name = str(row.get("stuff_name") or "").strip()
            display_name = stuff_name or username or f"User {int(user_id)}"
            return {
                "user_id": int(row.get("user_id") or user_id),
                "username": username,
                "stuff_name": stuff_name,
                "display_name": display_name,
            }
        except Exception:
            username = str(st.session_state.get("username") or "")
            display_name = username or f"User {int(user_id)}"
            return {
                "user_id": int(user_id),
                "username": username,
                "stuff_name": "",
                "display_name": display_name,
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass

    
    
    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_receiving_addresses(customer_id: int) -> pd.DataFrame:
        """Fetch customer receiving (shipping) addresses for dropdown."""
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
        sql = """
            SELECT receiving_id, receiving_add, warehouse_contact_person, tel, is_active
            FROM customer_receiving_add
            WHERE customer_id = %s
            ORDER BY receiving_id ASC
        """
        df = pd.read_sql(sql, conn, params=[int(customer_id)])
        try:
            conn.close()
        except Exception:
            pass
        return df
    
    
    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_customer_order_deliver_to(customer_order_id: int) -> Optional[int]:
        """Return customer_order.deliver_to if present in schema; otherwise None."""
        if not customer_order_id:
            return None
    
        cols = get_table_columns("customer_order")
        if "deliver_to" not in cols:
            return None
    
        conn = get_connection()
        if conn is None:
            return None
        try:
            df = pd.read_sql(
                "SELECT deliver_to FROM customer_order WHERE customer_order_id = %s",
                conn,
                params=[int(customer_order_id)],
            )
            if df is None or df.empty:
                return None
            v = df.iloc[0].get("deliver_to")
            if pd.isna(v):
                return None
            return int(v)
        except Exception:
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass
    
    
    
    def fetch_products_by_customer(customer_id: int, limit: int = 5000) -> pd.DataFrame:
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
    
        sql = """
            SELECT
                p.product_id,
                p.product_code,
                p.product_name,
                p.customer_id,
                p.customer_production_id AS customer_product_id,
                p.Specification AS specification,
                p.Specification_unit AS specification_unit,
                p.color,
                p.qty_per_carton,
                p.is_active
            FROM product p
            WHERE p.customer_id = %s
            ORDER BY p.product_name ASC
            LIMIT %s
        """
    
        df = pd.read_sql(sql, conn, params=[int(customer_id), int(limit)])
        try:
            conn.close()
        except Exception:
            pass
        return df
    
    
    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_customer_orders_for_delivery(customer_id: int) -> pd.DataFrame:
        """回傳該客戶的訂單清單，並嘗試計算已出貨/未出貨數量。
    
        注意：你目前的 dump 中 customer_order_item 可能是空的；
        因此這裡不會硬過濾 remaining_qty > 0，避免選單變空。
        """
    
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
    
        sql = """
            SELECT
                co.customer_order_id,
                co.customer_order_num,
                co.customer_order_code,
                co.customer_order_category,
                co.deliver_date,
                co.order_status,
                co.created_at,
                COALESCE(oi.ordered_qty, 0) AS ordered_qty,
                COALESCE(dv.delivered_qty, 0) AS delivered_qty,
                (COALESCE(oi.ordered_qty, 0) - COALESCE(dv.delivered_qty, 0)) AS remaining_qty
            FROM customer_order co
            LEFT JOIN (
                SELECT customer_order_id, SUM(quantity) AS ordered_qty
                FROM customer_order_item
                GROUP BY customer_order_id
            ) oi ON oi.customer_order_id = co.customer_order_id
            LEFT JOIN (
                SELECT dh.customer_order_id, SUM(dp.qty) AS delivered_qty
                FROM delivery_head dh
                JOIN delivery_product dp ON dp.delivery_head_id = dh.delivery_note_id
                WHERE dh.status = 'posted'
                  AND dh.customer_order_id IS NOT NULL
                GROUP BY dh.customer_order_id
            ) dv ON dv.customer_order_id = co.customer_order_id
            WHERE co.customer_id = %s
              AND COALESCE(co.order_status, '') <> 'closed'
            ORDER BY co.deliver_date DESC, co.created_at DESC, co.customer_order_id DESC
        """
    
        df = pd.read_sql(sql, conn, params=[int(customer_id)])
        try:
            conn.close()
        except Exception:
            pass
    
        return df
    
    
    def suggest_delivery_code_de(customer_shortname: str) -> str:
        """Suggest the next DE-<customer>-<yymm><###> delivery code."""
        conn = get_connection()
        if conn is None:
            return f"DE-{customer_shortname}-{datetime.now().strftime('%y%m')}001"
        try:
            return generate_delivery_code_de(conn, customer_shortname)
        except Exception:
            return f"DE-{customer_shortname}-{datetime.now().strftime('%y%m')}001"
        finally:
            try:
                conn.close()
            except Exception:
                pass
    
    
    
    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_customer_order_by_code(order_code_or_num: str) -> pd.DataFrame:
        """以「我方公司訂單號碼（customer_order_code）」或「客戶訂單號碼（customer_order_num）」查詢訂單。
        回傳欄位：customer_order_id, customer_id, customer_order_num, customer_order_code
        """
        code = (order_code_or_num or "").strip()
        if not code:
            return pd.DataFrame()
    
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
    
        sql = """
            SELECT
                co.customer_order_id,
                co.customer_id,
                co.customer_order_num,
                co.customer_order_code,
                co.customer_order_category
            FROM customer_order co
            WHERE co.customer_order_code = %s
               OR co.customer_order_num  = %s
            ORDER BY co.customer_order_id DESC
            LIMIT 1
        """
        df = pd.read_sql(sql, conn, params=[code, code])
        try:
            conn.close()
        except Exception:
            pass
        return df
    
    
    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_customer_order_items(customer_order_id: int) -> pd.DataFrame:
        """載入指定訂單的品項（customer_order_item + product）。"""
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
    
        sql = """
            SELECT
                coi.customer_order_item_id,
                coi.customer_order_id,
                coi.line_no,
                coi.product_id,
                coi.quantity,
                coi.unit AS order_unit,
                coi.price_unit AS order_price_unit,
                coi.barcode AS order_barcode,
                p.product_code,
                p.product_name,
                p.customer_production_id AS customer_product_id,
                p.Specification AS specification,
                p.Specification_unit AS specification_unit,
                p.color,
                p.qty_per_carton
            FROM customer_order_item coi
            JOIN product p ON p.product_id = coi.product_id
            WHERE coi.customer_order_id = %s
            ORDER BY coi.line_no ASC, coi.customer_order_item_id ASC
        """
        df = pd.read_sql(sql, conn, params=[int(customer_order_id)])
        try:
            conn.close()
        except Exception:
            pass
        return df


    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_sample_orders_for_delivery(customer_id: int) -> pd.DataFrame:
        """取得可供送貨的樣品單；樣品不要求先建立正式產品。"""
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
        try:
            return pd.read_sql("""
                SELECT sample_order_id, sample_order_code, sample_category,
                       target_completion_date, status, created_at
                FROM sample_order_head
                WHERE customer_id = %s AND COALESCE(status, '') <> 'cancelled'
                ORDER BY created_at DESC, sample_order_id DESC
            """, conn, params=[int(customer_id)])
        finally:
            conn.close()


    @st.cache_data(show_spinner=False, ttl=30)
    def fetch_sample_order_items(sample_order_id: int) -> pd.DataFrame:
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
        try:
            return pd.read_sql("""
                SELECT soi.sample_order_item_id, soi.line_no, soi.product_id,
                       soi.sample_name AS product_name,
                       soi.customer_item_code AS customer_product_id,
                       soi.specification, soi.material_structure, soi.quantity,
                       soi.unit AS order_unit, soi.unit_price AS order_price_unit,
                       COALESCE(p.product_code, '') AS product_code,
                       COALESCE(p.Specification_unit, 'mm') AS specification_unit,
                       COALESCE(p.color, '') AS color, p.qty_per_carton
                FROM sample_order_item soi
                LEFT JOIN product p ON p.product_id = soi.product_id
                WHERE soi.sample_order_id = %s
                ORDER BY soi.line_no, soi.sample_order_item_id
            """, conn, params=[int(sample_order_id)])
        finally:
            conn.close()


    @st.cache_data(show_spinner=False, ttl=15)
    def fetch_customer_order_delivery_summary(customer_order_id: int) -> pd.DataFrame:
        """依 customer_order_id + product_id 彙總訂購量與已送貨量。"""
        if not customer_order_id:
            return pd.DataFrame()
    
        conn = get_connection()
        if conn is None:
            return pd.DataFrame()
    
        sql = """
            SELECT
                coi.product_id,
                MAX(COALESCE(p.product_code, '')) AS product_code,
                MAX(COALESCE(p.product_name, '')) AS product_name,
                SUM(COALESCE(coi.quantity, 0)) AS qty_ordered,
                COALESCE(dv.qty_delivered, 0) AS qty_delivered
            FROM customer_order_item coi
            LEFT JOIN product p
              ON p.product_id = coi.product_id
            LEFT JOIN (
                SELECT
                    dh.customer_order_id,
                    dp.product_id,
                    SUM(COALESCE(dp.qty, 0)) AS qty_delivered
                FROM delivery_head dh
                JOIN delivery_product dp
                  ON dp.delivery_head_id = dh.delivery_note_id
                WHERE dh.customer_order_id = %s
                  AND dh.status = 'posted'
                GROUP BY dh.customer_order_id, dp.product_id
            ) dv
              ON dv.customer_order_id = coi.customer_order_id
             AND dv.product_id = coi.product_id
            WHERE coi.customer_order_id = %s
            GROUP BY coi.product_id, dv.qty_delivered
            ORDER BY coi.product_id
        """
        df = pd.read_sql(sql, conn, params=[int(customer_order_id), int(customer_order_id)])
        try:
            conn.close()
        except Exception:
            pass
        return df
    
    
    def build_delivery_over_warning_lines(customer_order_id: Optional[int], draft_lines: List[Dict[str, Any]]) -> List[str]:
        """回傳超送警告訊息清單（只提醒，不阻擋）。"""
        if not customer_order_id or not draft_lines:
            return []
    
        summary_df = fetch_customer_order_delivery_summary(int(customer_order_id))
        if summary_df.empty:
            return []
    
        draft_by_product: Dict[int, float] = {}
        for r in draft_lines:
            pid = r.get('product_id')
            qty = r.get('qty')
            try:
                pid_i = int(pid)
                qty_f = float(qty)
            except Exception:
                continue
            if qty_f <= 0:
                continue
            draft_by_product[pid_i] = draft_by_product.get(pid_i, 0.0) + qty_f
    
        warnings: List[str] = []
        for _, row in summary_df.iterrows():
            try:
                pid = int(row.get('product_id'))
            except Exception:
                continue
            current_add = float(draft_by_product.get(pid, 0.0))
            if current_add <= 0:
                continue
    
            qty_ordered = float(row.get('qty_ordered') or 0)
            qty_delivered = float(row.get('qty_delivered') or 0)
            qty_after = qty_delivered + current_add
            over_qty = qty_after - qty_ordered
            if over_qty > 0:
                product_code = str(row.get('product_code') or '').strip()
                product_name = str(row.get('product_name') or '').strip()
                display_name = ' | '.join([x for x in [product_code, product_name] if x]) or f'product_id={pid}'
                warnings.append(
                    f"⚠️ {display_name}：訂購 {qty_ordered:g}，已送 {qty_delivered:g}，本次送貨 {current_add:g}，累計將達 {qty_after:g}，超出 {over_qty:g}"
                )
        return warnings
    
    
    
    # ---------------------------
    # Write helpers
    # ---------------------------
    
    def _yyyymm(dt: Optional[datetime] = None) -> str:
        if dt is None:
            dt = datetime.now()
        return dt.strftime("%Y%m")
    
    
    def generate_delivery_code(prefix: str = "DN") -> str:
        """Legacy random code generator (kept for backward compatibility)."""
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        rnd = random.randint(100, 999)
        return f"{prefix}{ts}{rnd}"
    
    
    def generate_delivery_code_de(
        conn, customer_shortname: str, dt: Optional[datetime] = None
    ) -> str:
        """Generate ``DE-<customer>-<yymm><###>`` per customer and month."""
        shortname = str(customer_shortname or "").strip()
        if not shortname:
            raise ValueError("客戶簡稱不可空白，無法產生送貨單號")
        if dt is None:
            dt = datetime.now()
        yymm = dt.strftime("%y%m")
        code_prefix = f"DE-{shortname}-{yymm}"
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(MAX(CAST(RIGHT(delivery_code, 3) AS UNSIGNED)), 0)
            FROM delivery_head
            WHERE LEFT(delivery_code, %s) = %s
              AND CHAR_LENGTH(delivery_code) = %s
              AND RIGHT(delivery_code, 3) REGEXP '^[0-9]{3}$'
        """, (len(code_prefix), code_prefix, len(code_prefix) + 3))
        row = cur.fetchone()
        last_no = int(row[0] or 0) if row else 0
        if last_no >= 999:
            raise ValueError("本客戶本月的送貨單流水號已達三碼上限")
        return f"{code_prefix}{last_no + 1:03d}"
    
    
    def insert_delivery_and_stock_out(
        *,
        delivery_code: Optional[str],
        delivery_date: Optional[date],
        customer_id: int,
        customer_order_id: Optional[int],
        sample_order_id: Optional[int],
        customer_order_no: Optional[str],
        vehicle_no: Optional[str],
        deliver_to: Optional[int],
        status: str,
        created_by: int,
        lines: List[Dict[str, Any]],
    ) -> Tuple[bool, str]:
        """寫入送貨單與庫存 OUT。
    
        lines: list of dict
          - product_id (required)
          - product_code (optional)
          - customer_product_id (optional)
          - product_name (optional)
          - qty (required)
          - product_unit_price (optional; from E01/customer_order_item.price_unit)
          - line_amount (optional; qty * product_unit_price)
          - specification (optional)
          - specification_unit (optional)
          - color (optional)
          - qty_per_carton (optional)
          - carton_used (optional)
          - note (optional)
        """
    
        if not lines:
            return False, "沒有任何出貨明細"
    
        conn = get_connection()
        if conn is None:
            return False, "DB 連線失敗"
    
        try:
            cur = conn.cursor()
    
            # -------------------------------------------------------------
            # Delivery code / 送貨單號
            # - Required by you: DE-客戶簡稱-yymm + 3-digit running number.
            # - If UI provided a delivery_code, use it; otherwise auto-generate.
            # -------------------------------------------------------------
            if delivery_code and str(delivery_code).strip():
                delivery_code = str(delivery_code).strip()
            else:
                cur.execute(
                    "SELECT customer_shortname FROM customer WHERE customer_id = %s",
                    (int(customer_id),),
                )
                customer_row = cur.fetchone()
                customer_shortname = str(customer_row[0] or "").strip() if customer_row else ""
                delivery_code = generate_delivery_code_de(
                    conn,
                    customer_shortname,
                    datetime.combine(delivery_date, datetime.min.time()) if delivery_date else None,
                )
    
            
            # 1) delivery_head  (schema-aware; supports optional deliver_to / delivery_date column)
            head_cols = get_table_columns("delivery_head")

            insert_cols = [
                "delivery_code",
                "customer_id",
                "customer_order_id",
                "customer_order_no",
                "vehicle_no",
                "status",
                "created_by",
            ]
            insert_vals = [
                delivery_code,
                int(customer_id),
                (int(customer_order_id) if customer_order_id else None),
                (customer_order_no or None),
                (vehicle_no or None),
                (status or "draft"),
                int(created_by),
            ]

            # Required by you: save delivery_date (if column exists)
            if "delivery_date" in head_cols:
                insert_cols.insert(1, "delivery_date")
                insert_vals.insert(1, delivery_date if delivery_date else None)

            if "sample_order_id" in head_cols:
                sample_idx = insert_cols.index("customer_order_no")
                insert_cols.insert(sample_idx, "sample_order_id")
                insert_vals.insert(sample_idx, (int(sample_order_id) if sample_order_id else None))

            # Optional: delivery_head.deliver_to (FK -> customer_receiving_add.receiving_id)
            if "deliver_to" in head_cols:
                insert_cols.append("deliver_to")
                insert_vals.append(int(deliver_to) if deliver_to else None)

            col_sql = ", ".join(f"`{c}`" for c in insert_cols)
            ph_sql = ", ".join(["%s"] * len(insert_cols))

            sql_head = f"""
                INSERT INTO delivery_head
                ({col_sql}, `created_at`)
                VALUES ({ph_sql}, NOW())
            """

            cur.execute(sql_head, tuple(insert_vals))
    
            delivery_note_id = cur.lastrowid
# 2) delivery_product (schema-aware: include note if exists)
            dp_cols = get_table_columns("delivery_product")
            insert_dp_cols = ["line_no", "delivery_head_id", "product_id", "customer_product_id", "product_name", "qty",
                              "specification", "specification_unit", "color", "qty_per_carton"]
            if "customer_order_item_id" in dp_cols:
                insert_dp_cols.append("customer_order_item_id")
            if "schedule_id" in dp_cols:
                insert_dp_cols.append("schedule_id")
            if "product_unit_price" in dp_cols:
                insert_dp_cols.append("product_unit_price")
            if "line_amount" in dp_cols:
                insert_dp_cols.append("line_amount")
            if "note" in dp_cols:
                insert_dp_cols.append("note")
            col_sql_dp = ", ".join(insert_dp_cols)
            ph_sql_dp = ", ".join(["%s"] * len(insert_dp_cols))
            sql_line = f"""INSERT INTO delivery_product ({col_sql_dp}) VALUES ({ph_sql_dp})"""
# 3) product_stock_io_head + product_stock_io_line (OUT)
            #    You migrated schema: product_stock_io -> head/line.
            #    So D02 must write into product_stock_io_head and product_stock_io_line.
            psh_cols = get_table_columns("product_stock_io_head")
            psl_cols = get_table_columns("product_stock_io_line")
    
            # New schema (2026-02): split head/line tables.
            # Only enforce truly NOT NULL columns used by OUT flow.
            _psh_required = {"doc_no", "io_type", "delivery_head_id", "created_by"}
            _psl_required = {"psioh_id", "line_no", "item_id", "customer_material_num", "production_num", "qty_PCS", "created_by"}
    
            if not _psh_required.issubset(psh_cols):
                missing = ", ".join(sorted(_psh_required - psh_cols))
                raise RuntimeError(f"product_stock_io_head 缺少必要欄位：{missing}")
            if not _psl_required.issubset(psl_cols):
                missing = ", ".join(sorted(_psl_required - psl_cols))
                raise RuntimeError(f"product_stock_io_line 缺少必要欄位：{missing}")
    
            # 3) product_stock_io_head (OUT)
            # truck_no belongs to delivery_head.vehicle_no per requirement; keep NULL in io_head.
            sql_psh_cols = ["doc_no", "io_type", "delivery_head_id", "created_by"]
            sql_psh_vals = [delivery_code, "OUT", int(delivery_note_id), int(created_by)]
    
            # Optional columns (schema-aware)
            if "io_time" in psh_cols:
                sql_psh_cols.append("io_time")
                # use NOW() in SQL (no placeholder)
            if "customer_order_id" in psh_cols:
                sql_psh_cols.append("customer_order_id")
                sql_psh_vals.append(int(customer_order_id) if customer_order_id else None)
            if "status" in psh_cols:
                sql_psh_cols.append("status")
                sql_psh_vals.append("posted" if status == "posted" else "draft")
            if "note" in psh_cols:
                sql_psh_cols.append("note")
                sql_psh_vals.append(None)
            if "operator" in psh_cols:
                sql_psh_cols.append("operator")
                sql_psh_vals.append(None)
            if "period" in psh_cols:
                sql_psh_cols.append("period")
                sql_psh_vals.append(_yyyymm())
            if "truck_no" in psh_cols:
                sql_psh_cols.append("truck_no")
                sql_psh_vals.append(None)
    
            col_sql = ", ".join(f"`{c}`" for c in sql_psh_cols)
            ph_sql_parts = []
            v_iter = iter(sql_psh_cols)
            # build placeholders; io_time handled as NOW()
            for c in sql_psh_cols:
                if c == "io_time":
                    ph_sql_parts.append("NOW()")
                else:
                    ph_sql_parts.append("%s")
            ph_sql = ", ".join(ph_sql_parts)
    
            sql_psh = f"""INSERT INTO product_stock_io_head ({col_sql}, `created_at`) VALUES ({ph_sql}, NOW())"""
            cur.execute(sql_psh, tuple(sql_psh_vals))
            psioh_id = cur.lastrowid
    
            # 4) product_stock_io_line (OUT lines)
            sql_psl = """
                INSERT INTO product_stock_io_line
                (psioh_id, line_no, item_id, customer_material_num, production_num,
                 customer_order_item_id, schedule_id,
                 note, operator, created_by, created_at, period, reversed_io_id, qty_PCS, carton_used)
                VALUES (%s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, NOW(),
                        %s, %s, %s, %s)
            """
    
            inserted_lines = 0
            inserted_stock_lines = 0
            line_no = 1
            for r in lines:
                pid = r.get("product_id")
                qty = r.get("qty")
    
                pid_i = None
                if pid not in (None, ""):
                    try:
                        pid_i = int(pid)
                    except Exception:
                        continue
    
                try:
                    qty_f = float(qty)
                except Exception:
                    continue
    
                if qty_f <= 0:
                    continue

                customer_order_item_id = r.get("customer_order_item_id")
                if customer_order_item_id in (None, "") and customer_order_id and pid_i:
                    cur.execute("""
                        SELECT customer_order_item_id
                        FROM customer_order_item
                        WHERE customer_order_id=%s AND product_id=%s
                        ORDER BY customer_order_item_id
                        LIMIT 1
                    """, (int(customer_order_id), int(pid_i)))
                    matched_item = cur.fetchone()
                    customer_order_item_id = matched_item[0] if matched_item else None
                customer_order_item_id = (
                    int(customer_order_item_id) if customer_order_item_id not in (None, "") else None
                )

                schedule_id = r.get("schedule_id")
                if schedule_id in (None, "") and customer_order_item_id:
                    cur.execute("""
                        SELECT schedule_id
                        FROM customer_order_item_schedule
                        WHERE customer_order_item_id=%s
                          AND COALESCE(status, 'open') <> 'cancelled'
                        ORDER BY due_date, schedule_id
                        LIMIT 1
                    """, (customer_order_item_id,))
                    matched_schedule = cur.fetchone()
                    schedule_id = matched_schedule[0] if matched_schedule else None
                schedule_id = int(schedule_id) if schedule_id not in (None, "") else None
    
                # delivery_product row (include note when column exists)
                dp_params = [
                    line_no,
                    int(delivery_note_id),
                    pid_i,
                    (r.get("customer_product_id") or None),
                    (r.get("product_name") or None),
                    qty_f,
                    (r.get("specification") or None),
                    (r.get("specification_unit") or None),
                    (r.get("color") or None),
                    (None if r.get("qty_per_carton") in (None, "") else int(r.get("qty_per_carton"))),
                ]
                if "customer_order_item_id" in dp_cols:
                    dp_params.append(customer_order_item_id)
                if "schedule_id" in dp_cols:
                    dp_params.append(schedule_id)
                unit_price_val = None
                if r.get("product_unit_price") not in (None, ""):
                    try:
                        unit_price_val = float(r.get("product_unit_price"))
                    except Exception:
                        unit_price_val = None

                line_amount_val = None
                if r.get("line_amount") not in (None, ""):
                    try:
                        line_amount_val = float(r.get("line_amount"))
                    except Exception:
                        line_amount_val = None
                elif unit_price_val is not None:
                    line_amount_val = round(float(unit_price_val) * float(qty_f), 2)

                if "product_unit_price" in dp_cols:
                    dp_params.append(unit_price_val)
                if "line_amount" in dp_cols:
                    dp_params.append(line_amount_val)
                if "note" in dp_cols:
                    dp_params.append(r.get("note") or None)

                cur.execute(sql_line, tuple(dp_params))

                # 樣品可尚未轉為正式產品：保留送貨與 AR 明細，但不建立庫存 OUT。
                inserted_lines += 1
                if pid_i is None:
                    line_no += 1
                    continue
    
                # product_stock_io_line row (OUT)
                customer_material_num = (
                    (r.get("customer_product_id") or "")
                    if str(r.get("customer_product_id") or "").strip()
                    else (r.get("product_code") or "")
                )
                if not customer_material_num:
                    # product_stock_io_line.customer_material_num is NOT NULL
                    customer_material_num = f"PID{pid_i}"
    
                note_parts = []
                if vehicle_no:
                    note_parts.append(f"vehicle:{vehicle_no}")
                if r.get("note"):
                    note_parts.append(str(r.get("note")))
                note_text = " | ".join(note_parts) if note_parts else None
    
                carton_used_val = None
                if r.get("carton_used") not in (None, ""):
                    try:
                        carton_used_val = float(r.get("carton_used"))
                    except Exception:
                        carton_used_val = None
                cur.execute(
                    sql_psl,
                    (
                        int(psioh_id),
                        int(line_no),
                        int(pid_i),
                        customer_material_num,
                        int(pid_i),  # production_num (NOT NULL) - use product_id as fallback
                        customer_order_item_id,
                        schedule_id,
                        note_text,
                        None,  # operator
                        int(created_by),
                        _yyyymm(),
                        None,  # reversed_io_id
                        float(qty_f),
                        carton_used_val,
                    ),
                )
                inserted_stock_lines += 1
                line_no += 1
    
            if inserted_lines == 0:
                conn.rollback()
                return False, "沒有任何有效的出貨明細（product/qty）"

            # 純樣品出貨尚未對應 P01 產品，不應留下沒有明細的庫存 OUT 抬頭。
            if inserted_stock_lines == 0:
                cur.execute("DELETE FROM product_stock_io_head WHERE psioh_id = %s", (int(psioh_id),))

            # Refresh once after every delivery line has been written.  The
            # product-stock trigger also refreshes while inserting OUT lines,
            # but this final call guarantees that both order-head and schedule
            # statuses reflect the complete delivery in the same transaction.
            if customer_order_id:
                _refresh_customer_order_status_after_delivery_change(
                    cur, [int(customer_order_id)]
                )

            conn.commit()
            stock_message = "product_stock_io_head/line 已寫入 OUT" if inserted_stock_lines else "樣品未對應產品，未建立庫存 OUT"
            return True, f"儲存完成：{delivery_code}（{inserted_lines} 筆明細；{stock_message}）"
    
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
    
    
    # =============================================================================
    # UI
    # =============================================================================
    
    st.set_page_config(page_title=_t("D02 新建送貨單"), layout="wide")
    auth.require_read(PAGE_KEY)
    st.title(_t("D02 新建送貨單"))
    
    # ---------------------------
    # Load master data
    # ---------------------------
    
    customers_df = fetch_customers()
    if customers_df.empty:
        st.warning(_t("找不到客戶資料（customer）或 DB 連線失敗。"))
        st.stop()
    
    customer_options: List[str] = []
    customer_map: Dict[str, int] = {}
    customer_shortname_by_id: Dict[int, str] = {}
    for _, r in customers_df.iterrows():
        label = f"{r['customer_name']} | {r['customer_code']} | ID:{int(r['customer_id'])}"
        customer_options.append(label)
        customer_map[label] = int(r["customer_id"])
        customer_shortname_by_id[int(r["customer_id"])] = str(r.get("customer_shortname") or "").strip()
    
    
    # 反向 mapping：customer_id -> selectbox label
    customer_id_to_label: Dict[int, str] = {v: k for k, v in customer_map.items()}
    
    
    # ---------------------------
    # Session state
    # ---------------------------
    
    if "d02_lines" not in st.session_state:
        st.session_state.d02_lines = []  # type: ignore
    
    if "d02_selected_customer" not in st.session_state:
        st.session_state.d02_selected_customer = customer_options[0]
    
    # ---------------------------
    # One-shot actions (must run before widgets are instantiated)
    # ---------------------------
    
    flash = st.session_state.get("d02_flash")
    if flash:
        st.success(str(flash))
        st.session_state.d02_flash = None

    over_warning_flash = st.session_state.get("d02_over_warning_flash")
    if over_warning_flash:
        st.warning(_t("送貨數量超過客戶訂單數量提醒（本次已允許儲存）："))
        for _msg in over_warning_flash:
            st.write(_msg)
        st.session_state.d02_over_warning_flash = None
    
    if st.session_state.get("d02_reset_line_form"):
        # Reset add/edit form inputs. Important: run BEFORE widgets using these keys are created.
        st.session_state.d02_qty = 0.0
        st.session_state.d02_carton_used = 0.0
        st.session_state.d02_carton_used_manual = False
        st.session_state.d02_note = ""
        # Keep product selection; spec unit keep current default if present
        st.session_state.d02_reset_line_form = False
    
    
    
    # 自動載入（輸入我方公司訂單號碼）相關 state
    if "d02_company_order_code" not in st.session_state:
        st.session_state.d02_company_order_code = ""  # type: ignore
    if "d02_autoload_order_id" not in st.session_state:
        st.session_state.d02_autoload_order_id = None  # type: ignore
    if "d02_autoload_customer_id" not in st.session_state:
        st.session_state.d02_autoload_customer_id = None  # type: ignore
    if "_d02_pending_customer_label" not in st.session_state:
        st.session_state._d02_pending_customer_label = None  # type: ignore
    if "_d02_pending_order_label" not in st.session_state:
        st.session_state._d02_pending_order_label = None  # type: ignore
    if "_d02_apply_autoload" not in st.session_state:
        st.session_state._d02_apply_autoload = False  # type: ignore
    if "d02_autoload_error" not in st.session_state:
        st.session_state.d02_autoload_error = ""  # type: ignore
    
    # 若上一次 callback 設定了 pending，這裡要在 widget 建立前套用，避免 StreamlitAPIException
    if st.session_state.get("_d02_apply_autoload"):
        pend_cust = st.session_state.get("_d02_pending_customer_label")
        pend_order = st.session_state.get("_d02_pending_order_label")
        if pend_cust:
            st.session_state["d02_selected_customer"] = pend_cust
        if pend_order:
            st.session_state["d02_selected_order"] = pend_order
        st.session_state["_d02_apply_autoload"] = False
        st.session_state["_d02_pending_customer_label"] = None
        st.session_state["_d02_pending_order_label"] = None
    
    def _clear_autoload():
        st.session_state.d02_autoload_order_id = None  # type: ignore
        st.session_state.d02_autoload_customer_id = None  # type: ignore
        st.session_state.d02_autoload_error = ""  # type: ignore
    
    

    # ------------------------------------------------------------
    # After-save reset handling (avoid modifying widget-bound state
    # after widgets are instantiated in the same run)
    # ------------------------------------------------------------
    if st.session_state.get("d02_after_save_refresh"):
        # The next code depends on the next selected customer.
        st.session_state.pop("d02_delivery_code", None)

        # 2) Clear header fields (except delivery_date)
        st.session_state["d02_company_order_code"] = ""
        st.session_state["d02_selected_customer"] = ""  # 預設空白
        st.session_state["d02_selected_order"] = ""
        st.session_state["d02_deliver_to"] = None
        st.session_state["d02_vehicle_no"] = ""
        st.session_state["d02_status"] = "draft"

        # 3) Clear detail lines and edit state
        st.session_state.d02_lines = []
        st.session_state.d02_edit_idx = None
        st.session_state.d02_carton_used_manual = False

        # 4) Reset flag
        st.session_state["d02_after_save_refresh"] = False
    def _on_customer_change():
        # 使用者手動改客戶時，清掉「我方公司訂單號碼」自動載入狀態，避免客戶/訂單不一致
        st.session_state.d02_company_order_code = ""  # type: ignore
        st.session_state.pop("d02_delivery_code", None)
        _clear_autoload()
    
    def _on_company_order_code_change():
        code = (st.session_state.get("d02_company_order_code") or "").strip()
        if not code:
            _clear_autoload()
            return
    
        odf = fetch_customer_order_by_code(code)
        if odf.empty:
            st.session_state.d02_autoload_error = f"找不到訂單：{code}"  # type: ignore
            _clear_autoload()
            return
    
        row = odf.iloc[0]
        coid = int(row["customer_order_id"])
        cid = int(row["customer_id"])
    
        cust_label = customer_id_to_label.get(cid)
        if not cust_label:
            st.session_state.d02_autoload_error = f"訂單已找到，但找不到對應客戶（customer_id={cid}）"  # type: ignore
            _clear_autoload()
            return
    
        # 取得該客戶可送貨訂單清單，找出對應 label（需與下拉選單 label 格式一致）
        orders_df = fetch_customer_orders_for_delivery(cid)
        order_label = None
        if not orders_df.empty:
            for _, r in orders_df.iterrows():
                if int(r["customer_order_id"]) != coid:
                    continue
                order_no = (r.get("customer_order_num") or "").strip()
                order_code = (r.get("customer_order_code") or "").strip()
                deliver_date = r.get("deliver_date")
                deliver_date_str = str(deliver_date) if pd.notna(deliver_date) else ""
                status = (r.get("order_status") or "").strip()
                category = str(r.get("customer_order_category") or CUSTOMER_ORDER_CATEGORY_GENERAL).strip()
                category_text = customer_order_category_label(category)
                ordered_qty = float(r.get("ordered_qty") or 0)
                remaining_qty = float(r.get("remaining_qty") or 0)
                if ordered_qty <= 0:
                    qty_text = "無明細"
                else:
                    qty_text = f"remaining {remaining_qty:g}"
                order_label = f"{order_no or '(no num)'} | {order_code} | {category_text} | {deliver_date_str} | {status} | {qty_text} | ID:{coid}"
                break
    
        # 套用 pending（下一輪 rerun 在 widget 建立前套用）
        st.session_state["_d02_pending_customer_label"] = cust_label
        if order_label:
            st.session_state["_d02_pending_order_label"] = order_label
        st.session_state["_d02_apply_autoload"] = True
    
        # 記住自動載入訂單，後續「品項下拉」可改為訂單品項
        st.session_state.d02_autoload_order_id = coid  # type: ignore
        st.session_state.d02_autoload_customer_id = cid  # type: ignore
        st.session_state.d02_autoload_error = ""  # type: ignore
        st.rerun()
    
    
    # ---------------------------
    # Header section
    # ---------------------------
    
    st.subheader(_t("送貨單抬頭"))

    # ✅ 送貨日期（預設今天，可修改；儲存時寫回 delivery_head.delivery_date）
    # 需求：送貨日期的格子不要滿版，寬度對齊「送貨單號」那一欄（維持現有排列）。
    if "d02_delivery_date" not in st.session_state:
        st.session_state["d02_delivery_date"] = date.today()

    _dcols = st.columns([1.2, 2.6, 2.2, 1.2])
    with _dcols[0]:
        st.date_input(_t("送貨日期"), key="d02_delivery_date")
    # 其他欄位保持空白，只用來對齊
    with _dcols[1]:
        st.caption("")
    with _dcols[2]:
        st.caption("")
    with _dcols[3]:
        st.caption("")

    
    h1, h2, h3, h4 = st.columns([2.6, 1.2, 2.2, 1.2])
    
    with h1:
        st.text_input(
            _t("我方公司訂單號碼（輸入後自動帶入客戶與品項，可空）"),
            key="d02_company_order_code",
            on_change=_on_company_order_code_change,
            placeholder=_t("例：CO260125011 或你系統內的訂單號碼"),
        )
    
        customer_label = st.selectbox(
            _t("要送貨的客戶（必填）"),
            options=([""] + customer_options),
            key="d02_selected_customer",
            on_change=_on_customer_change,
        )
    
    customer_id = customer_map.get(customer_label) if customer_label else None
    if not customer_id:
        st.info(_t("請先選擇要送貨的客戶"))
        return
    customer_shortname = customer_shortname_by_id.get(int(customer_id), "")
    if not customer_shortname:
        st.error(_t("此客戶尚未設定客戶簡稱，無法產生送貨單號。"))
        return
    
    with h2:
        delivery_code_ui = st.text_input(
            _t("送貨單號"),
            value=(st.session_state.get("d02_delivery_code") or suggest_delivery_code_de(customer_shortname)),
            key="d02_delivery_code",
            help="規則：DE-客戶簡稱-年月(YYMM)三碼流水號。例如：DE-YI-2609001",
        )
        vehicle_no = st.text_input(_t("車號（可空）"), value="", placeholder=_t("例：51C-123.45"), key="d02_vehicle_no")
    
    with h3:
        source_type = st.selectbox(
            _d02_t("來源模組"),
            options=["customer_order", "sample_order"],
            format_func=lambda x: _d02_t("E01 客戶訂單") if x == "customer_order" else _d02_t("SP01 樣品單"),
            key="d02_source_type",
        )
        orders_df = fetch_customer_orders_for_delivery(int(customer_id)) if source_type == "customer_order" else fetch_sample_orders_for_delivery(int(customer_id))
        order_options: List[str] = [""]
        order_map: Dict[str, Dict[str, Any]] = {
            "（）": {
                "customer_order_id": None,
                "customer_order_no": None,
            }
        }
    
        if source_type == "sample_order" and not orders_df.empty:
            for _, r in orders_df.iterrows():
                sample_id = int(r["sample_order_id"])
                sample_code = str(r.get("sample_order_code") or "").strip()
                sample_category = str(r.get("sample_category") or "receivable").strip()
                category_text = _d02_t("樣品單（要收款）") if sample_category == "receivable" else _d02_t("樣品單（不收款）")
                target = str(r.get("target_completion_date") or "")
                label = f"{sample_code} | {category_text} | {target} | ID:{sample_id}"
                order_options.append(label)
                order_map[label] = {
                    "customer_order_id": None,
                    "sample_order_id": sample_id,
                    "customer_order_no": sample_code or None,
                    "sample_category": sample_category,
                }
        elif not orders_df.empty:
            for _, r in orders_df.iterrows():
                coid = int(r["customer_order_id"])
                order_no = (r.get("customer_order_num") or "").strip()
                order_code = (r.get("customer_order_code") or "").strip()
                deliver_date = r.get("deliver_date")
                deliver_date_str = str(deliver_date) if pd.notna(deliver_date) else ""
                status = (r.get("order_status") or "").strip()
                category = str(r.get("customer_order_category") or CUSTOMER_ORDER_CATEGORY_GENERAL).strip()
                category_text = customer_order_category_label(category)
                ordered_qty = float(r.get("ordered_qty") or 0)
                delivered_qty = float(r.get("delivered_qty") or 0)
                remaining_qty = float(r.get("remaining_qty") or 0)
    
                # 顯示策略：如果沒有明細，直接標註；有明細則顯示 remaining
                if ordered_qty <= 0:
                    qty_text = "無明細"
                else:
                    qty_text = f"remaining {remaining_qty:g}"
    
                label = f"{order_no or '(no num)'} | {order_code} | {category_text} | {deliver_date_str} | {status} | {qty_text} | ID:{coid}"
    
                order_options.append(label)
                order_map[label] = {
                    "customer_order_id": coid,
                    "customer_order_no": (order_no or order_code or None),
                    "customer_order_category": category,
                }
    
        selected_order_label = st.selectbox(
            _d02_t("選擇來源單據"),
            options=order_options,
            index=0,
            help=_d02_t("選擇客戶訂單或樣品單；樣品不必先建立正式產品。"),
            key="d02_selected_order",
        )
    
    selected_order = order_map.get(selected_order_label, {"customer_order_id": None, "sample_order_id": None, "customer_order_no": None, "customer_order_category": CUSTOMER_ORDER_CATEGORY_GENERAL})
    customer_order_id = selected_order.get("customer_order_id")
    sample_order_id = selected_order.get("sample_order_id")
    customer_order_no = selected_order.get("customer_order_no")
    customer_order_category = str(selected_order.get("customer_order_category") or CUSTOMER_ORDER_CATEGORY_GENERAL)
    source_module_text = _d02_t("E01 客戶訂單") if source_type == "customer_order" else _d02_t("SP01 樣品單")
    document_category_text = _d02_t("尚未選擇單據")
    ar_rule_text = _d02_t("尚未選擇單據")
    is_non_receivable = False
    if customer_order_id:
        document_category_text = customer_order_category_label(customer_order_category)
        is_non_receivable = customer_order_category == CUSTOMER_ORDER_CATEGORY_MATERIAL_REPLENISHMENT_NON_RECEIVABLE
        ar_rule_text = _d02_t("不建立應收帳款") if is_non_receivable else _d02_t("建立應收帳款")
    elif sample_order_id:
        sample_category = str(selected_order.get("sample_category") or "receivable")
        is_non_receivable = sample_category == "non_receivable"
        document_category_text = _d02_t("樣品單（不收款）") if is_non_receivable else _d02_t("樣品單（要收款）")
        ar_rule_text = _d02_t("不建立應收帳款") if is_non_receivable else _d02_t("建立應收帳款")
    
    with h4:
        status = st.selectbox(_t("狀態"), options=["draft", "posted"], index=0, key="d02_status")
        st.caption(f"{_d02_t('來源模組')}：{source_module_text}")
        st.caption(f"{_d02_t('單據類別')}：{document_category_text}")
        st.caption(f"{_d02_t('應收規則')}：{ar_rule_text}")
        if is_non_receivable:
            st.warning(_d02_t("本次送貨不會建立應收帳款（補料單不收款）。") if customer_order_id else _d02_t("本次送貨不會建立應收帳款（樣品不收款）。"))
    
    
    # 送貨地址（下拉）
    addr_df = fetch_receiving_addresses(int(customer_id))
    addr_df = addr_df if addr_df is not None else pd.DataFrame()
    
    addr_ids: List[int] = []
    addr_label: Dict[int, str] = {}
    
    if not addr_df.empty:
        for _, r in addr_df.iterrows():
            rid = r.get("receiving_id")
            if pd.isna(rid):
                continue
            rid_int = int(rid)
            add = (r.get("receiving_add") or "").strip()
            person = (r.get("warehouse_contact_person") or "").strip()
            tel = (r.get("tel") or "").strip()
            extra = " / ".join([x for x in [person, tel] if x])
            label = add if not extra else f"{add} ({extra})"
            addr_ids.append(rid_int)
            addr_label[rid_int] = label
    
    # 依訂單抬頭 deliver_to 當預設值（若可取得）
    default_deliver_to = None
    if customer_order_id:
        default_deliver_to = fetch_customer_order_deliver_to(int(customer_order_id))
    
    if addr_ids:
        if default_deliver_to not in addr_ids:
            default_deliver_to = addr_ids[0]
    
        # 若 session_state 已有值，優先使用（避免每次 rerun 都被 default 覆蓋）
        current_deliver_to = st.session_state.get("d02_deliver_to")
        if current_deliver_to is None:
            current_deliver_to = default_deliver_to
    
        a1, a2 = st.columns([3.0, 1.0])
        with a1:
            st.selectbox(
                _t("送貨地址（必填）"),
                options=addr_ids,
                index=addr_ids.index(int(current_deliver_to)) if int(current_deliver_to) in addr_ids else 0,
                format_func=lambda x: addr_label.get(int(x), str(x)),
                key="d02_deliver_to",
                help=_t("資料來源：customer_receiving_add（與 E01 相同）。若未來 delivery_head 新增 deliver_to 欄位，會一併寫入。"),
            )
        with a2:
            st.caption("")
    else:
        st.session_state["d02_deliver_to"] = None
        st.warning(_t("此客戶沒有收貨地址（customer_receiving_add）。請先建立收貨地址，否則送貨地址無法選取。"))
    
    
    current_user_id = _current_login_user_id()
    current_user_profile = fetch_login_user_profile(current_user_id)
    created_by = int(current_user_profile.get("user_id") or current_user_id)
    created_by_display = str(current_user_profile.get("display_name") or st.session_state.get("username") or f"User {created_by}")

    c1, c2 = st.columns([1.2, 3.8])
    with c1:
        st.text_input(
            _d02_t("建立人員"),
            value=f"{created_by_display}  |  ID:{created_by}",
            disabled=True,
            key=f"d02_created_by_display_{created_by}",
            help=_d02_t("系統會依目前登入者自動寫入 created_by，不可手動修改。"),
        )
    with c2:
        st.caption(_d02_t("建立人員會自動使用目前登入帳號；資料庫仍寫入 user_id。"))
    
    st.divider()
    
    # ---------------------------
    # Detail list section (view/edit/delete)  -- 顯示在抬頭下方
    # ---------------------------
    
    st.subheader(_t("已加入的明細"))
    
    lines: List[Dict[str, Any]] = st.session_state.d02_lines
    if not lines:
        st.info(_t("目前尚無明細。請在下方新增/編輯區加入產品。"))
    else:
        view_df = pd.DataFrame(lines)
        view_df.insert(0, "line_no", range(1, len(view_df) + 1))
    
        # 用可勾選的方式選取要操作的行（左側 Checkbox）
        # UI hides price fields, but keeps them in st.session_state.d02_lines
        # so they are still saved into delivery_product.product_unit_price / line_amount.
        display_cols = [
            "line_no",
            "product_code",
            "product_name",
            "customer_product_id",
            "qty",
            "carton_used",
            "specification",
            "specification_unit",
            "color",
            "note",
        ]
    
        # Keep internal keys in English for logic, but translate visible headers for users.
        pick_view_df = view_df[display_cols].copy()
        pick_view_df.insert(0, "_選取", False)
        pick_view_df_i18n, pick_reverse_map = _translate_d02_columns(pick_view_df, D02_LINE_COLUMN_LABELS)
        pick_select_col = _d02_t("選取")
    
        pick_ver = st.session_state.get("d02_lines_pick_ver", 0)
    
        pick_key = f"d02_lines_pick_df_{pick_ver}_{_d02_lang()}"

    
        edited_pick_df_i18n = st.data_editor(
            pick_view_df_i18n,
            use_container_width=True,
            hide_index=True,
            key=pick_key,
            disabled=[c for c in pick_view_df_i18n.columns if c != pick_select_col],
            column_config={
                pick_select_col: st.column_config.CheckboxColumn(
                    pick_select_col,
                    help=_t("勾選要操作的行（可多選刪除；若要編輯請只勾選一行）"),
                )
            },
        )
        edited_pick_df = _restore_d02_columns(edited_pick_df_i18n, pick_reverse_map)
    
        selected_rows = (
            edited_pick_df.index[edited_pick_df["_選取"] == True].tolist()
            if (not edited_pick_df.empty and "_選取" in edited_pick_df.columns)
            else []
        )
    
        op1, op2, op3 = st.columns([1.2, 1.2, 3.6])
        with op1:
            load_clicked = st.button(_t("載入到編輯"), use_container_width=True)
        with op2:
            del_clicked = st.button(_t("刪除勾選行"), use_container_width=True)
        with op3:
            st.caption(_t("提示：編輯 = 請只勾選 1 行；刪除 = 可勾選多行。"))
        def _reset_picker(lines_now: List[Dict[str, Any]]) -> None:
            """重置 data_editor 勾選狀態。

            Streamlit 不允許在 widget (data_editor) instantiate 後直接改寫同 key 的 session_state。
            這裡改用「版本號換 key」的方式重置：把 d02_lines_pick_ver +1，讓 data_editor 使用新的 key。
            """
            st.session_state["d02_lines_pick_ver"] = st.session_state.get("d02_lines_pick_ver", 0) + 1
            st.rerun()

        if del_clicked:

            if not selected_rows:
                st.error(_t("請先勾選要刪除的行。"))
            else:
                removed_idxs = sorted([int(i) for i in selected_rows if 0 <= int(i) < len(lines)], reverse=True)
                removed_items = []
                for idx in removed_idxs:
                    removed_items.append(lines.pop(idx))
    
                # 若正在編輯的行受到影響：同步修正 edit_idx
                edit_idx = st.session_state.get("d02_edit_idx")
                if edit_idx is not None:
                    try:
                        e = int(edit_idx)
                        if e in removed_idxs:
                            st.session_state.d02_edit_idx = None
                        else:
                            shift = sum(1 for i in removed_idxs if i < e)
                            st.session_state.d02_edit_idx = e - shift
                    except Exception:
                        st.session_state.d02_edit_idx = None
    
                st.session_state.d02_lines = lines
                _reset_picker(lines)
    
                st.success(f"已刪除 {len(removed_items)} 行明細。")
    
        if load_clicked:
            if len(selected_rows) != 1:
                st.error(_t("要載入編輯請『只勾選一行』。"))
            else:
                idx = int(selected_rows[0])
                if 0 <= idx < len(lines):
                    r = lines[idx]
                    st.session_state.d02_edit_idx = idx
    
                    # 將該行資料載入表單（下方新增/編輯區）
                    st.session_state.d02_edit_product_id = r.get("product_id")
                    st.session_state.d02_qty = float(r.get("qty") or 0)
                    st.session_state.d02_spec_unit = str(r.get("specification_unit") or "mm")
                    st.session_state.d02_note = str(r.get("note") or "")
    
                    # 使用紙箱：帶入原值，並視為手動（避免被自動值覆寫）
                    st.session_state.d02_carton_used = float(r.get("carton_used") or 0)
                    st.session_state.d02_carton_used_manual = True
    
                    _reset_picker(lines)
                    st.success(f"已載入第 {idx+1} 行到編輯區。")
    st.divider()
    
    # ---------------------------
    # Detail entry section (add/edit)  -- 三行輸入
    # ---------------------------
    
    st.subheader(_t("新增/編輯送貨明細"))
    
    
    autoload_order_id = st.session_state.get("d02_autoload_order_id")
    autoload_customer_id = st.session_state.get("d02_autoload_customer_id")
    
    # 若使用者輸入了「我方公司訂單號碼」且成功找到訂單，則優先以該訂單明細作為品項來源
    order_items_df = pd.DataFrame()
    if autoload_order_id and autoload_customer_id and int(autoload_customer_id) == int(customer_id):
        order_items_df = fetch_customer_order_items(int(autoload_order_id))
    elif sample_order_id:
        order_items_df = fetch_sample_order_items(int(sample_order_id))
    
    if not order_items_df.empty:
        products_df = order_items_df.copy()
    else:
        products_df = fetch_products_by_customer(int(customer_id))
    
    if products_df.empty:
        st.warning(_t("此客戶目前沒有可用的產品/訂單明細，無法新增明細。"))
        st.stop()
    
    # 建立產品下拉：依序呈現「產品 CODE、品名」（不顯示 PID、客戶料號）
    product_options: List[str] = []
    product_map: Dict[str, Dict[str, Any]] = {}
    product_id_to_label: Dict[int, str] = {}
    _label_count: Dict[str, int] = {}
    
    for _, r in products_df.iterrows():
        pid = None if pd.isna(r.get("product_id")) else int(r["product_id"])
        code = str(r.get("product_code") or "").strip()
        name = str(r.get("product_name") or "").strip()
        if "sample_order_item_id" in r.index:
            line_no = int(r.get("line_no") or 0)
            sample_qty = float(r.get("quantity") or 0)
            sample_item_id = int(r.get("sample_order_item_id") or 0)
            base_label = f"{line_no:02d} | {code or 'SAMPLE'} | {name} | {sample_qty:g}PCS | SAMPLE-ITEM:{sample_item_id}"
        elif "customer_order_item_id" in r.index:
            line_no = int(r.get("line_no") or 0)
            order_qty = float(r.get("quantity") or 0)
            coi_id = int(r.get("customer_order_item_id") or 0)
            base_label = f"{line_no:02d} | {code} | {name} | {order_qty:g}PCS | ITEM:{coi_id}"
        else:
            base_label = f"{code} | {name}" if code else name
    
        n = _label_count.get(base_label, 0) + 1
        _label_count[base_label] = n
        label = base_label if n == 1 else f"{base_label} ({n})"
    
        product_options.append(label)
        if pid is not None:
            product_id_to_label[pid] = label
        product_map[label] = {
            "product_id": pid,
            "product_code": code,
            "customer_product_id": (r.get("customer_product_id") or ""),
            "product_name": name,
            "specification": (r.get("specification") or ""),
            "specification_unit": (r.get("specification_unit") or "mm"),
            "color": (r.get("color") or ""),
            "qty_per_carton": (None if pd.isna(r.get("qty_per_carton")) else int(r.get("qty_per_carton"))),
            "product_unit_price": (0.0 if ("order_price_unit" not in r.index or pd.isna(r.get("order_price_unit"))) else float(r.get("order_price_unit"))),
            # 若品項來源是「訂單明細」，這些欄位可用於顯示/後續擴充（目前不強制使用）
            "customer_order_item_id": (int(r.get("customer_order_item_id")) if "customer_order_item_id" in r.index and pd.notna(r.get("customer_order_item_id")) else None),
            "order_line_no": (int(r.get("line_no")) if "line_no" in r.index and pd.notna(r.get("line_no")) else None),
            "order_qty": (float(r.get("quantity")) if "quantity" in r.index and pd.notna(r.get("quantity")) else None),
            "sample_order_item_id": (int(r.get("sample_order_item_id")) if "sample_order_item_id" in r.index and pd.notna(r.get("sample_order_item_id")) else None),
        }
    
    # 初始化表單狀態
    if "d02_edit_idx" not in st.session_state:
        st.session_state.d02_edit_idx = None
    if "d02_qty" not in st.session_state:
        st.session_state.d02_qty = 0.0
    if "d02_carton_used" not in st.session_state:
        st.session_state.d02_carton_used = 0.0
    if "d02_carton_used_manual" not in st.session_state:
        st.session_state.d02_carton_used_manual = False
    if "d02_spec_unit" not in st.session_state:
        st.session_state.d02_spec_unit = "mm"
    if "d02_note" not in st.session_state:
        st.session_state.d02_note = ""
    if "d02_product_pick" not in st.session_state:
        st.session_state.d02_product_pick = product_options[0]
    
    # 若剛才從明細載入編輯：把 product_id 對應回 label
    edit_pid = st.session_state.get("d02_edit_product_id")
    if edit_pid:
        label = product_id_to_label.get(int(edit_pid))
        if label:
            st.session_state.d02_product_pick = label
        # 用完就清掉，避免後續客戶切換造成錯亂
        st.session_state.d02_edit_product_id = None
    
    # 第 1 行：產品、客戶料號、數量、使用紙箱
    r1c1, r1c2, r1c3, r1c4 = st.columns([3.2, 1.6, 1.2, 1.2])
    
    with r1c1:
        selected_product_label = st.selectbox(
            _t("產品（CODE | 品名）"),
            options=product_options,
            key="d02_product_pick",
        )
    
    prod = product_map.get(selected_product_label, {})
    
    with r1c2:
        st.text_input(_t("客戶料號"), value=str(prod.get("customer_product_id", "")), disabled=True)
    
    
    def _on_qty_change():
        # qty 變動時，先恢復自動計算（使用者仍可再手動改）
        st.session_state.d02_carton_used_manual = False
    
    
    def _on_carton_change():
        st.session_state.d02_carton_used_manual = True
    
    
    with r1c3:
        qty = st.number_input(
            _t("數量（PCS）"),
            min_value=0.0,
            step=1.0,
            format="%.0f",
            key="d02_qty",
            on_change=_on_qty_change,
        )
    
    # 自動計算 carton_used = ceil(qty / qty_per_carton)
    qty_per_carton = prod.get("qty_per_carton")
    suggested_carton = 0.0
    if qty_per_carton and float(qty) > 0:
        try:
            suggested_carton = float(math.ceil(float(qty) / float(qty_per_carton)))
        except Exception:
            suggested_carton = 0.0
    
    # 若產品切換，也恢復自動計算（避免上一個產品的手動值卡住）
    last_pid = st.session_state.get("d02_last_pid")
    current_pid = prod.get("product_id")
    if current_pid != last_pid:
        st.session_state.d02_carton_used_manual = False
        st.session_state.d02_last_pid = current_pid
    
    if not st.session_state.d02_carton_used_manual:
        st.session_state.d02_carton_used = suggested_carton
    
    with r1c4:
        carton_used = st.number_input(
            _t("使用紙箱（自動可改）"),
            min_value=0.0,
            step=1.0,
            format="%.0f",
            key="d02_carton_used",
            on_change=_on_carton_change,
            help=_t("預設依 qty / qty_per_carton 取上整（有餘數自動 +1）。你仍可手動修改。"),
        )
    
    # 第 2 行：規格、備註
    # 單價 / 金額不顯示在 UI，但仍在背景計算，加入明細後保存在 d02_lines，
    # 儲存時照常寫入 delivery_product.product_unit_price / line_amount。
    unit_price_preview = float(prod.get("product_unit_price") or 0.0)
    line_amount_preview = float(unit_price_preview) * float(qty or 0.0)

    r2c1, r2c2, r2c3, r2c4 = st.columns([1.7, 0.75, 0.9, 3.2])

    with r2c1:
        st.text_input(_t("規格"), value=str(prod.get("specification", "")), disabled=True)

    with r2c2:
        spec_unit = st.selectbox(
            _t("規格單位"),
            options=["mm", "cm"],
            index=0 if str(st.session_state.d02_spec_unit) == "mm" else 1,
            key="d02_spec_unit",
        )

    with r2c3:
        st.text_input(_t("顏色"), value=str(prod.get("color", "")), disabled=True)

    with r2c4:
        line_note = st.text_input(_t("備註（可空）"), value=str(st.session_state.d02_note), key="d02_note")

    # 第 3 行：按鈕
    is_edit_mode = st.session_state.get("d02_edit_idx") is not None
    b1, b2, b3, b4 = st.columns([1.2, 1.2, 1.2, 3.4])
    
    with b1:
        add_or_update_clicked = st.button(_t("更新明細") if is_edit_mode else _t("加入明細"), use_container_width=True)
    with b2:
        cancel_edit_clicked = st.button(_t("取消編輯"), use_container_width=True, disabled=not is_edit_mode)
    with b3:
        clear_clicked = st.button(_t("清空全部明細"), use_container_width=True)
    with b4:
        if is_edit_mode:
            st.caption(_t("你目前在編輯模式：按『更新明細』會覆寫該行；或按『取消編輯』回到新增模式。"))
        else:
            st.caption(_t("提示：先完成新增/編輯；上方明細區可用下拉選擇要刪除或載入編輯。"))
    
    if cancel_edit_clicked:
        st.session_state.d02_edit_idx = None
        st.session_state.d02_carton_used_manual = False
        st.success(_t("已取消編輯模式。"))
    
    if clear_clicked:
        st.session_state.d02_lines = []
        st.session_state.d02_edit_idx = None
        st.session_state.d02_carton_used_manual = False
        st.success(_t("已清空全部明細。"))
    
    if add_or_update_clicked:
        if qty <= 0:
            st.error(_t("數量（PCS）必須大於 0"))
        elif not prod:
            st.error(_t("請先選擇產品"))
        else:
            row = {
                "product_id": prod.get("product_id"),
                "product_code": prod.get("product_code"),
                "customer_product_id": prod.get("customer_product_id"),
                "product_name": prod.get("product_name"),
                "customer_order_item_id": prod.get("customer_order_item_id"),
                "order_line_no": prod.get("order_line_no"),
                "order_qty": prod.get("order_qty"),
                "sample_order_item_id": prod.get("sample_order_item_id"),
                "qty": float(qty),
                "product_unit_price": float(unit_price_preview),
                "line_amount": float(line_amount_preview),
                "specification": prod.get("specification"),
                "specification_unit": spec_unit,
                "color": prod.get("color"),
                "qty_per_carton": prod.get("qty_per_carton"),
                "carton_used": (float(carton_used) if float(carton_used) > 0 else None),
                "note": line_note.strip() or None,
            }
    
            edit_idx = st.session_state.get("d02_edit_idx")
            msg = "已加入明細。"
            if edit_idx is not None and 0 <= int(edit_idx) < len(st.session_state.d02_lines):
                st.session_state.d02_lines[int(edit_idx)] = row
                st.session_state.d02_edit_idx = None
                msg = "已更新明細。"
            else:
                st.session_state.d02_lines.append(row)
    
            # 清理表單（保留產品選擇；qty 回到 0）
            # 注意：不能在 widget 產生後直接改同 key 的 session_state，改用 rerun 於下一輪先重置。
            st.session_state.d02_flash = msg
            st.session_state.d02_reset_line_form = True
            st.rerun()
    
    st.divider()
    
    # ---------------------------
    # Save
    # ---------------------------
    
    s1, s2 = st.columns([1.2, 3.8])
    with s1:
        save_clicked = st.button(_t("儲存送貨單"), use_container_width=True)
    with s2:
        st.caption(_t("儲存時會同步寫入 product_stock_io_head / product_stock_io_line（io_type='OUT'）。"))
    
    if save_clicked:
        # 基本檢核
        if not customer_id:
            st.error(_t("請先選擇客戶"))
        elif not st.session_state.d02_lines:
            st.error(_t("請先新增至少一筆明細"))
        else:
            auth.require_edit(PAGE_KEY)

            warning_lines = build_delivery_over_warning_lines(
                int(customer_order_id) if customer_order_id else None,
                st.session_state.d02_lines,
            )
            if warning_lines:
                st.session_state["d02_over_warning_flash"] = warning_lines
                st.warning(_t("送貨數量超過客戶訂單數量提醒（本次仍允許儲存）："))
                for _msg in warning_lines:
                    st.write(_msg)

            ok, msg = insert_delivery_and_stock_out(
                delivery_code=None,
                customer_id=int(customer_id),
                delivery_date=st.session_state.get('d02_delivery_date'),
                customer_order_id=(int(customer_order_id) if customer_order_id else None),
                sample_order_id=(int(sample_order_id) if sample_order_id else None),
                customer_order_no=(str(customer_order_no).strip() if customer_order_no else None),
                vehicle_no=vehicle_no.strip() or None,
                deliver_to=(int(st.session_state.get('d02_deliver_to')) if st.session_state.get('d02_deliver_to') else None),
                status=status,
                created_by=int(created_by),
                lines=st.session_state.d02_lines,
            )
            if ok:
                st.success(msg)

                # 保留：送貨單號、送貨日期（其餘輸入區清空）
                # 注意：不可在 widget (key=...) 已經 instantiate 後直接改 st.session_state[key]
                # 這裡改用旗標 + rerun，讓下一次 rerun 在「建立 widget 前」完成清空與重算 delivery_code
                st.session_state["d02_after_save_refresh"] = True

                # 讓上方訂單 remaining 與 D02 母表重新計算，避免 data_editor / cache 吃到舊狀態
                fetch_customer_orders_for_delivery.clear()
                _refresh_d01_master_state()

                st.rerun()

            else:
                st.error(msg)


# ---------------------------
# Page entry
# ---------------------------
if __name__ == '__main__':
    # Streamlit runs top-level; keep for linting only
    pass


def main():
    selected_ids = render_d01_master_and_detail()
    if selected_ids:
        st.info(_t("已勾選主表資料：下方『新建送貨單』已自動隱藏。取消勾選後會自動顯示。"))
        return
    st.divider()
    st.subheader(_t("新建送貨單（D02）"))
    render_delivery_entry_d02()

if __name__ == "__main__":
    main()
