"""SP01 sample-making, pricing, and work-queue page."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from compact_layout import apply_compact_layout
from db import get_connection


apply_compact_layout()
st.set_page_config(page_title="SP01 Sample Making & Pricing", layout="wide")


TRANSLATIONS = {
    "SP01 樣品打樣與計價": {"en": "SP01 Sample Making & Pricing", "vi": "SP01 Làm mẫu & Báo giá"},
    "可建立樣品單；樣品不必先建立正式產品。收款樣品於 D02 出貨後會建立 AR，免收款樣品則不會。": {"en": "Create sample orders without first creating a product. Receivable samples create AR after D02 delivery; free samples do not.", "vi": "Có thể tạo đơn mẫu mà chưa cần tạo sản phẩm chính thức. Mẫu có thu tiền sẽ tạo AR sau khi giao D02; mẫu miễn phí thì không."},
    "建立樣品單": {"en": "Create Sample Order", "vi": "Tạo đơn hàng mẫu"},
    "樣品單清單": {"en": "Sample Order List", "vi": "Danh sách đơn hàng mẫu"},
    "樣品單號（系統建立後產生）": {"en": "Sample Order No. (generated after saving)", "vi": "Số đơn mẫu (tạo sau khi lưu)"},
    "樣品類別": {"en": "Sample Category", "vi": "Loại mẫu"},
    "樣品單（要收款）": {"en": "Sample Order (Receivable)", "vi": "Đơn mẫu (cần thu tiền)"},
    "樣品單（不收款）": {"en": "Sample Order (Non-Receivable)", "vi": "Đơn mẫu (không thu tiền)"},
    "樣品狀態": {"en": "Sample Status", "vi": "Trạng thái mẫu"},
    "草稿": {"en": "Draft", "vi": "Bản nháp"},
    "待報價": {"en": "Pending Quote", "vi": "Chờ báo giá"},
    "待客戶確認": {"en": "Awaiting Customer Approval", "vi": "Chờ khách xác nhận"},
    "打樣中": {"en": "In Production", "vi": "Đang làm mẫu"},
    "已完成": {"en": "Completed", "vi": "Hoàn thành"},
    "客戶與時程": {"en": "Customer & Schedule", "vi": "Khách hàng & Tiến độ"},
    "客戶": {"en": "Customer", "vi": "Khách hàng"},
    "需求日期": {"en": "Requested Date", "vi": "Ngày yêu cầu"},
    "預計完成日": {"en": "Target Completion", "vi": "Ngày dự kiến hoàn thành"},
    "樣品規格": {"en": "Sample Specification", "vi": "Quy cách mẫu"},
    "樣品名稱": {"en": "Sample Name", "vi": "Tên mẫu"},
    "客戶料號（可空）": {"en": "Customer Item No. (Optional)", "vi": "Mã hàng khách (Tùy chọn)"},
    "規格／需求說明": {"en": "Specification / Requirements", "vi": "Quy cách / Yêu cầu"},
    "材質與結構": {"en": "Material & Structure", "vi": "Vật liệu & Kết cấu"},
    "樣品數量": {"en": "Sample Quantity", "vi": "Số lượng mẫu"},
    "單位": {"en": "Unit", "vi": "Đơn vị"},
    "PCS": {"en": "PCS", "vi": "PCS"},
    "SET": {"en": "SET", "vi": "BỘ"},
    "樣品計價": {"en": "Sample Pricing", "vi": "Báo giá mẫu"},
    "幣別": {"en": "Currency", "vi": "Tiền tệ"},
    "打樣費": {"en": "Sample Making Fee", "vi": "Phí làm mẫu"},
    "運費": {"en": "Freight", "vi": "Phí vận chuyển"},
    "其他費用": {"en": "Other Charges", "vi": "Chi phí khác"},
    "未稅小計": {"en": "Subtotal Before Tax", "vi": "Tạm tính trước thuế"},
    "稅率": {"en": "Tax Rate", "vi": "Thuế suất"},
    "含稅總額": {"en": "Total Including Tax", "vi": "Tổng cộng gồm thuế"},
    "備註與下一步": {"en": "Notes & Next Step", "vi": "Ghi chú & Bước tiếp theo"},
    "內部備註": {"en": "Internal Notes", "vi": "Ghi chú nội bộ"},
    "樣品完成後可轉正式產品／客戶訂單": {"en": "After approval, the sample can be converted into a product / customer order.", "vi": "Sau khi được duyệt, mẫu có thể chuyển thành sản phẩm / đơn hàng khách."},
    "儲存草稿": {"en": "Save Draft", "vi": "Lưu nháp"},
    "送交報價確認": {"en": "Send for Quote Approval", "vi": "Gửi xác nhận báo giá"},
    "轉成正式產品": {"en": "Convert to Product", "vi": "Chuyển thành sản phẩm"},
    "樣品明細可先不建立正式產品；轉產品功能將於後續階段開放。": {"en": "Sample items do not need a formal product yet. Product conversion will be available in a later phase.", "vi": "Chi tiết mẫu chưa cần tạo sản phẩm chính thức. Chức năng chuyển thành sản phẩm sẽ có ở giai đoạn sau."},
    "請輸入樣品名稱。": {"en": "Please enter a sample name.", "vi": "Vui lòng nhập tên mẫu."},
    "找不到客戶資料，無法建立樣品單。": {"en": "No customer records were found, so a sample order cannot be created.", "vi": "Không tìm thấy dữ liệu khách hàng nên không thể tạo đơn mẫu."},
    "收款設定": {"en": "Receivable Setting", "vi": "Thiết lập thu tiền"},
    "會建立 AR": {"en": "Will create AR", "vi": "Sẽ tạo công nợ phải thu"},
    "不建立 AR": {"en": "Will not create AR", "vi": "Không tạo công nợ phải thu"},
    "樣品不收款，不顯示或儲存對外價格。": {"en": "This sample is non-receivable, so no customer price is shown or saved.", "vi": "Mẫu này không thu tiền nên không hiển thị hoặc lưu giá bán cho khách hàng."},
    "待打樣清單": {"en": "Sample Work Queue", "vi": "Danh sách cần làm mẫu"},
    "目前待打樣": {"en": "Currently Pending", "vi": "Đang chờ làm"},
    "今日到期": {"en": "Due Today", "vi": "Đến hạn hôm nay"},
    "逾期": {"en": "Overdue", "vi": "Quá hạn"},
    "已完成／取消": {"en": "Completed / Cancelled", "vi": "Hoàn thành / Đã hủy"},
    "全部狀態": {"en": "All Statuses", "vi": "Tất cả trạng thái"},
    "尚無符合條件的樣品單。": {"en": "No sample orders match the selected conditions.", "vi": "Không có đơn mẫu phù hợp điều kiện đã chọn."},
    "新增樣品單": {"en": "Add Sample Order", "vi": "Thêm đơn mẫu"},
    "請勾選一筆樣品單以查看或處理明細。": {"en": "Select a sample order to view or process its details.", "vi": "Hãy chọn một đơn mẫu để xem hoặc xử lý chi tiết."},
    "勾選": {"en": "Select", "vi": "Chọn"},
    "樣品明細與進度": {"en": "Sample Details & Progress", "vi": "Chi tiết & Tiến độ mẫu"},
    "更新狀態": {"en": "Update Status", "vi": "Cập nhật trạng thái"},
    "狀態已更新。": {"en": "Status updated.", "vi": "Đã cập nhật trạng thái."},
    "需求": {"en": "Requirements", "vi": "Yêu cầu"},
    "材質": {"en": "Material", "vi": "Vật liệu"},
    "顯示新增樣品表單": {"en": "Show New Sample Form", "vi": "Hiển thị biểu mẫu tạo mẫu mới"},
    "樣品單號": {"en": "Sample Order No.", "vi": "Mã đơn mẫu"},
    "客戶名稱": {"en": "Customer", "vi": "Khách hàng"},
    "金額": {"en": "Amount", "vi": "Số tiền"},
    "預計完成": {"en": "Target Completion", "vi": "Ngày dự kiến hoàn thành"},
    "下一步": {"en": "Next Step", "vi": "Bước tiếp theo"},
    "報價確認": {"en": "Quote Approval", "vi": "Xác nhận báo giá"},
    "安排打樣": {"en": "Schedule Sample Making", "vi": "Sắp xếp làm mẫu"},
    "安排送貨": {"en": "Arrange Delivery", "vi": "Sắp xếp giao hàng"},
}


def _lang() -> str:
    lang = st.session_state.get("lang", "zh")
    return lang if lang in {"zh", "en", "vi"} else "zh"


def t(text: str) -> str:
    if _lang() == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(_lang(), text)


def _current_user_id() -> int | None:
    try:
        value = st.session_state.get("user_id")
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=30)
def load_customers() -> list[tuple[int, str]]:
    conn = get_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT customer_id, customer_name, customer_shortname FROM customer ORDER BY customer_name")
        return [(int(r[0]), f"{r[1]} | {r[2] or ''}") for r in cur.fetchall()]
    finally:
        conn.close()


def next_sample_code(cur) -> str:
    prefix = f"SP-{date.today():%y%m%d}-"
    cur.execute("SELECT COALESCE(MAX(CAST(RIGHT(sample_order_code, 3) AS UNSIGNED)), 0) FROM sample_order_head WHERE sample_order_code LIKE %s", (prefix + "%",))
    return f"{prefix}{int(cur.fetchone()[0] or 0) + 1:03d}"


def save_sample_order(*, customer_id: int, category: str, status: str, request_date: date, target_date: date, currency: str, tax_rate: float, sample_fee: float, freight: float, other_fee: float, note: str, sample_name: str, customer_item_code: str, specification: str, material_structure: str, quantity: float, unit: str) -> str:
    if not sample_name.strip():
        raise ValueError(t("請輸入樣品名稱。"))
    conn = get_connection()
    if conn is None:
        raise RuntimeError("DB 連線失敗")
    try:
        cur = conn.cursor()
        code = next_sample_code(cur)
        user_id = _current_user_id()
        cur.execute("""
            INSERT INTO sample_order_head
            (sample_order_code, sample_category, customer_id, request_date,
             target_completion_date, status, currency, tax_rate, sample_fee, freight_fee,
             other_fee, note, created_by, updated_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (code, category, customer_id, request_date, target_date, status,
              currency, tax_rate, sample_fee, freight, other_fee, note.strip() or None,
              user_id, user_id))
        sample_id = int(cur.lastrowid)
        cur.execute("""
            INSERT INTO sample_order_item
            (sample_order_id, line_no, sample_name, customer_item_code, specification,
             material_structure, quantity, unit, unit_price)
            VALUES (%s,1,%s,%s,%s,%s,%s,%s,%s)
        """, (sample_id, sample_name.strip(), customer_item_code.strip() or None,
              specification.strip() or None, material_structure.strip() or None,
              quantity, unit, sample_fee))
        conn.commit()
        load_customers.clear()
        return code
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@st.cache_data(ttl=15)
def load_sample_orders() -> list[dict]:
    conn = get_connection()
    if conn is None:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT h.sample_order_id, h.sample_order_code, c.customer_name, h.sample_category,
                   h.status, h.request_date, h.target_completion_date,
                   i.sample_name, i.customer_item_code, i.specification,
                   i.material_structure, i.quantity, i.unit,
                   (h.sample_fee + h.freight_fee + h.other_fee) * (1 + h.tax_rate / 100) AS total
            FROM sample_order_head h
            JOIN customer c ON c.customer_id = h.customer_id
            LEFT JOIN sample_order_item i ON i.sample_order_id = h.sample_order_id
            ORDER BY FIELD(h.status, 'making', 'approval', 'quote', 'draft', 'completed'),
                     h.target_completion_date IS NULL, h.target_completion_date, h.sample_order_id DESC
            LIMIT 200
        """)
        return cur.fetchall()
    finally:
        conn.close()


def update_sample_status(sample_order_id: int, status: str) -> None:
    conn = get_connection()
    if conn is None:
        raise RuntimeError("DB 連線失敗")
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE sample_order_head SET status=%s, updated_by=%s WHERE sample_order_id=%s",
            (status, _current_user_id(), int(sample_order_id)),
        )
        conn.commit()
        load_sample_orders.clear()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


st.markdown(
    """<style>
    .block-container { padding-top: .4rem; max-width: 100% !important; }
    .sample-card { border: 1px solid #d7e3f4; background: #f7fbff; border-radius: 12px; padding: 14px 16px; margin: 8px 0 15px; }
    .sample-title { color: #173b63; font-size: 1.15rem; font-weight: 750; margin-bottom: 2px; }
    .sample-muted { color: #64748b; font-size: .9rem; }
    .sample-total { font-size: 1.35rem; font-weight: 800; color: #0f4c5c; padding-top: .2rem; }
    </style>""",
    unsafe_allow_html=True,
)

st.markdown(f"<div class='sample-title'>{t('SP01 樣品打樣與計價')}</div>", unsafe_allow_html=True)
st.caption(t("可建立樣品單；樣品不必先建立正式產品。收款樣品於 D02 出貨後會建立 AR，免收款樣品則不會。"))

def render_work_queue() -> None:
    """Render established sample orders before the new-order work area."""
    rows = load_sample_orders()
    pending_rows = [row for row in rows if row["status"] not in {"completed", "cancelled"}]
    today = date.today()
    due_today = sum(1 for row in pending_rows if row["target_completion_date"] == today)
    overdue = sum(1 for row in pending_rows if row["target_completion_date"] and row["target_completion_date"] < today)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric(t("目前待打樣"), len(pending_rows))
    a2.metric(t("今日到期"), due_today)
    a3.metric(t("逾期"), overdue)
    a4.metric(t("已完成／取消"), len(rows) - len(pending_rows))

    st.markdown(f"#### {t('待打樣清單')}")
    status_filter = st.multiselect(
        t("樣品狀態"),
        options=["draft", "quote", "approval", "making", "completed", "cancelled"],
        default=["draft", "quote", "approval", "making"],
        format_func=lambda x: t({"draft":"草稿", "quote":"待報價", "approval":"待客戶確認", "making":"打樣中", "completed":"已完成", "cancelled":"已完成／取消"}[x]),
    )
    display_rows = [row for row in rows if row["status"] in status_filter]
    queue_rows = [{
        "_sample_order_id": row["sample_order_id"],
        t("勾選"): False,
        t("樣品單號"): row["sample_order_code"],
        t("客戶名稱"): row["customer_name"],
        t("樣品名稱"): row["sample_name"],
        t("樣品數量"): f"{float(row['quantity'] or 0):g} {row['unit'] or ''}",
        t("樣品類別"): t("樣品單（要收款）") if row["sample_category"] == "receivable" else t("樣品單（不收款）"),
        t("樣品狀態"): t({"draft":"草稿", "quote":"待報價", "approval":"待客戶確認", "making":"打樣中", "completed":"已完成"}.get(row["status"], "已完成／取消")),
        t("預計完成"): str(row["target_completion_date"] or ""),
    } for row in display_rows]

    selected_row = None
    if queue_rows:
        edited_queue = st.data_editor(
            pd.DataFrame(queue_rows), hide_index=True, use_container_width=True,
            disabled=["_sample_order_id"] + [c for c in queue_rows[0] if c not in {t("勾選"), "_sample_order_id"}],
            column_config={"_sample_order_id": None, t("勾選"): st.column_config.CheckboxColumn(t("勾選"), default=False)},
            key="sp01_work_queue",
        )
        chosen = edited_queue[edited_queue[t("勾選")] == True]
        if len(chosen) > 0:
            selected_id = int(chosen.iloc[0]["_sample_order_id"])
            selected_row = next((row for row in display_rows if int(row["sample_order_id"]) == selected_id), None)
    else:
        st.info(t("尚無符合條件的樣品單。"))

    if not selected_row:
        st.caption(t("請勾選一筆樣品單以查看或處理明細。"))
        return

    st.divider()
    st.markdown(f"#### {t('樣品明細與進度')}：{selected_row['sample_order_code']}")
    d1, d2, d3, d4 = st.columns(4)
    d1.write(f"**{t('客戶名稱')}**  \n{selected_row['customer_name']}")
    d2.write(f"**{t('樣品名稱')}**  \n{selected_row['sample_name']}")
    d3.write(f"**{t('樣品數量')}**  \n{float(selected_row['quantity'] or 0):g} {selected_row['unit'] or ''}")
    d4.write(f"**{t('預計完成')}**  \n{selected_row['target_completion_date'] or ''}")
    st.write(f"**{t('需求')}**：{selected_row['specification'] or '—'}")
    st.write(f"**{t('材質')}**：{selected_row['material_structure'] or '—'}")
    status_options = ["draft", "quote", "approval", "making", "completed", "cancelled"]
    current_status = selected_row["status"] if selected_row["status"] in status_options else "draft"
    p1, p2 = st.columns([1.25, 4])
    with p1:
        next_status = st.selectbox(
            t("樣品狀態"), options=status_options, index=status_options.index(current_status),
            format_func=lambda x: t({"draft":"草稿", "quote":"待報價", "approval":"待客戶確認", "making":"打樣中", "completed":"已完成", "cancelled":"已完成／取消"}[x]),
            key=f"sp01_status_{selected_row['sample_order_id']}",
        )
    with p2:
        if st.button(t("更新狀態"), type="primary", key=f"sp01_update_{selected_row['sample_order_id']}"):
            try:
                update_sample_status(int(selected_row["sample_order_id"]), next_status)
                st.success(t("狀態已更新。"))
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


render_work_queue()

show_new_sample_form = st.toggle(t("顯示新增樣品表單"), value=False, key="sp01_show_new_sample_form")
if show_new_sample_form:
    customers = load_customers()
    if not customers:
        st.error(t("找不到客戶資料，無法建立樣品單。"))
        st.stop()
    customer_ids = [r[0] for r in customers]
    customer_labels = {r[0]: r[1] for r in customers}
    top1, top2, top3 = st.columns([1.65, 1.35, 1.15])
    with top1:
        sample_category = st.selectbox(t("樣品類別"), ["receivable", "non_receivable"], format_func=lambda x: t("樣品單（要收款）") if x == "receivable" else t("樣品單（不收款）"))
    with top2:
        st.text_input(t("收款設定"), value=t("會建立 AR") if sample_category == "receivable" else t("不建立 AR"), disabled=True)
    with top3:
        st.text_input(t("樣品單號（系統建立後產生）"), value="SP-DRAFT-0001", disabled=True)

    left, right = st.columns([1.45, 1])
    with left:
        st.markdown(f"#### {t('客戶與時程')}")
        c1, c2 = st.columns([1, 1])
        with c1:
            sample_customer_id = st.selectbox(t("客戶"), customer_ids, format_func=lambda x: customer_labels[int(x)])
        c3, c4 = st.columns(2)
        with c3:
            request_date = st.date_input(t("需求日期"), value=date.today())
        with c4:
            target_date = st.date_input(t("預計完成日"), value=date.today() + timedelta(days=7))

        st.markdown(f"#### {t('樣品規格')}")
        s1, s2 = st.columns([1.4, 1])
        with s1:
            sample_name = st.text_input(t("樣品名稱"), placeholder="Example: Honeycomb carton sample")
        with s2:
            customer_item_code = st.text_input(t("客戶料號（可空）"))
        specification = st.text_area(t("規格／需求說明"), placeholder="Length × Width × Height, printing, testing requirement, special notes...", height=92)
        s3, s4, s5 = st.columns([1.6, .7, .7])
        with s3:
            material_structure = st.text_input(t("材質與結構"), placeholder="Example: B-flute / 5-layer corrugated board")
        with s4:
            quantity = st.number_input(t("樣品數量"), min_value=1, value=10, step=1)
        with s5:
            unit = st.selectbox(t("單位"), ["PCS", "SET"], format_func=t)

    with right:
        st.markdown(f"#### {t('樣品計價')}")
        if sample_category == "non_receivable":
            currency, tax_rate, sample_fee, freight, other_charge = "VND", 0.0, 0.0, 0.0, 0.0
            st.info(t("樣品不收款，不顯示或儲存對外價格。"))
        else:
            p1, p2 = st.columns(2)
            with p1:
                currency = st.selectbox(t("幣別"), ["VND", "USD", "TWD"])
            with p2:
                tax_rate = st.number_input(t("稅率"), min_value=0.0, max_value=100.0, value=10.0, step=1.0)
            sample_fee = st.number_input(t("打樣費"), min_value=0.0, value=500000.0, step=10000.0)
            freight = st.number_input(t("運費"), min_value=0.0, value=50000.0, step=10000.0)
            other_charge = st.number_input(t("其他費用"), min_value=0.0, value=0.0, step=10000.0)
            subtotal = sample_fee + freight + other_charge
            total = subtotal * (1 + tax_rate / 100)
            st.markdown("<div class='sample-card'>", unsafe_allow_html=True)
            st.write(f"{t('未稅小計')}：{subtotal:,.0f} {currency}")
            st.markdown(f"<div class='sample-total'>{t('含稅總額')}：{total:,.0f} {currency}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"#### {t('備註與下一步')}")
    note = st.text_area(t("內部備註"), placeholder=t("樣品完成後可轉正式產品／客戶訂單"), height=72)
    b1, b2, b3, b4 = st.columns([1.25, 1.55, 1.4, 4.2])
    with b1:
        save_draft = st.button(t("儲存草稿"), use_container_width=True, key="sp01_preview_draft")
    with b2:
        save_quote = st.button(t("送交報價確認"), type="primary", use_container_width=True, key="sp01_preview_quote")
    with b3:
        st.button(t("轉成正式產品"), use_container_width=True, disabled=True, key="sp01_preview_convert")
    with b4:
        st.caption(t("樣品明細可先不建立正式產品；轉產品功能將於後續階段開放。"))
    if save_draft or save_quote:
        try:
            code = save_sample_order(
                customer_id=int(sample_customer_id), category=sample_category,
                status="draft" if save_draft else "quote",
                request_date=request_date, target_date=target_date, currency=currency,
                tax_rate=float(tax_rate), sample_fee=float(sample_fee), freight=float(freight),
                other_fee=float(other_charge), note=note, sample_name=sample_name,
                customer_item_code=customer_item_code, specification=specification,
                material_structure=material_structure, quantity=float(quantity), unit=unit,
            )
            load_sample_orders.clear()
            st.success(f"{t('已完成')}：{code}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
