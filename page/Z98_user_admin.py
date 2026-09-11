import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd
import bcrypt

import auth

apply_compact_layout()
from db import get_connection

try:
    from core.i18n import tr as _t
except ImportError:  # pragma: no cover
    def _t(term: str) -> str:
        return term

PAGE_KEY = "Z98_user_admin"

COLUMN_LABELS = {
    "user_id": "使用者 ID",
    "user_code": "使用者代碼",
    "stuff_id": "員工 ID",
    "stuff_name": "員工姓名",
    "username": "帳號",
    "is_active": "啟用",
    "is_admin": "最高權限",
}

st.set_page_config(page_title=_t("使用者管理"), layout="wide")

# --- guard ---
auth.require_login()
me = auth.get_current_user()
if not me.get("is_admin"):
    st.error(_t("你沒有權限使用此頁（僅限最高權限）。"))
    st.stop()

st.title(_t("👤 使用者管理（最高權限）"))
st.caption(_t("新增/啟用帳號、重設密碼、設定 is_active / is_admin。"))

@st.cache_data(ttl=10)
def load_stuff():
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT stuff_id, stuff_name FROM stuff ORDER BY stuff_id",
            conn
        )
    finally:
        conn.close()

@st.cache_data(ttl=10)
def load_users():
    conn = get_connection()
    try:
        return pd.read_sql(
            """
            SELECT u.user_id, u.user_code, u.stuff_id, s.stuff_name, u.username, u.is_active, u.is_admin
            FROM `user` u
            LEFT JOIN stuff s ON s.stuff_id = u.stuff_id
            ORDER BY u.user_id
            """,
            conn
        )
    finally:
        conn.close()

def _current_user_id() -> int:
    """Return current logged-in user's user_id; fallback to admin user_id=1."""
    try:
        return int(me.get("user_id") or 1)
    except Exception:
        return 1


def _make_user_code(stuff_id: int) -> str:
    """Follow existing DB style: user_0001, user_0002..."""
    return f"user_{int(stuff_id):04d}"


def upsert_user_by_stuff(stuff_id: int, username: str, password_plain: str | None, is_active: int, is_admin: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        current_user_id = _current_user_id()

        # username unique check (excluding same stuff_id's current user)
        cur.execute(
            """
            SELECT user_id FROM `user`
            WHERE username = %s AND (stuff_id <> %s OR stuff_id IS NULL)
            """,
            (username, stuff_id)
        )
        if cur.fetchone():
            raise ValueError(_t("此 username 已被其他使用者使用。"))

        password_hash = None
        if password_plain:
            password_hash = bcrypt.hashpw(password_plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # check existing by stuff_id
        cur.execute("SELECT user_id, user_code FROM `user` WHERE stuff_id = %s", (stuff_id,))
        row = cur.fetchone()

        if row:
            # UPDATE
            if password_hash:
                cur.execute(
                    """
                    UPDATE `user`
                    SET username=%s, password_hash=%s, is_active=%s, is_admin=%s,
                        updated_at=NOW(), updated_by=%s
                    WHERE stuff_id=%s
                    """,
                    (username, password_hash, is_active, is_admin, current_user_id, stuff_id)
                )
            else:
                cur.execute(
                    """
                    UPDATE `user`
                    SET username=%s, is_active=%s, is_admin=%s,
                        updated_at=NOW(), updated_by=%s
                    WHERE stuff_id=%s
                    """,
                    (username, is_active, is_admin, current_user_id, stuff_id)
                )
        else:
            # INSERT (password required for new user)
            if not password_hash:
                raise ValueError(_t("新建使用者必須設定密碼。"))

            user_code = _make_user_code(stuff_id)

            # user_code unique check
            cur.execute("SELECT user_id FROM `user` WHERE user_code = %s", (user_code,))
            if cur.fetchone():
                raise ValueError(_t(f"使用者代碼 {user_code} 已存在，請檢查員工是否已經建立帳號。"))

            cur.execute(
                """
                INSERT INTO `user`(
                    user_code, stuff_id, created_at, created_by,
                    username, password_hash, is_active, is_admin
                )
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s)
                """,
                (user_code, stuff_id, current_user_id, username, password_hash, is_active, is_admin)
            )

        conn.commit()
        cur.close()
    finally:
        conn.close()

def reset_password(user_id: int, new_password: str):
    conn = get_connection()
    try:
        pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE `user`
            SET password_hash=%s, updated_at=NOW(), updated_by=%s
            WHERE user_id=%s
            """,
            (pw_hash, _current_user_id(), user_id)
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

def translate_user_headers(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {col: _t(label) for col, label in COLUMN_LABELS.items() if col in df.columns}
    return df.rename(columns=rename_map)

stuff_df = load_stuff()
users_df = load_users()

st.subheader(_t("A) 新增 / 啟用 / 更新使用者（依 stuff）"))

with st.form("create_or_update_user"):
    c1, c2, c3 = st.columns([2, 2, 2])

    with c1:
        stuff_df["label"] = stuff_df.apply(lambda r: f'{int(r["stuff_id"])} | {r["stuff_name"]}', axis=1)
        stuff_label = st.selectbox(_t("選擇員工（stuff）"), stuff_df["label"].tolist())
        stuff_id = int(stuff_label.split("|", 1)[0].strip())

    with c2:
        username = st.text_input(_t("username（唯一）"), placeholder=_t("例如：shambhala"))

    with c3:
        is_active = st.checkbox(_t("啟用 is_active"), value=True)
        is_admin = st.checkbox(_t("最高權限 is_admin"), value=False)

    pw1 = st.text_input(_t("設定/更新密碼（留空=不變更）"), type="password")
    submit = st.form_submit_button(_t("💾 儲存"), type="primary")

if submit:
    try:
        if not username.strip():
            raise ValueError(_t("username 不能空白。"))
        upsert_user_by_stuff(
            stuff_id=stuff_id,
            username=username.strip(),
            password_plain=pw1.strip() if pw1 else None,
            is_active=1 if is_active else 0,
            is_admin=1 if is_admin else 0
        )
        st.cache_data.clear()
        st.success(_t("已儲存 ✅"))
    except Exception as e:
        st.error(str(e))

st.divider()
st.subheader(_t("B) 重設密碼（依 user）"))

users_df["label"] = users_df.apply(
    lambda r: f'{int(r["user_id"])} | {r.get("username") or "(no-username)"} | {r.get("stuff_name") or ""}'.strip(),
    axis=1
)

with st.form("reset_pw"):
    user_label = st.selectbox(_t("選擇使用者"), users_df["label"].tolist())
    target_user_id = int(user_label.split("|", 1)[0].strip())
    new_pw = st.text_input(_t("新密碼"), type="password")
    do = st.form_submit_button(_t("🔁 重設密碼"))

if do:
    try:
        if not new_pw:
            raise ValueError(_t("新密碼不能空白。"))
        reset_password(target_user_id, new_pw)
        st.success(_t("已重設密碼 ✅（請使用者重新登入）"))
    except Exception as e:
        st.error(str(e))

st.divider()
st.subheader(_t("現有使用者列表"))
show_df = translate_user_headers(users_df.copy())
st.dataframe(show_df, use_container_width=True, hide_index=True)
