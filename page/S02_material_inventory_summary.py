# S02_material_inventory_summary.py
# 原料庫存統計（只查詢、不新增、不修改）

import datetime
from typing import Any, Dict, Optional, List

import pandas as pd
import streamlit as st
from compact_layout import apply_compact_layout
import auth
from splitter_component import apply_vertical_splitter

apply_compact_layout()

from db import get_connection


TRANSLATIONS = {
    "原料庫存統計": {"vi": "Thống kê tồn kho nguyên liệu", "en": "Material Inventory Summary"},
    "庫存彙總（只查詢）": {"vi": "Tổng hợp tồn kho (chỉ tra cứu)", "en": "Inventory Summary (Query Only)"},
    "查詢條件": {"vi": "Điều kiện tra cứu", "en": "Search Criteria"},
    "結束日期": {"vi": "Ngày kết thúc", "en": "End Date"},
    "原料名稱（精準）": {"vi": "Tên nguyên liệu (chính xác)", "en": "Material Name (Exact)"},
    "原料名稱（關鍵字）": {"vi": "Tên nguyên liệu (từ khóa)", "en": "Material Name (Keyword)"},
    "顯示筆數": {"vi": "Số dòng hiển thị", "en": "Rows to Display"},
    "排序": {"vi": "Sắp xếp", "en": "Sort By"},
    "只顯示有庫存": {"vi": "Chỉ hiển thị mặt hàng còn tồn kho", "en": "Show In-Stock Only"},
    "只顯示低於安全庫存": {"vi": "Chỉ hiển thị dưới mức tồn kho an toàn", "en": "Show Below Safety Stock Only"},
    "查詢": {"vi": "Tra cứu", "en": "Search"},
    "請先設定條件後按「查詢」。": {"vi": "Vui lòng thiết lập điều kiện rồi nhấn 'Tra cứu'.", "en": "Please set the conditions first, then click 'Search'."},
    "查無資料（或該條件下尚無進出庫紀錄）。": {"vi": "Không tìm thấy dữ liệu (hoặc chưa có ghi nhận nhập xuất theo điều kiện này).", "en": "No data found (or no stock I/O records match these conditions yet)."},
    "共 {total} 筆｜低於安全庫存 {below} 筆": {"vi": "Tổng {total} dòng｜Dưới mức tồn kho an toàn {below} dòng", "en": "{total} rows｜{below} below safety stock"},
    "原料名稱": {"vi": "Tên nguyên liệu", "en": "Material Name"},
    "追蹤模式": {"vi": "Chế độ theo dõi", "en": "Tracking Mode"},
    "安全庫存": {"vi": "Tồn kho an toàn", "en": "Safety Stock"},
    "低於安全庫存": {"vi": "Dưới tồn kho an toàn", "en": "Below Safety Stock"},
    "全部": {"vi": "Tất cả", "en": "All"},
    "原料名稱_SORT": {"vi": "Tên nguyên liệu", "en": "Material Name"},
    "重量(g) 由大到小": {"vi": "Trọng lượng (g) giảm dần", "en": "Weight (g) High to Low"},
    "重量(g) 由小到大": {"vi": "Trọng lượng (g) tăng dần", "en": "Weight (g) Low to High"},
    "PCS 由大到小": {"vi": "PCS giảm dần", "en": "PCS High to Low"},
    "PCS 由小到大": {"vi": "PCS tăng dần", "en": "PCS Low to High"},
    "DB 連線失敗：get_connection() 回傳 None": {"vi": "Kết nối DB thất bại: get_connection() trả về None", "en": "DB connection failed: get_connection() returned None"},
}

SORT_OPTION_CODES = {
    "name": "原料名稱_SORT",
    "g_desc": "重量(g) 由大到小",
    "g_asc": "重量(g) 由小到大",
    "pcs_desc": "PCS 由大到小",
    "pcs_asc": "PCS 由小到大",
}


def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    if lang not in {"zh", "vi", "en"}:
        return "zh"
    return lang


def _t(text: str, **kwargs) -> str:
    lang = get_lang()
    result = text if lang == "zh" else TRANSLATIONS.get(text, {}).get(lang, text)
    if kwargs:
        try:
            return result.format(**kwargs)
        except Exception:
            return result
    return result


PAGE_KEY = "S02_material_inventory_summary"
auth.require_read(PAGE_KEY)

TABLE_IO_H = "material_stock_io_head"
TABLE_IO_L = "material_stock_io_line"
TABLE_MATERIAL = "material"


def fetch_df(sql: str, params: Any = None) -> pd.DataFrame:
    conn = get_connection()
    if conn is None:
        raise RuntimeError(_t("DB 連線失敗：get_connection() 回傳 None"))
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


@st.cache_data(show_spinner=False)
def get_material_options() -> Dict[str, int]:
    sql = f"SELECT item_id, item_name FROM `{TABLE_MATERIAL}` ORDER BY item_name"
    df = fetch_df(sql)
    return {str(r["item_name"]): int(r["item_id"]) for _, r in df.iterrows()}


def fetch_inventory_summary(
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date],
    item_id: Optional[int],
    material_kw: str,
    only_nonzero: bool,
    only_below_safety: bool,
    limit_rows: int,
    sort_by_code: str,
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
        conditions.append("m.item_id = %(item_id)s")
        params["item_id"] = item_id

    material_kw = (material_kw or "").strip()
    if material_kw:
        conditions.append("m.item_name LIKE %(mkw)s")
        params["mkw"] = f"%{material_kw}%"

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
    SELECT
        m.item_id,
        m.item_name AS `原料名稱`,
        m.TrackingMod AS `追蹤模式`,
        m.safety_stock AS `安全庫存`,
        COALESCE(SUM(
            CASE
                WHEN l.qty_pcs IS NULL THEN 0
                WHEN h.io_type = 'OUT' THEN -ABS(l.qty_pcs)
                ELSE ABS(l.qty_pcs)
            END
        ), 0) AS net_pcs,
        COALESCE(SUM(
            CASE
                WHEN l.qty_base IS NOT NULL THEN
                    CASE
                        WHEN h.io_type = 'OUT' THEN -ABS(l.qty_base)
                        ELSE ABS(l.qty_base)
                    END
                WHEN l.qty_raw IS NULL THEN 0
                ELSE
                    (CASE WHEN h.io_type = 'OUT' THEN -1 ELSE 1 END) *
                    ABS(l.qty_raw) *
                    (CASE WHEN l.weight_unit = 'kg' THEN 1000 ELSE 1 END)
            END
        ), 0) AS net_g
    FROM `{TABLE_MATERIAL}` m
    LEFT JOIN `{TABLE_IO_L}` l
           ON l.item_id = m.item_id
    LEFT JOIN `{TABLE_IO_H}` h
           ON h.msioh_id = l.msioh_id
    {where_clause}
    GROUP BY m.item_id, m.item_name, m.TrackingMod, m.safety_stock
    """
    df = fetch_df(sql, params)

    if df.empty:
        return df

    df["kg"] = (df["net_g"] / 1000).round(3)
    df["PCS"] = df["net_pcs"].round(2)
    df["g"] = df["net_g"].round(2)

    def is_below(row) -> bool:
        try:
            ss = float(row["安全庫存"]) if row["安全庫存"] is not None else 0.0
        except Exception:
            ss = 0.0
        mode = str(row["追蹤模式"] or "").lower()
        if mode == "pcs":
            return float(row["PCS"]) < ss
        if mode == "weight":
            return float(row["kg"]) < ss
        return False

    df["低於安全庫存"] = df.apply(is_below, axis=1)

    if only_nonzero:
        df = df[(df["PCS"] != 0) | (df["g"] != 0)]

    if only_below_safety:
        df = df[df["低於安全庫存"] == True]  # noqa: E712

    if sort_by_code == "name":
        df = df.sort_values(["原料名稱"], ascending=[True])
    elif sort_by_code == "g_asc":
        df = df.sort_values(["g"], ascending=[True])
    elif sort_by_code == "g_desc":
        df = df.sort_values(["g"], ascending=[False])
    elif sort_by_code == "pcs_asc":
        df = df.sort_values(["PCS"], ascending=[True])
    elif sort_by_code == "pcs_desc":
        df = df.sort_values(["PCS"], ascending=[False])

    out = df[["原料名稱", "追蹤模式", "PCS", "g", "kg", "安全庫存", "低於安全庫存"]].head(int(limit_rows))
    return out.rename(columns={
        "原料名稱": _t("原料名稱"),
        "追蹤模式": _t("追蹤模式"),
        "安全庫存": _t("安全庫存"),
        "低於安全庫存": _t("低於安全庫存"),
    })


st.header(_t("原料庫存統計"))
st.markdown(f"#### {_t('庫存彙總（只查詢）')}")

with st.expander(_t("查詢條件"), expanded=True):
    start_date = None
    c1, c2, c3, c4, c5 = st.columns([1.1, 1.25, 1.2, 1.1, 1.0])

    with c1:
        end_date = st.date_input(_t("結束日期"), value=datetime.date.today())

    material_options = get_material_options()
    all_label = _t("全部")
    material_names = [all_label] + list(material_options.keys())
    with c2:
        selected_name = st.selectbox(_t("原料名稱（精準）"), material_names)
        selected_item_id = None if selected_name == all_label else material_options[selected_name]

    with c3:
        material_kw = st.text_input(_t("原料名稱（關鍵字）"), value="")

    with c4:
        limit_rows = st.selectbox(_t("顯示筆數"), [10, 20, 30, 40, 50], index=1)

    sort_codes = ["name", "g_desc", "g_asc", "pcs_desc", "pcs_asc"]
    with c5:
        sort_by_code = st.selectbox(
            _t("排序"),
            sort_codes,
            index=0,
            format_func=lambda x: _t(SORT_OPTION_CODES[x]),
        )

    d1, d2, d3 = st.columns([1.2, 1.2, 1.0])
    with d1:
        only_nonzero = st.checkbox(_t("只顯示有庫存"), value=True)
    with d2:
        only_below_safety = st.checkbox(_t("只顯示低於安全庫存"), value=False)
    with d3:
        do_search = st.button(_t("查詢"), use_container_width=True)

if do_search:
    df = fetch_inventory_summary(
        start_date=start_date,
        end_date=end_date,
        item_id=selected_item_id,
        material_kw=material_kw,
        only_nonzero=only_nonzero,
        only_below_safety=only_below_safety,
        limit_rows=limit_rows,
        sort_by_code=sort_by_code,
    )

    if df.empty:
        st.info(_t("查無資料（或該條件下尚無進出庫紀錄）。"))
    else:
        below_col = _t("低於安全庫存")
        below_cnt = int(df[below_col].sum()) if below_col in df.columns else 0
        st.caption(_t("共 {total} 筆｜低於安全庫存 {below} 筆", total=len(df), below=below_cnt))

        try:
            st.dataframe(df, use_container_width=True, height=int(st.session_state.setdefault("s02_top_height", 220)), hide_index=True)
        except TypeError:
            st.dataframe(df, use_container_width=True, height=int(st.session_state.setdefault("s02_top_height", 220)))
        apply_vertical_splitter("s02_top_height", "s02_vertical_splitter_control", default=220, min_top=150, max_top=430)
else:
    st.info(_t("請先設定條件後按「查詢」。"))
