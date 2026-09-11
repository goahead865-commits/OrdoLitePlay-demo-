import datetime as dt
import math
from typing import Optional

import pandas as pd
import streamlit as st
from compact_layout import apply_compact_layout
from sqlalchemy import text

apply_compact_layout()

try:
    import auth
except ImportError:  # pragma: no cover
    auth = None

try:
    from db import get_engine
except ImportError:  # pragma: no cover
    get_engine = None

try:
    from core.i18n import tr as _t
except ImportError:  # pragma: no cover
    def _t(term: str) -> str:
        return term


PAGE_TITLE = "ST01 員工資料維護"
PAGE_KEY = "st01_staff_admin"

STATUS_LABELS = {
    "still": "在職",
    "inactive": "停用",
    "leave": "離職",
}

COLUMN_LABELS = {
    "stuff_id": "員工主鍵 ID",
    "stuff_code": "員工代碼",
    "stuff_name": "員工姓名",
    "stuff_birthday": "生日",
    "ID/passport number": "身分證 / 護照號碼",
    "stuff_address": "戶籍地址 / 地址",
    "contact_address": "聯絡地址",
    "stuff_phone": "電話",
    "stuff_department": "部門 ID",
    "created_at": "建立時間",
    "create_by_id": "建立者 ID",
    "creator_name": "建立者",
    "status": "狀態",
    "updated_at": "更新時間",
    "updated_by_id": "更新者 ID",
    "department_code": "部門代碼",
    "department_name": "部門",
}

STAFF_COLUMNS = [
    "stuff_id",
    "stuff_code",
    "stuff_name",
    "stuff_birthday",
    "ID/passport number",
    "stuff_address",
    "contact_address",
    "stuff_phone",
    "stuff_department",
    "created_at",
    "create_by_id",
    "status",
    "updated_at",
    "updated_by_id",
]

DISPLAY_COLUMNS = [
    "stuff_id",
    "stuff_code",
    "stuff_name",
    "stuff_birthday",
    "ID/passport number",
    "stuff_address",
    "contact_address",
    "stuff_phone",
    "department_name",
    "created_at",
    "creator_name",
    "status",
    "updated_at",
    "updated_by_id",
]

st.set_page_config(page_title=PAGE_TITLE, layout="wide")

if auth is not None and hasattr(auth, "require_read"):
    auth.require_read(PAGE_KEY)


@st.cache_resource
def safe_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        s = str(value).strip()
        if s == "" or s.lower() == "nan":
            return default
        return int(float(s))
    except Exception:
        return default



def status_to_label(status_value: str) -> str:
    raw = str(status_value or "").strip()
    if not raw:
        return ""
    zh_label = STATUS_LABELS.get(raw, raw)
    return _t(zh_label)



def translate_df_headers(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {col: _t(label) for col, label in COLUMN_LABELS.items() if col in df.columns for label in [COLUMN_LABELS[col]]}
    return df.rename(columns=rename_map)



def get_db_engine():
    if get_engine is None:
        raise RuntimeError(_t("找不到 db.get_engine()，請確認專案內已有 db.py。"))
    return get_engine()


@st.cache_data(ttl=300)
def load_departments() -> pd.DataFrame:
    sql = """
        SELECT
            depratment_id,
            department_code,
            department_name
        FROM department
        ORDER BY department_code, department_name
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


@st.cache_data(ttl=300)
def load_user_display_map() -> dict[int, str]:
    """Return user_id -> stuff_name/username display map for creator/updater presentation."""
    sql = """
        SELECT
            u.user_id,
            u.username,
            s.stuff_name
        FROM `user` u
        LEFT JOIN stuff s
               ON s.stuff_id = u.stuff_id
        ORDER BY u.user_id
    """
    with get_db_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)

    result: dict[int, str] = {}
    for _, r in df.iterrows():
        uid = safe_int(r.get("user_id"), 0)
        if uid <= 0:
            continue
        stuff_name = str(r.get("stuff_name") or "").strip()
        username = str(r.get("username") or "").strip()
        result[uid] = stuff_name or username or f"User#{uid}"
    return result


def get_user_display_name(user_id: Optional[int]) -> str:
    uid = safe_int(user_id, 0)
    if uid <= 0:
        return ""
    return load_user_display_map().get(uid, f"User#{uid}")


def get_current_user_id() -> int:
    if auth is not None and hasattr(auth, "get_current_user"):
        try:
            user = auth.get_current_user() or {}
            uid = safe_int(user.get("user_id"), 0)
            if uid > 0:
                return uid
        except Exception:
            pass
    return safe_int(st.session_state.get("user_id"), 1) or 1


@st.cache_data(ttl=180)
def load_staff(keyword: str = "", department_id: Optional[int] = None, status: str = "") -> pd.DataFrame:
    where_parts = ["1=1"]
    params: dict = {}

    if keyword:
        where_parts.append(
            """
            (
                s.stuff_code LIKE :kw
                OR s.stuff_name LIKE :kw
                OR COALESCE(s.`ID/passport number`, '') LIKE :kw
                OR COALESCE(s.stuff_phone, '') LIKE :kw
                OR COALESCE(s.stuff_address, '') LIKE :kw
                OR COALESCE(s.contact_address, '') LIKE :kw
            )
            """
        )
        params["kw"] = f"%{keyword.strip()}%"
    if department_id:
        where_parts.append("s.stuff_department = :department_id")
        params["department_id"] = int(department_id)
    if status:
        where_parts.append("COALESCE(s.status, '') = :status")
        params["status"] = status.strip()

    sql = f"""
        SELECT
            s.stuff_id,
            s.stuff_code,
            s.stuff_name,
            s.stuff_birthday,
            s.`ID/passport number`,
            s.stuff_address,
            s.contact_address,
            s.stuff_phone,
            s.stuff_department,
            s.created_at,
            s.create_by_id,
            s.status,
            s.updated_at,
            s.updated_by_id,
            d.department_code,
            d.department_name,
            COALESCE(creator_stuff.stuff_name, creator_user.username, '') AS creator_name,
            COALESCE(updater_stuff.stuff_name, updater_user.username, '') AS updater_name
        FROM stuff s
        LEFT JOIN department d
               ON d.depratment_id = s.stuff_department
        LEFT JOIN `user` creator_user
               ON creator_user.user_id = s.create_by_id
        LEFT JOIN stuff creator_stuff
               ON creator_stuff.stuff_id = creator_user.stuff_id
        LEFT JOIN `user` updater_user
               ON updater_user.user_id = s.updated_by_id
        LEFT JOIN stuff updater_stuff
               ON updater_stuff.stuff_id = updater_user.stuff_id
        WHERE {' AND '.join(where_parts)}
        ORDER BY s.stuff_id DESC
    """
    with get_db_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    if not df.empty:
        for col in ["stuff_birthday", "created_at", "updated_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data(ttl=60)
def get_status_options() -> list[str]:
    sql = """
        SELECT DISTINCT COALESCE(status, '') AS status_value
        FROM stuff
        ORDER BY status_value
    """
    with get_db_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)
    options = [x for x in df["status_value"].dropna().astype(str).tolist() if x != ""]
    seed = ["still", "inactive", "leave"]
    for item in seed:
        if item not in options:
            options.append(item)
    return sorted(set(options), key=lambda x: (x == "", x))



def clear_staff_cache() -> None:
    load_staff.clear()
    load_departments.clear()
    load_user_display_map.clear()
    get_status_options.clear()



def get_next_stuff_code() -> str:
    sql = """
        SELECT stuff_code
        FROM stuff
        WHERE stuff_code REGEXP '^s_[0-9]+$'
        ORDER BY CAST(SUBSTRING(stuff_code, 3) AS UNSIGNED) DESC
        LIMIT 1
    """
    with get_db_engine().connect() as conn:
        value = conn.execute(text(sql)).scalar()
    if not value:
        return "s_0001"
    try:
        n = int(str(value).split("_")[-1]) + 1
    except Exception:
        n = 1
    return f"s_{n:04d}"



def normalize_timestamp_str(value: str | None, *, default_now: bool = False) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        if default_now:
            return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return None

    try:
        if len(raw) == 10:
            parsed = dt.datetime.strptime(raw, "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d 00:00:00")
        parsed = dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            parsed = dt.datetime.strptime(raw, "%Y-%m-%d %H:%M")
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError(_t("時間格式請用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM[:SS]")) from exc



def date_to_python(value) -> dt.date:
    if value is None or value == "":
        return dt.date.today()
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return pd.to_datetime(value).date()



def maybe_int(value) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)



def build_payload(prefix: str, widget_prefix: Optional[str] = None) -> dict:
    widget_prefix = widget_prefix or prefix

    birthday = date_to_python(st.session_state[f"{widget_prefix}_stuff_birthday"])
    created_at = normalize_timestamp_str(st.session_state.get(f"{widget_prefix}_created_at"), default_now=True)
    updated_at = normalize_timestamp_str(st.session_state.get(f"{widget_prefix}_updated_at"), default_now=False)

    create_by_id_val = get_current_user_id() if prefix == "new" else safe_int(st.session_state.get(f"{widget_prefix}_create_by_id"), get_current_user_id())

    payload = {
        "stuff_code": st.session_state[f"{widget_prefix}_stuff_code"].strip(),
        "stuff_name": st.session_state[f"{widget_prefix}_stuff_name"].strip(),
        "stuff_birthday": birthday,
        "id_passport_number": (st.session_state.get(f"{widget_prefix}_id_passport_number") or "").strip() or None,
        "stuff_address": (st.session_state.get(f"{widget_prefix}_stuff_address") or "").strip() or None,
        "contact_address": (st.session_state.get(f"{widget_prefix}_contact_address") or "").strip() or None,
        "stuff_phone": (st.session_state.get(f"{widget_prefix}_stuff_phone") or "").strip() or None,
        "stuff_department": int(st.session_state[f"{widget_prefix}_stuff_department"]),
        "created_at": created_at,
        "create_by_id": int(create_by_id_val),
        "status": (st.session_state.get(f"{widget_prefix}_status") or "").strip() or "still",
        "updated_at": updated_at,
        "updated_by_id": maybe_int(st.session_state.get(f"{widget_prefix}_updated_by_id")),
    }

    if not payload["stuff_code"]:
        raise ValueError(_t("員工代碼不可為空。"))
    if not payload["stuff_name"]:
        raise ValueError(_t("員工姓名不可為空。"))

    return payload



def insert_staff(payload: dict) -> None:
    if auth is not None and hasattr(auth, "require_edit"):
        auth.require_edit(PAGE_KEY)
    sql = """
        INSERT INTO stuff (
            stuff_code,
            stuff_name,
            stuff_birthday,
            `ID/passport number`,
            stuff_address,
            contact_address,
            stuff_phone,
            stuff_department,
            created_at,
            create_by_id,
            status,
            updated_at,
            updated_by_id
        )
        VALUES (
            :stuff_code,
            :stuff_name,
            :stuff_birthday,
            :id_passport_number,
            :stuff_address,
            :contact_address,
            :stuff_phone,
            :stuff_department,
            :created_at,
            :create_by_id,
            :status,
            :updated_at,
            :updated_by_id
        )
    """
    with get_db_engine().begin() as conn:
        conn.execute(text(sql), payload)
    clear_staff_cache()



def update_staff(staff_id: int, payload: dict) -> None:
    if auth is not None and hasattr(auth, "require_edit"):
        auth.require_edit(PAGE_KEY)
    payload = payload.copy()
    payload["stuff_id"] = int(staff_id)
    sql = """
        UPDATE stuff
        SET
            stuff_code = :stuff_code,
            stuff_name = :stuff_name,
            stuff_birthday = :stuff_birthday,
            `ID/passport number` = :id_passport_number,
            stuff_address = :stuff_address,
            contact_address = :contact_address,
            stuff_phone = :stuff_phone,
            stuff_department = :stuff_department,
            created_at = :created_at,
            status = :status,
            updated_at = :updated_at,
            updated_by_id = :updated_by_id
        WHERE stuff_id = :stuff_id
    """
    with get_db_engine().begin() as conn:
        conn.execute(text(sql), payload)
    clear_staff_cache()



def delete_staff(staff_id: int) -> str:
    """
    刪除員工。

    ERP 正式資料不建議硬刪。
    若該員工已被 our_company / user / 單據等外鍵引用，MySQL 會擋硬刪。
    遇到外鍵限制時，改成 soft delete：status = 'inactive'。
    """
    if auth is not None and hasattr(auth, "require_delete"):
        auth.require_delete(PAGE_KEY)

    staff_id = int(staff_id)
    user_id = get_current_user_id()

    delete_sql = "DELETE FROM stuff WHERE stuff_id = :stuff_id"
    soft_delete_sql = """
        UPDATE stuff
        SET status = 'inactive',
            updated_at = NOW(),
            updated_by_id = :updated_by_id
        WHERE stuff_id = :stuff_id
    """

    try:
        with get_db_engine().begin() as conn:
            conn.execute(text(delete_sql), {"stuff_id": staff_id})
        clear_staff_cache()
        return "deleted"
    except Exception as exc:
        msg = str(exc)
        # 1451 = Cannot delete or update a parent row: a foreign key constraint fails
        if "1451" not in msg and "foreign key constraint fails" not in msg.lower():
            raise

        with get_db_engine().begin() as conn:
            conn.execute(
                text(soft_delete_sql),
                {"stuff_id": staff_id, "updated_by_id": int(user_id)},
            )
        clear_staff_cache()
        return "deactivated"



def render_staff_fields(prefix: str, departments_df: pd.DataFrame, row: Optional[pd.Series], *, is_new: bool = False) -> None:
    status_options = get_status_options()
    user_id_default = get_current_user_id()

    # 編輯模式下，每個員工使用不同 widget key prefix。
    # 否則 Streamlit 會保留上一位員工的 edit_* widget state，導致選人後欄位不會跳。
    if is_new:
        widget_prefix = prefix
    else:
        row_id = safe_int(row.get("stuff_id"), 0) if row is not None else 0
        widget_prefix = f"{prefix}_{row_id}"

    dep_options = {
        int(r["depratment_id"]): f'{r["department_code"]}｜{r["department_name"]}'
        for _, r in departments_df.iterrows()
    }
    dep_ids = list(dep_options.keys())
    if not dep_ids:
        st.error(_t("部門主檔是空的，這頁不能正常新增或編輯。"))
        st.stop()

    row_dict = row.to_dict() if row is not None else {}
    default_dep = int(row_dict.get("stuff_department") or dep_ids[0])
    if default_dep not in dep_options:
        default_dep = dep_ids[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input(_t("員工代碼"), key=f"{widget_prefix}_stuff_code", value=str(row_dict.get("stuff_code") or (get_next_stuff_code() if is_new else "")))
    with col2:
        st.text_input(_t("員工姓名"), key=f"{widget_prefix}_stuff_name", value=str(row_dict.get("stuff_name") or ""))
    with col3:
        st.date_input(_t("生日"), key=f"{widget_prefix}_stuff_birthday", value=date_to_python(row_dict.get("stuff_birthday")))

    col4, col5, col6 = st.columns(3)
    with col4:
        st.text_input(_t("身分證 / 護照號碼"), key=f"{widget_prefix}_id_passport_number", value=str(row_dict.get("ID/passport number") or ""))
    with col5:
        dept_index = dep_ids.index(default_dep)
        st.selectbox(
            _t("部門"),
            options=dep_ids,
            format_func=lambda x: dep_options.get(x, str(x)),
            index=dept_index,
            key=f"{widget_prefix}_stuff_department",
        )
    with col6:
        current_status = str(row_dict.get("status") or "still")
        if current_status not in status_options:
            status_options = status_options + [current_status]
        st.selectbox(
            _t("狀態"),
            options=status_options,
            index=status_options.index(current_status),
            format_func=status_to_label,
            key=f"{widget_prefix}_status",
        )

    st.text_input(_t("戶籍地址 / 地址"), key=f"{widget_prefix}_stuff_address", value=str(row_dict.get("stuff_address") or ""))
    st.text_input(_t("聯絡地址"), key=f"{widget_prefix}_contact_address", value=str(row_dict.get("contact_address") or ""))
    st.text_input(_t("電話"), key=f"{widget_prefix}_stuff_phone", value=str(row_dict.get("stuff_phone") or ""))

    col7, col8, col9, col10 = st.columns(4)

    creator_id = user_id_default if is_new else safe_int(row_dict.get("create_by_id"), user_id_default)
    st.session_state[f"{widget_prefix}_create_by_id"] = creator_id
    creator_display = get_user_display_name(creator_id)

    with col7:
        st.text_input(_t("建立者"), value=creator_display, disabled=True, key=f"{widget_prefix}_creator_display")
    with col8:
        st.text_input(
            _t("建立時間"),
            key=f"{widget_prefix}_created_at",
            value="" if pd.isna(row_dict.get("created_at")) else str(pd.to_datetime(row_dict.get("created_at")).strftime("%Y-%m-%d %H:%M:%S")),
            help=_t("格式：YYYY-MM-DD HH:MM:SS，留白則新增時自動帶現在時間。"),
        )
    with col9:
        st.number_input(_t("更新者 ID"), min_value=0, step=1, key=f"{widget_prefix}_updated_by_id", value=safe_int(row_dict.get("updated_by_id"), 0))
    with col10:
        st.text_input(
            _t("更新時間"),
            key=f"{widget_prefix}_updated_at",
            value="" if pd.isna(row_dict.get("updated_at")) else str(pd.to_datetime(row_dict.get("updated_at")).strftime("%Y-%m-%d %H:%M:%S")),
            help=_t("格式：YYYY-MM-DD HH:MM:SS，可留白。"),
        )

    if row is not None:
        st.text_input(_t("員工主鍵 ID（唯讀）"), value=str(int(row_dict.get("stuff_id"))), disabled=True)




def clear_edit_widget_state() -> None:
    """
    切換要編輯的員工時，清掉 edit_ 開頭的 widget 狀態。
    否則 Streamlit 會保留上一位員工的表單輸入值，看起來像選人後不會自己跳。
    """
    for key in list(st.session_state.keys()):
        if str(key).startswith("edit_"):
            del st.session_state[key]

    st.session_state.pop("stuff_delete_confirm", None)
    st.session_state["stuff_edit_form_nonce"] = int(st.session_state.get("stuff_edit_form_nonce", 0)) + 1


def on_selected_staff_change() -> None:
    clear_edit_widget_state()


def main():
    st.title(_t(PAGE_TITLE))
    st.caption(_t("可查詢、檢視、新增、編輯員工主檔。若員工不再使用，請將狀態改為停用或離職。"))

    st.session_state.setdefault("stuff_edit_form_nonce", 0)

    departments_df = load_departments()

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.6, 1.6, 1.4, 1.2])
        with c1:
            keyword = st.text_input(_t("關鍵字"), placeholder=_t("員工代碼 / 姓名 / 身分證 / 電話 / 地址"))
        with c2:
            dep_map = {0: _t("全部部門")}
            dep_map.update({int(r["depratment_id"]): f'{r["department_code"]}｜{r["department_name"]}' for _, r in departments_df.iterrows()})
            dep_options = list(dep_map.keys())
            department_id = st.selectbox(_t("部門"), dep_options, format_func=lambda x: dep_map[x], index=0)
        with c3:
            status_options = [""] + get_status_options()
            selected_status = st.selectbox(
                _t("狀態"),
                status_options,
                format_func=lambda x: _t("全部狀態") if x == "" else status_to_label(x),
                index=0,
            )
        with c4:
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if st.button(_t("重新整理"), use_container_width=True):
                clear_staff_cache()
                st.rerun()

    staff_df = load_staff(keyword=keyword, department_id=(department_id or None), status=selected_status)

    st.markdown(f"### {_t('員工清單')}")
    if staff_df.empty:
        st.info(_t("查無員工資料。先新增一筆，別讓這頁像空辦公桌。"))
    else:
        show_df = staff_df.copy()
        if "stuff_birthday" in show_df.columns:
            show_df["stuff_birthday"] = pd.to_datetime(show_df["stuff_birthday"], errors="coerce").dt.strftime("%Y-%m-%d")
        for col in ["created_at", "updated_at"]:
            if col in show_df.columns:
                show_df[col] = pd.to_datetime(show_df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        if "status" in show_df.columns:
            show_df["status"] = show_df["status"].apply(status_to_label)
        # 先用原始欄位挑出真正要顯示的欄位，再改表頭。
        # 不要先整張表 rename，否則隱藏欄位 stuff_department/create_by_id
        # 會跟顯示欄位 department_name/creator_name 一起變成「部門」「建立者」，
        # PyArrow 會因為重複欄名直接報錯。
        display_raw_cols = [col for col in DISPLAY_COLUMNS if col in show_df.columns]
        display_df = show_df[display_raw_cols].copy()
        display_df = translate_df_headers(display_df)
        display_df = display_df.loc[:, ~display_df.columns.duplicated()]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=220)

    options_df = staff_df[["stuff_id", "stuff_code", "stuff_name"]].copy() if not staff_df.empty else pd.DataFrame(columns=["stuff_id", "stuff_code", "stuff_name"])
    choice_map = {
        int(r["stuff_id"]): f'{int(r["stuff_id"])}｜{r["stuff_code"]}｜{r["stuff_name"]}'
        for _, r in options_df.iterrows()
    }

    tab1, tab2 = st.tabs([_t("編輯 / 刪除既有員工"), _t("新增員工")])

    with tab1:
        if staff_df.empty:
            st.info(_t("目前沒有可編輯資料。"))
        else:
            selected_id = st.selectbox(
                _t("選擇員工"),
                options=list(choice_map.keys()),
                format_func=lambda x: choice_map[x],
                key="stuff_edit_id",
            )

            # 這裡不用只靠 on_change；直接比對上一輪選取 ID。
            # 一旦換人，就在表單渲染前清掉舊 edit widget state。
            previous_selected_id = st.session_state.get("stuff_edit_last_selected_id")
            if previous_selected_id != selected_id:
                clear_edit_widget_state()
                st.session_state["stuff_edit_last_selected_id"] = selected_id
                st.rerun()

            selected_row = staff_df.loc[staff_df["stuff_id"] == selected_id].iloc[0]
            edit_widget_prefix = f"edit_{int(selected_id)}"

            with st.form(f"stuff_edit_form_{selected_id}_{st.session_state.get('stuff_edit_form_nonce', 0)}", clear_on_submit=False):
                render_staff_fields("edit", departments_df, selected_row, is_new=False)
                b1, _ = st.columns([1.2, 5])
                save_clicked = b1.form_submit_button(_t("儲存修改"), use_container_width=True)
                if save_clicked:
                    try:
                        payload = build_payload("edit", widget_prefix=edit_widget_prefix)
                        if int(st.session_state.get(f"{edit_widget_prefix}_updated_by_id", 0) or 0) == 0:
                            payload["updated_by_id"] = int(st.session_state.get("user_id", 1) or 1)
                        if not payload["updated_at"]:
                            payload["updated_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        update_staff(selected_id, payload)
                        st.success(_t("員工資料已更新。"))
                        st.rerun()
                    except Exception as exc:
                        st.error(f"{_t('更新失敗：')}{exc}")


    with tab2:
        with st.form("stuff_add_form", clear_on_submit=False):
            render_staff_fields("new", departments_df, None, is_new=True)
            add_clicked = st.form_submit_button(_t("新增員工"), use_container_width=True)
            if add_clicked:
                try:
                    payload = build_payload("new")
                    payload["updated_at"] = payload["updated_at"] or None
                    if (st.session_state.get("new_updated_by_id") or 0) == 0:
                        payload["updated_by_id"] = None
                    insert_staff(payload)
                    st.success(_t("員工資料已新增。"))
                    for key in list(st.session_state.keys()):
                        if key.startswith("new_"):
                            del st.session_state[key]
                    st.rerun()
                except Exception as exc:
                    st.error(f"{_t('新增失敗：')}{exc}")


if __name__ == "__main__":
    main()
