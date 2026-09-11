# S01_material_stock_io.py
# 原料進出庫作業頁面（material_stock_io_head + material_stock_io_line）
#
# 需求重點（依 Cyrus 指示）：
# 1) 同一個入庫單號（doc_no）可新增多筆原料明細（line）。
# 2) 日期、入庫單號、採購單號(可空白)、工單號碼(可空白)、供應商、供應商送貨單號(可空白)、進出庫類型、備註
#    → 視為 Head 欄位，必須「確認」後鎖定不可改，並先暫存（同時建立 head 記錄）。
# 3) Head 確認後，使用者在下方操作 Line 欄位：原料名稱、數量、進貨重量、重量單位；按「新增紀錄」只新增 line。
# 4) 需有「完成作業」按鈕：解除 head 鎖定並清空狀態，入庫單號自動跳成新的。
# 5) UI 可略微調整，但原本功能（查詢/限制物料清單/PO 帶入供應商等）不可漏掉。

import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from compact_layout import apply_compact_layout

apply_compact_layout()
import streamlit as st

import auth
from splitter_component import apply_vertical_splitter
from db import get_connection


# ================== I18N Helper ==================
TRANSLATIONS = {
    "S01 進出庫紀錄": {"vi": "S01 Ghi nhận xuất nhập kho", "en": "S01 Stock In/Out Records"},
    "進出庫紀錄": {"vi": "Ghi nhận xuất nhập kho", "en": "Stock In/Out Records"},
    "起始日期": {"vi": "Ngày bắt đầu", "en": "Start Date"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "原料名稱（精準）": {"vi": "Tên nguyên liệu (chính xác)", "en": "Material Name (Exact)"},
    "進出庫類型": {"vi": "Loại xuất nhập kho", "en": "Stock I/O Type"},
    "原料名稱（關鍵字）": {"vi": "Tên nguyên liệu (từ khóa)", "en": "Material Name (Keyword)"},
    "顯示筆數": {"vi": "Số dòng hiển thị", "en": "Rows per page"},
    "上一頁": {"vi": "Trang trước", "en": "Previous Page"},
    "下一頁": {"vi": "Trang sau", "en": "Next Page"},
    "全部": {"vi": "Tất cả", "en": "All"},
    "入庫": {"vi": "Nhập kho", "en": "Stock In"},
    "出庫": {"vi": "Xuất kho", "en": "Stock Out"},
    "調整": {"vi": "Điều chỉnh", "en": "Adjustment"},
    "回收入庫": {"vi": "Nhập kho tái chế", "en": "Recycle In"},
    "進出庫紀錄（列表）": {"vi": "Ghi nhận xuất nhập kho (danh sách)", "en": "Stock I/O Records (List)"},
    "沒有符合條件的資料。": {"vi": "Không có dữ liệu phù hợp điều kiện.", "en": "No matching records found."},
    "選取": {"vi": "Chọn", "en": "Select"},
    "勾選要刪除的紀錄（以同一個 msioh_id 為單位）": {"vi": "Chọn các bản ghi cần xóa (theo cùng một msioh_id)", "en": "Select records to delete (grouped by the same msioh_id)"},
    "⚠️ 刪除將以同一個 `_msioh_id` 為單位：會連同該 Head 下所有 Line 一起刪除。": {"vi": "⚠️ Xóa sẽ theo cùng một `_msioh_id`: sẽ xóa luôn tất cả line dưới head đó.", "en": "⚠️ Deletion is by the same `_msioh_id`: all lines under that head will be deleted together."},
    "刪除": {"vi": "Xóa", "en": "Delete"},
    "請先勾選要刪除的資料。": {"vi": "Vui lòng chọn dữ liệu cần xóa trước.", "en": "Please select records to delete first."},
    "一次只能勾選一張入庫單刪除，請取消其他勾選。": {"vi": "Mỗi lần chỉ được chọn một phiếu nhập để xóa, vui lòng bỏ chọn các phiếu khác.", "en": "You can only select one receiving record to delete at a time. Please uncheck the others."},
    "刪除確認": {"vi": "Xác nhận xóa", "en": "Delete Confirmation"},
    "是否刪除以上資料？資料刪除後無法回復。": {"vi": "Bạn có muốn xóa các dữ liệu trên không? Dữ liệu sau khi xóa sẽ không thể khôi phục.", "en": "Delete the above records? This action cannot be undone."},
    "你將刪除以下送貨單號（資料刪除後無法回復）：": {"vi": "Bạn sẽ xóa các số phiếu giao hàng sau (không thể khôi phục sau khi xóa):", "en": "You are about to delete the following delivery numbers (cannot be recovered):"},
    "確認": {"vi": "Xác nhận", "en": "Confirm"},
    "取消": {"vi": "Hủy", "en": "Cancel"},
    "刪除完成。": {"vi": "Đã xóa xong.", "en": "Deletion completed."},
    "新增紀錄": {"vi": "Thêm bản ghi", "en": "Add Record"},
    "重新讀取原料": {"vi": "Tải lại nguyên liệu", "en": "Reload Materials"},
    "重新整理": {"vi": "Làm mới", "en": "Refresh"},
    "採購單號": {"vi": "Số đơn mua hàng", "en": "PO Number"},
    "供應商送貨單號": {"vi": "Số phiếu giao hàng NCC", "en": "Supplier Delivery No."},
    "工單號碼": {"vi": "Mã lệnh sản xuất", "en": "Work Order No."},
    "物料名稱": {"vi": "Tên vật liệu", "en": "Material Name"},
    "數量(PCS)": {"vi": "Số lượng (PCS)", "en": "Quantity (PCS)"},
    "g": {"vi": "g", "en": "g"},
    "建檔人": {"vi": "Người tạo", "en": "Created By"},
    "期間": {"vi": "Kỳ", "en": "Period"},
    "時間": {"vi": "Thời gian", "en": "Time"},
    "條碼掃描": {"vi": "Quét mã vạch", "en": "Barcode Scan"},
    "掃描或輸入條碼": {"vi": "Quét hoặc nhập mã vạch", "en": "Scan or enter barcode"},
    "找不到符合目前供應商/採購單條件的原料條碼：": {"vi": "Không tìm thấy mã vạch nguyên liệu phù hợp với NCC/PO hiện tại: ", "en": "No material barcode matches the current supplier/PO: "},
    "已掃描帶入：": {"vi": "Đã quét và đưa vào: ", "en": "Scanned and loaded: "},
    "出入庫基本資料": {"vi": "Thông tin cơ bản xuất nhập kho", "en": "Stock I/O Basic Information"},
    "日期": {"vi": "Ngày", "en": "Date"},
    "入庫單號": {"vi": "Số phiếu nhập kho", "en": "Receiving No."},
    "採購單號（可空白）": {"vi": "Số đơn mua hàng (có thể để trống)", "en": "PO Number (Optional)"},
    "工單號碼（可空白）": {"vi": "Mã lệnh sản xuất (có thể để trống)", "en": "Work Order No. (Optional)"},
    "供應商": {"vi": "Nhà cung cấp", "en": "Supplier"},
    "供應商送貨單號（可空白）": {"vi": "Số phiếu giao hàng NCC (có thể để trống)", "en": "Supplier Delivery No. (Optional)"},
    "備註": {"vi": "Ghi chú", "en": "Remarks"},
    "操作人員": {"vi": "Nhân viên thao tác", "en": "Operator"},
    "建檔人員": {"vi": "Người lập hồ sơ", "en": "Created By"},
    "※未來完成權限後，將依登入帳號自動帶入": {"vi": "※ Sau khi hoàn thiện quyền hạn, hệ thống sẽ tự động lấy theo tài khoản đăng nhập", "en": "※ Once permissions are completed, this will auto-fill from the login account"},
    "確認（鎖定主表）": {"vi": "Xác nhận (khóa biểu đầu)", "en": "Confirm (Lock Head)"},
    "完成作業（解除鎖定）": {"vi": "Hoàn tất tác vụ (mở khóa)", "en": "Finish (Unlock)"},
    "請先選擇供應商。": {"vi": "Vui lòng chọn nhà cung cấp trước.", "en": "Please select a supplier first."},
    "請先選擇操作人員。": {"vi": "Vui lòng chọn nhân viên thao tác trước.", "en": "Please select an operator first."},
    "採購單號不存在（外鍵指向 order_head.order_id）。請確認採購單號或留空。": {"vi": "Số đơn mua hàng không tồn tại (khóa ngoại trỏ đến order_head.order_id). Vui lòng kiểm tra lại hoặc để trống.", "en": "PO number does not exist (foreign key to order_head.order_id). Please verify it or leave it blank."},
    "主表已確認並鎖定。現在可在下方新增明細。": {"vi": "Biểu đầu đã được xác nhận và khóa. Bây giờ bạn có thể thêm chi tiết bên dưới.", "en": "Head record confirmed and locked. You can add lines below now."},
    "主表建立失敗：": {"vi": "Tạo biểu đầu thất bại: ", "en": "Head creation failed: "},
    "已完成作業並解除鎖定。可開始下一張單。": {"vi": "Đã hoàn tất và mở khóa. Có thể bắt đầu chứng từ mới.", "en": "Finished and unlocked. You can start the next document now."},
    "出入庫明細": {"vi": "Chi tiết xuất nhập kho", "en": "Stock I/O Lines"},
    "請先在上方按「確認（鎖定主表）」建立主表後，才能新增明細。": {"vi": "Vui lòng nhấn \"Xác nhận (khóa biểu đầu)\" ở phía trên để tạo biểu đầu trước rồi mới thêm chi tiết.", "en": "Please click \"Confirm (Lock Head)\" above to create the head record before adding lines."},
    "原料名稱": {"vi": "Tên nguyên liệu", "en": "Material Name"},
    "規格": {"vi": "Quy cách", "en": "Specification"},
    "(無可用品項)": {"vi": "(Không có mặt hàng khả dụng)", "en": "(No available items)"},
    "單價": {"vi": "Đơn giá", "en": "Unit Price"},
    "數量": {"vi": "Số lượng", "en": "Quantity"},
    "進貨重量": {"vi": "Trọng lượng nhập", "en": "Incoming Weight"},
    "小計": {"vi": "Thành tiền", "en": "Subtotal"},
    "重量單位": {"vi": "Đơn vị trọng lượng", "en": "Weight Unit"},
    "新增紀錄（新增明細）": {"vi": "Thêm bản ghi (thêm chi tiết)", "en": "Add Record (Add Line)"},
    "目前條件下沒有可選的原料品項。請檢查採購單號/供應商是否選錯。": {"vi": "Hiện không có nguyên liệu nào có thể chọn. Vui lòng kiểm tra lại số đơn mua hàng / nhà cung cấp.", "en": "No material items are available under current conditions. Please check the PO number / supplier."},
    "主表狀態遺失（msioh_id）。請按「完成作業」後重新建立。": {"vi": "Trạng thái biểu đầu bị mất (msioh_id). Vui lòng nhấn \"Hoàn tất tác vụ\" rồi tạo lại.", "en": "Head state lost (msioh_id). Please click \"Finish\" and recreate it."},
    "請輸入數量，數量不可為 0。": {"vi": "Vui lòng nhập số lượng, số lượng không được bằng 0.", "en": "Please enter a quantity. Quantity cannot be 0."},
    "請輸入進貨重量，數量不可為 0。": {"vi": "Vui lòng nhập trọng lượng nhập, số lượng không được bằng 0.", "en": "Please enter incoming weight. Quantity cannot be 0."},
    "請輸入數量或進貨重量，數量不可為 0。": {"vi": "Vui lòng nhập số lượng hoặc trọng lượng nhập, không được bằng 0.", "en": "Please enter quantity or incoming weight. Quantity cannot be 0."},
    "明細新增成功。": {"vi": "Đã thêm chi tiết thành công.", "en": "Line added successfully."},
    "明細寫入失敗：": {"vi": "Ghi chi tiết thất bại: ", "en": "Line insert failed: "},
    "請先選擇供應商。": {"vi": "Vui lòng chọn nhà cung cấp trước.", "en": "Please select a supplier first."},
    "(未選)": {"vi": "(Chưa chọn)", "en": "(Not Selected)"},
    "請檢查採購單號/供應商是否選錯。": {"vi": "Vui lòng kiểm tra lại số đơn mua hàng / nhà cung cấp.", "en": "Please check whether the PO number / supplier is incorrect."},
    "⚠️ 本次入庫後將超收：訂購 ": {"vi": "⚠️ Sau lần nhập này sẽ vượt số lượng đặt: Đặt ", "en": "⚠️ This receipt will exceed the ordered quantity: Ordered "},
    "已入庫 ": {"vi": "Đã nhập ", "en": "Already received "},
    "本次新增 ": {"vi": "Lần này thêm ", "en": "This time adding "},
    "累計將達 ": {"vi": "Tổng cộng sẽ thành ", "en": "Total will become "},
    "超出 ": {"vi": "Vượt ", "en": "Exceeds "},
}
def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    return lang if lang in {"zh", "vi", "en"} else "zh"

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)


def _translate_stock_io_table_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Translate S01 list-table headers and simple status/type values for display only."""
    if df is None or df.empty:
        return df

    out = df.copy()

    # Translate IO type values before renaming headers.
    if "進出庫類型" in out.columns:
        out["進出庫類型"] = out["進出庫類型"].map(lambda v: _t(str(v)) if v is not None else v)

    rename_map = {
        "_選取": _t("選取"),
        "日期": _t("日期"),
        "入庫單號": _t("入庫單號"),
        "採購單號": _t("採購單號"),
        "供應商送貨單號": _t("供應商送貨單號"),
        "工單號碼": _t("工單號碼"),
        "供應商": _t("供應商"),
        "物料名稱": _t("物料名稱"),
        "數量(PCS)": _t("數量(PCS)"),
        "進貨重量": _t("進貨重量"),
        "重量單位": _t("重量單位"),
        "g": _t("g"),
        "操作人員": _t("操作人員"),
        "建檔人": _t("建檔人"),
        "期間": _t("期間"),
        "備註": _t("備註"),
        "進出庫類型": _t("進出庫類型"),
        "時間": _t("時間"),
    }
    rename_map = {k: v for k, v in rename_map.items() if k in out.columns}
    out = out.rename(columns=rename_map)

    # PyArrow / Streamlit cannot display duplicate column names. Keep first if translation collides.
    if out.columns.duplicated().any():
        out = out.loc[:, ~out.columns.duplicated()].copy()
    return out


# ================== 進出庫類型對照 ==================
IO_LABEL_TO_CODE = {
    "入庫": "IN",
    "出庫": "OUT",
    "調整": "ADJUST",
    "回收入庫": "RECYCLE",
}
IO_CODE_TO_LABEL = {v: k for k, v in IO_LABEL_TO_CODE.items()}


def resolve_io_type_code(value: Optional[str], default: str = "IN") -> str:
    """Accept zh labels, translated labels, or raw codes and return stable code."""
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    if s in IO_CODE_TO_LABEL:
        return s
    if s in IO_LABEL_TO_CODE:
        return IO_LABEL_TO_CODE[s]
    for zh_label, code in IO_LABEL_TO_CODE.items():
        if _t(zh_label) == s:
            return code
    return default


# doc_no 前綴（你可以自行調整）
DOC_PREFIX_BY_TYPE = {
    "IN": "RC",       # receiving
    "OUT": "IS",      # issue
    "ADJUST": "AD",   # adjust
    "RECYCLE": "RE",  # recycle
}

TABLE_STOCK_IO_H = "material_stock_io_head"
TABLE_STOCK_IO_L = "material_stock_io_line"
TABLE_MATERIAL = "material"
TABLE_STUFF = "stuff"
TABLE_USER = "user"  # MySQL 保留字，SQL 用反引號
TABLE_SUPPLIER = "supplier"


# ================== Page config ==================

# ================== Permission ==================
PAGE_KEY = "S01_material_stock_io"
auth.require_read(PAGE_KEY)



# ================== DB Helper ==================
def fetch_df(sql: str, params: Any = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def execute_sql(conn, sql: str, params: Optional[Iterable[Any]] = None) -> None:
    cur = conn.cursor()
    cur.execute(sql, params or ())
    cur.close()


def execute_sql_return_id(conn, sql: str, params: Optional[Iterable[Any]] = None) -> int:
    cur = conn.cursor()
    cur.execute(sql, params or ())
    last_id = cur.lastrowid
    cur.close()
    return int(last_id)


def _make_in_clause(values: List[int]) -> Tuple[str, Tuple[Any, ...]]:
    """Return (placeholders_sql, params_tuple) for an IN (...) clause."""
    if not values:
        return "(NULL)", tuple()
    placeholders = ",".join(["%s"] * len(values))
    return f"({placeholders})", tuple(values)


def hard_delete_material_stock_io(msioh_ids: List[int]) -> None:
    auth.require_delete(PAGE_KEY)
    """
    依 Cyrus 指示：硬刪除（抹除）原料進出庫與其衍生 AP 資料。

    會刪除：
      1) ap_resource（AP 明細；trigger 由 material_stock_io_line 產生）
      2) accounts_payable_head（AP 主檔；trigger 由 material_stock_io_head 產生）
      3) material_stock_io_line
      4) material_stock_io_head

    安全規則：
      - 只要關聯 AP 已有任何有效付款紀錄，或 AP 狀態已經是 paid / partial，
        就禁止刪除 S01 與 AP01，避免已付款資料被一起抹除。

    對應規則：
      accounts_payable_head.reference_receipts = 'delivery'
      accounts_payable_head.delivery_no = material_stock_io_head.doc_no
      accounts_payable_head.supplier_id = material_stock_io_head.supplier_id

    注意：這是「硬刪除」，不是作廢/沖銷。測試階段可以用；正式上線後建議改成 void + audit log。
    """
    if not msioh_ids:
        return

    normalized_ids = sorted({int(x) for x in msioh_ids if x is not None})
    if not normalized_ids:
        return
    if len(normalized_ids) > 1:
        raise ValueError("一次只能刪除一張入庫單，請取消其他勾選後再刪除。")

    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor()

        in_sql, in_params = _make_in_clause(normalized_ids)

        # 1) 先抓出本次要刪的 S01 head，並鎖住，避免刪除過程中又被補 line / 補 AP。
        cur.execute(
            f"""
            SELECT msioh_id, doc_no, supplier_id
            FROM material_stock_io_head
            WHERE msioh_id IN {in_sql}
            FOR UPDATE
            """,
            in_params,
        )
        rows = cur.fetchall()
        headers = [{"msioh_id": int(r[0]), "doc_no": r[1], "supplier_id": r[2]} for r in rows]

        # 2) 找出 trigger 依入庫單產生的 AP head。
        #    加 COLLATE 是為了避開不同欄位/參數 collation 不一致造成的 1267 錯誤。
        ap_ids: List[int] = []
        for h in headers:
            doc_no = h.get("doc_no")
            supplier_id = h.get("supplier_id")
            if not doc_no or not supplier_id:
                continue

            cur.execute(
                """
                SELECT ap_id
                FROM accounts_payable_head
                WHERE reference_receipts = 'delivery'
                  AND supplier_id = %s
                  AND delivery_no COLLATE utf8mb4_unicode_ci = CAST(%s AS CHAR) COLLATE utf8mb4_unicode_ci
                """,
                (int(supplier_id), str(doc_no)),
            )
            ap_ids.extend([int(r[0]) for r in cur.fetchall()])
        ap_ids = sorted(set(ap_ids))

        # 3) 安全鎖：只要關聯 AP 已經有有效付款紀錄，就禁止刪除。
        #    這是為了避免「S01 一刪，AP01 與付款紀錄也被硬刪」造成財務帳消失。
        if ap_ids:
            ap_in_sql, ap_in_params = _make_in_clause(ap_ids)

            # 鎖住 AP 主表，避免刪除檢查與實際刪除之間，另一台電腦又新增付款。
            cur.execute(
                f"SELECT ap_id FROM accounts_payable_head WHERE ap_id IN {ap_in_sql} FOR UPDATE",
                ap_in_params,
            )
            cur.fetchall()

            cur.execute(
                f"""
                SELECT
                    h.ap_id,
                    COALESCE(h.ap_code, CONCAT('AP#', h.ap_id)) AS ap_code,
                    COALESCE(h.delivery_no, '') AS delivery_no,
                    COALESCE(h.status, '') AS ap_status,
                    COALESCE(SUM(
                        CASE
                            WHEN COALESCE(p.status, 'posted') <> 'void'
                            THEN COALESCE(p.payment_amount, 0)
                            ELSE 0
                        END
                    ), 0) AS paid_amount,
                    COUNT(
                        CASE
                            WHEN COALESCE(p.status, 'posted') <> 'void'
                              AND COALESCE(p.payment_amount, 0) > 0
                            THEN 1
                        END
                    ) AS payment_count
                FROM accounts_payable_head h
                LEFT JOIN accounts_payable_payment p
                       ON p.ap_id = h.ap_id
                WHERE h.ap_id IN {ap_in_sql}
                GROUP BY h.ap_id, h.ap_code, h.delivery_no, h.status
                HAVING paid_amount > 0
                    OR payment_count > 0
                    OR LOWER(COALESCE(h.status, '')) IN ('paid', 'partial')
                """,
                ap_in_params,
            )
            protected_rows = cur.fetchall()

            if protected_rows:
                protected_info = []
                for r in protected_rows:
                    ap_code = str(r[1] or f"AP#{r[0]}")
                    delivery_no = str(r[2] or "")
                    ap_status = str(r[3] or "")
                    try:
                        paid_amount = float(r[4] or 0)
                    except Exception:
                        paid_amount = 0.0
                    protected_info.append(
                        f"{ap_code} / 入庫單號：{delivery_no} / 狀態：{ap_status or '未知'} / 已付：{paid_amount:,.2f}"
                    )

                raise ValueError(
                    "此入庫單已經產生付款紀錄，S01 與 AP01 不可刪除。"
                    "若真的要更正，請先走付款作廢/沖銷流程，再由管理者處理。\n"
                    + "\n".join(protected_info)
                )

            # 只有「完全沒有有效付款」的 AP，才允許跟著 S01 一起硬刪。
            cur.execute(f"DELETE FROM accounts_payable_payment WHERE ap_id IN {ap_in_sql}", ap_in_params)
            cur.execute(f"DELETE FROM ap_resource WHERE ap_id IN {ap_in_sql}", ap_in_params)
            cur.execute(f"DELETE FROM accounts_payable_head WHERE ap_id IN {ap_in_sql}", ap_in_params)

        # 4) 再刪 S01 line/head。line 的 FK 是 ON DELETE RESTRICT，所以 line 必須先刪。
        cur.execute(f"DELETE FROM material_stock_io_line WHERE msioh_id IN {in_sql}", in_params)
        cur.execute(f"DELETE FROM material_stock_io_head WHERE msioh_id IN {in_sql}", in_params)

        cur.close()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ================== 型別轉換（解 numpy.int64 的雷） ==================
def to_py_int(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if hasattr(v, "item"):  # numpy scalar
        v = v.item()
    if v == "":
        return None
    return int(v)


def to_py_float(v):
    if v is None:
        return None
    if hasattr(v, "item"):
        v = v.item()
    if v == "":
        return None
    return float(v)


# ================== 下拉選單資料 ==================
@st.cache_data(ttl=10, show_spinner=False)
def get_material_df() -> pd.DataFrame:
    sql = f"""
        SELECT 
            m.item_id,
            m.item_code,
            m.item_name,
            m.specification,
            m.material_barcode,
            m.supplier_id,
            m.TrackingMod,
            (
                SELECT mup.material_unit_price
                FROM `material_unit_price` mup
                WHERE mup.material_item_id = m.item_id
                  AND (mup.current_flag = 1 OR mup.valid_to IS NULL)
                ORDER BY mup.valid_from DESC, mup.material_price_id DESC
                LIMIT 1
            ) AS material_unit_price
        FROM `{TABLE_MATERIAL}` m
        ORDER BY m.item_name
    """
    df = fetch_df(sql)
    if not df.empty:
        df["item_id"] = df["item_id"].astype(int)
        if "material_unit_price" in df.columns:
            df["material_unit_price"] = pd.to_numeric(df["material_unit_price"], errors="coerce").fillna(0.0)
    return df


@st.cache_data(show_spinner=False)
def get_stuff_options() -> Dict[str, int]:
    sql = f"SELECT stuff_id, stuff_name FROM `{TABLE_STUFF}` ORDER BY stuff_name"
    df = fetch_df(sql)
    options: Dict[str, int] = {}
    for _, r in df.iterrows():
        options[str(r["stuff_name"])] = int(r["stuff_id"])
    return options


@st.cache_data(show_spinner=False)
def get_user_options() -> Dict[str, int]:
    sql = f"""
        SELECT
            u.user_id,
            COALESCE(s.stuff_name, CONCAT('User#', u.user_id)) AS display_name
        FROM `{TABLE_USER}` u
        LEFT JOIN `{TABLE_STUFF}` s
               ON u.stuff_id = s.stuff_id
        ORDER BY display_name
    """
    df = fetch_df(sql)
    options: Dict[str, int] = {}
    for _, r in df.iterrows():
        options[str(r["display_name"])] = int(r["user_id"])
    return options


@st.cache_data(show_spinner=False)
def get_supplier_options() -> Dict[str, int]:
    sql = f"""
        SELECT supplier_id,
               supplier_shortname,
               supplier_name
        FROM `{TABLE_SUPPLIER}`
        WHERE is_active = 1
        ORDER BY supplier_shortname, supplier_name
    """
    df = fetch_df(sql)
    options: Dict[str, int] = {}
    for _, r in df.iterrows():
        shortname = str(r.get("supplier_shortname") or "").strip()
        name = str(r.get("supplier_name") or "").strip()
        label = shortname if not name else f"{shortname}｜{name}"
        options[label] = int(r["supplier_id"])
    return options


# ================== PO / Order context（保留原本功能） ==================
def _table_exists(table_name: str) -> bool:
    try:
        df = fetch_df(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name=%s LIMIT 1",
            (table_name,),
        )
        return not df.empty
    except Exception:
        return False


def _resolve_order_item_table() -> str:
    for t in ("ordo_item", "order_item"):
        if _table_exists(t):
            return t
    return "order_item"


def fetch_po_context(order_num: str) -> Optional[Dict[str, Any]]:
    order_num = (order_num or "").strip()
    if not order_num:
        return None

    df_head = fetch_df(
        "SELECT order_id, supplier_id FROM order_head WHERE order_num=%s LIMIT 1",
        (order_num,),
    )
    if df_head.empty:
        return None

    order_id = int(df_head.loc[0, "order_id"])
    supplier_id = df_head.loc[0, "supplier_id"]
    supplier_id = int(supplier_id) if supplier_id is not None and str(supplier_id) != "nan" else None

    item_table = _resolve_order_item_table()
    try:
        df_items = fetch_df(
            f"SELECT material_id, material_code, material_name, price_unit AS unit_price, qty_ordered FROM `{item_table}` WHERE order_id=%s ORDER BY line_no, material_id",
            (order_id,),
        )
    except Exception:
        df_items = fetch_df(
            f"SELECT material_id, material_code, material_name, price_unit AS unit_price, qty_ordered FROM `{item_table}` WHERE order_id=%s ORDER BY material_id",
            (order_id,),
        )

    if not df_items.empty:
        df_items = df_items.drop_duplicates(subset=["material_id"]).copy()
        df_items["material_id"] = df_items["material_id"].astype(int)
        if "unit_price" in df_items.columns:
            df_items["unit_price"] = pd.to_numeric(df_items["unit_price"], errors="coerce").fillna(0.0)
        if "qty_ordered" in df_items.columns:
            df_items["qty_ordered"] = pd.to_numeric(df_items["qty_ordered"], errors="coerce").fillna(0.0)

    return {"order_id": order_id, "supplier_id": supplier_id, "items": df_items}


def normalize_barcode_text(value: Optional[str]) -> str:
    """Normalize scanner input for matching material_barcode / item_code."""
    if value is None:
        return ""
    s = str(value).strip()
    # Barcode scanners often append Enter/Tab or keep Code39 * guards.
    s = s.replace("\r", "").replace("\n", "").replace("\t", "").strip()
    return s


def _barcode_candidates(value: Optional[str]) -> List[str]:
    raw = normalize_barcode_text(value)
    if not raw:
        return []
    candidates = [raw]
    stripped = raw.strip("*")
    if stripped and stripped not in candidates:
        candidates.append(stripped)
    guarded = f"*{stripped}*" if stripped else ""
    if guarded and guarded not in candidates:
        candidates.append(guarded)
    return candidates


def resolve_scanned_material_id(scan_value: Optional[str], material_df: pd.DataFrame, allowed_item_ids: Optional[List[int]] = None) -> Optional[int]:
    """Resolve barcode scanner input to material.item_id.

    Matching order:
      1) material_barcode
      2) item_code
      3) numeric item_id

    If allowed_item_ids is supplied, the matched item must be in the current supplier / PO filtered list.
    """
    if material_df is None or material_df.empty:
        return None

    candidates = _barcode_candidates(scan_value)
    if not candidates:
        return None

    allowed_set = set(int(x) for x in allowed_item_ids) if allowed_item_ids is not None else None

    df = material_df.copy()
    if allowed_set is not None:
        df = df[df["item_id"].astype(int).isin(allowed_set)]
    if df.empty:
        return None

    norm_candidates = {c.strip().upper() for c in candidates if c is not None}

    for col in ("material_barcode", "item_code"):
        if col not in df.columns:
            continue
        hit = df[df[col].fillna("").astype(str).str.strip().str.upper().isin(norm_candidates)]
        if not hit.empty:
            return int(hit.iloc[0]["item_id"])

    # Last fallback: user/scanner may provide item_id directly.
    for c in candidates:
        if str(c).isdigit():
            item_id = int(c)
            if allowed_set is None or item_id in allowed_set:
                hit = df[df["item_id"].astype(int) == item_id]
                if not hit.empty:
                    return item_id

    return None


def get_unit_price_for_order_item(order_id: Optional[int], item_id: Optional[int]) -> float:
    """Return the hidden unit price written to material_stock_io_line.unit_price.

    Rule per Cyrus / Shambhala:
      1) If the receipt is based on a PO, use the PO line price_unit as the frozen price.
      2) If the PO line has no price, fall back to latest material_unit_price.material_unit_price.

    Note: this value is intentionally NOT displayed on S01, but is still written to DB
    for AP/accounting calculations.
    """
    if not item_id:
        return 0.0

    if order_id:
        try:
            item_table = _resolve_order_item_table()
            df_order_price = fetch_df(
                f"""
                SELECT price_unit
                FROM `{item_table}`
                WHERE order_id = %s
                  AND material_id = %s
                  AND COALESCE(price_unit, 0) <> 0
                ORDER BY line_no, material_id
                LIMIT 1
                """,
                (int(order_id), int(item_id)),
            )
            if not df_order_price.empty:
                return float(df_order_price.iloc[0]["price_unit"] or 0.0)
        except Exception:
            # Do not block S01 if an old DB/schema has unexpected differences; fallback below.
            pass

    try:
        df_mup = fetch_df(
            """
            SELECT material_unit_price
            FROM `material_unit_price`
            WHERE material_item_id = %s
              AND (current_flag = 1 OR valid_to IS NULL)
            ORDER BY valid_from DESC, material_price_id DESC
            LIMIT 1
            """,
            (int(item_id),),
        )
        if not df_mup.empty:
            return float(df_mup.iloc[0]["material_unit_price"] or 0.0)
    except Exception:
        pass

    return 0.0


def get_material_display_info(item_id: Optional[int], material_df: pd.DataFrame) -> str:
    if not item_id or material_df is None or material_df.empty:
        return ""
    try:
        r = material_df[material_df["item_id"].astype(int) == int(item_id)].iloc[0]
    except Exception:
        return ""
    item_code = str(r.get("item_code") or "").strip()
    item_name = str(r.get("item_name") or "").strip()
    barcode = str(r.get("material_barcode") or "").strip()
    specification = str(r.get("specification") or "").strip()
    tracking = str(r.get("TrackingMod") or "").strip()
    parts = []
    if item_code:
        parts.append(f"品號：{item_code}")
    if item_name:
        parts.append(f"品名：{item_name}")
    if barcode:
        parts.append(f"條碼：{barcode}")
    if specification:
        parts.append(f"規格：{specification}")
    if tracking:
        parts.append(f"追蹤：{tracking}")
    return "　｜　".join(parts)


def get_po_over_receipt_warning(order_id: Optional[int], item_id: Optional[int], incoming_qty: Optional[float]) -> Optional[str]:
    """
    只做警告，不阻擋寫入。
    以 PO + material 聚合比對：
    - 訂購量：order_item.qty_ordered
    - 已入庫量：material_stock_io_head/material_stock_io_line 的累計 IN 數量
    與目前 PO 狀態邏輯一致：先不管 head.status。
    """
    if not order_id or not item_id or incoming_qty is None:
        return None

    try:
        incoming_qty = float(incoming_qty)
    except Exception:
        return None

    if incoming_qty <= 0:
        return None

    item_table = _resolve_order_item_table()
    df_chk = fetch_df(
        f"""
        SELECT
            COALESCE(oi.qty_ordered, 0) AS qty_ordered,
            COALESCE(rcv.qty_received, 0) AS qty_received,
            COALESCE(m.TrackingMod, 'kg') AS tracking_mod,
            COALESCE(oi.unit, '') AS po_unit
        FROM
            (
                SELECT
                    material_id,
                    SUM(qty_ordered) AS qty_ordered,
                    MAX(unit) AS unit
                FROM `{item_table}`
                WHERE order_id=%s AND material_id=%s
                GROUP BY material_id
            ) oi
        LEFT JOIN
            (
                SELECT
                    l.item_id AS material_id,
                    SUM(
                        CASE
                            WHEN m2.TrackingMod = 'PCS' THEN COALESCE(l.qty_pcs, 0)
                            ELSE COALESCE(l.qty_raw, 0)
                        END
                    ) AS qty_received
                FROM `{TABLE_STOCK_IO_H}` h
                JOIN `{TABLE_STOCK_IO_L}` l
                  ON h.msioh_id = l.msioh_id
                JOIN `{TABLE_MATERIAL}` m2
                  ON m2.item_id = l.item_id
                WHERE h.order_id=%s
                  AND h.io_type='IN'
                  AND l.item_id=%s
                GROUP BY l.item_id
            ) rcv
          ON oi.material_id = rcv.material_id
        LEFT JOIN `{TABLE_MATERIAL}` m
          ON m.item_id = oi.material_id
        """,
        (int(order_id), int(item_id), int(order_id), int(item_id)),
    )

    if df_chk.empty:
        return None

    qty_ordered = to_py_float(df_chk.iloc[0].get("qty_ordered")) or 0.0
    qty_received = to_py_float(df_chk.iloc[0].get("qty_received")) or 0.0
    tracking_mod = str(df_chk.iloc[0].get("tracking_mod") or "").strip().upper()
    po_unit = str(df_chk.iloc[0].get("po_unit") or "").strip()
    unit_label = "PCS" if tracking_mod == "PCS" else (po_unit or "kg")

    total_after = qty_received + incoming_qty
    over_qty = total_after - qty_ordered

    if over_qty > 0:
        return (
            f"⚠️ 本次入庫後將超收：訂購 {qty_ordered:g} {unit_label}，"
            f"已入庫 {qty_received:g} {unit_label}，"
            f"本次新增 {incoming_qty:g} {unit_label}，"
            f"累計將達 {total_after:g} {unit_label}，超出 {over_qty:g} {unit_label}。"
        )
    return None


# ================== 單號產生 ==================
def _generate_doc_no(io_date: datetime.date, io_type_code: str) -> str:
    prefix2 = DOC_PREFIX_BY_TYPE.get(io_type_code, "IO")
    prefix = f"{prefix2}{io_date.strftime('%y%m')}"  # e.g. RC2602
    sql = f"""
        SELECT MAX(doc_no) AS max_no
        FROM `{TABLE_STOCK_IO_H}`
        WHERE doc_no LIKE %(prefix)s
    """
    df = fetch_df(sql, {"prefix": prefix + "%"})
    max_no = None
    if not df.empty:
        max_no = df.iloc[0].get("max_no")

    last_seq = 0
    if isinstance(max_no, str) and max_no.startswith(prefix):
        suffix = max_no.replace(prefix, "", 1)
        if suffix.isdigit():
            last_seq = int(suffix)

    return f"{prefix}{(last_seq + 1):04d}"


def generate_material_receiving_number(io_date: datetime.date) -> str:
    return _generate_doc_no(io_date, "IN")


def _calc_qty_base(qty_raw: Optional[float], weight_unit: Optional[str], io_type_code: str) -> Tuple[Optional[float], Optional[float]]:
    """
    回傳 (factor_sn, qty_base)
    - qty_base 以 g 為基準
    - OUT 視為負數（維持「出庫扣庫」直覺）
    - ADJUST/RECYCLE：依你現場定義，這裡先視為正數（若未來要做「調整增/減」再擴充 UI）
    """
    if qty_raw is None:
        return None, None

    factor = None
    if weight_unit == "kg":
        factor = 1000.0
    elif weight_unit == "g":
        factor = 1.0
    else:
        return None, None

    sign = -1.0 if io_type_code == "OUT" else 1.0
    return factor, sign * float(qty_raw) * factor


# ================== 查詢列表（維持原列表欄位） ==================
def fetch_stock_io_view(
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    item_id: Optional[int],
    io_label: str,
    material_kw: str,
    limit_rows: int,
    offset_rows: int = 0,
) -> pd.DataFrame:
    conditions: List[str] = []
    params: Dict[str, Any] = {}

    if start_date:
        conditions.append("h.io_time >= %(start)s")
        params["start"] = datetime.datetime.combine(start_date, datetime.time.min)

    if end_date:
        conditions.append("h.io_time <= %(end)s")
        params["end"] = datetime.datetime.combine(end_date, datetime.time.max)

    if item_id:
        conditions.append("l.item_id = %(item_id)s")
        params["item_id"] = int(item_id)

    if io_label and io_label != "全部":
        conditions.append("h.io_type = %(io_type)s")
        params["io_type"] = resolve_io_type_code(io_label)

    material_kw = (material_kw or "").strip()
    if material_kw:
        conditions.append("m.item_name LIKE %(mkw)s")
        params["mkw"] = f"%{material_kw}%"

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # pagination
    params["limit"] = int(limit_rows)
    params["offset"] = int(offset_rows)

    sql = f"""
        SELECT
            h.msioh_id AS `_msioh_id`,
            DATE(h.io_time) AS `日期`,
            CASE WHEN h.io_type='IN' THEN COALESCE(h.doc_no,'') ELSE '' END AS `入庫單號`,
            oh.order_num AS `採購單號`,
            h.supplier_delivery_number AS `供應商送貨單號`,
            h.work_order_id AS `工單號碼`,
            s.supplier_shortname AS `供應商`,
            m.item_name AS `物料名稱`,
            h.io_type AS `_io_type_code`,
l.qty_pcs AS `數量(PCS)`,
            l.qty_raw AS `進貨重量`,
l.weight_unit AS `重量單位`,
            l.qty_base AS `g`,
            op.stuff_name AS `操作人員`,
            creator_stuff.stuff_name AS `建檔人`,
            h.period AS `期間`,
            h.note AS `備註`,
            h.io_time AS `時間`
        FROM `{TABLE_STOCK_IO_H}` h
        INNER JOIN `{TABLE_STOCK_IO_L}` l
                ON h.msioh_id = l.msioh_id
        LEFT JOIN `order_head` oh
               ON h.order_id = oh.order_id
        LEFT JOIN `{TABLE_MATERIAL}` m
               ON l.item_id = m.item_id
        LEFT JOIN `{TABLE_SUPPLIER}` s
               ON h.supplier_id = s.supplier_id
        LEFT JOIN `{TABLE_STUFF}` op
               ON h.operator = op.stuff_id
        LEFT JOIN `{TABLE_USER}` u
               ON h.created_by = u.user_id
        LEFT JOIN `{TABLE_STUFF}` creator_stuff
               ON u.stuff_id = creator_stuff.stuff_id
        {where_clause}
        ORDER BY h.io_time DESC, h.msioh_id DESC, l.line_no ASC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    df = fetch_df(sql, params)

    if not df.empty:
        df["進出庫類型"] = df["_io_type_code"].map(IO_CODE_TO_LABEL).fillna(df["_io_type_code"])
        df.drop(columns=["_io_type_code"], inplace=True)
        cols = [c for c in df.columns if c != "時間"] + ["時間"]
        df = df[cols]
        df = df.where(pd.notnull(df), None)

    return df


def count_stock_io_rows(
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    item_id: Optional[int],
    io_label: str,
    material_kw: str,
) -> int:
    """Count rows in the same result-set as fetch_stock_io_view (line-level rows)."""
    conditions: List[str] = []
    params: Dict[str, Any] = {}

    if start_date:
        conditions.append("h.io_time >= %(start)s")
        params["start"] = datetime.datetime.combine(start_date, datetime.time.min)

    if end_date:
        conditions.append("h.io_time <= %(end)s")
        params["end"] = datetime.datetime.combine(end_date, datetime.time.max)

    if item_id:
        conditions.append("l.item_id = %(item_id)s")
        params["item_id"] = int(item_id)

    if io_label and io_label != "全部":
        conditions.append("h.io_type = %(io_type)s")
        params["io_type"] = resolve_io_type_code(io_label)

    material_kw = (material_kw or "").strip()
    if material_kw:
        conditions.append("m.item_name LIKE %(mkw)s")
        params["mkw"] = f"%{material_kw}%"

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM `{TABLE_STOCK_IO_H}` h
        INNER JOIN `{TABLE_STOCK_IO_L}` l
                ON h.msioh_id = l.msioh_id
        LEFT JOIN `{TABLE_MATERIAL}` m
               ON l.item_id = m.item_id
        {where_clause}
    """
    df = fetch_df(sql, params)
    if df.empty:
        return 0
    return int(df.iloc[0]["cnt"])


# ================== Head / Line 寫入 ==================
def insert_head(
    io_date: datetime.date,
    io_type_code: str,
    order_id: Optional[int],
    work_order_id: Optional[int],
    supplier_id: int,
    supplier_delivery_number: Optional[str],
    note: Optional[str],
    operator_id: Optional[int],
    created_by_id: int,
) -> Tuple[int, str]:
    auth.require_edit(PAGE_KEY)
    """
    建立 head，回傳 (msioh_id, doc_no)
    - IN：doc_no 使用入庫單號規則（會顯示在 UI）
    - 非 IN：doc_no 仍會生成（DB NOT NULL），但 UI 不顯示
    """
    doc_no = generate_material_receiving_number(io_date) if io_type_code == "IN" else None
    io_dt = datetime.datetime.combine(io_date, datetime.datetime.now().time().replace(microsecond=0))
    period = io_dt.strftime("%Y%m")

    conn = get_connection()
    try:
        conn.start_transaction()
        sql_h = f"""
            INSERT INTO `{TABLE_STOCK_IO_H}` (
                doc_no, io_type, io_time,
                supplier_id, supplier_delivery_number,
                order_id, work_order_id,
                status, note, operator, period,
                created_by
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,'posted',%s,%s,%s,%s)
        """
        msioh_id = execute_sql_return_id(
            conn,
            sql_h,
            (
                doc_no,
                io_type_code,
                io_dt,
                supplier_id,
                supplier_delivery_number,
                order_id,
                work_order_id,
                note,
                operator_id,
                period,
                created_by_id,
            ),
        )
        conn.commit()
        return msioh_id, doc_no
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _next_line_no(msioh_id: int) -> int:
    df = fetch_df(
        f"SELECT COALESCE(MAX(line_no), 0) AS mx FROM `{TABLE_STOCK_IO_L}` WHERE msioh_id=%s",
        (msioh_id,),
    )
    mx = int(df.iloc[0]["mx"]) if not df.empty else 0
    return mx + 1


def insert_line(
    msioh_id: int,
    io_type_code: str,
    item_id: int,
    item_name: Optional[str],
    qty_pcs: Optional[float],
    qty_raw: Optional[float],
    unit_price: Optional[float],
    subtotal: Optional[float],
    weight_unit: Optional[str],
    note: Optional[str],
) -> None:
    auth.require_edit(PAGE_KEY)
    line_no = _next_line_no(msioh_id)
    factor_sn, qty_base = _calc_qty_base(qty_raw, weight_unit, io_type_code)

    conn = get_connection()
    try:
        conn.start_transaction()
        sql_l = f"""
            INSERT INTO `{TABLE_STOCK_IO_L}` (
                msioh_id, line_no,
                item_id, item_name,
                qty_raw, weight_unit, factor_sn, qty_base,
                qty_pcs,
                unit_price, subtotal,
                note
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        execute_sql(
            conn,
            sql_l,
            (
                int(msioh_id),
                int(line_no),
                int(item_id),
                item_name,
                qty_raw,
                weight_unit,
                factor_sn,
                qty_base,
                qty_pcs,
                unit_price,
                subtotal,
                (note or "")[:255] if note else None,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ================== Session state keys ==================
def _ensure_state():
    st.session_state.setdefault("head_locked", False)
    st.session_state.setdefault("current_msioh_id", None)
    st.session_state.setdefault("current_doc_no", "")
    st.session_state.setdefault("current_io_type_code", "IN")
    st.session_state.setdefault("reset_head_inputs", False)
    st.session_state.setdefault("reset_line_inputs", False)
    st.session_state.setdefault("unit_price_line", 0.0)
    st.session_state.setdefault("subtotal_line", 0.0)
    st.session_state.setdefault("weight_unit_label_line", "kg")
    st.session_state.setdefault("line_warning_msg", "")
    st.session_state.setdefault("material_barcode_scan", "")
    st.session_state.setdefault("barcode_scan_msg", "")
    st.session_state.setdefault("msio_table_editor_seed", 0)


def refresh_s01_master_table_state() -> None:
    """Clear cached dropdown data and reset the S01 master data_editor state."""
    # S01 master query itself reads DB directly, but the surrounding dropdowns and
    # Streamlit data_editor state can still hold old values after another page/session
    # changes stock records.  Clearing cache + changing the editor key makes refresh
    # deterministic.
    for cached_func in (get_material_df, get_stuff_options, get_user_options, get_supplier_options):
        try:
            cached_func.clear()
        except Exception:
            pass

    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.session_state["msio_table_editor_seed"] = int(st.session_state.get("msio_table_editor_seed", 0)) + 1
    st.session_state["msio_delete_selected_ids"] = []
    st.session_state["msio_show_delete_dialog"] = False


_ensure_state()


# ================== UI：查詢區（不動） ==================
st.header(_t("進出庫紀錄"))

# ---- 分頁控制（上一頁 / 顯示筆數 / 下一頁）----
st.session_state.setdefault("msio_page", 0)
st.session_state.setdefault("msio_filter_sig", None)

# 查詢條件 + 分頁控制：同一排、格子大小平均一點（依 Cyrus 指示）
# 最後加 spacer 欄吃掉多餘寬度，避免被拉得太寬
# ---- defaults for date filters & material exact dropdown (防止 NameError) ----
from datetime import date, timedelta

default_start = st.session_state.get("msio_default_start", date.today() - timedelta(days=30))
default_end = st.session_state.get("msio_default_end", date.today())

# material exact options
_material_df = get_material_df()
_material_labels: list[str] = ["全部"]
_material_label_to_id: dict[str, int] = {}

if not _material_df.empty and "item_id" in _material_df.columns and "item_name" in _material_df.columns:
    # 若品名重複，追加 item_id 以確保 label 唯一
    for _item_id, _item_name in _material_df[["item_id", "item_name"]].itertuples(index=False, name=None):
        _base = str(_item_name)
        _label = _base
        if _label in _material_label_to_id:
            _label = f"{_base} (#{int(_item_id)})"
        _material_labels.append(_label)
        _material_label_to_id[_label] = int(_item_id)

material_exact_options = _material_labels
material_exact_default_idx = 0
material_label_to_id = _material_label_to_id

# 給後面新增明細區共用，避免 material_df_all 未定義
material_df_all = _material_df.copy()

c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.35, 1.35, 1.9, 1.5, 2.25, 0.95, 0.95, 0.95], vertical_alignment="bottom")

with c1:
    start_date = st.date_input(_t("起始日期"), value=default_start, key="msio_start")
with c2:
    end_date = st.date_input(_t("結束日期"), value=default_end, key="msio_end")
with c3:
    material_exact_label = st.selectbox(_t("原料名稱（精準）"), options=material_exact_options, index=material_exact_default_idx, key="msio_item_exact")
with c4:
    io_label = st.selectbox(_t("進出庫類型"), options=["全部", "入庫", "出庫", "調整", "回收入庫"], index=0, key="msio_io_label", format_func=_t)
with c5:
    material_kw = st.text_input(_t("原料名稱（關鍵字）"), value="", key="msio_kw")

# 解析精準原料
selected_item_id = None
if material_exact_label and material_exact_label != "全部":
    selected_item_id = int(material_label_to_id.get(material_exact_label))

# page size / 分頁按鈕：由同列的 bottom alignment 對齊輸入框。
with c7:
    page_size = st.selectbox(_t("顯示筆數"), options=[10, 20, 30, 50, 100], index=1, key="msio_page_size", label_visibility="collapsed")

# filter signature -> 改條件就回到第 1 頁
filter_sig = (start_date, end_date, selected_item_id, io_label, material_kw, int(page_size))
if st.session_state.get("msio_filter_sig") != filter_sig:
    st.session_state["msio_filter_sig"] = filter_sig
    st.session_state["msio_page"] = 0

# 先算總筆數，確保上一頁/下一頁不會「莫名其妙永遠灰色」
try:
    total_rows = count_stock_io_rows(start_date, end_date, selected_item_id, io_label, material_kw)
except Exception:
    total_rows = 0

offset_rows = int(st.session_state["msio_page"]) * int(page_size)
has_prev = int(st.session_state["msio_page"]) > 0
has_next = (offset_rows + int(page_size)) < int(total_rows)

with c6:
    if st.button(_t("上一頁"), disabled=not has_prev, key="msio_prev", use_container_width=True):
        st.session_state["msio_page"] = max(0, int(st.session_state["msio_page"]) - 1)
        st.rerun()

with c8:
    if st.button(_t("下一頁"), disabled=not has_next, key="msio_next", use_container_width=True):
        st.session_state["msio_page"] = int(st.session_state["msio_page"]) + 1
        st.rerun()

# 依目前頁碼抓資料（只抓本頁）
df_view = fetch_stock_io_view(
    start_date, end_date, selected_item_id, io_label, material_kw,
    int(page_size), offset_rows
)

st.markdown("#### " + _t("進出庫紀錄（列表）"))

if df_view.empty:
    st.info(_t("沒有符合條件的資料。"))
else:
    # 左側增加勾選欄（選取要刪除的 Head）
    # 這裡用 data_editor 才能有 checkbox
    df_edit = df_view.copy()

    # 建立/保留選取欄
    if "_選取" not in df_edit.columns:
        df_edit.insert(0, "_選取", False)
    else:
        # 確保在最左側
        cols = ["_選取"] + [c for c in df_edit.columns if c != "_選取"]
        df_edit = df_edit[cols]

    select_col = _t("選取")
    df_display = _translate_stock_io_table_for_display(df_edit)

    edited = st.data_editor(
        df_display,
        use_container_width=True,
        height=int(st.session_state.setdefault("s01_top_height", 230)),
        hide_index=True,
        column_config={
            select_col: st.column_config.CheckboxColumn(select_col, help=_t("勾選要刪除的紀錄（以同一個 msioh_id 為單位）")),
            "_msioh_id": None,
            "_io_type_code": None,
        },
        disabled=[c for c in df_display.columns if c not in (select_col,)],
        key=f"msio_table_editor_{st.session_state.get('msio_table_editor_seed', 0)}",
    )

    st.caption(_t("⚠️ 刪除將以同一個 `_msioh_id` 為單位：會連同該 Head 下所有 Line 一起刪除。") + " 只允許一次刪除一張入庫單。")

    # ---- 刪除：真正刪除動作在 hard_delete_material_stock_io() 內檢查 delete 權限 ----
    st.session_state.setdefault("msio_delete_selected_ids", [])
    st.session_state.setdefault("msio_show_delete_dialog", False)

    col_del1, col_del2, col_del3 = st.columns([1.2, 1, 6])
    with col_del1:
        do_delete = st.button(_t("刪除"), type="primary")

    if do_delete:
        # 找出被勾選的 msioh_id（去重）
        try:
            selected_ids = (
                edited.loc[edited[select_col] == True, "_msioh_id"]
                .dropna()
                .astype(int)
                .unique()
                .tolist()
            )
        except Exception:
            selected_ids = []

        if not selected_ids:
            st.warning(_t("請先勾選要刪除的資料。"))
        elif len(selected_ids) > 1:
            st.warning(_t("一次只能勾選一張入庫單刪除，請取消其他勾選。"))
        else:
            # UI 安全限制：一次只保存一張入庫單，避免誤刪多張。
            st.session_state["msio_delete_selected_ids"] = [int(selected_ids[0])]
            st.session_state["msio_show_delete_dialog"] = True
            st.rerun()

    # 使用對話框（比 checkbox 二次確認更穩，避免勾一下就 rerun 把 UI 弄亂）
    if st.session_state.get("msio_show_delete_dialog", False):
        selected_ids = st.session_state.get("msio_delete_selected_ids", [])

        # 顯示用：列出「送貨單號」（優先 supplier_delivery_number，沒有就用 doc_no）
        delivery_nos: List[str] = []
        try:
            conn2 = get_connection()
            cur2 = conn2.cursor()
            in_sql2, in_params2 = _make_in_clause([int(x) for x in selected_ids])
            cur2.execute(
                f"""
                SELECT COALESCE(NULLIF(supplier_delivery_number,''), doc_no) AS delivery_no
                FROM material_stock_io_head
                WHERE msioh_id IN {in_sql2}
                ORDER BY msioh_id
                """,
                in_params2,
            )
            delivery_nos = [str(r[0]) for r in cur2.fetchall() if r and r[0] is not None]
            cur2.close()
            conn2.close()
        except Exception:
            try:
                conn2.close()
            except Exception:
                pass
            delivery_nos = []


        if hasattr(st, "dialog"):
            @st.dialog(_t("刪除確認"))
            def _delete_dialog():
                st.warning(_t("是否刪除以上資料？資料刪除後無法回復。"))
                st.write(_t("你將刪除以下送貨單號（資料刪除後無法回復）："))
                st.code(", ".join(delivery_nos) if delivery_nos else "(無)")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(_t("確認"), type="primary", use_container_width=True):
                        try:
                            hard_delete_material_stock_io(selected_ids)
                        except Exception as e:
                            st.error(f"刪除失敗：{e}")
                            st.stop()
                        st.session_state["msio_show_delete_dialog"] = False
                        st.session_state["msio_delete_selected_ids"] = []
                        refresh_s01_master_table_state()
                        st.success(_t("刪除完成。"))
                        st.rerun()
                with c2:
                    if st.button(_t("取消"), use_container_width=True):
                        st.session_state["msio_show_delete_dialog"] = False
                        st.session_state["msio_delete_selected_ids"] = []
                        st.rerun()

            _delete_dialog()
        else:
            # 兼容舊版 Streamlit：沒有 st.dialog 時，用簡單區塊模擬「確認 / 取消」
            st.warning(_t("是否刪除以上資料？資料刪除後無法回復。"))
            st.write(_t("你將刪除以下送貨單號（資料刪除後無法回復）："))
            st.code(", ".join(delivery_nos) if delivery_nos else "(無)")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(_t("確認"), type="primary", use_container_width=True):
                    try:
                        hard_delete_material_stock_io(selected_ids)
                    except Exception as e:
                        st.error(f"刪除失敗：{e}")
                        st.stop()
                    st.session_state["msio_show_delete_dialog"] = False
                    st.session_state["msio_delete_selected_ids"] = []
                    st.success(_t("刪除完成。"))
                    st.rerun()
            with c2:
                if st.button(_t("取消"), use_container_width=True):
                    st.session_state["msio_show_delete_dialog"] = False
                    st.session_state["msio_delete_selected_ids"] = []
                    st.rerun()

# 母表下方重新整理：清掉 Streamlit cache 與 data_editor 狀態，避免看到舊資料。
refresh_col, _refresh_spacer = st.columns([1.1, 6.0], vertical_alignment="center")
with refresh_col:
    if st.button(_t("重新整理"), key="msio_refresh_master_table", use_container_width=True):
        refresh_s01_master_table_state()
        st.rerun()

apply_vertical_splitter(
    "s01_top_height",
    "s01_vertical_splitter_control",
    default=230,
    min_top=150,
    max_top=430,
)

st.divider()


# ================== UI：新增（Head 確認鎖定 + Line 追加 + 完成作業） ==================
with st.expander(_t("新增紀錄"), expanded=True):
    # ---- Reset widget keys safely (must happen BEFORE widgets with those keys are instantiated) ----
    if st.session_state.get("reset_head_inputs"):
        # Clear/initialize head input widget keys
        st.session_state["io_date"] = datetime.date.today()
        st.session_state["order_number_new"] = ""
        st.session_state["work_order_number_new"] = ""
        st.session_state["supplier_display_new"] = _t("(未選)")
        st.session_state["supplier_delivery_number_new"] = ""
        st.session_state["io_label_head"] = "入庫"
        st.session_state["note_head"] = ""
        # 操作人員改為預設空白，避免系統自動帶入第一位人員而寫錯責任歸屬。
        st.session_state["operator_name_head"] = ""
        st.session_state["reset_head_inputs"] = False

    if st.session_state.get("reset_line_inputs"):
        st.session_state.pop("item_id_line", None)
        st.session_state["qty_pcs_line"] = 0.0
        st.session_state["qty_raw_line"] = 0.0
        st.session_state["weight_unit_label_line"] = "kg"
        st.session_state["unit_price_line"] = 0.0
        st.session_state["subtotal_line"] = 0.0
        st.session_state["material_barcode_scan"] = ""
        st.session_state["barcode_scan_msg"] = ""
        st.session_state.pop("unit_price_item_id", None)
        st.session_state["reset_line_inputs"] = False

    supplier_options = get_supplier_options()
    stuff_options = get_stuff_options()
    user_options = get_user_options()

    # 這些 head 欄位改由 session_state 管理預設值；widget 本身不再同時傳 value，
    # 避免 Streamlit 出現「default value + Session State API」黃色提醒。
    st.session_state.setdefault("io_date", datetime.date.today())
    st.session_state.setdefault("order_number_new", "")
    st.session_state.setdefault("work_order_number_new", "")
    st.session_state.setdefault("supplier_delivery_number_new", "")
    st.session_state.setdefault("note_head", "")

    # --- Head 區：輸入 + 確認鎖定 ---
    st.markdown("### " + _t("出入庫基本資料"))
    locked = bool(st.session_state["head_locked"])

    # PO 自動帶入供應商 / 限制原料清單（保留）
    def on_order_number_change():
        if locked:
            return
        order_no = (st.session_state.get("order_number_new") or "").strip()
        if not order_no:
            return
        ctx = fetch_po_context(order_no)
        if not ctx:
            return
        sid = ctx.get("supplier_id")
        if sid is not None:
            po_display = next((k for k, v in supplier_options.items() if int(v) == int(sid)), None)
            if po_display:
                st.session_state["supplier_display_new"] = po_display

    r1 = st.columns([1.0, 1.1, 1.35, 1.1])
    with r1[0]:
        io_date = st.date_input(_t("日期"), key="io_date", disabled=locked)
    with r1[1]:
        # 入庫單號只在 IN 顯示，但 doc_no 必然存在；非 IN 顯示空白
        if locked:
            doc_no_display = st.session_state.get("current_doc_no", "") if st.session_state.get("current_io_type_code") == "IN" else ""
        else:
            io_type_preview = resolve_io_type_code(st.session_state.get("io_label_head", "入庫"))
            doc_no_display = generate_material_receiving_number(io_date) if io_type_preview == "IN" else ""
        st.text_input(_t("入庫單號"), value=doc_no_display, key="doc_no_preview", disabled=True)

    with r1[2]:
        order_number_new = st.text_input(_t("採購單號（可空白）"), key="order_number_new", on_change=on_order_number_change, disabled=locked)
    with r1[3]:
        work_order_number_new = st.text_input(_t("工單號碼（可空白）"), key="work_order_number_new", disabled=locked)

    r2 = st.columns([1.3, 1.7, 1.0])
    with r2[0]:
        supplier_keys = [_t("(未選)")] + list(supplier_options.keys())

        # Streamlit 會在同一個 widget 同時使用 `index=` 預設值，
        # 又被 session_state 指定值時跳出黃色提示。
        # 這裡改成只維護 session_state，不再傳 index，
        # PO 單號自動帶入供應商時也不會再顯示 warning。
        cur_sel = st.session_state.get("supplier_display_new") or _t("(未選)")
        if cur_sel not in supplier_keys:
            st.session_state["supplier_display_new"] = _t("(未選)")

        supplier_display_new = st.selectbox(
            _t("供應商"),
            options=supplier_keys,
            key="supplier_display_new",
            disabled=locked,
        )
        supplier_id_new = None if supplier_display_new == _t("(未選)") else int(supplier_options[supplier_display_new])

    with r2[1]:
        supplier_delivery_number_new = st.text_input(_t("供應商送貨單號（可空白）"), key="supplier_delivery_number_new", disabled=locked)

    with r2[2]:
        io_label_head = st.selectbox(_t("進出庫類型"), ["入庫", "出庫", "調整", "回收入庫"], key="io_label_head", disabled=locked, format_func=_t)
        io_type_code_head = resolve_io_type_code(io_label_head)
        st.session_state["current_io_type_code"] = io_type_code_head if locked else io_type_code_head

    r3 = st.columns([2.3, 1.05, 1.05])
    with r3[0]:
        note_head = st.text_area(_t("備註"), height=70, key="note_head", disabled=locked)
    with r3[1]:
        # 操作人員允許空白：有些入出庫紀錄只需要追蹤建檔人，
        # 不一定要指定實際操作人員；DB 的 material_stock_io_head.operator 也允許 NULL。
        operator_keys = [""] + list(stuff_options.keys())
        if st.session_state.get("operator_name_head", "") not in operator_keys:
            st.session_state["operator_name_head"] = ""
        operator_name_head = st.selectbox(
            _t("操作人員"),
            operator_keys,
            key="operator_name_head",
            disabled=locked,
            format_func=lambda x: _t("(未選)") if x == "" else x,
        )
        operator_id_head = int(stuff_options[operator_name_head]) if operator_name_head else None
    with r3[2]:
        # 建檔人員固定為「目前登入者」，不再讓使用者手動選擇。
        # created_by 寫入 DB 時使用 st.session_state["user_id"]，畫面只顯示對應人名。
        current_user_id = None
        try:
            current_user_id = int(st.session_state.get("user_id"))
        except Exception:
            current_user_id = None

        # 若登入狀態異常沒有 user_id，保留安全 fallback，避免畫面直接炸掉。
        if current_user_id is None:
            try:
                current_user_id = int(next(iter(user_options.values()))) if user_options else 1
            except Exception:
                current_user_id = 1

        created_by_id_head = int(current_user_id)
        created_by_display_head = next(
            (name for name, uid in user_options.items() if int(uid) == int(created_by_id_head)),
            f"User#{created_by_id_head}",
        )
        st.text_input(
            _t("建檔人員"),
            value=created_by_display_head,
            key="created_by_display_head_display",
            disabled=True,
        )
        st.caption("※已依目前登入帳號自動帶入")

    # 確認 / 完成按鈕列
    b1, b2, _sp = st.columns([1.0, 1.0, 3.0])
    with b1:
        confirm = st.button(_t("確認（鎖定主表）"), use_container_width=True, disabled=locked)
    with b2:
        finish = st.button(_t("完成作業（解除鎖定）"), use_container_width=True, disabled=not locked)

    # 確認：建立 head、鎖定
    if confirm:
        if supplier_id_new is None:
            st.error(_t("請先選擇供應商。"))
            st.stop()
        # 操作人員可空白；未選時 operator_id_head 會以 None 寫入 DB。
        # 解析採購單號（order_num -> order_id）
        order_no_str = (order_number_new or "").strip()
        po_ctx = fetch_po_context(order_no_str) if order_no_str else None
        if order_no_str and not po_ctx:
            st.error(_t("採購單號不存在（外鍵指向 order_head.order_id）。請確認採購單號或留空。"))
            st.stop()
        order_id = int(po_ctx["order_id"]) if po_ctx else None

        work_order_id = to_py_int(work_order_number_new.strip()) if (work_order_number_new or "").strip() else None
        supplier_delivery_val = supplier_delivery_number_new.strip() if (supplier_delivery_number_new or "").strip() else None
        note_val = note_head.strip() if (note_head or "").strip() else None

        try:
            msioh_id, doc_no = insert_head(
                io_date=io_date,
                io_type_code=io_type_code_head,
                order_id=order_id,
                work_order_id=work_order_id,
                supplier_id=int(supplier_id_new),
                supplier_delivery_number=supplier_delivery_val,
                note=note_val,
                operator_id=operator_id_head,
                created_by_id=int(created_by_id_head),
            )
            st.session_state["head_locked"] = True
            st.session_state["current_msioh_id"] = msioh_id
            st.session_state["current_doc_no"] = doc_no or ""
            st.session_state["current_io_type_code"] = io_type_code_head
            st.success(_t("主表已確認並鎖定。現在可在下方新增明細。"))
            st.rerun()
        except Exception as e:
            st.error(f"{_t('主表建立失敗：')}{e}")
            st.stop()

    # 完成：解除鎖定、清空狀態
    if finish:
            st.session_state["head_locked"] = False
            st.session_state["current_msioh_id"] = None
            st.session_state["current_doc_no"] = ""
            # Defer clearing widget keys to next rerun (avoids StreamlitAPIException)
            st.session_state["reset_head_inputs"] = True
            st.session_state["reset_line_inputs"] = True
            st.success(_t("已完成作業並解除鎖定。可開始下一張單。"))
            st.rerun()

    st.divider()

    # --- Line 區：只有 head_locked 才允許新增 ---
    line_title_col, line_refresh_col = st.columns([5, 1.2], vertical_alignment="center")
    with line_title_col:
        st.markdown("### " + _t("出入庫明細"))
    with line_refresh_col:
        if st.button(_t("重新讀取原料"), key="reload_material_options", use_container_width=True):
            try:
                get_material_df.clear()
            except Exception:
                pass
            st.rerun()

    if not locked:
        st.warning(_t("請先在上方按「確認（鎖定主表）」建立主表後，才能新增明細。"))
        st.stop()

    msioh_id_current = st.session_state.get("current_msioh_id")
    io_type_code_current = st.session_state.get("current_io_type_code", "IN")

    pending_line_warning = (st.session_state.get("line_warning_msg") or "").strip()
    if pending_line_warning:
        st.warning(pending_line_warning)
        st.session_state["line_warning_msg"] = ""

    # 依 supplier / PO 限制原料清單（保留原功能）
    order_no_str = (st.session_state.get("order_number_new") or "").strip()
    po_ctx = fetch_po_context(order_no_str) if order_no_str else None
    po_item_ids = None
    po_label_map: Dict[int, str] = {}
    current_order_id = int(po_ctx["order_id"]) if po_ctx and po_ctx.get("order_id") else None
    if po_ctx and isinstance(po_ctx.get("items"), pd.DataFrame) and not po_ctx["items"].empty:
        po_item_ids = po_ctx["items"]["material_id"].astype(int).tolist()
        po_label_map = {
            int(r["material_id"]): f"{r['material_code']}｜{r['material_name']}"
            for _, r in po_ctx["items"].iterrows()
        }

    material_df = material_df_all.copy()
    if supplier_id_new is not None:
        material_df = material_df[material_df["supplier_id"].fillna(0).astype(int) == int(supplier_id_new)]
    if po_item_ids is not None:
        material_df = material_df[material_df["item_id"].isin(po_item_ids)]

    id_to_name = {int(r["item_id"]): str(r["item_name"]) for _, r in material_df.iterrows()} if not material_df.empty else {}
    id_to_label = {iid: po_label_map.get(iid, nm) for iid, nm in id_to_name.items()}
    item_ids = list(id_to_label.keys())

    
    # 注意：S01 不顯示進料單價與小計，避免現場員工看到採購價格。
    # 單價/小計仍會在後端計算並寫入 material_stock_io_line，供 AP 與成本使用。
    lr1 = st.columns([2.0, 1.25, 1.35, 0.85, 0.95, 0.75])

    def on_material_barcode_scan_change():
        scan_value = st.session_state.get("material_barcode_scan")
        matched_id = resolve_scanned_material_id(scan_value, material_df_all, item_ids)
        if matched_id is None:
            raw = normalize_barcode_text(scan_value)
            st.session_state["barcode_scan_msg"] = f"{_t('找不到符合目前供應商/採購單條件的原料條碼：')}{raw}" if raw else ""
            return
        st.session_state["item_id_line"] = int(matched_id)
        # Force price recalculation after scanner changes material.
        st.session_state.pop("unit_price_item_id", None)
        info = get_material_display_info(int(matched_id), material_df_all)
        st.session_state["barcode_scan_msg"] = f"{_t('已掃描帶入：')}{info}" if info else f"{_t('已掃描帶入：')}item_id={matched_id}"

    # ① 原料名稱（下拉）
    with lr1[0]:
        if not item_ids:
            st.selectbox(_t("原料名稱"), [_t("(無可用品項)")], key="item_id_line_disabled", disabled=True)
            selected_item_id = None
        else:
            cur = st.session_state.get("item_id_line")
            if cur not in item_ids:
                st.session_state["item_id_line"] = item_ids[0]
            selected_item_id = st.selectbox(
                _t("原料名稱"),
                item_ids,
                format_func=lambda x: id_to_label.get(int(x), str(x)),
                key="item_id_line",
            )

    # ①-2 條碼槍輸入：掃描 material_barcode / item_code / item_id 後，自動切換上方原料
    with lr1[1]:
        st.text_input(
            _t("條碼掃描"),
            key="material_barcode_scan",
            placeholder=_t("掃描或輸入條碼"),
            on_change=on_material_barcode_scan_change,
        )

    scan_msg = (st.session_state.get("barcode_scan_msg") or "").strip()
    if scan_msg:
        if scan_msg.startswith("找不到"):
            st.warning(scan_msg)
        else:
            st.caption(scan_msg)

    # ①-3 規格：依目前選定原料，從 material.specification 顯示；只顯示不寫入 line
    selected_specification = ""
    if selected_item_id is not None and "specification" in material_df_all.columns:
        try:
            selected_specification = str(
                material_df_all.loc[
                    material_df_all["item_id"].astype(int) == int(selected_item_id),
                    "specification",
                ].iloc[0]
                or ""
            ).strip()
        except Exception:
            selected_specification = ""

    with lr1[2]:
        st.text_input(
            _t("規格"),
            value=selected_specification,
            key=f"specification_line_{int(selected_item_id) if selected_item_id is not None else 'none'}",
            disabled=True,
        )

    # 依物料 TrackingMod 決定可輸入欄位：weight → 禁用「數量」；PCS → 禁用「進貨重量」
    tracking_mod = None
    if selected_item_id is not None:
        try:
            tracking_mod = str(
                material_df_all.loc[
                    material_df_all["item_id"] == int(selected_item_id),
                    "TrackingMod",
                ].iloc[0]
            ).strip()
        except Exception:
            tracking_mod = None

    is_weight_tracking = (tracking_mod or "").lower() == "weight"
    is_pcs_tracking = (tracking_mod or "").lower() == "pcs"

    # 隱藏單價：系統依採購單上的 price_unit 自動帶入；若採購單沒有單價，才抓原料最新單價。
    # 不建立 Streamlit input，避免現場操作人員在 S01 看到採購價格。
    latest_unit_price = 0.0
    if selected_item_id is not None:
        try:
            selected_item_id_int = int(selected_item_id)
        except Exception:
            selected_item_id_int = None

        if selected_item_id_int is not None:
            latest_unit_price = get_unit_price_for_order_item(current_order_id, selected_item_id_int)

            # 只有在「選擇的原料」或「採購單」變更時才自動回填隱藏單價。
            price_sig = (int(current_order_id) if current_order_id else None, selected_item_id_int)
            if st.session_state.get("unit_price_item_id") != price_sig:
                st.session_state["unit_price_line"] = latest_unit_price
                st.session_state["unit_price_item_id"] = price_sig

    # ② 數量（PCS）
    with lr1[3]:
        qty_pcs_disabled = is_weight_tracking  # weight 計價不輸入 PCS 數量
        # 注意：Streamlit 不允許在 widget 建立後再改同 key 的 session_state
        # 所以在建立 number_input 前就先把 disabled 欄位清成 0
        if qty_pcs_disabled and float(st.session_state.get("qty_pcs_line") or 0.0) != 0.0:
            st.session_state["qty_pcs_line"] = 0.0
        st.number_input(
            _t("數量"),
            step=1.0,
            format="%g",
            key="qty_pcs_line",
            disabled=qty_pcs_disabled,
        )
    # ③ 進貨重量
    with lr1[4]:
        qty_raw_disabled = is_pcs_tracking  # PCS 計價不輸入重量
        # 同上：在 widget 建立前清值，避免 Streamlit session_state 修改例外
        if qty_raw_disabled and float(st.session_state.get("qty_raw_line") or 0.0) != 0.0:
            st.session_state["qty_raw_line"] = 0.0
        st.number_input(
            _t("進貨重量"),
            step=0.001,
            format="%g",
            key="qty_raw_line",
            disabled=qty_raw_disabled,
        )

    # 小計仍在後端計算，但不顯示在 S01。
    qty_for_calc = 0.0
    if is_weight_tracking:
        qty_for_calc = float(st.session_state.get("qty_raw_line") or 0.0)
    elif is_pcs_tracking:
        qty_for_calc = float(st.session_state.get("qty_pcs_line") or 0.0)

    subtotal_calc = float(st.session_state.get("unit_price_line") or 0.0) * qty_for_calc
    st.session_state["subtotal_line"] = subtotal_calc

    # ④ 重量單位（預設 kg）
    with lr1[5]:
        st.selectbox(_t("重量單位"), ["kg", "g"], key="weight_unit_label_line")
    add_line_btn = st.button(_t("新增紀錄（新增明細）"), use_container_width=True)

    if add_line_btn:
        if selected_item_id is None:
            st.error(_t("目前條件下沒有可選的原料品項。請檢查採購單號/供應商是否選錯。"))
            st.stop()
        if not msioh_id_current:
            st.error(_t("主表狀態遺失（msioh_id）。請按「完成作業」後重新建立。"))
            st.stop()

        qty_pcs_line = st.session_state.get("qty_pcs_line")
        qty_raw_line = st.session_state.get("qty_raw_line")
        weight_unit_label = st.session_state.get("weight_unit_label_line")

        qty_pcs_val = to_py_float(qty_pcs_line)
        qty_raw_val = to_py_float(qty_raw_line)

        # 數量防呆：不可讓 0 或空白數量寫入明細。
        # S01 依原料追蹤模式決定有效輸入欄位：
        # - PCS：檢查「數量」
        # - weight：檢查「進貨重量」
        # - 其他/異常設定：至少要有一個數量欄位 > 0
        qty_pcs_num = float(qty_pcs_val or 0.0)
        qty_raw_num = float(qty_raw_val or 0.0)
        if is_pcs_tracking and qty_pcs_num <= 0:
            st.error(_t("請輸入數量，數量不可為 0。"))
            st.stop()
        if is_weight_tracking and qty_raw_num <= 0:
            st.error(_t("請輸入進貨重量，數量不可為 0。"))
            st.stop()
        if (not is_pcs_tracking) and (not is_weight_tracking) and qty_pcs_num <= 0 and qty_raw_num <= 0:
            st.error(_t("請輸入數量或進貨重量，數量不可為 0。"))
            st.stop()

        unit_price_val = to_py_float(st.session_state.get('unit_price_line'))
        subtotal_val = to_py_float(st.session_state.get('subtotal_line'))
        weight_unit_db = "kg" if (weight_unit_label or "kg") == "kg" else "g"
        item_name_val = id_to_name.get(int(selected_item_id))
        note_val = (st.session_state.get("note_head") or "").strip() or None

        current_order_id = None
        if st.session_state.get("order_number_new"):
            po_ctx_for_warn = fetch_po_context(st.session_state.get("order_number_new"))
            current_order_id = int(po_ctx_for_warn["order_id"]) if po_ctx_for_warn and po_ctx_for_warn.get("order_id") else None

        incoming_qty_for_warn = qty_pcs_val if is_pcs_tracking else qty_raw_val
        over_receipt_msg = get_po_over_receipt_warning(
            order_id=current_order_id,
            item_id=int(selected_item_id),
            incoming_qty=incoming_qty_for_warn,
        )

        try:
            insert_line(
                msioh_id=int(msioh_id_current),
                io_type_code=io_type_code_current,
                item_id=int(selected_item_id),
                item_name=item_name_val,
                qty_pcs=qty_pcs_val,
                qty_raw=qty_raw_val,
                unit_price=unit_price_val,
                subtotal=subtotal_val,
                weight_unit=weight_unit_db,
                note=note_val,
            )
            if over_receipt_msg:
                st.session_state["line_warning_msg"] = over_receipt_msg
            refresh_s01_master_table_state()
            st.success(_t("明細新增成功。"))
            # 保留 head 鎖定；明細欄位不強制清空（避免連續輸入被打斷）
            st.rerun()
        except Exception as e:
            st.error(f"{_t('明細寫入失敗：')}{e}")
            st.stop()
