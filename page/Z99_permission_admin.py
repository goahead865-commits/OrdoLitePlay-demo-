import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd

import auth
from db import get_connection

apply_compact_layout()

try:
    from core.i18n import tr as _t
except ImportError:  # pragma: no cover
    def _t(term: str) -> str:
        return term

PAGE_KEY = "Z99_permission_admin"  # 可選：若你要把這頁也納入 permission_resource

REQUIRED_RESOURCES = [
    # 主資料
    {"resource_code": "P01_product", "resource_name": "P01 產品主檔", "is_active": 1},
    {"resource_code": "P02_product_materials", "resource_name": "P02 產品所需物料", "is_active": 1},
    {"resource_code": "P04_product_price_tier", "resource_name": "P04 產品價格級距設定", "is_active": 1},
    {"resource_code": "C01_material", "resource_name": "C01 原料主檔", "is_active": 1},
    {"resource_code": "C02_supplier", "resource_name": "C02 供應商主檔", "is_active": 1},
    {"resource_code": "C03_customer", "resource_name": "C03 客戶主檔", "is_active": 1},
    {"resource_code": "OC01_our_company_settings", "resource_name": "OC01 我方公司資料", "is_active": 1},

    # 原料 / 庫存
    {"resource_code": "S01_material_stock_io", "resource_name": "S01 原料進出庫", "is_active": 1},
    {"resource_code": "S02_material_inventory_summary", "resource_name": "S02 原料庫存統計", "is_active": 1},
    {"resource_code": "S03_product_stock_io", "resource_name": "S03 產品進出庫", "is_active": 1},
    {"resource_code": "S04_product_inventory_summary", "resource_name": "S04 產品庫存統計", "is_active": 1},

    # 單據 / 訂單
    {"resource_code": "B02_purchase_order_create", "resource_name": "B02 新建與查詢採購單", "is_active": 1},
    {"resource_code": "B03_purchase_arrival_dashboard", "resource_name": "B03 採購到貨總覽", "is_active": 1},
    {"resource_code": "E01_customer_order_create", "resource_name": "E01 新建與查詢客戶訂單", "is_active": 1},
    {"resource_code": "E02_customer_order_progress_dashboard", "resource_name": "E02 客戶訂單完成進度", "is_active": 1},
    {"resource_code": "OT01_order_stock_tracking", "resource_name": "OT01 訂單狀況追蹤（庫存分配預覽）", "is_active": 1},
    {"resource_code": "D02_delivery_entry", "resource_name": "D02 新建送貨單", "is_active": 1},

    # 會計
    {"resource_code": "AP01_accounts_payable", "resource_name": "AP01 應付帳款", "is_active": 1},
    {"resource_code": "AP02_Statement_Page", "resource_name": "AP02 供應商對帳單", "is_active": 1},
    {"resource_code": "AP03_batch_processing_payment_records", "resource_name": "AP03 批量處理付款紀錄", "is_active": 1},
    {"resource_code": "AR01_Accounts Receivable", "resource_name": "AR01 應收帳款", "is_active": 1},
    {"resource_code": "AR02_prepare_accounts_receivable", "resource_name": "AR02 客戶對帳單", "is_active": 1},
    {"resource_code": "AR03_batch_processing_customer_payment_records", "resource_name": "AR03 批量處理收款紀錄", "is_active": 1},

    # 管理
    {"resource_code": "st01_staff_admin", "resource_name": "ST01 員工主檔", "is_active": 1},
    {"resource_code": "Z98_user_admin", "resource_name": "Z98 使用者管理", "is_active": 1},
    {"resource_code": "Z99_permission_admin", "resource_name": "Z99 權限管理", "is_active": 1},
]

st.set_page_config(page_title=_t("權限管理"), layout="wide")

# --------- Guard: 必須登入 + 必須是 admin ---------
auth.require_login()

user = auth.get_current_user()  # dict: {user_id, username, is_admin, stuff_id, stuff_name}
if not user.get("is_admin"):
    st.error(_t("你沒有權限進入此頁（僅限最高權限）。"))
    st.stop()

st.title(_t("🔐 權限管理（以人為單位 / 以頁為單位）"))
st.caption(_t("動作：可看見(can_read) / 可編輯(can_create+can_update) / 可刪除(can_delete) / 可許可(can_approve)"))
st.caption(_t("只顯示已啟用的正式 PAGE_KEY。ST01 因資料庫大小寫規則，固定使用 st01_staff_admin。"))

# --------- Load users + resources ---------
def ensure_required_resources():
    """
    確保權限資源表至少包含目前需要被管理的頁面。
    這樣就算 dump 還沒補 INSERT，Z99 也能先把頁面拉進來管理。
    """
    conn = get_connection()
    try:
        sql = """
        INSERT INTO permission_resource (resource_code, resource_name, is_active)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            resource_name = VALUES(resource_name),
            is_active = VALUES(is_active)
        """
        cur = conn.cursor()
        cur.executemany(
            sql,
            [
                (r["resource_code"], r["resource_name"], int(r.get("is_active", 1)))
                for r in REQUIRED_RESOURCES
            ],
        )
        # 停用舊 KEY / 重複 KEY，避免 Z99 顯示兩個看起來相同的頁面。
        obsolete_codes = [
            "ap_statement_page",
            "B03_purchase_arrival_overview",
            "E02_customer_order_edit",
            "AR_01",
        ]
        cur.executemany(
            "UPDATE permission_resource SET is_active = 0 WHERE resource_code = %s",
            [(code,) for code in obsolete_codes],
        )

        conn.commit()
        cur.close()
    finally:
        conn.close()

@st.cache_data(ttl=10)
def load_users():
    conn = get_connection()
    try:
        q = """
        SELECT u.user_id, u.username, u.is_active, u.is_admin, u.stuff_id, s.stuff_name
        FROM user u
        LEFT JOIN stuff s ON s.stuff_id = u.stuff_id
        ORDER BY u.user_id
        """
        df = pd.read_sql(q, conn)
        return df
    finally:
        conn.close()

@st.cache_data(ttl=10)
def load_resources():
    conn = get_connection()
    try:
        q = """
        SELECT resource_id, resource_code, resource_name, is_active
        FROM permission_resource
        WHERE is_active = 1
        ORDER BY resource_code
        """
        return pd.read_sql(q, conn)
    finally:
        conn.close()

def load_overrides(target_user_id: int):
    conn = get_connection()
    try:
        # 用 GROUP BY 合併可能殘留的舊重複資料。
        # MAX() 的意思是：只要曾經有一筆開啟，就先視為開啟；
        # 下一次儲存時會用 delete + insert 清乾淨。
        q = """
        SELECT
            resource_id,
            MAX(can_read) AS can_read,
            MAX(can_create) AS can_create,
            MAX(can_update) AS can_update,
            MAX(can_delete) AS can_delete,
            MAX(can_approve) AS can_approve
        FROM user_permission_override
        WHERE user_id = %s
        GROUP BY resource_id
        """
        cur = conn.cursor(dictionary=True)
        cur.execute(q, (target_user_id,))
        rows = cur.fetchall()
        cur.close()
        return {int(r["resource_id"]): r for r in rows}
    finally:
        conn.close()

def upsert_overrides(target_user_id: int, payload_rows: list[dict]):
    """
    payload_rows: [{resource_id, can_read, can_create, can_update, can_delete, can_approve}, ...]

    注意：
    這裡不用 ON DUPLICATE KEY UPDATE。
    因為若 user_permission_override 沒有 UNIQUE(user_id, resource_id)，
    ON DUPLICATE KEY 不會更新，反而會一直新增重複列，造成「看起來沒存」。

    Z99 是整張權限表一次儲存，所以最穩的做法是：
    1. 先刪除該使用者既有 override
    2. 再整批寫入目前畫面設定
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM user_permission_override WHERE user_id = %s",
            (int(target_user_id),),
        )

        sql = """
        INSERT INTO user_permission_override
            (user_id, resource_id, can_read, can_create, can_update, can_delete, can_approve)
        VALUES
            (%s,%s,%s,%s,%s,%s,%s)
        """

        data = [
            (
                int(target_user_id),
                int(r["resource_id"]),
                int(r["can_read"]),
                int(r["can_create"]),
                int(r["can_update"]),
                int(r["can_delete"]),
                int(r["can_approve"]),
            )
            for r in payload_rows
        ]

        if data:
            cur.executemany(sql, data)

        conn.commit()
        cur.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

ensure_required_resources()
users_df = load_users()
res_df = load_resources()

# 選使用者（只列出 is_active=1 的）
active_users = users_df[users_df["is_active"] == 1].copy()
active_users["label"] = active_users.apply(
    lambda r: f'{int(r["user_id"])} | {r["username"] or "(no-username)"} | {r["stuff_name"] or ""}'.strip(),
    axis=1
)

colA, colB = st.columns([2, 3], vertical_alignment="top")
with colA:
    user_labels = active_users["label"].tolist()
    current_user_id = int(user.get("user_id") or 0)

    # 預設選目前登入者；儲存後則保留剛剛編輯的目標使用者。
    default_target_user_id = int(st.session_state.get("z99_target_user_id", current_user_id) or current_user_id)

    default_index = 0
    for i, label in enumerate(user_labels):
        try:
            label_user_id = int(str(label).split("|", 1)[0].strip())
            if label_user_id == default_target_user_id:
                default_index = i
                break
        except Exception:
            pass

    selected_label = st.selectbox(
        _t("選擇要編輯權限的使用者"),
        user_labels,
        index=default_index if user_labels else 0,
        key="z99_selected_user_label",
    )
    target_user_id = int(selected_label.split("|", 1)[0].strip())
    st.session_state["z99_target_user_id"] = target_user_id

with colB:
    target_row = users_df[users_df["user_id"] == target_user_id].iloc[0].to_dict()
    st.markdown(
        f"""
        **{_t("目標使用者")}**  
        - user_id: `{target_row["user_id"]}`  
        - username: `{target_row["username"]}`  
        - stuff_name: `{target_row.get("stuff_name")}`  
        - is_admin: `{target_row["is_admin"]}`  
        """
    )
    if int(target_row["user_id"]) == int(user.get("user_id") or 0):
        st.caption(_t("目前正在編輯：你自己的帳號"))

overrides = load_overrides(target_user_id)

# 組合表格：每個 resource 一列，4個勾勾（看/編/刪/許可）
table_rows = []
for _, r in res_df.iterrows():
    rid = int(r["resource_id"])
    o = overrides.get(rid, {})
    can_read = int(o.get("can_read", 0) or 0)
    can_create = int(o.get("can_create", 0) or 0)
    can_update = int(o.get("can_update", 0) or 0)
    can_delete = int(o.get("can_delete", 0) or 0)
    can_approve = int(o.get("can_approve", 0) or 0)

    # UI 的「可編輯」= create 或 update
    can_edit_ui = 1 if (can_create or can_update) else 0

    table_rows.append(
        {
            "resource_id": rid,
            "page_key": r["resource_code"],
            "page_name": r["resource_name"],
            _t("可看見"): bool(can_read),
            _t("可編輯"): bool(can_edit_ui),
            _t("可刪除"): bool(can_delete),
            _t("可許可"): bool(can_approve),
        }
    )

df_ui = pd.DataFrame(table_rows)

st.divider()
st.subheader(_t("頁面權限（勾選後按儲存）"))

edited = st.data_editor(
    df_ui,
    use_container_width=True,
    hide_index=True,
    disabled=["resource_id", "page_key", "page_name"],
    column_config={
        "page_key": st.column_config.TextColumn("PAGE_KEY", width="medium"),
        "page_name": st.column_config.TextColumn(_t("頁面名稱"), width="large"),
    },
)

# 轉回 payload（套你定的規則：任一動作=1 → can_read=1）
payload = []
for _, row in edited.iterrows():
    rid = int(row["resource_id"])
    can_read = 1 if bool(row[_t("可看見")]) else 0
    can_edit = 1 if bool(row[_t("可編輯")]) else 0
    can_delete = 1 if bool(row[_t("可刪除")]) else 0
    can_approve = 1 if bool(row[_t("可許可")]) else 0

    can_create = can_edit
    can_update = can_edit

    # 強制依賴：只要有 create/update/delete/approve 任一，就必須可看見
    if can_create or can_update or can_delete or can_approve:
        can_read = 1

    payload.append(
        {
            "resource_id": rid,
            "can_read": can_read,
            "can_create": can_create,
            "can_update": can_update,
            "can_delete": can_delete,
            "can_approve": can_approve,
        }
    )

col1, col2 = st.columns([1, 3])
with col1:
    if st.button(_t("💾 儲存權限"), type="primary"):
        upsert_overrides(target_user_id, payload)
        st.session_state["z99_target_user_id"] = int(target_user_id)
        st.cache_data.clear()
        st.success(_t("已儲存 ✅"))
        st.rerun()

with col2:
    st.info(_t("提示：你現在走 A 方案（只看 user_permission_override）。角色(role)先不用管。"))
