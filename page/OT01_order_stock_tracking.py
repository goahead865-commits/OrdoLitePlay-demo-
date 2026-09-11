"""
OT01_order_stock_tracking.py
OrdoLite - 訂單狀況追蹤（庫存分配預覽）
作者：ChatGPT (依使用者需求生成)

用法（擇一）：
1) 直接在 Streamlit multipage 目錄下放這支檔案，於 home.py / navigation 註冊頁面
2) 單獨跑：streamlit run OT01_order_stock_tracking.py

需求：
- 使用者可勾選多張客戶訂單（含交期）
- 勾選後顯示：有庫存 / 部分不足 / 未入庫
- 同產品多張單會依交期排序「吃掉」庫存（allocation 預覽）
- 不新增 table，不寫入資料庫（Preview only）
"""

from compact_layout import apply_compact_layout

apply_compact_layout()

import pandas as pd
import streamlit as st
import auth

from datetime import date, timedelta

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from core.i18n import init_language, tr as _t

init_language()


# 你的 db.py（使用者上傳）提供 get_engine()
from db import get_engine


# -----------------------------
# SQL helpers
# -----------------------------
@st.cache_data(ttl=30, show_spinner=False)
def _read_sql(query: str, params: dict | tuple | None = None) -> pd.DataFrame:
    eng = get_engine()
    with eng.connect() as conn:
        return pd.read_sql_query(query, conn, params=params)


# -----------------------------
# 基礎設定
# -----------------------------
st.set_page_config(page_title=_t("訂單狀況追蹤（庫存分配預覽）"), layout="wide")

PAGE_KEY = "OT01_order_stock_tracking"
auth.require_read(PAGE_KEY)


def _can_edit_page() -> bool:
    """
    OT01 是庫存分配預覽頁，不寫入 DB。
    但若 Z99 有設定「可編輯」，這裡用 can_update 來控制是否可勾選與重新計算。
    """
    # 管理員直接放行
    try:
        if bool(st.session_state.get("is_admin")):
            return True
    except Exception:
        pass

    user_id = st.session_state.get("user_id")
    if not user_id:
        return False

    sql = """
        SELECT
            COALESCE(upo.can_update, 0) AS can_update,
            COALESCE(upo.can_create, 0) AS can_create,
            COALESCE(upo.can_delete, 0) AS can_delete,
            COALESCE(upo.can_approve, 0) AS can_approve
        FROM permission_resource pr
        LEFT JOIN user_permission_override upo
               ON upo.resource_id = pr.resource_id
              AND upo.user_id = %(user_id)s
        WHERE pr.resource_code = %(page_key)s
          AND COALESCE(pr.is_active, 1) = 1
        LIMIT 1
    """
    try:
        df = _read_sql(sql, {"user_id": int(user_id), "page_key": PAGE_KEY})
        if df.empty:
            return False
        r = df.iloc[0]
        return any(bool(int(r.get(c) or 0)) for c in ["can_update", "can_create", "can_delete", "can_approve"])
    except Exception:
        # 若權限查詢本身失敗，不要讓畫面直接爆掉；但保守起見不開編輯。
        return False


TITLE = f"📦 {_t('訂單狀況追蹤（庫存分配預覽）')}"
st.title(TITLE)
st.caption(_t("勾選多張客戶訂單後，系統會依交期排序進行庫存分配預覽（不寫入 DB）。"))

CAN_EDIT_PAGE = _can_edit_page()
if not CAN_EDIT_PAGE:
    st.warning(_t("你目前只有查看權限，不能勾選訂單或重新計算分配預覽。請到 Z99 開啟 OT01 的可編輯權限。"))


# -----------------------------
# Query helpers
# -----------------------------
@st.cache_data(ttl=30, show_spinner=False)
def fetch_customers() -> pd.DataFrame:
    # 依你的 dump，客戶表是 customer，常見欄位 customer_id / customer_name
    q = """
    SELECT customer_id, customer_name
    FROM customer
    ORDER BY customer_name
    """
    try:
        return _read_sql(q)
    except Exception:
        # 若你沒有 customer 表或欄位不同，至少不讓整頁爆炸
        return pd.DataFrame(columns=["customer_id", "customer_name"])


@st.cache_data(ttl=15, show_spinner=False)
def fetch_orders(deliver_from: date, deliver_to: date, created_from: date | None, created_to: date | None,
               customer_id: int | None, keyword: str) -> pd.DataFrame:
    # 取得訂單池：每張訂單一列（含品項數/總量）
    # deliver_date 用兩個框（起/迄）
    # created_at 若資料庫沒有此欄位，會在查詢時報錯，你再告訴我你的實際欄位名我再調整。
    q = """
    SELECT
        co.customer_order_id,
        co.customer_order_num,
        co.customer_order_code,
        co.deliver_date,
        c.customer_name,
        COUNT(coi.customer_order_item_id) AS item_count,
        COALESCE(SUM(coi.quantity), 0) AS total_qty
    FROM customer_order co
    LEFT JOIN customer c ON c.customer_id = co.customer_id
    LEFT JOIN customer_order_item coi ON coi.customer_order_id = co.customer_order_id
    WHERE co.deliver_date BETWEEN %(deliver_from)s AND %(deliver_to)s
      AND (%(customer_id)s IS NULL OR co.customer_id = %(customer_id)s)
      AND (
            %(kw)s = '' OR
            co.customer_order_num LIKE CONCAT('%%', %(kw)s, '%%') OR
            co.customer_order_code LIKE CONCAT('%%', %(kw)s, '%%')
          )
      AND (
            %(created_from)s IS NULL OR DATE(co.created_at) >= %(created_from)s
          )
      AND (
            %(created_to)s IS NULL OR DATE(co.created_at) <= %(created_to)s
          )
    GROUP BY
        co.customer_order_id, co.customer_order_num, co.customer_order_code, co.deliver_date, c.customer_name
    ORDER BY co.deliver_date, co.customer_order_id
    """
    params = {
        "deliver_from": deliver_from,
        "deliver_to": deliver_to,
        "created_from": created_from,
        "created_to": created_to,
        "customer_id": customer_id,
        "kw": keyword.strip(),
    }
    return _read_sql(q, params=params)


@st.cache_data(ttl=15, show_spinner=False)
def fetch_order_items(order_ids: list[int]) -> pd.DataFrame:
    if not order_ids:
        return pd.DataFrame()

    # 注意：line_no 欄位若不存在，改用 customer_order_item_id 當排序鍵
    q = f"""
    SELECT
        co.customer_order_id,
        co.customer_order_code,
        co.customer_order_num,
        co.deliver_date,

        coi.customer_order_item_id,
        COALESCE(coi.line_no, coi.customer_order_item_id) AS line_no,
        coi.product_id,

        p.product_code AS product_code,
        p.customer_production_id AS customer_production_id,
        p.product_name AS product_name,

        coi.quantity
    FROM customer_order_item coi
    JOIN customer_order co ON co.customer_order_id = coi.customer_order_id
    LEFT JOIN product p ON p.product_id = coi.product_id
    WHERE co.customer_order_id IN ({",".join(["%s"] * len(order_ids))})
    """

    eng = get_engine()
    with eng.connect() as conn:
        df = pd.read_sql_query(q, conn, params=tuple(order_ids))

    # ensure required columns exist (schema差異時不炸)
    for c in ["customer_order_code","customer_order_num","product_code","customer_production_id","product_name"]:
        if c not in df.columns:
            df[c] = None
    return df



@st.cache_data(ttl=15, show_spinner=False)
def fetch_on_hand(product_ids: list[int]) -> pd.DataFrame:
    if not product_ids:
        return pd.DataFrame(columns=["product_id", "on_hand"])

    q = f"""
    SELECT
        l.item_id AS product_id,
        SUM(
            CASE h.io_type
                WHEN 'IN'  THEN  l.qty_PCS
                WHEN 'OUT' THEN -l.qty_PCS
                ELSE l.qty_PCS
            END
        ) AS on_hand
    FROM product_stock_io_head h
    JOIN product_stock_io_line l ON l.psioh_id = h.psioh_id
    WHERE h.status = 'posted'
      AND l.item_id IN ({",".join(["%s"] * len(product_ids))})
      AND (l.reversed_io_id IS NULL)
    GROUP BY l.item_id
    """
    eng = get_engine()
    with eng.connect() as conn:
        return pd.read_sql_query(q, conn, params=tuple(product_ids))


# -----------------------------
# Allocation (Python side)
# -----------------------------
def allocate_preview(items: pd.DataFrame, on_hand_df: pd.DataFrame) -> pd.DataFrame:
    """
    items 欄位要求：
    - customer_order_id, customer_order_num, deliver_date, line_no, product_id, product_name, quantity
    on_hand_df：
    - product_id, on_hand
    """
    if items.empty:
        return items

    items = items.copy()
    items["deliver_date"] = pd.to_datetime(items["deliver_date"])

    # merge on_hand
    on_hand_df = on_hand_df.copy()
    if on_hand_df.empty:
        on_hand_df = pd.DataFrame({"product_id": items["product_id"].unique(), "on_hand": 0})
    items = items.merge(on_hand_df, on="product_id", how="left")
    items["on_hand"] = items["on_hand"].fillna(0).astype(float)

    # sort by rule: deliver_date ASC -> order_id ASC -> line_no ASC
    items = items.sort_values(["deliver_date", "customer_order_id", "line_no"], ascending=[True, True, True])

    # cumulative demand per product
    items["cum_demand"] = items.groupby("product_id")["quantity"].cumsum()

    items["shortage"] = (items["cum_demand"] - items["on_hand"]).clip(lower=0)
    items["balance_after_alloc"] = items["on_hand"] - items["cum_demand"]

    # status: 有庫存 / 部分不足 / 未入庫
    prev_cum = items["cum_demand"] - items["quantity"]
    cond_in_stock = items["on_hand"] >= items["cum_demand"]
    cond_out_of_stock_before = items["on_hand"] < prev_cum  # 這張單之前就已經不夠

    items["stock_status"] = _t("部分不足")
    items.loc[cond_in_stock, "stock_status"] = _t("有庫存")
    items.loc[cond_out_of_stock_before, "stock_status"] = _t("未入庫")

    # 讓數字好看
    for col in ["quantity", "on_hand", "cum_demand", "shortage", "balance_after_alloc"]:
        if col in items.columns:
            items[col] = items[col].astype(float)

    return items


# -----------------------------
# UI - A 區：訂單池
# -----------------------------
with st.container(border=True):
    st.subheader(_t("A｜訂單池（挑單）"))

    # 交期區間(起/迄) + 開單日期(起/迄) + 客戶 + 關鍵字
    col1, col2, col3, col4, col5, col6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.0, 2.0])

    today = date.today()

    with col1:
        deliver_from = st.date_input(_t("交期區間(起)"), value=today)

    with col2:
        deliver_to = st.date_input(_t("交期區間(迄)"), value=today + timedelta(days=30))

    with col3:
        created_from = st.date_input(_t("開單日期(起)"), value=today - timedelta(days=30))

    with col4:
        created_to = st.date_input(_t("開單日期(迄)"), value=today)

    with col5:
        customers = fetch_customers()
        customer_opt = [(_t("全部"), None)]
        if not customers.empty:
            customer_opt += [(r["customer_name"], int(r["customer_id"])) for _, r in customers.iterrows()]
        customer_label = st.selectbox(_t("客戶"), options=[x[0] for x in customer_opt], index=0)
        customer_id = dict(customer_opt).get(customer_label)

    with col6:
        keyword = st.text_input(_t("關鍵字（我方公司訂單號碼/客戶訂單號碼）"), value="").strip()

    st.markdown(_t("**排序規則（固定）**：交期 ASC → 訂單ID ASC → 行號 ASC  ⚠️  同產品多張單會依此順序吃庫存。"))


    try:
        orders = fetch_orders(deliver_from, deliver_to, created_from, created_to, customer_id, keyword)
    except Exception as e:
        st.error(f"{_t('讀取訂單池失敗：')}{e}")
        st.stop()

    if orders.empty:
        st.info(_t("此區間沒有訂單。調整交期或清掉篩選條件再試。"))
        st.stop()

    # 勾選狀態
    if "ot_selected" not in st.session_state:
        st.session_state.ot_selected = set()

    # data_editor 需要一個 bool 欄位
    edit_df = orders.copy()
    edit_df["selected"] = edit_df["customer_order_id"].apply(lambda x: x in st.session_state.ot_selected)

    # 顯示欄位
    show_cols = ["selected", "deliver_date", "customer_name", "customer_order_code", "customer_order_num", "item_count", "total_qty"]
    for c in show_cols:
        if c not in edit_df.columns:
            # 避免 schema 差異炸掉
            edit_df[c] = None

    edited = st.data_editor(
        edit_df[show_cols],
        hide_index=True,
        use_container_width=True,
        column_config={
            "selected": st.column_config.CheckboxColumn(_t("勾選"), help=_t("勾選後按『重新計算』才會跑分配預覽")),
            "deliver_date": st.column_config.DateColumn(_t("交期")),
            "customer_name": st.column_config.TextColumn(_t("客戶")),
            "customer_order_code": st.column_config.TextColumn(_t("我方公司訂單號碼")),
            "customer_order_num": st.column_config.TextColumn(_t("客戶訂單號碼")),
            
            "item_count": st.column_config.NumberColumn(_t("品項數")),
            "total_qty": st.column_config.NumberColumn(_t("總PCS")),
        },
        disabled=(
            ["deliver_date", "customer_name", "customer_order_num", "customer_order_code", "item_count", "total_qty"]
            if CAN_EDIT_PAGE
            else True
        ),
        key="ot_orders_editor",
    )

    b1, b2, b3 = st.columns([1, 1, 4])
    with b1:
        do_preview = st.button(f"🔍 {_t('重新計算（Preview）')}", type="primary", use_container_width=True, disabled=not CAN_EDIT_PAGE)
    with b2:
        clear_sel = st.button(f"🧹 {_t('清空勾選')}", use_container_width=True, disabled=not CAN_EDIT_PAGE)
    with b3:
        st.caption(_t("提示：這頁不寫入 DB；你只是在看『如果照交期順序分配』，庫存是否足夠。"))

    if clear_sel:
        st.session_state.ot_selected = set()
        st.rerun()

    # 先把勾選同步回 session_state（即使未按預覽也同步）
    if CAN_EDIT_PAGE:
        new_selected = set(orders["customer_order_id"].tolist())
        chosen_ids = set(
            orders.loc[edited["selected"].astype(bool).values, "customer_order_id"].astype(int).tolist()
        )
        # 避免 edited 行數與 orders 不一致的意外
        st.session_state.ot_selected = chosen_ids.intersection(new_selected)


# -----------------------------
# UI - B 區：分配結果
# -----------------------------
if do_preview:
    selected_ids = sorted(list(st.session_state.ot_selected))
    if not selected_ids:
        st.warning(_t("你還沒勾選訂單。先勾選，再按『重新計算』。"))
        st.stop()

    with st.spinner(_t("計算庫存分配預覽中…")):
        try:
            items = fetch_order_items(selected_ids)
            if items.empty:
                st.warning(_t("勾選的訂單沒有明細品項（或資料表欄位不符合）。"))
                st.stop()

            product_ids = sorted(items["product_id"].dropna().astype(int).unique().tolist())
            on_hand_df = fetch_on_hand(product_ids)
            result = allocate_preview(items, on_hand_df)

        except Exception as e:
            st.error(f"{_t('計算失敗：')}{e}")
            st.stop()

    st.divider()
    st.subheader(_t("B｜分配結果（預覽）"))

    # 摘要卡片
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(_t("勾選訂單數"), len(selected_ids))
    with c2:
        st.metric(_t("缺口品項數"), int((result["shortage"] > 0).sum()))
    with c3:
        st.metric(_t("缺口總PCS"), float(result["shortage"].sum()))

    
    # (已移除『按產品看』)
    # 下面直接呈現『按訂單看』

    # 每張訂單一個 expander
    for oid in selected_ids:
        sub = result[result["customer_order_id"] == oid].copy()
        if sub.empty:
            continue
        order_num = str(sub["customer_order_num"].iloc[0])
        ddate = sub["deliver_date"].iloc[0].date() if pd.notna(sub["deliver_date"].iloc[0]) else None

        # 訂單摘要：有庫存 / 部分不足 / 未入庫
        status_counts = sub["stock_status"].value_counts().to_dict()
        summary = "｜".join([f"{k}:{v}" for k, v in status_counts.items()])

        title = f"📄 {ddate}｜{order_num}｜{summary}"
        with st.expander(title, expanded=False):
            cols = [
                "line_no",
                "customer_order_code",
                "customer_order_num",
                "product_code",
                "customer_production_id",
                "product_name",
                "quantity",
                "on_hand",
                "cum_demand",
                "shortage",
                "balance_after_alloc",
                "stock_status",
            ]
            # 用 reindex 避免缺欄位 KeyError（缺的欄位會補空值）
            show = sub.reindex(columns=cols).copy()
            show = show.rename(columns={
                "customer_order_code": _t("我方公司訂單號碼"),
                "customer_order_num": _t("客戶訂單號碼"),
                "product_code": _t("我方公司產品號碼"),
                "customer_production_id": _t("客戶料號"),
                "product_name": _t("產品名稱"),
                "quantity": _t("訂購量"),
                "on_hand": _t("現有庫存"),
                "cum_demand": _t("累積需求"),
                "shortage": _t("缺口"),
                "balance_after_alloc": _t("分配後餘額"),
                "stock_status": _t("狀態"),
            })
            st.dataframe(show, use_container_width=True, hide_index=True)


    # drilldown


    # 匯出（先做 CSV，最穩）
    st.divider()
    csv = result.to_csv(index=False).encode("utf-8-sig")
    st.download_button(f"⬇️ {_t('匯出分配結果 CSV')}", data=csv, file_name="order_stock_allocation_preview.csv", mime="text/csv")

else:
    st.info(_t("先在上方『訂單池』勾選訂單，再按『重新計算（Preview）』。"))
