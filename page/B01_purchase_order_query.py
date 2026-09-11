import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd
from sqlalchemy import text
from datetime import date
from decimal import Decimal, InvalidOperation

apply_compact_layout()

from db import get_engine


# ------------------------------
# DB helpers
# ------------------------------
@st.cache_resource
def _engine():
    return get_engine()


def df_from_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    eng = _engine()
    with eng.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def exec_sql(sql: str, params: dict | None = None) -> None:
    eng = _engine()
    with eng.begin() as conn:
        conn.execute(text(sql), params or {})


def show_cols(table: str) -> list[str]:
    df = df_from_sql(f"SHOW COLUMNS FROM `{table}`")
    field_col = None
    for c in df.columns:
        if str(c).lower() == "field":
            field_col = c
            break
    if field_col is None:
        return []
    return df[field_col].astype(str).tolist()


def colset(table: str) -> set[str]:
    return set(show_cols(table))


def first_existing(cols: set[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None


def sql_ident(col_name: str) -> str:
    return f"`{col_name}`"


def get_index_cols(table: str, key_name: str) -> list[str]:
    """取某個 index / unique key 的欄位順序（依 Seq_in_index）"""
    try:
        df = df_from_sql(
            f"SHOW INDEX FROM `{table}` WHERE Key_name = :k ORDER BY Seq_in_index",
            {"k": key_name},
        )
        if df.empty:
            return []
        col_field = None
        for c in df.columns:
            if str(c).lower() == "column_name":
                col_field = c
                break
        if not col_field:
            return []
        return df[col_field].dropna().astype(str).tolist()
    except Exception:
        return []


def to_decimal(x, default=Decimal("0")) -> Decimal:
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return default
        return Decimal(str(x))
    except (InvalidOperation, ValueError):
        return default


# ------------------------------
# Metadata / table / columns
# ------------------------------
ORDER_HEAD = "order_head"
ORDER_ITEM = "order_item"
SUPPLIER = "supplier"
MATERIAL = "material"

ORDER_HEAD_COLS = colset(ORDER_HEAD)
ORDER_ITEM_COLS = colset(ORDER_ITEM)
SUPPLIER_COLS = colset(SUPPLIER)
MATERIAL_COLS = colset(MATERIAL)

MATERIAL_BARCODE_COL = first_existing(
    MATERIAL_COLS,
    ["material_barcode", "barcode", "item_barcode"],
)

ORDER_HEAD_CREATED_BY_COL = first_existing(
    ORDER_HEAD_COLS,
    ["created_by", "created_by_id", "created_by_user_id", "created_by_uid"],
)

MATERIAL_PRICE_COL = first_existing(
    MATERIAL_COLS,
    ["unit_price", "price_unit", "price/unit"],
)

ORDER_ITEM_PRICE_COL = first_existing(
    ORDER_ITEM_COLS,
    ["unit_price", "price_unit", "price/unit"],
) or "unit_price"

ORDER_ITEM_LINE_COL = first_existing(
    ORDER_ITEM_COLS,
    ["line_no", "line_num", "seq", "seq_no", "line"],
)

ORDER_ITEM_AMOUNT_COL = first_existing(
    ORDER_ITEM_COLS,
    ["amount", "line_amount", "total_amount"],
)


# ------------------------------
# Master data loaders
# ------------------------------
@st.cache_data(ttl=120)
def load_suppliers(active_only: bool = False) -> pd.DataFrame:
    cols = SUPPLIER_COLS
    fields: list[str] = []
    for c in ["supplier_id", "supplier_code", "supplier_shortname", "supplier_name", "is_active"]:
        if c in cols:
            fields.append(c)

    if not fields:
        return pd.DataFrame()

    where_sql = ""
    if active_only and "is_active" in cols:
        where_sql = "WHERE is_active = 1"

    sql = f"""
      SELECT {", ".join([sql_ident(c) for c in fields])}
      FROM `{SUPPLIER}`
      {where_sql}
      ORDER BY supplier_code
    """
    return df_from_sql(sql)
@st.cache_data(ttl=120)
def load_materials_by_supplier(supplier_id: int | None) -> pd.DataFrame:
    if supplier_id is None:
        return pd.DataFrame()

    price_expr = "NULL AS unit_price"
    if MATERIAL_PRICE_COL:
        price_expr = f"{sql_ident(MATERIAL_PRICE_COL)} AS unit_price"

    spec_col = "specification" if "specification" in MATERIAL_COLS else None
    track_col = "TrackingMod" if "TrackingMod" in MATERIAL_COLS else None
    statute_col = "statute" if "statute" in MATERIAL_COLS else None

    select_parts = [
        "item_id",
        "item_code",
        "item_name",
        (sql_ident(MATERIAL_BARCODE_COL) + " AS material_barcode") if MATERIAL_BARCODE_COL else "NULL AS material_barcode",
        (sql_ident(spec_col) + " AS specification") if spec_col else "NULL AS specification",
        (sql_ident(track_col) + " AS TrackingMod") if track_col else "NULL AS TrackingMod",
        price_expr,
        (sql_ident(statute_col) + " AS statute") if statute_col else "NULL AS statute",
    ]

    where_statute = ""
    if statute_col:
        where_statute = f"AND ({sql_ident(statute_col)} = 1 OR {sql_ident(statute_col)} IS NULL)"

    sql = f"""
        SELECT
          {", ".join(select_parts)}
        FROM `{MATERIAL}`
        WHERE supplier_id = :supplier_id
          {where_statute}
        ORDER BY item_code
    """
    return df_from_sql(sql, {"supplier_id": supplier_id})




# ------------------------------
# Barcode helpers (Code39 / 3 of 9)
# ------------------------------
def _fmt_qty_barcode(qty_val) -> str:
    """將數量格式化成可掃描字串（避免 1.0 / 1.00 這種噪音）"""
    try:
        if qty_val is None:
            return ""
        # streamlit number_input 可能給 float
        q = float(qty_val)
        if abs(q - round(q)) < 1e-9:
            return str(int(round(q)))
        # 最多保留 3 位小數，去掉尾零
        s = f"{q:.3f}".rstrip("0").rstrip(".")
        return s
    except Exception:
        return str(qty_val)

def _render_code39_pair_html(code_left: str, code_right: str, height: int = 48, gap_px: int = 36) -> str:
    """回傳一段 HTML，使用 JsBarcode 生成兩段 Code39 條碼並保持間距。"""
    # HTML id 必須唯一
    import uuid
    uid = uuid.uuid4().hex
    left_id = f"bcL_{uid}"
    right_id = f"bcR_{uid}"

    # 重要：Code39 支援的字元有限；先用最保守方式處理（空字串就不畫）
    safe_left = (code_left or "").strip()
    safe_right = (code_right or "").strip()

    return f"""
<style>
  html, body {{ background: transparent !important; margin: 0; padding: 0; }}
  svg {{ background: transparent !important; }}
</style>

<div style="display:flex; align-items:flex-start; gap:{gap_px}px; padding:0; margin:0;">
  <svg id="{left_id}"></svg>
  <svg id="{right_id}"></svg>
</div>

<script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
<script>
(function(){{
  const left = {safe_left!r};
  const right = {safe_right!r};

  function draw(id, val){{
    const el = document.getElementById(id);
    if(!el) return;
    if(!val) {{
      el.innerHTML = "";
      return;
    }}
    try {{
      JsBarcode(el, val, {{
        format: "CODE39",
        displayValue: true,
        height: {height},
        margin: 0,
        background: "transparent"
      }});
    }} catch(e) {{
      // 不要用大片白底的 error，改成小字提示，避免畫面像破圖
      el.innerHTML = "<text x='0' y='14' fill='#b00020' font-size='12'>barcode err</text>";
    }}
  }}

  draw("{left_id}", left);
  draw("{right_id}", right);
}})();
</script>
"""
# ------------------------------
# Order num generator: yymmdd + xxx
# ------------------------------
def next_order_num(po_date: date, supplier_shortname: str) -> str:
    """單號格式：OD + 供應商簡稱 + yymmdd + 3 碼流水號。"""
    shortname = str(supplier_shortname or "").strip()
    if not shortname:
        raise ValueError("供應商簡稱為必填，無法產生採購單號。")

    ymd = po_date.strftime("%y%m%d")
    prefix = f"OD{shortname}{ymd}"

    df = df_from_sql(
        f"""
        SELECT MAX(CAST(RIGHT(order_num, 3) AS UNSIGNED)) AS max_num
        FROM `{ORDER_HEAD}`
        WHERE LEFT(order_num, :prefix_len) = :prefix
          AND CHAR_LENGTH(order_num) = :code_len
          AND RIGHT(order_num, 3) REGEXP '^[0-9]{{3}}$'
        """,
        {"prefix_len": len(prefix), "prefix": prefix, "code_len": len(prefix) + 3},
    )
    max_num = df["max_num"].iloc[0] if not df.empty else None
    try:
        seq = int(max_num or 0)
    except (TypeError, ValueError):
        seq = 0

    if seq >= 999:
        raise ValueError(f"{prefix} 當日流水號已達三碼上限。")
    return f"{prefix}{seq+1:03d}"


# ------------------------------
# Save logic
# ------------------------------
def save_new_order():
    # 主表
    order_date = st.session_state.get("po_order_date", date.today())
    due_date = st.session_state.get("po_due_date", None)
    supplier_choice = st.session_state.get("po_supplier_choice", "未選")
    currency = st.session_state.get("po_currency", "VND")
    head_remark = st.session_state.get("po_head_remark", "")

    if supplier_choice == "未選":
        st.error("你沒選供應商。沒有對象的訂購單，只是情書。")
        return

    try:
        supplier_id = int(supplier_choice.split("|")[0].strip())
    except Exception:
        st.error("供應商選項格式怪怪的，請重新選一次。")
        return

    suppliers = load_suppliers()
    sup_row = suppliers[suppliers["supplier_id"] == supplier_id]
    if sup_row.empty:
        st.error("供應商清單裡找不到這個 ID，麻煩你檢查一下資料庫。")
        return
    sup = sup_row.iloc[0]
    # ✅ 供應商停用（非合作中）則不可再開單
    if "is_active" in sup.index:
        try:
            active_flag = int(sup.get("is_active") or 0)
        except Exception:
            active_flag = 0
        if active_flag != 1:
            st.error("此供應商已停用（非「合作中」），不可再開訂購單。請改選其他供應商，或先到 C02 供應商主檔把它設回「合作中」。")
            return


    # 明細
    line_count = st.session_state.get("po_line_count", 1)
    mats = load_materials_by_supplier(supplier_id)
    if mats.empty:
        st.error("這個供應商暫時沒有綁任何原料品項，請先去 C01 / Material 補。")
        return

    # label -> material row
    label_map = {}
    for _, r in mats.iterrows():
        code = str(r.get("item_code") or "")
        name = str(r.get("item_name") or "")
        label = f"{code} | {name}" if code else name
        label_map[label] = r

    cleaned = []
    for i in range(line_count):
        label_key = f"po_line_{i}_item"
        qty_key = f"po_line_{i}_qty"
        remark_key = f"po_line_{i}_remark"

        label = st.session_state.get(label_key, "")
        if not label or label not in label_map:
            continue

        qty = to_decimal(st.session_state.get(qty_key, 0), Decimal("0"))
        if qty <= 0:
            continue

        base = label_map[label]
        item_id = base.get("item_id")
        item_code = str(base.get("item_code") or "")
        item_name = str(base.get("item_name") or "")
        spec = str(base.get("specification") or "")
        tm = str(base.get("TrackingMod") or "").lower()
        unit = "PCS" if "pcs" in tm else ("kg" if tm else "")
        unit_price = to_decimal(base.get("unit_price"), Decimal("0"))
        remark = str(st.session_state.get(remark_key, "") or "")

        cleaned.append(
            {
                "item_id": int(item_id) if pd.notna(item_id) else None,
                "item_code": item_code,
                "item_name": item_name,
                "specification": spec,
                "unit": unit,
                "qty_ordered": qty,
                "unit_price": unit_price,
                "remark": remark,
            }
        )

    if not cleaned:
        st.error("沒有任何有效的明細列。至少要選一個品項，數量 > 0。")
        return

    # 行號重排
    for idx, row in enumerate(cleaned, start=1):
        row["line_no"] = idx

    # 總額
    total = Decimal("0")
    for row in cleaned:
        total += row["qty_ordered"] * row["unit_price"]

    supplier_shortname = str(sup.get("supplier_shortname") or "").strip()
    if not supplier_shortname:
        st.error("供應商簡稱為必填，無法產生採購單號。")
        return

    # 單號 & 交期
    order_num = next_order_num(order_date, supplier_shortname)
    if "due_date" in ORDER_HEAD_COLS and not due_date:
        due_date = order_date

    # 寫入 DB
    eng = _engine()
    with eng.begin() as conn:
        insert_cols = []
        insert_vals = {}

        def add_head(col, val):
            if col in ORDER_HEAD_COLS and val is not None:
                insert_cols.append(col)
                insert_vals[col] = val

        add_head("order_num", order_num)
        add_head("order_date", order_date)
        add_head("order_type", "PO")
        add_head("status", "Not delivered" if "status" in ORDER_HEAD_COLS else None)
        add_head("currency_code", currency)
        add_head("total_amount", float(total) if "total_amount" in ORDER_HEAD_COLS else None)
        add_head("due_date", due_date)
        add_head("remark", head_remark)

        # 供應商欄位
        if "supplier_id" in ORDER_HEAD_COLS:
            add_head("supplier_id", supplier_id)
        if "supplier_code" in ORDER_HEAD_COLS and "supplier_code" in sup.index:
            add_head("supplier_code", sup.get("supplier_code"))
        if "supplier_name" in ORDER_HEAD_COLS and "supplier_name" in sup.index:
            add_head("supplier_name", sup.get("supplier_name"))

        # created_by 暫時硬塞 1
        if ORDER_HEAD_CREATED_BY_COL and ORDER_HEAD_CREATED_BY_COL not in insert_cols:
            insert_cols.append(ORDER_HEAD_CREATED_BY_COL)
            insert_vals[ORDER_HEAD_CREATED_BY_COL] = 1

        cols_sql = ", ".join([sql_ident(c) for c in insert_cols])
        vals_sql = ", ".join([f":{c}" for c in insert_cols])

        conn.execute(
            text(f"INSERT INTO `{ORDER_HEAD}` ({cols_sql}) VALUES ({vals_sql})"),
            insert_vals,
        )
        new_id = conn.execute(text("SELECT LAST_INSERT_ID() AS id")).fetchone()[0]

        # 行號 unique=全表 line_no 的防呆
        global_line_mode = False
        global_line_seed = 0
        if ORDER_ITEM_LINE_COL:
            ucols = get_index_cols(ORDER_ITEM, "order_item_unique")
            if ucols == [ORDER_ITEM_LINE_COL]:
                global_line_mode = True
                global_line_seed = conn.execute(
                    text(f"SELECT COALESCE(MAX({sql_ident(ORDER_ITEM_LINE_COL)}),0) FROM `{ORDER_ITEM}`")
                ).fetchone()[0]

        for i, row in enumerate(cleaned, start=1):
            insert_cols = []
            insert_vals = {}

            def add_item(col, val):
                if col in ORDER_ITEM_COLS and val is not None:
                    insert_cols.append(col)
                    insert_vals[col] = val

            add_item("order_id", int(new_id))

            if "material_id" in ORDER_ITEM_COLS and row["item_id"] is not None:
                add_item("material_id", row["item_id"])

            add_item("material_code", row["item_code"])
            add_item("material_name", row["item_name"])
            add_item("spec", row["specification"])
            add_item("unit", row["unit"] or None)
            add_item("qty_ordered", float(row["qty_ordered"]))
            add_item(ORDER_ITEM_PRICE_COL, float(row["unit_price"]))
            add_item("remark", row["remark"])

            if ORDER_ITEM_LINE_COL:
                line_val = (global_line_seed + i) if global_line_mode else int(row["line_no"])
                add_item(ORDER_ITEM_LINE_COL, line_val)

            if ORDER_ITEM_AMOUNT_COL and ORDER_ITEM_AMOUNT_COL in insert_cols:
                insert_cols.remove(ORDER_ITEM_AMOUNT_COL)
                insert_vals.pop(ORDER_ITEM_AMOUNT_COL, None)

            cols_sql = ", ".join([sql_ident(c) for c in insert_cols])
            vals_sql = ", ".join([f":{c}" for c in insert_cols])
            conn.execute(
                text(f"INSERT INTO `{ORDER_ITEM}` ({cols_sql}) VALUES ({vals_sql})"),
                insert_vals,
            )

    st.success(f"✅ 已建立訂購單：{order_num}")

    # 重置明細欄位（保留供應商、日期，方便連續開單）
    line_count = st.session_state.get("po_line_count", 1)
    for i in range(line_count):
        for key in [
            f"po_line_{i}_item",
            f"po_line_{i}_qty",
            f"po_line_{i}_remark",
            f"po_line_{i}_spec",
            f"po_line_{i}_unit",
            f"po_line_{i}_price",
        ]:
            if key in st.session_state:
                del st.session_state[key]


# ------------------------------
# UI
# ------------------------------
def init_state():
    # 只維護列數，其他欄位交給 widget 自己控管，避免 po_order_date 警告
    st.session_state.setdefault("po_line_count", 1)


init_state()

st.header("B02 新建採購單")

suppliers = load_suppliers(active_only=("is_active" in SUPPLIER_COLS))

st.markdown("#### 主表資訊")

# 第一行：日期、供應商、幣別
h1, h2, h3 = st.columns([1.2, 2.5, 1.2])

with h1:
    order_date = st.date_input(
        "訂單日期",
        key="po_order_date",
        value=date.today(),  # 只給預設值，不再手動改它
    )

with h2:
    if suppliers.empty:
        st.write("⚠ 尚無供應商資料。")
        supplier_choice = "未選"
    else:
        sup_opts = ["未選"] + [
            f'{int(r["supplier_id"])} | {r.get("supplier_code","")} | {r.get("supplier_name","")}'
            for _, r in suppliers.iterrows()
        ]
        existing = st.session_state.get("po_supplier_choice", None)
        default_index = sup_opts.index(existing) if isinstance(existing, str) and existing in sup_opts else 0
        supplier_choice = st.selectbox(
            "供應商（必選）",
            options=sup_opts,
            index=default_index,
            key="po_supplier_choice",
        )

with h3:
    currency = st.selectbox(
        "幣別",
        options=["VND", "USD", "NTD"],
        index=["VND", "USD", "NTD"].index(st.session_state.get("po_currency", "VND"))
        if "po_currency" in st.session_state else 0,
        key="po_currency",
    )

# 第二行：單號 + 交期（同一行）
c_num, c_due = st.columns([2.0, 1.2])

preview_supplier_shortname = ""
if supplier_choice != "未選":
    try:
        preview_supplier_id = int(str(supplier_choice).split("|")[0].strip())
        preview_supplier_row = suppliers.loc[suppliers["supplier_id"] == preview_supplier_id]
        if not preview_supplier_row.empty:
            preview_supplier_shortname = str(preview_supplier_row.iloc[0].get("supplier_shortname") or "").strip()
    except (TypeError, ValueError):
        preview_supplier_shortname = ""

with c_num:
    try:
        preview_order_num = next_order_num(order_date, preview_supplier_shortname) if preview_supplier_shortname else ""
    except ValueError as e:
        preview_order_num = ""
        st.warning(str(e))
    st.text_input(
        "單號（自動產生，儲存時依規則再算一次）",
        value=preview_order_num,
        disabled=True,
    )

with c_due:
    due_date = st.date_input(
        "交期（可空）",
        key="po_due_date",
        value=date.today(),
    )

head_remark = st.text_area(
    "備註（主表）",
    key="po_head_remark",
    value=st.session_state.get("po_head_remark", ""),
    height=80,
)

st.markdown("#### 品項與數量（依供應商過濾）")

# 依供應商載入品項
supplier_id_for_items = None
if supplier_choice != "未選":
    try:
        supplier_id_for_items = int(supplier_choice.split("|")[0].strip())
    except Exception:
        supplier_id_for_items = None

mats = load_materials_by_supplier(supplier_id_for_items) if supplier_id_for_items else pd.DataFrame()

if mats.empty:
    st.info("選好供應商後，若這裡還是空的，代表這個供應商暫時沒有品項。")
else:
    labels = []
    label_map = {}
    for _, r in mats.iterrows():
        code = str(r.get("item_code") or "")
        name = str(r.get("item_name") or "")
        label = f"{code} | {name}" if code else name
        labels.append(label)
        label_map[label] = r

    display_labels = [""] + labels  # "" 代表尚未選擇 → 預設空白

    line_count = st.session_state.get("po_line_count", 1)

    for i in range(line_count):
        st.markdown(f"##### 第 {i+1} 列")

        c1, c2, c3, c4, c5 = st.columns([3.0, 1.5, 1.0, 1.2, 2.3])

        label_key = f"po_line_{i}_item"
        qty_key = f"po_line_{i}_qty"
        remark_key = f"po_line_{i}_remark"
        spec_key = f"po_line_{i}_spec"
        unit_key = f"po_line_{i}_unit"
        price_key = f"po_line_{i}_price"

        with c1:
            current_label = st.session_state.get(label_key, "")
            if current_label not in display_labels:
                current_label = ""
            selected_label = st.selectbox(
                "品項",
                options=display_labels,
                key=label_key,
                index=display_labels.index(current_label),
            )

        base = label_map.get(selected_label) if selected_label else None
        if base is not None:
            spec = str(base.get("specification") or "")
            tm = str(base.get("TrackingMod") or "").lower()
            unit = "PCS" if "pcs" in tm else ("kg" if tm else "")
            unit_price = to_decimal(base.get("unit_price"), Decimal("0"))
        else:
            spec = ""
            unit = ""
            unit_price = Decimal("0")

        # 把計算好的值寫回 session_state，widget 只吃 key
        st.session_state[spec_key] = spec
        st.session_state[unit_key] = unit
        st.session_state[price_key] = float(unit_price)

        with c2:
            st.text_input(
                "規格",
                key=spec_key,
                disabled=True,
            )
        with c3:
            st.text_input(
                "單位",
                key=unit_key,
                disabled=True,
            )
        with c4:
            st.number_input(
                "數量",
                key=qty_key,
                min_value=0.0,
                step=1.0,
            )
        with c5:
            st.number_input(
                "單價",
                key=price_key,
                min_value=0.0,
                step=1.0,
                disabled=True,  # 使用者不能改
            )
            st.text_input(
                "備註",
                key=remark_key,
            )

        # 條碼（每列兩段：原料條碼 + 數量條碼）
        # - 原料條碼：material.material_barcode
        # - 數量條碼：qty（格式化後）
        material_bc = ""
        if base is not None:
            material_bc = str(base.get("material_barcode") or "")
        qty_bc = _fmt_qty_barcode(st.session_state.get(qty_key, 0))

        # 只有在「已選品項」時才畫；數量為 0 仍可先畫原料碼（方便先貼標）
        if selected_label:
            # 同一行但要留距離，避免掃碼槍一次掃到兩個
            import streamlit.components.v1 as components
            components.html(
                _render_code39_pair_html(material_bc, qty_bc, height=44, gap_px=42),
                height=96,
            )

    # 預估總額（用現在的品項 + DB 價格算）
    preview_total = Decimal("0")
    for i in range(line_count):
        label = st.session_state.get(f"po_line_{i}_item", "")
        if not label or label not in label_map:
            continue
        qty = to_decimal(st.session_state.get(f"po_line_{i}_qty", 0), Decimal("0"))
        base = label_map[label]
        up = to_decimal(base.get("unit_price"), Decimal("0"))
        if qty > 0 and up >= 0:
            preview_total += qty * up
    st.info(f"稅金（未含稅/未含運）：{preview_total:,}")

# 先「增加一行」，再「儲存訂單」
if st.button("➕ 增加一行", use_container_width=True):
    st.session_state["po_line_count"] = st.session_state.get("po_line_count", 1) + 1

# 列印（先用目前畫面資料生成 PDF，不影響 DB）
if st.button("🖨️ 列印 A4（只印 B02）", use_container_width=True):
    if mats.empty:
        st.error("請先選擇供應商並選入至少一筆品項，才能列印。")
    else:
        supplier_lbl = supplier_choice if supplier_choice != "未選" else ""
        lines = []
        for i in range(st.session_state.get("po_line_count", 1)):
            lab = st.session_state.get(f"po_line_{i}_item", "")
            if not lab or lab not in label_map:
                continue
            base = label_map[lab]
            qty_val = st.session_state.get(f"po_line_{i}_qty", 0)
            qty_dec = to_decimal(qty_val, Decimal("0"))
            if qty_dec <= 0:
                continue
            tm = str(base.get("TrackingMod") or "").lower()
            unit = "PCS" if "pcs" in tm else ("kg" if tm else "")
            lines.append({
                "item_code": str(base.get("item_code") or ""),
                "item_name": str(base.get("item_name") or ""),
                "specification": str(base.get("specification") or ""),
                "unit": unit,
                "qty_ordered": float(qty_dec),
                "material_barcode": str(base.get("material_barcode") or ""),
            })

        pdf_bytes = _build_b02_pdf(
            preview_order_num=st.session_state.get("po_order_num_preview", preview_order_num),
            supplier_label=supplier_lbl,
            order_date=st.session_state.get("po_order_date", date.today()),
            due_date=st.session_state.get("po_due_date", None),
            lines=lines,
        )
        st.download_button(
            "下載列印檔（PDF）",
            data=pdf_bytes,
            file_name=f'B02_{st.session_state.get("po_order_num_preview", preview_order_num)}.pdf',
            mime="application/pdf",
            use_container_width=True,
        )

if st.button("儲存訂單", use_container_width=True):
    save_new_order()
