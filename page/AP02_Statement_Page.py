import base64
import calendar
import html
import math
import tempfile
import threading
import http.server
import socketserver
from compact_layout import apply_compact_layout

apply_compact_layout()
import socket
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import auth
from sqlalchemy import text

try:
    from db import get_engine
except ImportError as e:
    raise ImportError(
        "找不到 db.py。請把這支檔案放到你的專案頁面目錄下，並確認基礎連線檔名稱為 db.py。"
    ) from e


# =========================
# Safe I18N helper
# =========================
TRANSLATIONS = {
    "供應商對帳單": {"vi": "Bảng đối chiếu công nợ nhà cung cấp", "en": "Supplier Statement"},
    "起始日期": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "供應商": {"vi": "Nhà cung cấp", "en": "Supplier"},
    "供應商名稱": {"vi": "Tên nhà cung cấp", "en": "Supplier Name"},
    "勾選所有": {"vi": "Chọn tất cả", "en": "Select All"},
    "取消勾選": {"vi": "Bỏ chọn tất cả", "en": "Clear Selection"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "列印勾選項目": {"vi": "In các mục đã chọn", "en": "Print Selected Items"},
    "供應商清單會依目前日期區間抓有應付資料者。": {
        "vi": "Danh sách nhà cung cấp sẽ lọc theo khoảng ngày hiện tại và chỉ hiển thị những nhà cung cấp có dữ liệu công nợ phải trả.",
        "en": "The supplier list is filtered by the current date range and only shows suppliers with payable data."
    },
    "這段期間沒有符合條件的應付帳款資料。": {
        "vi": "Không có dữ liệu công nợ phải trả phù hợp trong khoảng thời gian này.",
        "en": "No payable data matches this period."
    },
    "勾選總計：": {"vi": "Tổng cộng đã chọn:", "en": "Selected Total:"},
    "列印內容為 A4 直式，會只列出目前勾選的明細與各入庫單小計。": {
        "vi": "Nội dung in sẽ ở khổ A4 dọc và chỉ in các dòng đã chọn cùng tổng phụ của từng phiếu nhập kho.",
        "en": "Printing uses A4 portrait and includes only selected lines and each receipt subtotal."
    },
    "你一筆都沒勾。列印機不是通靈板，沒資料不會自己生。": {
        "vi": "Bạn chưa chọn dòng nào. Máy in không tự tạo dữ liệu đâu.",
        "en": "You did not select any rows. The printer cannot invent data."
    },
    "目前資料庫裡沒有可用的應付帳款資料，這頁先沒東西可演。": {
        "vi": "Hiện cơ sở dữ liệu chưa có dữ liệu công nợ phải trả để hiển thị trên trang này.",
        "en": "There is no payable data available in the database for this page yet."
    },
    "勾選": {"vi": "Chọn", "en": "Select"},
    "入庫單號": {"vi": "Số phiếu nhập kho", "en": "Receiving No."},
    "訂單號碼": {"vi": "Số đơn hàng", "en": "Order No."},
    "供應商送貨單號": {"vi": "Số phiếu giao hàng NCC", "en": "Supplier Delivery No."},
    "原料編號": {"vi": "Mã nguyên liệu", "en": "Material Code"},
    "原料名稱": {"vi": "Tên nguyên liệu", "en": "Material Name"},
    "單價": {"vi": "Đơn giá", "en": "Unit Price"},
    "單位": {"vi": "Đơn vị", "en": "Unit"},
    "數量": {"vi": "Số lượng", "en": "Quantity"},
    "未稅總計": {"vi": "Tổng chưa thuế", "en": "Untaxed Total"},
    "稅率": {"vi": "Thuế suất", "en": "Tax Rate"},
    "已稅金額": {"vi": "Số tiền đã gồm thuế", "en": "Tax Included Amount"},
    "調整金額": {"vi": "Số tiền điều chỉnh", "en": "Adjustment"},
    "調整後未稅總計": {"vi": "Tổng chưa thuế sau điều chỉnh", "en": "Adjusted Untaxed Total"},
    "明細未稅小計": {"vi": "Tạm tính chưa thuế", "en": "Line Untaxed Subtotal"},
    "已開啟列印預覽：": {"vi": "Đã mở bản xem trước khi in: ", "en": "Print preview opened: "},
    "起始日期不能大於結束日期。這不是哲學問題，是 where 條件會直接死給你看。": {
        "vi": "Ngày bắt đầu không được lớn hơn ngày kết thúc.",
        "en": "Start Date cannot be later than End Date."
    },
}

def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    return lang if lang in {"zh", "vi", "en"} else "zh"

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)


PAGE_KEY = "AP02_Statement_Page"
auth.require_read(PAGE_KEY)

# =========================
# LAN HTML print server
# =========================
PRINT_PORT = 8767
_PRINT_SERVER = {"thread": None, "dir": None, "port": PRINT_PORT}


def _get_lan_ip() -> str:
    """Best-effort LAN IP for links opened by other PCs on the same network."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        host = socket.gethostbyname(socket.gethostname())
        if host and not host.startswith("127."):
            return host
    except Exception:
        pass
    return "localhost"


def ensure_print_server() -> tuple[str, str]:
    """Start a small HTTP server for AP02 print HTML and return (base_url, dir_path)."""
    if _PRINT_SERVER["thread"] is not None and _PRINT_SERVER["dir"] is not None:
        return f"http://{_get_lan_ip()}:{PRINT_PORT}", str(_PRINT_SERVER["dir"])

    serve_dir = Path(tempfile.gettempdir()) / "ordolite_print_ap02"
    serve_dir.mkdir(parents=True, exist_ok=True)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)
        def log_message(self, format, *args):
            return
        def end_headers(self):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            super().end_headers()

    def _serve():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("0.0.0.0", PRINT_PORT), QuietHandler) as httpd:
                httpd.serve_forever()
        except OSError:
            # Port may already be serving from a previous Streamlit run. Keep UI usable.
            pass

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    _PRINT_SERVER["thread"] = t
    _PRINT_SERVER["dir"] = serve_dir
    return f"http://{_get_lan_ip()}:{PRINT_PORT}", str(serve_dir)


FONT_CANDIDATES = [
    Path(r"D:\Python_Plactice\OrdoLitePlay\NotoSansTC-VariableFont_wght.ttf"),
    Path(__file__).resolve().parent / "NotoSansTC-VariableFont_wght.ttf",
    Path.cwd() / "NotoSansTC-VariableFont_wght.ttf",
]


# =========================
# 基礎工具
# =========================
def vnd(x):
    if pd.isna(x) or x is None:
        return 0.0
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


def to_date(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return pd.to_datetime(value).date()


def end_of_month(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def prev_month_same_logic(d: date):
    if d.month == 1:
        return d.year - 1, 12
    return d.year, d.month - 1


def suggested_start_date(today: date, checkout_day: int | None) -> date:
    """
    依供應商 checkout_date 算預設起始日。
    規則照你的 Word：
    - 若 today.day <= checkout_day，起始日 = 上個月 checkout_day + 1
    - 若 today.day > checkout_day，起始日 = 本月 checkout_day + 1

    例：checkout_day = 25
    - 3/01~3/25 => 2/26
    - 3/26~3/31 => 3/26
    """
    if checkout_day is None or checkout_day <= 0 or checkout_day > 31:
        return today.replace(day=1)

    if today.day <= checkout_day:
        y, m = prev_month_same_logic(today)
    else:
        y, m = today.year, today.month

    last_day = calendar.monthrange(y, m)[1]
    effective_checkout_day = min(checkout_day, last_day)
    checkout_dt = date(y, m, effective_checkout_day)
    return checkout_dt + timedelta(days=1)


@st.cache_resource(show_spinner=False)
def get_db_engine():
    return get_engine()

def force_refresh_statement_data() -> None:
    """Release cached DB resources and clear AP02 cached table state."""
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

    try:
        st.session_state.pop(f"{PAGE_KEY}_signature", None)
        st.session_state.pop(f"{PAGE_KEY}_df", None)
    except Exception:
        pass

    st.session_state[f"{PAGE_KEY}_editor_seed"] = int(st.session_state.get(f"{PAGE_KEY}_editor_seed", 0)) + 1



@st.cache_data(ttl=60, show_spinner=False)
def load_supplier_master():
    engine = get_db_engine()
    sql = text(
        """
        SELECT
            s.supplier_id,
            s.supplier_name,
            s.supplier_shortname,
            s.checkout_date,
            COUNT(DISTINCT aph.ap_id) AS ap_count,
            MAX(COALESCE(aph.posting_date, aph.supplier_invoice_date, DATE(aph.created_at))) AS last_ap_date
        FROM supplier s
        JOIN accounts_payable_head aph
          ON aph.supplier_id = s.supplier_id
        WHERE COALESCE(aph.status, '') <> 'cancelled'
        GROUP BY
            s.supplier_id, s.supplier_name, s.supplier_shortname, s.checkout_date
        ORDER BY s.supplier_name
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def load_supplier_options_in_range(start_date: date, end_date: date):
    engine = get_db_engine()
    sql = text(
        """
        SELECT DISTINCT
            s.supplier_id,
            s.supplier_name,
            s.supplier_shortname,
            s.checkout_date
        FROM accounts_payable_head aph
        JOIN supplier s
          ON s.supplier_id = aph.supplier_id
        WHERE COALESCE(aph.status, '') <> 'cancelled'
          AND COALESCE(aph.posting_date, aph.supplier_invoice_date, DATE(aph.created_at))
              BETWEEN :start_date AND :end_date
        ORDER BY s.supplier_name
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={
            "start_date": start_date,
            "end_date": end_date,
        })
    return df


@st.cache_data(ttl=60, show_spinner=False)
def load_statement_source(supplier_id: int, start_date: date, end_date: date):
    engine = get_db_engine()
    sql = text(
        """
        SELECT
            aph.ap_id,
            aph.ap_code,
            aph.supplier_id,
            s.supplier_name,
            COALESCE(NULLIF(s.supplier_shortname, ''), s.supplier_name) AS supplier_display_name,
            aph.delivery_no,
            aph.order_no,
            aph.tax_rate,
            COALESCE(aph.adjustment_amount, 0) AS adjustment_amount,
            aph.note AS ap_note,
            COALESCE(aph.posting_date, aph.supplier_invoice_date, DATE(aph.created_at)) AS ap_effective_date,
            msioh.supplier_delivery_number,
            apr.ap_resuorce_id AS ap_resource_id,
            apr.material_id,
            COALESCE(m.item_code, '') AS material_code,
            apr.material_name,
            apr.price_unit,
            apr.purchase_unit,
            apr.qty,
            apr.line_amount,
            apr.note AS line_note
        FROM accounts_payable_head aph
        JOIN supplier s
          ON s.supplier_id = aph.supplier_id
        LEFT JOIN material_stock_io_head msioh
          ON msioh.doc_no = aph.delivery_no
        LEFT JOIN ap_resource apr
          ON apr.ap_id = aph.ap_id
        LEFT JOIN material m
          ON m.item_id = apr.material_id
        WHERE aph.supplier_id = :supplier_id
          AND COALESCE(aph.status, '') <> 'cancelled'
          AND COALESCE(aph.posting_date, aph.supplier_invoice_date, DATE(aph.created_at))
              BETWEEN :start_date AND :end_date
        ORDER BY
            ap_effective_date,
            aph.delivery_no,
            apr.ap_resuorce_id
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={
            "supplier_id": supplier_id,
            "start_date": start_date,
            "end_date": end_date,
        })
    return df


# =========================
# 資料整理
# =========================
def build_display_rows(src: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []

    if src.empty:
        return pd.DataFrame(columns=[
            "_row_key", "_row_type", "勾選", "入庫單號", "供應商名稱", "訂單號碼", "供應商送貨單號",
            "原料編號", "原料名稱", "單價", "單位", "數量", "未稅總計",
            "調整金額", "調整後未稅總計", "稅率", "已稅金額", "_ap_id", "_line_id"
        ])

    grouped = src.groupby(["ap_id", "delivery_no"], dropna=False, sort=False)

    for (ap_id, delivery_no), g in grouped:
        g = g.copy()
        tax_rate = g["tax_rate"].dropna().iloc[0] if not g["tax_rate"].dropna().empty else 0
        adjustment_amount = g["adjustment_amount"].dropna().iloc[0] if "adjustment_amount" in g.columns and not g["adjustment_amount"].dropna().empty else 0
        supplier_delivery_number = g["supplier_delivery_number"].dropna().iloc[0] if not g["supplier_delivery_number"].dropna().empty else ""
        supplier_display_name = g["supplier_display_name"].dropna().iloc[0] if "supplier_display_name" in g.columns and not g["supplier_display_name"].dropna().empty else ""
        order_no = g["order_no"].dropna().iloc[0] if not g["order_no"].dropna().empty else ""

        untaxed_sum = 0.0
        for _, r in g.iterrows():
            line_amount = vnd(r.get("line_amount"))
            untaxed_sum += line_amount
            line_note = r.get("line_note")
            ap_note = r.get("ap_note")
            note = line_note if pd.notna(line_note) and str(line_note).strip() else ap_note

            rows.append({
                "_row_key": f"I-{int(ap_id)}-{int(r['ap_resource_id']) if pd.notna(r['ap_resource_id']) else 0}",
                "_row_type": "item",
                "勾選": False,
                "入庫單號": delivery_no or "",
                "供應商名稱": supplier_display_name or "",
                "訂單號碼": order_no or "",
                "供應商送貨單號": supplier_delivery_number or "",
                "原料編號": r.get("material_code") or "",
                "原料名稱": r.get("material_name") or "",
                "單價": vnd(r.get("price_unit")),
                "單位": r.get("purchase_unit") or "",
                "數量": vnd(r.get("qty")),
                "未稅總計": line_amount,
                "調整金額": None,
                "調整後未稅總計": None,
                "稅率": None,
                "已稅金額": None,
                "_ap_id": int(ap_id),
                "_line_id": int(r["ap_resource_id"]) if pd.notna(r["ap_resource_id"]) else None,
            })

        adjustment = vnd(adjustment_amount)
        adjusted_untaxed = untaxed_sum + adjustment
        taxed_sum = round(adjusted_untaxed * (1 + (vnd(tax_rate) / 100)), 2)
        rows.append({
            "_row_key": f"S-{int(ap_id)}",
            "_row_type": "summary",
            "勾選": False,
            "入庫單號": "",
            "供應商名稱": "",
            "訂單號碼": "",
            "供應商送貨單號": "",
            "原料編號": "",
            "原料名稱": "",
            "單價": None,
            "單位": "",
            "數量": None,
            "未稅總計": untaxed_sum,
            "調整金額": adjustment,
            "調整後未稅總計": adjusted_untaxed,
            "稅率": vnd(tax_rate),
            "已稅金額": taxed_sum,
            "_ap_id": int(ap_id),
            "_line_id": None,
        })

    return pd.DataFrame(rows)


# =========================
# 列印 HTML
# =========================
def money_fmt(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        amount = Decimal(str(value))
    except Exception:
        amount = Decimal("0")
    q = amount.quantize(Decimal("0.01"))
    s = f"{q:,.2f}"
    return s[:-3] if s.endswith(".00") else s


def rate_fmt(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        return f"{int(float(value))}%"
    except Exception:
        return ""


def font_base64() -> str:
    for path in FONT_CANDIDATES:
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
    return ""


def build_print_html(selected_items: pd.DataFrame, supplier_name: str, start_date: date, end_date: date) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if selected_items.empty:
        raise ValueError("請至少勾選一筆入庫單後再列印。")

    font64 = font_base64()
    font_css = ""
    if font64:
        font_css = f"""
        @font-face {{
            font-family: 'NotoSansTCEmbedded';
            src: url(data:font/ttf;base64,{font64}) format('truetype');
        }}
        body, table, th, td {{
            font-family: 'NotoSansTCEmbedded', 'Microsoft JhengHei', sans-serif;
        }}
        """

    grouped_sections = []
    grand_untaxed = Decimal("0")
    grand_adjusted_untaxed = Decimal("0")
    grand_taxed = Decimal("0")

    for delivery_no, g in selected_items.groupby("入庫單號", sort=False):
        g = g.copy().reset_index(drop=True)
        tax_rate_series = g["_tax_rate_for_print"].dropna()
        tax_rate = float(tax_rate_series.iloc[0]) if not tax_rate_series.empty else 0.0
        adj_series = g["_adjustment_for_print"].dropna() if "_adjustment_for_print" in g.columns else pd.Series(dtype=float)
        adjustment_amount = Decimal(str(float(adj_series.iloc[0]))) if not adj_series.empty else Decimal("0")
        supplier_delivery_number = g["供應商送貨單號"].dropna().iloc[0] if not g["供應商送貨單號"].dropna().empty else ""
        order_no = g["訂單號碼"].dropna().iloc[0] if not g["訂單號碼"].dropna().empty else ""

        g["未稅總計"] = pd.to_numeric(g["未稅總計"], errors="coerce").fillna(0.0)
        delivery_untaxed = Decimal(str(g["未稅總計"].sum()))
        if delivery_untaxed == 0:
            continue

        delivery_adjusted_untaxed = delivery_untaxed + adjustment_amount
        delivery_taxed = (delivery_adjusted_untaxed * Decimal(str(1 + tax_rate / 100))).quantize(Decimal("0.01"))
        grand_untaxed += delivery_untaxed
        grand_adjusted_untaxed += delivery_adjusted_untaxed
        grand_taxed += delivery_taxed

        line_rows = []
        for idx, r in g.iterrows():
            first = idx == 0
            line_rows.append(
                f"""
                <tr>
                    <td>{html.escape(str(delivery_no)) if first else ''}</td>
                    <td>{html.escape(str(order_no)) if first else ''}</td>
                    <td>{html.escape(str(supplier_delivery_number)) if first else ''}</td>
                    <td>{html.escape(str(r.get('原料編號', '') or ''))}</td>
                    <td>{html.escape(str(r.get('原料名稱', '') or ''))}</td>
                    <td class='r'>{money_fmt(r.get('單價'))}</td>
                    <td class='c'>{html.escape(str(r.get('單位', '') or ''))}</td>
                    <td class='r'>{money_fmt(r.get('數量'))}</td>
                    <td class='r'>{money_fmt(r.get('未稅總計'))}</td>
                </tr>
                """
            )

        grouped_sections.append(
            f"""
            <div class='block'>
                <div class='head'>
                    <div>入庫單號：{html.escape(str(delivery_no))}</div>
                    <div>訂單號碼：{html.escape(str(order_no or '-'))}</div>
                    <div>供應商送貨單號：{html.escape(str(supplier_delivery_number or '-'))}</div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>入庫單號</th>
                            <th>訂單號碼</th>
                            <th>供應商送貨單號</th>
                            <th>原料編號</th>
                            <th>原料名稱</th>
                            <th>單價</th>
                            <th>單位</th>
                            <th>數量</th>
                            <th>未稅總計</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(line_rows)}
                        <tr><td colspan='8' class='label'>明細未稅小計</td><td class='r'>{money_fmt(delivery_untaxed)}</td></tr>
                        <tr><td colspan='8' class='label'>調整金額</td><td class='r'>{money_fmt(adjustment_amount)}</td></tr>
                        <tr><td colspan='8' class='label'>調整後未稅金額</td><td class='r'>{money_fmt(delivery_adjusted_untaxed)}</td></tr>
                        <tr><td colspan='8' class='label'>稅率</td><td class='r'>{rate_fmt(tax_rate)}</td></tr>
                        <tr class='final'><td colspan='8' class='label'>已稅金額</td><td class='r'>{money_fmt(delivery_taxed)}</td></tr>
                    </tbody>
                </table>
            </div>
            """
        )

    return f"""
    <!doctype html>
    <html lang='zh-Hant'>
    <head>
        <meta charset='utf-8'>
        <title>供應商對帳單</title>
        <style>
            {font_css}
            @page {{ size: A4; margin: 12mm; }}
            body {{ color:#111; font-size:12px; }}
            .title {{ font-size:20px; font-weight:700; margin-bottom:8px; }}
            .meta {{ margin-bottom:12px; }}
            .print-time {{ margin-top:4px; color:#666; font-size:11px; }}
            .block {{ margin-bottom:16px; page-break-inside: avoid; }}
            .head {{ display:flex; gap:24px; margin-bottom:6px; font-weight:600; }}
            table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
            th, td {{ border:1px solid #222; padding:6px; word-break:break-word; }}
            th {{ background:#efefef; }}
            .r {{ text-align:right; }}
            .c {{ text-align:center; }}
            .label {{ text-align:right; font-weight:700; }}
            .final td {{ background:#f6f1e5; font-weight:700; }}
            .grand {{ margin-top:12px; display:flex; justify-content:flex-end; gap:20px; font-size:18px; font-weight:700; }}
        </style>
    </head>
    <body>
        <div class='title'>供應商對帳單</div>
        <div class='meta'>供應商：{html.escape(supplier_name)}｜期間：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}<div class='print-time'>列印時間：{now_str}</div></div>
        {''.join(grouped_sections)}
        <div class='grand'>
            <div>勾選明細未稅小計：{money_fmt(grand_untaxed)}</div>
            <div>勾選調整後未稅總計：{money_fmt(grand_adjusted_untaxed)}</div>
            <div>勾選含稅總計：{money_fmt(grand_taxed)}</div>
        </div>
        <script>window.onload=function(){{setTimeout(function(){{window.print();}},300);}};</script>
    </body>
    </html>
    """


def open_print_tab(html_content: str) -> str:
    """Write print HTML into the LAN print server directory and open it in the user's browser.

    Important: do not use file:///C:/... because other PCs cannot read the host's C drive.
    This function always serves HTML via http://<host LAN IP>:8767/.
    """
    # Keep this import inside the function so the function never depends on a global name.
    import streamlit.components.v1 as components

    base_url, dir_path = ensure_print_server()
    file_name = f"ap_statement_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.html"
    file_path = Path(dir_path) / file_name
    file_path.write_text(html_content, encoding="utf-8")
    url = f"{base_url}/{file_name}?t={int(datetime.now().timestamp())}"

    # 只開一次新分頁。
    # 原本同時使用 a.click() 與 window.open()，Chrome 可能會成功執行兩次，
    # 導致按一次「列印勾選項目」卻跳出兩個列印分頁。
    # 這裡改為只使用 window.open()；若被瀏覽器擋下，只顯示手動備用連結，不再自動開第二次。
    safe_url = html.escape(url, quote=True)
    components.html(
        f"""
        <html>
        <body style="margin:0;padding:0;">
        <script>
        (function() {{
            const u = {url!r};
            let opened = null;
            try {{
                opened = window.open(u, "_blank", "noopener,noreferrer");
            }} catch (e) {{}}

            if (!opened) {{
                document.body.innerHTML = `
                    <div style="font-family:Arial,sans-serif;font-size:13px;padding:6px;color:#8a4b00;">
                        Chrome 可能封鎖了新分頁。
                        <a href="{safe_url}" target="_blank" rel="noopener noreferrer">請點這裡手動開啟列印頁</a>。
                    </div>
                `;
            }}
        }})();
        </script>
        </body>
        </html>
        """,
        height=42,
    )
    return url


# =========================
# 畫面
# =========================
def ensure_state():
    today = date.today()
    master = load_supplier_master()

    if master.empty:
        if f"{PAGE_KEY}_initialized" not in st.session_state:
            st.session_state[f"{PAGE_KEY}_initialized"] = True
        return

    if f"{PAGE_KEY}_supplier_id" not in st.session_state:
        # 先抓最近有 AP 的供應商當預設，至少不是亂選。
        latest_idx = master["last_ap_date"].astype(str).idxmax()
        default_supplier_id = int(master.loc[latest_idx, "supplier_id"])
        st.session_state[f"{PAGE_KEY}_supplier_id"] = default_supplier_id

    current_supplier_id = st.session_state[f"{PAGE_KEY}_supplier_id"]
    row = master.loc[master["supplier_id"] == current_supplier_id]
    checkout_day = int(row.iloc[0]["checkout_date"]) if not row.empty and pd.notna(row.iloc[0]["checkout_date"]) else None
    default_start = suggested_start_date(today, checkout_day)

    if f"{PAGE_KEY}_start_date" not in st.session_state:
        st.session_state[f"{PAGE_KEY}_start_date"] = default_start
    if f"{PAGE_KEY}_end_date" not in st.session_state:
        st.session_state[f"{PAGE_KEY}_end_date"] = today

    st.session_state[f"{PAGE_KEY}_initialized"] = True


ensure_state()

st.title(_t("供應商對帳單"))

supplier_master = load_supplier_master()
if supplier_master.empty:
    st.warning(_t("目前資料庫裡沒有可用的應付帳款資料，這頁先沒東西可演。"))
    st.stop()

supplier_id_state = st.session_state[f"{PAGE_KEY}_supplier_id"]
start_date_state = st.session_state[f"{PAGE_KEY}_start_date"]
end_date_state = st.session_state[f"{PAGE_KEY}_end_date"]

# 先記住上一次供應商，避免 widget 建好之後才硬改 session_state。
last_supplier_key = f"{PAGE_KEY}_last_supplier_id"
if last_supplier_key not in st.session_state:
    st.session_state[last_supplier_key] = supplier_id_state

# 先用目前日期區間找可選供應商
range_suppliers = load_supplier_options_in_range(start_date_state, end_date_state)
if range_suppliers.empty:
    range_suppliers = supplier_master[["supplier_id", "supplier_name", "supplier_shortname", "checkout_date"]].copy()

supplier_options = range_suppliers.to_dict("records")
option_map = {
    int(r["supplier_id"]): f"{r['supplier_name']}"
    + (f"（{r['supplier_shortname']}）" if pd.notna(r.get("supplier_shortname")) and str(r.get("supplier_shortname")).strip() else "")
    for r in supplier_options
}

if supplier_id_state not in option_map:
    supplier_id_state = int(supplier_options[0]["supplier_id"])
    st.session_state[f"{PAGE_KEY}_supplier_id"] = supplier_id_state

# 在 widget 建立前，若偵測到供應商已改變，先更新預設起始日。
previous_supplier_id = st.session_state.get(last_supplier_key)
current_supplier_row_pre = supplier_master.loc[supplier_master["supplier_id"] == supplier_id_state]
if previous_supplier_id != supplier_id_state and not current_supplier_row_pre.empty:
    checkout_day_pre = current_supplier_row_pre.iloc[0]["checkout_date"]
    suggested_pre = (
        suggested_start_date(date.today(), int(checkout_day_pre))
        if pd.notna(checkout_day_pre)
        else date.today().replace(day=1)
    )
    st.session_state[f"{PAGE_KEY}_start_date"] = suggested_pre
    start_date_state = suggested_pre
    st.session_state[last_supplier_key] = supplier_id_state

col1, col2, col3, col4 = st.columns([1.1, 1.1, 2.6, 3.2])
with col1:
    start_date = st.date_input(_t("起始日期"), key=f"{PAGE_KEY}_start_date")
with col2:
    end_date = st.date_input(_t("結束日期"), key=f"{PAGE_KEY}_end_date")
with col3:
    supplier_id = st.selectbox(
        _t("供應商"),
        options=list(option_map.keys()),
        format_func=lambda x: option_map[x],
        # The widget key is deliberately initialised above so the selected
        # supplier survives reruns and date-range changes.  Do not also pass
        # ``index`` here: Streamlit treats that as a second default value and
        # emits a session-state warning.
        key=f"{PAGE_KEY}_supplier_id",
    )
with col4:
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    st.caption(_t("供應商清單會依目前日期區間抓有應付資料者。"))

# widget 建好後只記錄供應商，不再去改已實例化的 date_input 狀態。
st.session_state[last_supplier_key] = supplier_id

if start_date > end_date:
    st.error(_t("起始日期不能大於結束日期。這不是哲學問題，是 where 條件會直接死給你看。"))
    st.stop()

src = load_statement_source(supplier_id, start_date, end_date)
display_df = build_display_rows(src)

signature = f"{supplier_id}|{start_date.isoformat()}|{end_date.isoformat()}|{len(display_df)}"
state_sig_key = f"{PAGE_KEY}_signature"
state_df_key = f"{PAGE_KEY}_df"

if state_sig_key not in st.session_state or st.session_state[state_sig_key] != signature:
    st.session_state[state_sig_key] = signature
    st.session_state[state_df_key] = display_df.copy()
else:
    # 新資料若結構一樣，保留舊勾選狀態
    old_df = st.session_state[state_df_key].copy()
    merged = display_df.copy()
    if not old_df.empty and not merged.empty:
        keep = old_df[["_row_key", "勾選"]].drop_duplicates(subset=["_row_key"])
        merged = merged.merge(keep, on="_row_key", how="left", suffixes=("", "_old"))
        merged["勾選"] = merged["勾選_old"].fillna(False)
        merged = merged.drop(columns=["勾選_old"])
    st.session_state[state_df_key] = merged

btn1, btn2, btn3 = st.columns([1.0, 1.0, 1.0])
with btn1:
    if st.button(_t("勾選所有"), use_container_width=True):
        df = st.session_state[state_df_key].copy()
        df.loc[df["_row_type"] == "item", "勾選"] = True
        df.loc[df["_row_type"] != "item", "勾選"] = False
        st.session_state[state_df_key] = df
with btn2:
    if st.button(_t("取消勾選"), use_container_width=True):
        df = st.session_state[state_df_key].copy()
        df["勾選"] = False
        st.session_state[state_df_key] = df
with btn3:
    if st.button(_t("重新整理"), key="ap02_force_refresh", use_container_width=True):
        force_refresh_statement_data()
        st.rerun()

if st.session_state[state_df_key].empty:
    st.info(_t("這段期間沒有符合條件的應付帳款資料。"))
    st.stop()

editor_df = st.data_editor(
    st.session_state[state_df_key],
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "勾選": st.column_config.CheckboxColumn(_t("勾選")),
        "入庫單號": st.column_config.TextColumn(_t("入庫單號"), width="medium"),
        "供應商名稱": st.column_config.TextColumn(_t("供應商名稱"), width="medium"),
        "訂單號碼": st.column_config.TextColumn(_t("訂單號碼"), width="small"),
        "供應商送貨單號": st.column_config.TextColumn(_t("供應商送貨單號"), width="medium"),
        "原料編號": st.column_config.TextColumn(_t("原料編號"), width="small"),
        "原料名稱": st.column_config.TextColumn(_t("原料名稱"), width="large"),
        "單價": st.column_config.NumberColumn(_t("單價"), format="%.2f"),
        "單位": st.column_config.TextColumn(_t("單位"), width="small"),
        "數量": st.column_config.NumberColumn(_t("數量"), format="%.2f"),
        "未稅總計": st.column_config.NumberColumn(_t("未稅總計"), format="%.2f"),
        "調整金額": st.column_config.NumberColumn(_t("調整金額"), format="%.2f"),
        "調整後未稅總計": st.column_config.NumberColumn(_t("調整後未稅總計"), format="%.2f"),
        "稅率": st.column_config.NumberColumn(_t("稅率"), format="%.0f"),
        "已稅金額": st.column_config.NumberColumn(_t("已稅金額"), format="%.2f"),
        "_row_key": None,
        "_row_type": None,
        "_ap_id": None,
        "_line_id": None,
    },
    disabled=[
        "入庫單號", "供應商名稱", "訂單號碼", "供應商送貨單號", "原料編號", "原料名稱",
        "單價", "單位", "數量", "未稅總計", "調整金額", "調整後未稅總計", "稅率", "已稅金額",
        "_row_key", "_row_type", "_ap_id", "_line_id",
    ],
    key=f"{PAGE_KEY}_editor_{st.session_state.get(f'{PAGE_KEY}_editor_seed', 0)}",
)

# 小計列不給勾，硬鎖回去
editor_df.loc[editor_df["_row_type"] != "item", "勾選"] = False
st.session_state[state_df_key] = editor_df

selected_items = editor_df[(editor_df["_row_type"] == "item") & (editor_df["勾選"] == True)].copy()
selected_total = float(selected_items["未稅總計"].sum()) if not selected_items.empty else 0.0

st.markdown(f"### {_t('勾選總計：')}")
st.markdown(
    f"<div style='font-size:24px;font-weight:700;'>{_t('明細未稅小計')} {selected_total:,.2f}</div>",
    unsafe_allow_html=True,
)

print_col1, print_col2 = st.columns([1.2, 4])
with print_col1:
    if st.button(_t("列印勾選項目"), use_container_width=True, type="primary"):
        if selected_items.empty:
            st.warning(_t("你一筆都沒勾。列印機不是通靈板，沒資料不會自己生。"))
        else:
            ap_tax_map = (
                src[["ap_id", "tax_rate", "adjustment_amount"]]
                .drop_duplicates(subset=["ap_id"])
                .assign(tax_rate=lambda d: d["tax_rate"].fillna(0).astype(float),
                        adjustment_amount=lambda d: d["adjustment_amount"].fillna(0).astype(float))
            )
            selected_items = selected_items.merge(
                ap_tax_map,
                left_on="_ap_id",
                right_on="ap_id",
                how="left",
            )
            selected_items = selected_items.rename(columns={"tax_rate": "_tax_rate_for_print", "adjustment_amount": "_adjustment_for_print"})

            supplier_name = option_map[supplier_id]
            html_content = build_print_html(selected_items, supplier_name, start_date, end_date)
            url = open_print_tab(html_content)
            st.success(f"{_t('已開啟列印預覽：')}{url}")
with print_col2:
    st.caption(_t("列印內容為 A4 直式，會只列出目前勾選的明細與各入庫單小計。"))
