import streamlit as st
import auth
from compact_layout import apply_compact_layout

apply_compact_layout()

# NOTE: set_page_config may be ignored if already set elsewhere (Streamlit only allows it once per app run).
# We'll enforce width via CSS regardless.
st.set_page_config(page_title="登入 OrdoLite", layout="wide")

st.markdown(
    """
    <style>
      /* ✅ Force the main content area to a fixed max width (works even if global layout is wide) */
      .main .block-container,
      section.main > div,
      div.block-container {
        max-width: 640px !important;
        margin-left: auto !important;
        margin-right: auto !important;
      padding-top: 0 !important;
        padding-bottom: 2rem !important;
      }

      /* Optional: make the card look nicer */
      .login-card{
        border: 1px solid rgba(49,51,63,0.18);
        border-radius: 12px;
        padding: 18px 18px 10px 18px;
        background: rgba(255,255,255,0.65);
      }

      /* Keep inputs from overflowing */
      input, textarea { max-width: 100% !important; }
      footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("登入 OrdoLite")

# Already logged in
if st.session_state.get("user_id"):
    st.success(f"已登入：{st.session_state.get('username','')}")
    st.caption("若要切換帳號，請先按左側「登出」。")
    st.stop()

with st.form("login_form"):
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    username = st.text_input("帳號", placeholder="例如：admin")
    password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
    submitted = st.form_submit_button("登入", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

if submitted:
    username = (username or "").strip()
    if not username or not password:
        st.error("請輸入帳號與密碼。")
        st.stop()

    ok, msg = auth.login(username, password)
    if ok:
        st.success("登入成功 ✅")
        st.rerun()
    else:
        st.error(msg or "登入失敗，請確認帳號密碼。")

st.caption("若忘記密碼，請聯絡系統管理者重設。")
