from __future__ import annotations

from compact_layout import apply_compact_layout

apply_compact_layout()

import base64
import html
import math
import tempfile
import webbrowser
import threading
import http.server
import socketserver
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import text

try:
    import streamlit.column_config as st_column_config
except Exception:
    st_column_config = None

from db import get_engine
import auth



# =============================
# Safe I18N helper
# =============================
TRANSLATIONS = {
    "AR02 客戶對帳單": {"vi": "AR02 Bảng đối chiếu công nợ khách hàng", "en": "AR02 Customer Statement"},
    "客戶對帳單": {"vi": "Bảng đối chiếu công nợ khách hàng", "en": "Customer Statement"},
    "起始日期": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "客戶名稱": {"vi": "Tên khách hàng", "en": "Customer Name"},
    "建議起始日依 checkout_day = ": {"vi": "Ngày bắt đầu đề xuất theo checkout_day = ", "en": "Suggested start date based on checkout_day = "},
    "勾選所有": {"vi": "Chọn tất cả", "en": "Select All"},
    "取消勾選": {"vi": "Bỏ chọn tất cả", "en": "Clear Selection"},
    "對帳資料": {"vi": "Dữ liệu đối chiếu", "en": "Statement Data"},
    "這個條件下查不到資料。先別怪系統，先怪條件。": {"vi": "Không tìm thấy dữ liệu theo điều kiện này. Hãy kiểm tra lại điều kiện trước.", "en": "No data found for these filters. Check the conditions first."},
    "送貨單號": {"vi": "Mã phiếu giao hàng", "en": "Delivery No."},
    "客戶訂單號碼": {"vi": "Số đơn hàng khách hàng", "en": "Customer Order No."},
    "原料編號": {"vi": "Mã vật liệu", "en": "Material Code"},
    "原料名稱": {"vi": "Tên vật liệu", "en": "Material Name"},
    "單價": {"vi": "Đơn giá", "en": "Unit Price"},
    "單位": {"vi": "Đơn vị", "en": "Unit"},
    "數量": {"vi": "Số lượng", "en": "Quantity"},
    "總計": {"vi": "Tổng cộng", "en": "Total"},
    "折扣/折讓": {"vi": "Chiết khấu / giảm trừ", "en": "Discount / Allowance"},
    "未稅金額": {"vi": "Số tiền chưa thuế", "en": "Untaxed Amount"},
    "稅率": {"vi": "Thuế suất", "en": "Tax Rate"},
    "已稅金額": {"vi": "Số tiền gồm thuế", "en": "Tax Included Amount"},
    "起始日期不能大於結束日期。": {"vi": "Ngày bắt đầu không được lớn hơn ngày kết thúc.", "en": "Start date cannot be later than end date."},
    "勾選總計：": {"vi": "Tổng đã chọn:", "en": "Selected Total:"},
    "列印勾選項目": {"vi": "In các mục đã chọn", "en": "Print Selected Items"},
    "已開啟列印預覽：": {"vi": "Đã mở xem trước khi in: ", "en": "Opened print preview: "},
    "列印失敗：": {"vi": "In thất bại: ", "en": "Print failed: "},
    "請至少勾選一筆送貨單後再列印。": {"vi": "Vui lòng chọn ít nhất một phiếu giao hàng trước khi in.", "en": "Please select at least one delivery note before printing."},
}
def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    return lang if lang in {"zh", "vi", "en"} else "zh"

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)


PAGE_TITLE = "AR02 客戶對帳單"
PAGE_KEY = "AR02_prepare_accounts_receivable"
auth.require_read(PAGE_KEY)
FONT_CANDIDATES = [
    Path(r"D:\Python_Plactice\OrdoLitePlay\NotoSansTC-VariableFont_wght.ttf"),
    Path(__file__).resolve().parent / "NotoSansTC-VariableFont_wght.ttf",
    Path.cwd() / "NotoSansTC-VariableFont_wght.ttf",
]

TABLE_COLUMNS = [
    "勾選",
    "送貨單號",
    "客戶訂單號碼",
    "原料編號",
    "原料名稱",
    "單價",
    "單位",
    "數量",
    "總計",
    "折扣/折讓",
    "未稅金額",
    "稅率",
    "已稅金額",
    "_statement_id",
    "_is_first_row",
]


@dataclass
class DeliveryGroup:
    delivery_code: str
    statement_id: int
    customer_name: str
    customer_order_number: str
    deliver_date: date
    adjustment_amount: Decimal
    non_tax_amount: Decimal
    tax_rate: Optional[int]
    final_total: Decimal
    lines: List[dict]


def set_page():
    try:
        st.set_page_config(page_title=_t("AR02 客戶對帳單"), layout="wide")
    except Exception:
        pass


@st.cache_resource(show_spinner=False)
def get_db_engine():
    return get_engine()


@st.cache_data(show_spinner=False, ttl=60)
def load_customers_with_ar() -> pd.DataFrame:
    sql = text(
        """
        SELECT DISTINCT
            h.customer_id,
            h.customer_name,
            COALESCE(c.checkout_day, 25) AS checkout_day,
            COALESCE(c.checkout_rule, 'DOM') AS checkout_rule
        FROM ar_statement_head h
        LEFT JOIN customer c ON c.customer_id = h.customer_id
        WHERE h.customer_name IS NOT NULL
        ORDER BY h.customer_name
        """
    )
    with get_db_engine().connect() as conn:
        return pd.read_sql(sql, conn)


@st.cache_data(show_spinner=False, ttl=60)
def load_customer_names_by_period(start_date: date, end_date: date) -> List[str]:
    sql = text(
        """
        SELECT DISTINCT customer_name
        FROM ar_statement_head
        WHERE deliver_date BETWEEN :start_date AND :end_date
          AND customer_name IS NOT NULL
        ORDER BY customer_name
        """
    )
    with get_db_engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date})
    return df["customer_name"].dropna().astype(str).tolist()


@st.cache_data(show_spinner=False, ttl=60)
def fetch_ar_detail(start_date: date, end_date: date, customer_name: str) -> pd.DataFrame:
    sql = text(
        """
        SELECT
            h.statement_id,
            h.delivery_code,
            h.customer_name,
            h.customer_order_number,
            h.deliver_date,
            COALESCE(h.adjustment_amount, 0) AS adjustment_amount,
            COALESCE(h.non_tax_amount, 0) AS non_tax_amount,
            h.tax_rate,
            COALESCE(h.final_total, 0) AS final_total,
            l.statement_line_id,
            l.line_no,
            l.customer_product_id,
            l.product_name,
            COALESCE(l.price_unit, 0) AS price_unit,
            COALESCE(l.qty, 0) AS qty,
            COALESCE(l.line_amount, 0) AS line_amount,
            COALESCE(p.unit, 'PCS') AS unit
        FROM ar_statement_head h
        INNER JOIN ar_statement_line l ON l.statement_id = h.statement_id
        LEFT JOIN product p ON p.product_id = l.product_id
        WHERE h.deliver_date BETWEEN :start_date AND :end_date
          AND h.customer_name = :customer_name
        ORDER BY h.deliver_date, h.delivery_code, h.statement_id, l.line_no, l.statement_line_id
        """
    )
    with get_db_engine().connect() as conn:
        return pd.read_sql(
            sql,
            conn,
            params={"start_date": start_date, "end_date": end_date, "customer_name": customer_name},
        )


def safe_decimal(value) -> Decimal:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def money_fmt(value) -> str:
    amount = safe_decimal(value)
    q = amount.quantize(Decimal("0.01"))
    s = f"{q:,.2f}"
    return s[:-3] if s.endswith(".00") else s


def rate_fmt(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        return f"{int(value)}%"
    except Exception:
        return ""


def compute_cycle_start(today: date, checkout_day: int) -> date:
    checkout_day = int(checkout_day or 25)
    if today.day <= checkout_day:
        prev_month_end = today.replace(day=1) - timedelta(days=1)
        return prev_month_end.replace(day=min(checkout_day + 1, prev_month_end.day))
    return today.replace(day=checkout_day + 1)


def get_selected_customer_info(customers_df: pd.DataFrame, customer_name: str) -> Tuple[int, str]:
    row = customers_df.loc[customers_df["customer_name"] == customer_name]
    if row.empty:
        return 25, "DOM"
    r = row.iloc[0]
    return int(r.get("checkout_day", 25) or 25), str(r.get("checkout_rule", "DOM") or "DOM")


def prepare_groups(df: pd.DataFrame) -> List[DeliveryGroup]:
    groups: List[DeliveryGroup] = []
    if df.empty:
        return groups

    for statement_id, grp in df.groupby("statement_id", sort=False):
        first = grp.iloc[0]
        lines = []
        for _, row in grp.iterrows():
            lines.append(
                {
                    "customer_product_id": row.get("customer_product_id") or "",
                    "product_name": row.get("product_name") or "",
                    "price_unit": safe_decimal(row.get("price_unit")),
                    "qty": safe_decimal(row.get("qty")),
                    "line_amount": safe_decimal(row.get("line_amount")),
                    "unit": str(row.get("unit") or "PCS"),
                }
            )

        groups.append(
            DeliveryGroup(
                delivery_code=str(first.get("delivery_code") or ""),
                statement_id=int(statement_id),
                customer_name=str(first.get("customer_name") or ""),
                customer_order_number=str(first.get("customer_order_number") or ""),
                deliver_date=pd.to_datetime(first.get("deliver_date")).date(),
                adjustment_amount=safe_decimal(first.get("adjustment_amount")),
                non_tax_amount=safe_decimal(first.get("non_tax_amount")),
                tax_rate=None if pd.isna(first.get("tax_rate")) else int(first.get("tax_rate")),
                final_total=safe_decimal(first.get("final_total")),
                lines=lines,
            )
        )
    return groups


def init_state():
    ss = st.session_state
    ss.setdefault("ar02_start_date", date.today().replace(day=1))
    ss.setdefault("ar02_end_date", date.today())
    ss.setdefault("ar02_customer_name", "")
    ss.setdefault("ar02_selected_map", {})
    ss.setdefault("ar02_last_customer", "")
    ss.setdefault("ar02_auto_applied", False)


def reset_selection(groups: List[DeliveryGroup], checked: bool):
    for g in groups:
        st.session_state.ar02_selected_map[str(g.statement_id)] = checked


def build_compact_table(groups: List[DeliveryGroup]) -> pd.DataFrame:
    rows = []
    selected_map = st.session_state.ar02_selected_map

    for g in groups:
        checked = bool(selected_map.get(str(g.statement_id), False))
        for idx, line in enumerate(g.lines):
            is_first = idx == 0
            rows.append(
                {
                    "勾選": checked if is_first else False,
                    "送貨單號": g.delivery_code if is_first else "",
                    "客戶訂單號碼": g.customer_order_number if is_first else "",
                    "原料編號": line["customer_product_id"],
                    "原料名稱": line["product_name"],
                    "單價": money_fmt(line["price_unit"]),
                    "單位": line["unit"],
                    "數量": money_fmt(line["qty"]),
                    "總計": money_fmt(line["line_amount"]),
                    "折扣/折讓": money_fmt(g.adjustment_amount) if is_first else "",
                    "未稅金額": money_fmt(g.non_tax_amount) if is_first else "",
                    "稅率": rate_fmt(g.tax_rate) if is_first else "",
                    "已稅金額": money_fmt(g.final_total) if is_first else "",
                    "_statement_id": str(g.statement_id),
                    "_is_first_row": is_first,
                }
            )
    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


def sync_selection_from_compact_editor(editor_df: pd.DataFrame):
    if editor_df is None or editor_df.empty:
        return

    chosen: Dict[str, bool] = {}
    for _, row in editor_df.iterrows():
        statement_id = str(row.get("_statement_id", "")).strip()
        if not statement_id:
            continue
        is_first = bool(row.get("_is_first_row", False))
        if is_first:
            chosen[statement_id] = bool(row.get("勾選", False))

    for statement_id, checked in chosen.items():
        st.session_state.ar02_selected_map[statement_id] = checked


def selected_total(groups: List[DeliveryGroup]) -> Decimal:
    total = Decimal("0")
    for g in groups:
        if st.session_state.ar02_selected_map.get(str(g.statement_id), False):
            total += g.final_total
    return total


def font_base64() -> str:
    for path in FONT_CANDIDATES:
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
    return ""


def render_print_html(groups: List[DeliveryGroup], customer_name: str, start_date: date, end_date: date) -> str:
    selected_groups = [g for g in groups if st.session_state.ar02_selected_map.get(str(g.statement_id), False)]
    if not selected_groups:
        raise ValueError("請至少勾選一筆送貨單後再列印。")

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

    sections = []
    grand_total = Decimal("0")
    for g in selected_groups:
        grand_total += g.final_total
        lines_html = "".join(
            f"""
            <tr>
                <td>{html.escape(str(line['customer_product_id']))}</td>
                <td>{html.escape(str(line['product_name']))}</td>
                <td class='r'>{money_fmt(line['price_unit'])}</td>
                <td class='c'>{html.escape(str(line['unit']))}</td>
                <td class='r'>{money_fmt(line['qty'])}</td>
                <td class='r'>{money_fmt(line['line_amount'])}</td>
            </tr>
            """
            for line in g.lines
        )
        sections.append(
            f"""
            <div class='block'>
                <div class='head'>
                    <div>送貨單號：{html.escape(g.delivery_code)}</div>
                    <div>客戶訂單號碼：{html.escape(g.customer_order_number or '-')}</div>
                    <div>日期：{g.deliver_date.strftime('%Y-%m-%d')}</div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>原料編號</th>
                            <th>原料名稱</th>
                            <th>單價</th>
                            <th>單位</th>
                            <th>數量</th>
                            <th>總計</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lines_html}
                        <tr><td colspan='5' class='label'>折扣/折讓</td><td class='r'>{money_fmt(g.adjustment_amount)}</td></tr>
                        <tr><td colspan='5' class='label'>未稅金額</td><td class='r'>{money_fmt(g.non_tax_amount)}</td></tr>
                        <tr><td colspan='5' class='label'>稅率</td><td class='r'>{rate_fmt(g.tax_rate)}</td></tr>
                        <tr class='final'><td colspan='5' class='label'>已稅金額</td><td class='r'>{money_fmt(g.final_total)}</td></tr>
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
        <title>客戶對帳單</title>
        <style>
            {font_css}
            @page {{ size: A4; margin: 12mm; }}
            body {{ color:#111; font-size:12px; }}
            .title {{ font-size:20px; font-weight:700; margin-bottom:8px; }}
            .meta {{ margin-bottom:12px; }}
            .block {{ margin-bottom:16px; page-break-inside: avoid; }}
            .head {{ display:flex; gap:24px; margin-bottom:6px; font-weight:600; }}
            table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
            th, td {{ border:1px solid #222; padding:6px; word-break:break-word; }}
            th {{ background:#efefef; }}
            .r {{ text-align:right; }}
            .c {{ text-align:center; }}
            .label {{ text-align:right; font-weight:700; }}
            .final td {{ background:#f6f1e5; font-weight:700; }}
            .grand {{ margin-top:12px; display:flex; justify-content:flex-end; font-size:18px; font-weight:700; }}
        </style>
    </head>
    <body>
        <div class='title'>客戶對帳單</div>
        <div class='meta'>客戶：{html.escape(customer_name)}｜期間：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}</div>
        {''.join(sections)}
        <div class='grand'>勾選總計：{money_fmt(grand_total)}</div>
        <script>window.onload=function(){{setTimeout(function(){{window.print();}},300);}};</script>
    </body>
    </html>
    """


# =========================
# LAN print HTML server
# =========================
# AR02 原本用 file:///C:/Users/.../Temp 開本機 HTML。
# 主機自己可以，但其他電腦會去找自己的 C 槽，所以一定失敗。
# 這裡改成固定 8768 port，並綁 0.0.0.0，讓同一個內網的使用者可以開：
# http://主機IP:8768/ar_statement_xxx.html
_AR02_PRINT_SERVER = {"thread": None, "dir": None, "port": 8768}


def _get_lan_ip() -> str:
    """Best-effort local LAN IP. Fallback to localhost if detection fails."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # UDP connect does not need internet access; it only asks OS which local IP would be used.
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return "localhost"


def _ensure_ar02_print_server() -> tuple[str, Path]:
    """Start/reuse AR02 HTML print server. Return (base_url, serving_dir)."""
    if _AR02_PRINT_SERVER["thread"] is not None and _AR02_PRINT_SERVER["dir"] is not None:
        base_url = f"http://{_get_lan_ip()}:{_AR02_PRINT_SERVER['port']}"
        return base_url, Path(_AR02_PRINT_SERVER["dir"])

    serve_dir = Path(tempfile.gettempdir()) / "ordolite_ar02_print"
    serve_dir.mkdir(parents=True, exist_ok=True)
    port = int(_AR02_PRINT_SERVER["port"])

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

        def log_message(self, format, *args):
            return

    class ReuseTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    def _serve():
        try:
            with ReuseTCPServer(("0.0.0.0", port), QuietHandler) as httpd:
                httpd.serve_forever()
        except OSError:
            # Port already in use, likely by a previous Streamlit/Python process.
            # Keep returning the same URL; if the old server is alive, files may not match.
            # Restarting Streamlit normally clears this.
            return

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    time.sleep(0.15)

    _AR02_PRINT_SERVER["thread"] = t
    _AR02_PRINT_SERVER["dir"] = str(serve_dir)
    base_url = f"http://{_get_lan_ip()}:{port}"
    return base_url, serve_dir


def open_print_preview(html_content: str) -> str:
    """Write AR02 statement HTML to LAN print server and auto-open it in a new tab."""
    import streamlit.components.v1 as components

    base_url, serve_dir = _ensure_ar02_print_server()
    filename = f"ar_statement_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.html"
    file_path = serve_dir / filename
    file_path.write_text(html_content, encoding="utf-8")
    url = f"{base_url}/{filename}?t={int(time.time())}"

    # Directly try to open a new tab after user clicks print.
    components.html(
        f"""
        <script>
        try {{
            window.open({url!r}, "_blank");
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )

    # Backup clickable link, useful if Chrome blocks the auto-open.
    try:
        if hasattr(st, "link_button"):
            st.link_button("開啟列印預覽（備用）", url, use_container_width=True)
        else:
            st.markdown(f"[開啟列印預覽（備用）]({url})")
    except Exception:
        pass

    return url


def inject_compact_css():
    st.markdown(
        """
        <style>
        div[data-testid="stDataEditor"] [data-testid="stDataEditorResizableContainer"] {
            border: 1px solid #b8b8b8;
        }
        div[data-testid="stDataEditor"] {
            margin-top: 0.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_query_area(customers_df: pd.DataFrame):
    st.markdown("### 客戶對帳單")

    all_customer_names = customers_df["customer_name"].dropna().astype(str).tolist()
    if not all_customer_names:
        st.warning("目前 ar_statement_head 查不到任何客戶資料。")
        return None, None, None, []

    if not st.session_state.ar02_customer_name or st.session_state.ar02_customer_name not in all_customer_names:
        st.session_state.ar02_customer_name = all_customer_names[0]

    selected_customer = st.session_state.ar02_customer_name
    checkout_day, _ = get_selected_customer_info(customers_df, selected_customer)
    suggested_start = compute_cycle_start(date.today(), checkout_day)

    if not st.session_state.ar02_auto_applied or st.session_state.ar02_last_customer != selected_customer:
        st.session_state.ar02_start_date = suggested_start
        st.session_state.ar02_end_date = date.today()
        st.session_state.ar02_auto_applied = True
        st.session_state.ar02_last_customer = selected_customer

    query_cols = st.columns([1.1, 1.1, 1.3, 4.5])
    with query_cols[0]:
        start_date = st.date_input("起始日期", key="ar02_start_date")
    with query_cols[1]:
        end_date = st.date_input("結束日期", key="ar02_end_date")
    with query_cols[2]:
        selectable_names = load_customer_names_by_period(start_date, end_date)
        options = selectable_names if selectable_names else all_customer_names
        if st.session_state.ar02_customer_name not in options:
            st.session_state.ar02_customer_name = options[0]
        customer_name = st.selectbox("客戶名稱", options=options, key="ar02_customer_name")
    with query_cols[3]:
        st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)
        st.caption(f"建議起始日依 checkout_day = {checkout_day} 推算。")

    st.markdown("<div style='height: 0.3rem;'></div>", unsafe_allow_html=True)

    action_box = st.container(border=True)
    with action_box:
        action_cols = st.columns([1.1, 1.1, 5.8])
        with action_cols[0]:
            select_all = st.button("勾選所有", key="ar02_btn_select_all", use_container_width=True)
        with action_cols[1]:
            unselect_all = st.button("取消勾選", key="ar02_btn_unselect_all", use_container_width=True)
        with action_cols[2]:
            st.markdown("<div style='height: 0.2rem;'></div>", unsafe_allow_html=True)
            st.caption("")

    if select_all:
        return start_date, end_date, customer_name, ["select_all"]
    if unselect_all:
        return start_date, end_date, customer_name, ["unselect_all"]

    return start_date, end_date, customer_name, []



def render_compact_editor(groups: List[DeliveryGroup]):
    st.markdown(f"#### {_t('對帳資料')}")
    if not groups:
        st.info(_t("這個條件下查不到資料。先別怪系統，先怪條件。"))
        return

    inject_compact_css()
    table_df = build_compact_table(groups)

    display_map = {
        "勾選": _t("勾選"),
        "送貨單號": _t("送貨單號"),
        "客戶訂單號碼": _t("客戶訂單號碼"),
        "原料編號": _t("原料編號"),
        "原料名稱": _t("原料名稱"),
        "單價": _t("單價"),
        "單位": _t("單位"),
        "數量": _t("數量"),
        "總計": _t("總計"),
        "折扣/折讓": _t("折扣/折讓"),
        "未稅金額": _t("未稅金額"),
        "稅率": _t("稅率"),
        "已稅金額": _t("已稅金額"),
    }

    table_df = table_df.rename(columns=display_map)

    check_col = display_map["勾選"]

    column_config = {
        check_col: st_column_config.CheckboxColumn(check_col, default=False, width="small") if st_column_config else None,
        display_map["送貨單號"]: st_column_config.TextColumn(display_map["送貨單號"], width="medium") if st_column_config else None,
        display_map["客戶訂單號碼"]: st_column_config.TextColumn(display_map["客戶訂單號碼"], width="medium") if st_column_config else None,
        display_map["原料編號"]: st_column_config.TextColumn(display_map["原料編號"], width="medium") if st_column_config else None,
        display_map["原料名稱"]: st_column_config.TextColumn(display_map["原料名稱"], width="large") if st_column_config else None,
        display_map["單價"]: st_column_config.TextColumn(display_map["單價"], width="small") if st_column_config else None,
        display_map["單位"]: st_column_config.TextColumn(display_map["單位"], width="small") if st_column_config else None,
        display_map["數量"]: st_column_config.TextColumn(display_map["數量"], width="small") if st_column_config else None,
        display_map["總計"]: st_column_config.TextColumn(display_map["總計"], width="small") if st_column_config else None,
        display_map["折扣/折讓"]: st_column_config.TextColumn(display_map["折扣/折讓"], width="small") if st_column_config else None,
        display_map["未稅金額"]: st_column_config.TextColumn(display_map["未稅金額"], width="small") if st_column_config else None,
        display_map["稅率"]: st_column_config.TextColumn(display_map["稅率"], width="small") if st_column_config else None,
        display_map["已稅金額"]: st_column_config.TextColumn(display_map["已稅金額"], width="small") if st_column_config else None,
        "_statement_id": None,
        "_is_first_row": None,
    } if st_column_config else None

    disabled_cols = [
        display_map["送貨單號"], display_map["客戶訂單號碼"], display_map["原料編號"], display_map["原料名稱"],
        display_map["單價"], display_map["單位"], display_map["數量"], display_map["總計"],
        display_map["折扣/折讓"], display_map["未稅金額"], display_map["稅率"], display_map["已稅金額"],
        "_statement_id", "_is_first_row"
    ]

    edited_df = st.data_editor(
        table_df,
        use_container_width=True,
        hide_index=True,
        height=220,
        disabled=disabled_cols,
        column_config=column_config,
        key="ar02_compact_editor",
    )

    reverse_map = {v: k for k, v in display_map.items()}
    edited_df = edited_df.rename(columns=reverse_map)
    sync_selection_from_compact_editor(edited_df)


def main():
    set_page()
    init_state()

    customers_df = load_customers_with_ar()
    start_date, end_date, customer_name, actions = render_query_area(customers_df)
    if not start_date or not end_date or not customer_name:
        return
    if start_date > end_date:
        st.error("起始日期不能大於結束日期。")
        return

    raw_df = fetch_ar_detail(start_date, end_date, customer_name)
    groups = prepare_groups(raw_df)

    if "select_all" in actions:
        reset_selection(groups, True)
    elif "unselect_all" in actions:
        reset_selection(groups, False)

    if "print" in actions:
        try:
            html_content = render_print_html(groups, customer_name, start_date, end_date)
            path = open_print_preview(html_content)
            st.success(f"已開啟列印預覽：{path}")
        except Exception as e:
            st.error(f"列印失敗：{e}")

    render_compact_editor(groups)

    st.markdown(f"**勾選總計：** {money_fmt(selected_total(groups))}")

    print_cols = st.columns([1.2, 5.8])
    with print_cols[0]:
        do_print = st.button("列印勾選項目", key="ar02_btn_print_bottom", type="primary", use_container_width=True)
    with print_cols[1]:
        st.markdown("<div style='height: 0.2rem;'></div>", unsafe_allow_html=True)

    if do_print:
        try:
            html_content = render_print_html(groups, customer_name, start_date, end_date)
            path = open_print_preview(html_content)
            st.success(f"已開啟列印預覽：{path}")
        except Exception as e:
            st.error(f"列印失敗：{e}")


if __name__ == "__main__":
    main()
