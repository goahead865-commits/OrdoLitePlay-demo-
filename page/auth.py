import os
import bcrypt
import streamlit as st
from typing import Dict, Tuple, Any

from db import get_connection

# ---------- Session helpers ----------
def require_login():
    if not st.session_state.get("user_id"):
        st.warning("尚未登入，請先登入。")
        st.stop()

def logout():
    for k in ["user_id", "username", "current_user", "perm_map"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

def get_current_user() -> Dict[str, Any]:
    """
    Returns dict: {user_id, username, is_admin, stuff_id, stuff_name}
    Cached in st.session_state['current_user'].
    """
    require_login()
    if st.session_state.get("current_user"):
        return st.session_state["current_user"]

    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT u.user_id, u.username, u.is_admin, u.stuff_id, s.stuff_name
            FROM user u
            LEFT JOIN stuff s ON s.stuff_id = u.stuff_id
            WHERE u.user_id = %s
            """,
            (st.session_state["user_id"],),
        )
        row = cur.fetchone() or {}
        cur.close()
        st.session_state["current_user"] = row
        return row
    finally:
        conn.close()

# ---------- Auth ----------
def login(username: str, password: str) -> Tuple[bool, str]:
    username = (username or "").strip()
    if not username or not password:
        return False, "請輸入帳號與密碼。"

    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT user_id, username, password_hash, is_active
            FROM user
            WHERE username = %s
            """,
            (username,),
        )
        row = cur.fetchone()
        cur.close()

        if not row:
            return False, "帳號不存在。"
        if int(row.get("is_active") or 0) != 1:
            return False, "此帳號已停用。"
        ph = row.get("password_hash") or ""
        if not ph:
            return False, "此帳號尚未設定密碼。"

        ok = bcrypt.checkpw(password.encode("utf-8"), ph.encode("utf-8"))
        if not ok:
            return False, "密碼錯誤。"

        st.session_state["user_id"] = int(row["user_id"])
        st.session_state["username"] = row["username"]
        # clear caches
        st.session_state.pop("current_user", None)
        st.session_state.pop("perm_map", None)
        return True, ""
    finally:
        conn.close()

# ---------- Permissions (A: override-only via view) ----------
def _load_perm_map(user_id: int) -> Dict[str, Dict[str, int]]:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT resource_code, can_read, can_create, can_update, can_delete, can_approve
            FROM v_user_permission_effective
            WHERE user_id = %s
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        cur.close()
        m = {}
        for r in rows:
            code = r["resource_code"]
            m[code] = {
                "can_read": int(r.get("can_read") or 0),
                "can_create": int(r.get("can_create") or 0),
                "can_update": int(r.get("can_update") or 0),
                "can_delete": int(r.get("can_delete") or 0),
                "can_approve": int(r.get("can_approve") or 0),
            }
        return m
    finally:
        conn.close()

def get_permissions_map() -> Dict[str, Dict[str, int]]:
    require_login()
    if st.session_state.get("perm_map"):
        return st.session_state["perm_map"]
    m = _load_perm_map(int(st.session_state["user_id"]))
    st.session_state["perm_map"] = m
    return m

def _require(page_key: str, predicate, message: str):
    pm = get_permissions_map()
    p = pm.get(page_key, {})
    if not predicate(p):
        st.error(message)
        st.stop()

def require_read(page_key: str):
    _require(page_key, lambda p: p.get("can_read", 0) == 1, f"你沒有權限看此頁：{page_key}")

def require_edit(page_key: str):
    _require(
        page_key,
        lambda p: (p.get("can_create", 0) == 1) or (p.get("can_update", 0) == 1),
        f"你沒有權限編輯此頁：{page_key}",
    )

def require_delete(page_key: str):
    _require(page_key, lambda p: p.get("can_delete", 0) == 1, f"你沒有權限刪除此頁：{page_key}")

def require_approve(page_key: str):
    _require(page_key, lambda p: p.get("can_approve", 0) == 1, f"你沒有權限許可/核可此頁：{page_key}")
