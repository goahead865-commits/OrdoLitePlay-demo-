import streamlit as st
from compact_layout import apply_compact_layout
import pandas as pd
from pathlib import Path
import sys
import auth
from db import get_connection

apply_compact_layout()

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.i18n import init_language, set_language, get_language, tr as _raw_tr


def tr(text: str) -> str:
    """Safe i18n wrapper for this home page.

    core.i18n.tr() returns [MISS:...] when a term is not found.
    For UI display, fall back to the original Chinese text so users do not see MISS tags.
    """
    try:
        v = _raw_tr(text)
        if isinstance(v, str) and v.startswith("[MISS:"):
            return text
        return v if v is not None else text
    except Exception:
        return text


# --- session defaults (avoid KeyError before login) ---
st.session_state.setdefault('user_id', None)
st.session_state.setdefault('username', None)


def _is_admin(user_id: int) -> bool:
    """Read user.is_admin from DB via existing db.get_connection()."""
    try:
        from db import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT is_admin FROM user WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            return bool(row and row[0])
        finally:
            conn.close()
    except Exception:
        return False


# ================== 全域設定 ==================
st.set_page_config(
    page_title="OrdoLite Portal",
    layout="wide",
)

# ================== i18n 初始化 ==================
init_language()

LANG_OPTIONS = {
    "中文": "zh",
    "Tiếng Việt": "vi",
    "English": "en",
}


def _language_label_from_code(lang_code: str) -> str:
    for label, code in LANG_OPTIONS.items():
        if code == lang_code:
            return label
    return "中文"


# ================== Login Gate ==================
# 未登入就直接在 home 顯示登入表單（避免 multipage / st.switch_page 造成空白）
if not st.session_state.get("user_id"):
    st.markdown(
        """
        <style>
        .ordo-login-card{
          border: 1px solid rgba(49,51,63,0.18);
          border-radius: 12px;
          padding: 18px 18px 10px 18px;
          background: rgba(255,255,255,0.65);
        }
        .ordo-login-title{
          margin: 6px 0 10px 0;
          font-size: 36px;
          line-height: 1.1;
          color: rgba(27, 35, 58, 0.96);
          font-family: inherit;
          font-style: normal;
          font-weight: 800;
          letter-spacing: 0;
        }
        .ordo-login-motto{
          position: fixed;
          right: 28px;
          bottom: 18px;
          max-width: 520px;
          text-align: right;
          color: rgba(20, 24, 35, 0.68);
          z-index: 999;
          pointer-events: none;
        }
        .ordo-login-motto-latin{
          font-size: 16px;
          line-height: 1.45;
          font-family: "Palatino Linotype", "Book Antiqua", Garamond, "Times New Roman", serif;
          letter-spacing: 0.3px;
          font-style: italic;
        }
        .ordo-login-motto-zh{
          margin-top: 4px;
          font-size: 13px;
          line-height: 1.45;
          font-family: "Noto Serif TC", "PMingLiU", "MingLiU", "Microsoft JhengHei", serif;
          letter-spacing: 0.8px;
          opacity: 0.82;
        }
        @media (max-width: 900px) {
          .ordo-login-motto{
            right: 16px;
            bottom: 12px;
            max-width: 260px;
            font-size: 13px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ordo-login-title">OrdoLite</div>', unsafe_allow_html=True)
    left, mid, right = st.columns([1.2, 2.0, 1.2])
    with mid:
        with st.form("login_form"):
            st.markdown(
                '<div class="ordo-login-card">'
                f'<div style="font-size:13px;opacity:.75;margin-bottom:8px;">{tr("請輸入帳號密碼")}</div>',
                unsafe_allow_html=True,
            )
            username = st.text_input(tr("帳號"), placeholder="", autocomplete="username")
            password = st.text_input(tr("密碼"), type="password", autocomplete="current-password")
            submitted = st.form_submit_button(tr("登入"), type="primary")
            st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            ok, msg = auth.login(username, password)
            if ok:
                st.success(tr("登入成功"))
                st.rerun()
            else:
                st.error(msg)

        st.info("作品集展示帳號／密碼：`demo_admin` / `demo_admin`。請勿輸入個人或機密資料。")
        st.caption(tr("此為展示環境；所有資料均為測試用途。"))

    st.markdown(
        '''
        <div class="ordo-login-motto">
          <div class="ordo-login-motto-latin">Ordo nascitur non ad imperium, sed ad communionem.</div>
          <div class="ordo-login-motto-zh">制度之生，非為控制，而為共融。</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    st.stop()

# ================== 🎨 背景主題（可切換） ==================

THEMES = {
    "blue": "#EAF4FF",
    "pink": "#FFEAF2",
    "purple": "#F2EAFF",
    "grey": "#F2F3F5",
    "white": "#FFFFFF",
}
THEME_ORDER = ["blue", "pink", "purple", "grey", "white"]
DEFAULT_THEME = "blue"

SIDEBAR_THEMES = {
    "blue": "#0A2E6E",
    "pink": "#8B1E5A",
    "purple": "#4A257A",
    "grey": "#30343B",
    "white": "#111111",
}


NAV_TRANSLATIONS = {
    "採購到貨總覽": {
        "en": "Purchase Arrival Dashboard",
        "vi": "Tổng quan hàng mua về",
    },
    "客戶訂單完成進度": {
        "en": "Customer Order Progress",
        "vi": "Tiến độ hoàn thành đơn hàng",
    },
    "產品價格級距設定": {
        "en": "Product Price Tier Settings",
        "vi": "Thiết lập bậc giá sản phẩm",
    },
}


def _nav_lang_key() -> str:
    try:
        lang = str(get_language()).lower()
    except Exception:
        lang = str(st.session_state.get("language", "zh")).lower()

    if lang.startswith("en"):
        return "en"
    if lang.startswith("vi") or lang.startswith("vn"):
        return "vi"
    return "zh"


def _tt(text: str) -> str:
    """
    導航專用翻譯：
    先吃 core.i18n.tr()；如果 i18n 尚未補字或回傳 [MISS:...]，
    就用本頁 fallback，避免 B03 / E02 不能中越英切換。
    """
    lang_key = _nav_lang_key()

    try:
        v = _raw_tr(text)
        if isinstance(v, str) and v.startswith("[MISS:"):
            return NAV_TRANSLATIONS.get(text, {}).get(lang_key, text)
        if v:
            return v
    except Exception:
        pass

    return NAV_TRANSLATIONS.get(text, {}).get(lang_key, text)


def _init_bg_theme() -> str:
    v = st.session_state.get("bg_theme", DEFAULT_THEME)
    if v not in THEMES:
        v = DEFAULT_THEME
    st.session_state["bg_theme"] = v
    return v



def _set_theme(theme_key: str) -> None:
    st.session_state["bg_theme"] = theme_key



def _apply_bg_color(color_hex: str) -> None:
    st.markdown(
        f"""
        <style>
        :root {{ --ordo-bg: {color_hex}; }}

        html, body, .stApp {{ background-color: var(--ordo-bg) !important; }}

        [data-testid="stAppViewContainer"] > .main > div,
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stAppViewContainer"] > div,
        [data-testid="stMainBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stHeader"],
        header,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{
            background-color: var(--ordo-bg) !important;
        }}

        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        .block-container {{
            background-color: var(--ordo-bg) !important;
        }}

        /* Remove the large default top offset before the first page element. */
        [data-testid="stAppViewContainer"] .main .block-container,
        [data-testid="stMainBlockContainer"],
        section.main > div {{
            padding-top: 0 !important;
            margin-top: 0 !important;
        }}

        header,
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{
            background-color: var(--ordo-bg) !important;
        }}

        /* Sidebar 不跟主畫面背景走，避免淺色主題污染左側導航 */
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_global_textbox_white_css() -> None:
    """Force text-like input boxes across all pages to use a clean white background."""
    st.markdown(
        """
        <style id="ordo-global-textbox-white">
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stTextArea"] textarea,
        div[data-baseweb="input"] input,
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] textarea {
            background-color: #FFFFFF !important;
            color: #111827 !important;
        }

        [data-testid="stTextInput"] input:disabled,
        [data-testid="stNumberInput"] input:disabled,
        [data-testid="stDateInput"] input:disabled,
        [data-testid="stTimeInput"] input:disabled,
        [data-testid="stTextArea"] textarea:disabled,
        div[data-baseweb="input"] input:disabled {
            background-color: #F9FAFB !important;
            color: #374151 !important;
            -webkit-text-fill-color: #374151 !important;
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stDateInput"] input::placeholder,
        [data-testid="stTimeInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #9CA3AF !important;
            opacity: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def _inject_sidebar_theme_css(selected_key: str) -> None:
    sidebar_bg = SIDEBAR_THEMES.get(selected_key, SIDEBAR_THEMES[DEFAULT_THEME])
    st.markdown(
        f"""
        <style>
        :root {{
            --ordo-sidebar-bg: {sidebar_bg};
            --ordo-sidebar-text: #FFFFFF;
            --ordo-sidebar-active: rgba(255,255,255,0.18);
            --ordo-sidebar-hover: rgba(255,255,255,0.10);
        }}

        /* Sidebar 最外層：固定深色，不吃主畫面淺色背景 */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div,
        [data-testid="stSidebarContent"],
        [data-testid="stSidebarUserContent"],
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarNavItems"] {{
            background-color: var(--ordo-sidebar-bg) !important;
            background-image: none !important;
            color: var(--ordo-sidebar-text) !important;
        }}

        /* 把 Streamlit navigation 內部那種淺色卡片/群組底色全部拔掉 */
        section[data-testid="stSidebar"] nav,
        section[data-testid="stSidebar"] nav > div,
        section[data-testid="stSidebar"] nav div,
        section[data-testid="stSidebar"] nav ul,
        section[data-testid="stSidebar"] nav li,
        [data-testid="stSidebarNav"] div,
        [data-testid="stSidebarNav"] ul,
        [data-testid="stSidebarNav"] li,
        [data-testid="stSidebarNavItems"] div,
        [data-testid="stSidebarNavItems"] ul,
        [data-testid="stSidebarNavItems"] li {{
            background-color: transparent !important;
            background-image: none !important;
            box-shadow: none !important;
            border-color: transparent !important;
        }}

        /* Streamlit navigation 群組標題/類別按鈕：不要出現淺色底 */
        section[data-testid="stSidebar"] nav button,
        section[data-testid="stSidebar"] nav [role="button"],
        section[data-testid="stSidebar"] nav summary,
        section[data-testid="stSidebar"] nav [data-baseweb="accordion"],
        section[data-testid="stSidebar"] nav [data-baseweb="accordion"] > div,
        [data-testid="stSidebarNav"] button,
        [data-testid="stSidebarNav"] [role="button"],
        [data-testid="stSidebarNavItems"] button,
        [data-testid="stSidebarNavItems"] [role="button"] {{
            background-color: rgba(255,255,255,0.06) !important;
            background-image: none !important;
            color: var(--ordo-sidebar-text) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            box-shadow: none !important;
            border-radius: 8px !important;
        }}

        section[data-testid="stSidebar"] nav button *,
        section[data-testid="stSidebar"] nav [role="button"] *,
        section[data-testid="stSidebar"] nav summary *,
        [data-testid="stSidebarNav"] button *,
        [data-testid="stSidebarNav"] [role="button"] *,
        [data-testid="stSidebarNavItems"] button *,
        [data-testid="stSidebarNavItems"] [role="button"] * {{
            background-color: transparent !important;
            background-image: none !important;
            color: var(--ordo-sidebar-text) !important;
        }}

        /* 類別標題裡常見的 stMarkdownContainer / paragraph 外層，也一起拔掉淺底 */
        section[data-testid="stSidebar"] nav [data-testid="stMarkdownContainer"],
        section[data-testid="stSidebar"] nav [data-testid="stMarkdownContainer"] > *,
        [data-testid="stSidebarNav"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebarNav"] [data-testid="stMarkdownContainer"] > *,
        [data-testid="stSidebarNavItems"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebarNavItems"] [data-testid="stMarkdownContainer"] > * {{
            background-color: transparent !important;
            background-image: none !important;
            color: var(--ordo-sidebar-text) !important;
        }}

        /* Sidebar 一般文字 */
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] a,
        section[data-testid="stSidebar"] small {{
            color: var(--ordo-sidebar-text) !important;
        }}

        /* Navigation links */
        section[data-testid="stSidebar"] nav a,
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarNavItems"] a {{
            color: var(--ordo-sidebar-text) !important;
            background-color: transparent !important;
            border-radius: 10px !important;
        }}

        section[data-testid="stSidebar"] nav a:hover,
        [data-testid="stSidebarNav"] a:hover,
        [data-testid="stSidebarNavItems"] a:hover {{
            background-color: var(--ordo-sidebar-hover) !important;
        }}

        section[data-testid="stSidebar"] nav a[aria-current="page"],
        [data-testid="stSidebarNav"] a[aria-current="page"],
        [data-testid="stSidebarNavItems"] a[aria-current="page"] {{
            background-color: var(--ordo-sidebar-active) !important;
        }}

        /* Sidebar 使用者自訂區：語言、色票、debug，不要再變淺色區塊 */
        [data-testid="stSidebarUserContent"],
        [data-testid="stSidebarUserContent"] > div,
        [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"],
        [data-testid="stSidebarUserContent"] [data-testid="stHorizontalBlock"],
        [data-testid="stSidebarUserContent"] [data-testid="stElementContainer"],
        [data-testid="stSidebarUserContent"] .stMarkdown,
        [data-testid="stSidebarUserContent"] .stButton,
        [data-testid="stSidebarUserContent"] .stSelectbox,
        [data-testid="stSidebarUserContent"] .stColumn {{
            background-color: transparent !important;
            background-image: none !important;
            box-shadow: none !important;
        }}

        /* Selectbox 改成深色半透明 */
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background-color: rgba(255,255,255,0.12) !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            border-radius: 10px !important;
            color: #FFFFFF !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] input,
        section[data-testid="stSidebar"] div[data-baseweb="select"] span {{
            color: #FFFFFF !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] svg {{
            fill: #FFFFFF !important;
        }}

        /* 色票按鈕保留原本顏色，不被白字規則吃掉 */
        section[data-testid="stSidebar"] button {{
            color: #FFFFFF !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_sidebar_final_patch_css(selected_key: str) -> None:
    sidebar_bg = SIDEBAR_THEMES.get(selected_key, SIDEBAR_THEMES[DEFAULT_THEME])
    st.markdown(
        f"""
        <style id="ordo-sidebar-final-patch">
        :root {{
            --ordo-sidebar-bg: {sidebar_bg};
            --ordo-sidebar-text: #FFFFFF;
            --ordo-sidebar-group: rgba(255,255,255,0.08);
            --ordo-sidebar-active: rgba(255,255,255,0.18);
        }}

        /* 最後補刀：只處理 sidebar navigation 區，不碰主畫面 */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] {{
            background: var(--ordo-sidebar-bg) !important;
            background-color: var(--ordo-sidebar-bg) !important;
            background-image: none !important;
        }}

        /* Streamlit navigation 的群組標題常藏在 button / div / p / span 外層，這裡全部壓成透明 */
        section[data-testid="stSidebar"] nav,
        section[data-testid="stSidebar"] nav *,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] *,
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] * {{
            background-image: none !important;
            box-shadow: none !important;
        }}

        section[data-testid="stSidebar"] nav div:not([data-baseweb="select"]):not([data-baseweb="popover"]),
        section[data-testid="stSidebar"] nav li,
        section[data-testid="stSidebar"] nav ul,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] div:not([data-baseweb="select"]):not([data-baseweb="popover"]),
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] div:not([data-baseweb="select"]):not([data-baseweb="popover"]) {{
            background-color: transparent !important;
            background: transparent !important;
            border-color: transparent !important;
        }}

        /* 群組標題列：有 aria-expanded 的就是那幾條類別列 */
        section[data-testid="stSidebar"] nav [aria-expanded],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] [aria-expanded],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] [aria-expanded],
        section[data-testid="stSidebar"] button[aria-expanded],
        section[data-testid="stSidebar"] div[role="button"][aria-expanded] {{
            background: var(--ordo-sidebar-group) !important;
            background-color: var(--ordo-sidebar-group) !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            border-radius: 8px !important;
            color: #FFFFFF !important;
        }}

        section[data-testid="stSidebar"] nav [aria-expanded] *,
        section[data-testid="stSidebar"] button[aria-expanded] *,
        section[data-testid="stSidebar"] div[role="button"][aria-expanded] * {{
            background: transparent !important;
            background-color: transparent !important;
            color: #FFFFFF !important;
        }}

        /* 如果 Streamlit 沒有 aria-expanded，就用第一層 section label 的文字容器補壓 */
        section[data-testid="stSidebar"] nav > ul > li > div:first-child,
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] p {{
            background: transparent !important;
            background-color: transparent !important;
            color: #FFFFFF !important;
        }}

        /* 頁面連結與選取狀態 */
        section[data-testid="stSidebar"] nav a,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a {{
            color: #FFFFFF !important;
            background: transparent !important;
            border-radius: 10px !important;
        }}

        section[data-testid="stSidebar"] nav a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a[aria-current="page"] {{
            background: var(--ordo-sidebar-active) !important;
            background-color: var(--ordo-sidebar-active) !important;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_sidebar_group_header_black_css() -> None:
    """Force st.navigation(dict) group/category labels to use dark text and keep page links white."""
    st.markdown(
        """
        <style id="ordo-sidebar-group-header-black">
        /*
          st.navigation(dict) 的大類標題不是 <a>，頁面項目是 <a>。
          所以先把 nav 裡的文字設為深色，再把 a 裡的文字改回白色。
          這比猜 Streamlit 內部 class 穩定。
        */
        section[data-testid="stSidebar"] nav p,
        section[data-testid="stSidebar"] nav span,
        section[data-testid="stSidebar"] nav div[role="button"],
        section[data-testid="stSidebar"] nav button,
        section[data-testid="stSidebar"] nav [aria-expanded],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] p,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span,
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] p,
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] span {
            color: #111827 !important;
            fill: #111827 !important;
            font-weight: 800 !important;
        }

        section[data-testid="stSidebar"] nav a,
        section[data-testid="stSidebar"] nav a *,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a *,
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a,
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a * {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _inject_palette_css(selected_key: str) -> None:
    css = ["<style>", "/* ===== Ordo 背景色票 ===== */"]

    css.extend([
        """
        /* 色票：不固定，跟著 Sidebar 正常排版 */
"""
    ])

    for k in THEME_ORDER:
        css.append(
            f"""
            .st-key-bg_btn_{k} {{
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0 !important;
                margin: 0 !important;
            }}

            .st-key-bg_btn_{k} button,
            .st-key-bg_btn_{k} [data-testid="stBaseButton-secondary"],
            .st-key-bg_btn_{k} [data-testid="stBaseButton-primary"],
            .st-key-bg_btn_{k} [data-testid="stBaseButton-secondary"] > button,
            .st-key-bg_btn_{k} [data-testid="stBaseButton-primary"] > button {{
                width: 18px !important;
                height: 18px !important;
                min-width: 18px !important;
                min-height: 18px !important;
                max-width: 18px !important;
                max-height: 18px !important;
                flex: 0 0 18px !important;
                align-self: center !important;
                box-sizing: border-box !important;
                padding: 0 !important;
                border-radius: 50% !important;
                aspect-ratio: 1 / 1 !important;
                background-color: {THEMES[k]} !important;
                border: 1px solid rgba(0,0,0,0.20) !important;
                box-shadow: 0 1px 4px rgba(0,0,0,0.12) !important;
                font-size: 0 !important;
                line-height: 0 !important;
            }}

            .st-key-bg_btn_{k} button:hover {{
                border-color: rgba(0,0,0,0.40) !important;
                transform: translateY(-1px);
            }}
            """
        )

    css.append(
        f"""
        .st-key-bg_btn_{selected_key} button,
        .st-key-bg_btn_{selected_key} [data-testid="stBaseButton-secondary"],
        .st-key-bg_btn_{selected_key} [data-testid="stBaseButton-primary"],
        .st-key-bg_btn_{selected_key} [data-testid="stBaseButton-secondary"] > button,
        .st-key-bg_btn_{selected_key} [data-testid="stBaseButton-primary"] > button {{
            border: 2px solid rgba(0,0,0,0.55) !important;
            box-shadow: 0 0 0 2px rgba(255,255,255,0.65), 0 2px 8px rgba(0,0,0,0.18) !important;
        }}
        """
    )

    css.append("</style>")
    st.markdown("\n".join(css), unsafe_allow_html=True)


_selected_theme = _init_bg_theme()
_apply_bg_color(THEMES[_selected_theme])
_inject_global_textbox_white_css()
_inject_palette_css(_selected_theme)
_inject_sidebar_theme_css(_selected_theme)
_inject_sidebar_group_header_black_css()

# Sidebar：語言選單 + 背景色票
with st.sidebar:
    selected_language_label = st.selectbox(
        "Language / Ngôn ngữ / 語言",
        list(LANG_OPTIONS.keys()),
        index=list(LANG_OPTIONS.keys()).index(_language_label_from_code(get_language())),
    )
    set_language(LANG_OPTIONS[selected_language_label])

    st.markdown(f"**{tr('背景主題')}**")
    cols = st.columns([1, 1, 1, 1, 1])
    for i, k in enumerate(THEME_ORDER):
        with cols[i]:
            st.button("", key=f"bg_btn_{k}", help=f"{tr('背景')}：{k}", on_click=_set_theme, args=(k,))


# ================== 🏠 首頁 Dashboard ==================
DASHBOARD_CACHE_TTL = 10  # seconds; keep dashboard fresh without forcing relogin

@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def _q_material_eta_not_arrived(refresh_token: int = 0):
    conn = get_connection()
    sql = """
        SELECT
            oh.order_id,
            oh.order_num,
            oh.supplier_name,
            oh.due_date,
            oh.status,
            GROUP_CONCAT(
                CONCAT(oi.material_name, ' x ', FORMAT(oi.qty_ordered, 0), ' ', oi.unit)
                ORDER BY oi.line_no SEPARATOR ' / '
            ) AS material_summary
        FROM order_head oh
        LEFT JOIN order_item oi ON oi.order_id = oh.order_id
        WHERE oh.order_type = 'PO'
          AND oh.due_date <= CURDATE()
          AND oh.status IN ('Not delivered', 'Partial arrival')
        GROUP BY oh.order_id, oh.order_num, oh.supplier_name, oh.due_date, oh.status
        ORDER BY oh.due_date ASC, oh.order_num ASC
    """
    try:
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def _q_today_shipment_count(refresh_token: int = 0):
    conn = get_connection()
    sql = """
        SELECT COALESCE(SUM(COALESCE(dp.qty, 0)), 0) AS shipment_count
        FROM delivery_head dh
        LEFT JOIN delivery_product dp ON dp.delivery_head_id = dh.delivery_note_id
        WHERE dh.delivery_date = CURDATE()
    """
    try:
        df = pd.read_sql(sql, conn)
        return float(df.iloc[0]["shipment_count"]) if not df.empty else 0
    finally:
        conn.close()


@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def _q_monthly_shipment_count(refresh_token: int = 0):
    conn = get_connection()
    sql = """
        SELECT
            DATE_FORMAT(dh.delivery_date, '%Y-%m') AS ym,
            COALESCE(SUM(COALESCE(dp.qty, 0)), 0) AS shipment_count
        FROM delivery_head dh
        LEFT JOIN delivery_product dp ON dp.delivery_head_id = dh.delivery_note_id
        WHERE dh.delivery_date >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 11 MONTH), '%Y-%m-01')
        GROUP BY DATE_FORMAT(dh.delivery_date, '%Y-%m')
        ORDER BY ym
    """
    try:
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()



@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def _q_overdue_customer_order_schedules(refresh_token: int = 0):
    """Return overdue customer orders by ORDER MAIN due date.

    阿辰這版口徑：
    - 上方「客戶交期逾期未出貨」看的是 customer_order.deliver_date。
    - 只要訂單主交期已過，且整張訂單仍有未出貨數量，就列出。
    - 不在這裡逐項列出明細，避免把主交期灌到每個品項造成 HOME 洗版。
    """
    conn = get_connection()
    sql = """
        WITH order_product_qty AS (
            SELECT
                co.customer_order_id,
                co.customer_order_code,
                co.customer_order_num,
                co.deliver_date AS due_date,
                COALESCE(c.customer_shortname, c.customer_name) AS customer_name,
                coi.product_id,
                MIN(coi.customer_order_item_id) AS customer_order_item_id,
                MIN(coi.line_no) AS line_no,
                MAX(COALESCE(p.product_code, '')) AS product_code,
                MAX(COALESCE(p.customer_production_id, '')) AS customer_product_id,
                MAX(COALESCE(p.product_name, '')) AS product_name,
                SUM(COALESCE(coi.quantity, 0)) AS ordered_qty
            FROM customer_order co
            JOIN customer_order_item coi
              ON coi.customer_order_id = co.customer_order_id
            LEFT JOIN customer c
              ON c.customer_id = co.customer_id
            LEFT JOIN product p
              ON p.product_id = coi.product_id
            WHERE co.deliver_date IS NOT NULL
            GROUP BY
                co.customer_order_id,
                co.customer_order_code,
                co.customer_order_num,
                co.deliver_date,
                COALESCE(c.customer_shortname, c.customer_name),
                coi.product_id
        ),
        delivered_by_order_product AS (
            SELECT
                dh.customer_order_id,
                dp.product_id,
                SUM(COALESCE(dp.qty, 0)) AS delivered_qty
            FROM delivery_head dh
            JOIN delivery_product dp
              ON dp.delivery_head_id = dh.delivery_note_id
            WHERE COALESCE(dh.status, '') <> 'void'
              AND dh.customer_order_id IS NOT NULL
            GROUP BY dh.customer_order_id, dp.product_id
        ),
        order_remaining AS (
            SELECT
                opq.customer_order_id,
                opq.customer_order_code,
                opq.customer_order_num,
                opq.customer_name,
                MIN(opq.customer_order_item_id) AS customer_order_item_id,
                0 AS line_no,
                '' AS product_code,
                '' AS customer_product_id,
                CASE
                    WHEN COUNT(*) = 1 THEN MAX(opq.product_name)
                    ELSE CONCAT('訂單主交期：', COUNT(*), ' 個品項')
                END AS product_name,
                NULL AS schedule_id,
                1 AS schedule_no,
                opq.due_date,
                SUM(opq.ordered_qty) AS schedule_qty,
                SUM(COALESCE(dbop.delivered_qty, 0)) AS delivered_qty,
                GREATEST(SUM(opq.ordered_qty) - SUM(COALESCE(dbop.delivered_qty, 0)), 0) AS remaining_qty,
                CASE
                    WHEN SUM(COALESCE(dbop.delivered_qty, 0)) <= 0 THEN 'open'
                    WHEN SUM(COALESCE(dbop.delivered_qty, 0)) < SUM(opq.ordered_qty) THEN 'partial_shipped'
                    ELSE 'shipped'
                END AS batch_status,
                'main_due' AS due_source
            FROM order_product_qty opq
            LEFT JOIN delivered_by_order_product dbop
              ON dbop.customer_order_id = opq.customer_order_id
             AND dbop.product_id = opq.product_id
            GROUP BY
                opq.customer_order_id,
                opq.customer_order_code,
                opq.customer_order_num,
                opq.customer_name,
                opq.due_date
        )
        SELECT *
        FROM order_remaining
        WHERE due_date < CURDATE()
          AND COALESCE(remaining_qty, 0) > 0
          AND COALESCE(batch_status, 'open') NOT IN ('shipped', 'cancelled')
        ORDER BY due_date ASC, customer_order_code ASC
        LIMIT 50
    """
    try:
        return pd.read_sql(sql, conn)
    except Exception as e:
        return pd.DataFrame({"_error": [str(e)]})
    finally:
        try:
            conn.close()
        except Exception:
            pass


@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def _q_pending_customer_order_schedules(refresh_token: int = 0):
    """Return future/today unfinished rows ONLY for orders with explicit schedules.

    阿辰這版口徑：
    - 下方「後續未完成交期」只看真正有分批交期的訂單。
    - 逐項列出尚未完成的分批交期。
    - 不 fallback 主交期；沒有分批交期的訂單不會出現在下方。
    - 舊版 E01 自動產生的假 schedule 會被排除。
    """
    conn = get_connection()
    sql = """
        WITH schedule_counts AS (
            SELECT
                customer_order_item_id,
                COUNT(*) AS schedule_count
            FROM customer_order_item_schedule
            WHERE COALESCE(status, 'open') <> 'cancelled'
            GROUP BY customer_order_item_id
        ),
        explicit_schedule_ids AS (
            SELECT
                s.schedule_id,
                s.customer_order_item_id
            FROM customer_order_item_schedule s
            JOIN customer_order_item coi
              ON coi.customer_order_item_id = s.customer_order_item_id
            JOIN customer_order co
              ON co.customer_order_id = coi.customer_order_id
            JOIN schedule_counts sc
              ON sc.customer_order_item_id = s.customer_order_item_id
            WHERE COALESCE(s.status, 'open') <> 'cancelled'
              AND (
                    COALESCE(s.updated_by, 0) <> 0
                 OR s.updated_at IS NOT NULL
                 OR COALESCE(s.note, '') <> ''
                 OR sc.schedule_count > 1
                 OR ABS(COALESCE(s.qty, 0) - COALESCE(coi.quantity, 0)) >= 0.0001
                 OR s.due_date <> COALESCE(coi.deliver_date, co.deliver_date)
              )
        ),
        explicit_orders AS (
            SELECT DISTINCT coi.customer_order_id
            FROM explicit_schedule_ids esi
            JOIN customer_order_item coi
              ON coi.customer_order_item_id = esi.customer_order_item_id
        ),
        delivered_by_schedule AS (
            SELECT
                dp.schedule_id,
                SUM(COALESCE(dp.qty, 0)) AS delivered_qty
            FROM delivery_head dh
            JOIN delivery_product dp
              ON dp.delivery_head_id = dh.delivery_note_id
            WHERE COALESCE(dh.status, '') <> 'void'
              AND dp.schedule_id IS NOT NULL
            GROUP BY dp.schedule_id
        ),
        scheduled_rows AS (
            SELECT
                co.customer_order_id,
                co.customer_order_code,
                co.customer_order_num,
                COALESCE(c.customer_shortname, c.customer_name) AS customer_name,
                coi.customer_order_item_id,
                coi.line_no,
                p.product_code,
                p.customer_production_id AS customer_product_id,
                p.product_name,
                s.schedule_id,
                COALESCE(s.schedule_no, 1) AS schedule_no,
                s.due_date,
                COALESCE(s.qty, 0) AS schedule_qty,
                COALESCE(dbs.delivered_qty, 0) AS delivered_qty,
                GREATEST(COALESCE(s.qty, 0) - COALESCE(dbs.delivered_qty, 0), 0) AS remaining_qty,
                CASE
                    WHEN COALESCE(dbs.delivered_qty, 0) <= 0 THEN 'open'
                    WHEN COALESCE(dbs.delivered_qty, 0) < COALESCE(s.qty, 0) THEN 'partial_shipped'
                    ELSE 'shipped'
                END AS batch_status,
                'schedule' AS due_source
            FROM customer_order co
            JOIN explicit_orders eo
              ON eo.customer_order_id = co.customer_order_id
            JOIN customer_order_item coi
              ON coi.customer_order_id = co.customer_order_id
            JOIN customer_order_item_schedule s
              ON s.customer_order_item_id = coi.customer_order_item_id
             AND COALESCE(s.status, 'open') <> 'cancelled'
            JOIN explicit_schedule_ids esi
              ON esi.schedule_id = s.schedule_id
            LEFT JOIN delivered_by_schedule dbs
              ON dbs.schedule_id = s.schedule_id
            LEFT JOIN customer c
              ON c.customer_id = co.customer_id
            LEFT JOIN product p
              ON p.product_id = coi.product_id
        )
        SELECT *
        FROM scheduled_rows
        WHERE due_date >= CURDATE()
          AND COALESCE(remaining_qty, 0) > 0
          AND COALESCE(batch_status, 'open') NOT IN ('shipped', 'cancelled')
        ORDER BY due_date ASC, customer_order_code ASC, line_no ASC, schedule_no ASC
        LIMIT 80
    """
    try:
        return pd.read_sql(sql, conn)
    except Exception as e:
        return pd.DataFrame({"_error": [str(e)]})
    finally:
        try:
            conn.close()
        except Exception:
            pass


def dashboard():
    top_title_col, top_refresh_col = st.columns([5, 1.2], vertical_alignment="center")
    with top_title_col:
        st.title(tr("儀表板"))
    with top_refresh_col:
        st.session_state.setdefault("dashboard_refresh_token", 0)
        if st.button(tr("重新整理 Dashboard"), key="dashboard_refresh_btn", use_container_width=True):
            st.session_state["dashboard_refresh_token"] += 1
            try:
                _q_material_eta_not_arrived.clear()
                _q_today_shipment_count.clear()
                _q_monthly_shipment_count.clear()
                _q_overdue_customer_order_schedules.clear()
                _q_pending_customer_order_schedules.clear()
            except Exception:
                pass
            st.rerun()
    dashboard_refresh_token = int(st.session_state.get("dashboard_refresh_token", 0))

    st.markdown(
        """
        <style>
        .ordo-card {
            border: 1px solid rgba(49,51,63,0.16);
            border-radius: 10px;
            padding: 8px 10px;
            background: rgba(255,255,255,0.72);
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            min-height: 64px;
        }
        .ordo-card-label {
            font-size: 12px;
            opacity: 0.72;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .ordo-card-value {
            font-size: 22px;
            font-weight: 800;
            line-height: 1.05;
            margin-bottom: 3px;
        }
        .ordo-card-note {
            font-size: 11px;
            opacity: 0.72;
            line-height: 1.25;
        }
        .ordo-panel {
            border: 1px solid rgba(49,51,63,0.14);
            border-radius: 10px;
            padding: 8px 10px 6px 10px;
            background: rgba(255,255,255,0.62);
            box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        }
        .ordo-section-title {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 2px;
        }
        .ordo-section-note {
            font-size: 12px;
            opacity: 0.72;
            margin-bottom: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        eta_df = _q_material_eta_not_arrived(dashboard_refresh_token)
        today_shipments = _q_today_shipment_count(dashboard_refresh_token)
        monthly_ship_df = _q_monthly_shipment_count(dashboard_refresh_token)
        overdue_schedule_df = _q_overdue_customer_order_schedules(dashboard_refresh_token)
        pending_schedule_df = _q_pending_customer_order_schedules(dashboard_refresh_token)
    except Exception as e:
        st.error(f"{tr('Dashboard 載入失敗')}：{e}")
        return

    eta_count = len(eta_df)
    overdue_schedule_has_error = (
        overdue_schedule_df is not None
        and not overdue_schedule_df.empty
        and "_error" in overdue_schedule_df.columns
    )
    overdue_schedule_count = 0 if overdue_schedule_has_error else len(overdue_schedule_df)
    pending_schedule_has_error = (
        pending_schedule_df is not None
        and not pending_schedule_df.empty
        and "_error" in pending_schedule_df.columns
    )
    pending_schedule_count = 0 if pending_schedule_has_error else len(pending_schedule_df)

    monthly_total = 0
    if not monthly_ship_df.empty:
        monthly_ship_df["shipment_count"] = pd.to_numeric(monthly_ship_df["shipment_count"], errors="coerce").fillna(0)
        monthly_total = int(monthly_ship_df.iloc[-1]["shipment_count"])

    eta_max_days = 0
    eta_supplier_cnt = 0
    if not eta_df.empty:
        eta_tmp = eta_df.copy()
        eta_tmp["due_date"] = pd.to_datetime(eta_tmp["due_date"], errors="coerce")
        eta_tmp["逾期天數"] = (pd.Timestamp.today().normalize() - eta_tmp["due_date"]).dt.days.fillna(0).astype(int)
        eta_max_days = int(eta_tmp["逾期天數"].max())
        eta_supplier_cnt = int(eta_tmp["supplier_name"].fillna("").nunique())


    overdue_schedule_max_days = 0
    overdue_schedule_customer_cnt = 0
    if not overdue_schedule_has_error and overdue_schedule_df is not None and not overdue_schedule_df.empty:
        overdue_schedule_tmp = overdue_schedule_df.copy()
        overdue_schedule_tmp["due_date"] = pd.to_datetime(overdue_schedule_tmp["due_date"], errors="coerce")
        overdue_schedule_tmp["逾期天數"] = (pd.Timestamp.today().normalize() - overdue_schedule_tmp["due_date"]).dt.days.fillna(0).astype(int)
        overdue_schedule_max_days = int(overdue_schedule_tmp["逾期天數"].max())
        overdue_schedule_customer_cnt = int(overdue_schedule_tmp["customer_name"].fillna("").nunique())

    cards = [
        (tr("應到貨未到貨"), eta_count, tr("逾期未到貨採購單")),
        (tr("未到貨供應商數"), eta_supplier_cnt, tr("目前受影響供應商")),
        (tr("今日出貨件數"), today_shipments, tr("今日送貨件數加總")),
        (tr("本月出貨件數"), monthly_total, tr("本月送貨件數加總")),
        (tr("逾期未出貨交期"), overdue_schedule_count, tr("批次交期或主交期已過但未完成")),
        (tr("最久交期逾期天數"), overdue_schedule_max_days, f"{tr('涉及')} {overdue_schedule_customer_cnt} {tr('家客戶')}"),
    ]

    cols = st.columns(6)
    for col, (label, value, note) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="ordo-card">
                  <div class="ordo-card-label">{label}</div>
                  <div class="ordo-card-value">{value}</div>
                  <div class="ordo-card-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="ordo-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="ordo-section-title">{tr("每月出貨件數")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ordo-section-note">{tr("最近 12 個月送貨件數趨勢")}</div>', unsafe_allow_html=True)

        if monthly_ship_df.empty:
            st.info(tr("最近 12 個月沒有出貨資料。"))
        else:
            # Use stable internal column names for chart data.
            # Altair/Streamlit can mis-parse translated labels in shorthand.
            chart_df = monthly_ship_df.copy()
            chart_df["month"] = chart_df["ym"].astype(str)
            chart_df["shipment_count"] = pd.to_numeric(chart_df["shipment_count"], errors="coerce").fillna(0)
            st.bar_chart(chart_df.set_index("month")[["shipment_count"]], height=180)

        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="ordo-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="ordo-section-title">{tr("應到貨未到貨提醒")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ordo-section-note">{tr("顯示截至今日所有未到貨資料")}</div>', unsafe_allow_html=True)

        if eta_df.empty:
            st.success(tr("目前沒有截至今日仍未到貨的物料採購單。"))
        else:
            eta_show = eta_df.copy()
            eta_show["due_date"] = pd.to_datetime(eta_show["due_date"], errors="coerce")
            eta_show["逾期天數"] = (pd.Timestamp.today().normalize() - eta_show["due_date"]).dt.days
            eta_show = eta_show.rename(columns={
                "order_num": tr("採購單號"),
                "supplier_name": tr("供應商"),
                "due_date": tr("應到貨日"),
                "status": tr("狀態"),
                "逾期天數": tr("逾期天數"),
            })
            st.dataframe(
                eta_show[[tr("採購單號"), tr("供應商"), tr("應到貨日"), tr("逾期天數"), tr("狀態")]],
                use_container_width=True,
                hide_index=True,
                height=140,
            )

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="ordo-panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="ordo-section-title">{tr("客戶交期逾期未出貨")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ordo-section-note">{tr("以訂單主交期判定；只要客戶訂單主交期已過且整張訂單仍未出完，就會顯示。")}</div>',
        unsafe_allow_html=True,
    )

    if overdue_schedule_has_error:
        err_msg = str(overdue_schedule_df.iloc[0].get("_error") or "")
        st.warning(f'{tr("客戶交期提醒載入失敗，請確認訂單、明細、排程與送貨資料表欄位是否完整")}：{err_msg}')
    elif overdue_schedule_df.empty:
        st.success(tr("目前沒有逾期未出貨的客戶交期。"))
    else:
        schedule_show = overdue_schedule_df.copy()
        schedule_show["due_date"] = pd.to_datetime(schedule_show["due_date"], errors="coerce")
        schedule_show["逾期天數"] = (pd.Timestamp.today().normalize() - schedule_show["due_date"]).dt.days
        schedule_show["schedule_qty"] = pd.to_numeric(schedule_show["schedule_qty"], errors="coerce").fillna(0)
        schedule_show["delivered_qty"] = pd.to_numeric(schedule_show["delivered_qty"], errors="coerce").fillna(0)
        schedule_show["remaining_qty"] = pd.to_numeric(schedule_show["remaining_qty"], errors="coerce").fillna(0)
        schedule_show["產品"] = (
            schedule_show["product_code"].fillna("").astype(str)
            + "｜"
            + schedule_show["product_name"].fillna("").astype(str)
        )
        schedule_show["交期類型"] = schedule_show.get("due_source", "schedule").map({
            "schedule": tr("分批交期"),
            "main_due": tr("主交期"),
        }).fillna(tr("分批交期"))
        schedule_show = schedule_show.rename(columns={
            "customer_order_code": tr("本公司訂單號"),
            "customer_order_num": tr("客戶訂單號"),
            "customer_name": tr("客戶名稱"),
            "customer_product_id": tr("客戶料號"),
            "schedule_no": tr("批次"),
            "due_date": tr("批次交期"),
            "schedule_qty": tr("批次數量"),
            "delivered_qty": tr("已出貨數量"),
            "remaining_qty": tr("未出貨數量"),
            "batch_status": tr("狀態"),
            "逾期天數": tr("逾期天數"),
            "產品": tr("產品"),
            "交期類型": tr("交期類型"),
        })
        st.dataframe(
            schedule_show[[
                tr("本公司訂單號"),
                tr("客戶訂單號"),
                tr("客戶名稱"),
                tr("產品"),
                tr("客戶料號"),
                tr("交期類型"),
                tr("批次"),
                tr("批次交期"),
                tr("逾期天數"),
                tr("批次數量"),
                tr("已出貨數量"),
                tr("未出貨數量"),
                tr("狀態"),
            ]],
            use_container_width=True,
            hide_index=True,
            height=170,
        )

    st.markdown('</div>', unsafe_allow_html=True)


    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="ordo-panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="ordo-section-title">{tr("後續未完成交期")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ordo-section-note">{tr("只顯示有分批交期的訂單；逐項列出今天以後尚未完成的分批交期。沒有分批交期的訂單不會列在這裡。")}</div>',
        unsafe_allow_html=True,
    )

    if pending_schedule_has_error:
        err_msg = str(pending_schedule_df.iloc[0].get("_error") or "")
        st.warning(f'{tr("後續未完成交期載入失敗")}：{err_msg}')
    elif pending_schedule_df.empty:
        st.success(tr("目前沒有今天以後尚未完成的客戶交期。"))
    else:
        pending_show = pending_schedule_df.copy()
        pending_show["due_date"] = pd.to_datetime(pending_show["due_date"], errors="coerce")
        pending_show["距交期天數"] = (pending_show["due_date"] - pd.Timestamp.today().normalize()).dt.days
        pending_show["schedule_qty"] = pd.to_numeric(pending_show["schedule_qty"], errors="coerce").fillna(0)
        pending_show["delivered_qty"] = pd.to_numeric(pending_show["delivered_qty"], errors="coerce").fillna(0)
        pending_show["remaining_qty"] = pd.to_numeric(pending_show["remaining_qty"], errors="coerce").fillna(0)
        pending_show["產品"] = (
            pending_show["product_code"].fillna("").astype(str)
            + "｜"
            + pending_show["product_name"].fillna("").astype(str)
        )
        pending_show["交期類型"] = pending_show.get("due_source", "schedule").map({
            "schedule": tr("分批交期"),
            "main_due": tr("主交期"),
        }).fillna(tr("分批交期"))
        pending_show = pending_show.rename(columns={
            "customer_order_code": tr("本公司訂單號"),
            "customer_order_num": tr("客戶訂單號"),
            "customer_name": tr("客戶名稱"),
            "customer_product_id": tr("客戶料號"),
            "schedule_no": tr("批次"),
            "due_date": tr("交期"),
            "schedule_qty": tr("批次數量"),
            "delivered_qty": tr("已出貨數量"),
            "remaining_qty": tr("未出貨數量"),
            "batch_status": tr("狀態"),
            "距交期天數": tr("距交期天數"),
            "產品": tr("產品"),
            "交期類型": tr("交期類型"),
        })
        st.dataframe(
            pending_show[[
                tr("本公司訂單號"),
                tr("客戶訂單號"),
                tr("客戶名稱"),
                tr("產品"),
                tr("客戶料號"),
                tr("交期類型"),
                tr("批次"),
                tr("交期"),
                tr("距交期天數"),
                tr("批次數量"),
                tr("已出貨數量"),
                tr("未出貨數量"),
                tr("狀態"),
            ]],
            use_container_width=True,
            hide_index=True,
            height=170,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    with st.expander(tr("Dashboard 指標口徑說明"), expanded=False):
        st.markdown(
            f"""
            1. **{tr('應到貨而未到貨提醒（物料）')}**：{tr("以 order_head 的 order_type='PO'、due_date <= 今天，且 status in ('Not delivered','Partial arrival') 判定，首頁顯示截至今日所有未到貨資料。")}  
            2. **{tr('今日出貨件數')}**：{tr('以 delivery_head 連接 delivery_product，加總送貨明細數量（delivery_product.qty）當日資料，不限制 status。')}  
            3. **{tr('每月出貨件數')}**：{tr('以 delivery_head 連接 delivery_product，加總送貨明細數量（delivery_product.qty）的月資料做統計，不限制 status。')}  
            4. **{tr('逾期未出貨交期')}**：{tr("以訂單主交期判定：customer_order.deliver_date < 今天，且整張訂單 remaining_qty > 0 即顯示。")}  
            """
        )


# ================== 📥 Demo：物料進出（之後你可以獨立成一頁） ==================
def page_stock_io_demo():
    st.title(tr("Material Stock I/O Demo（物料進出 Demo）"))
    st.write(tr("這只是示範頁，之後你可以改成正式的 S01_stock_io.py 再掛進來。"))

    st.selectbox(tr("物料"), ["示範料號 A", "示範料號 B"])
    st.number_input(tr("數量"), min_value=0.0, step=1.0)
    st.selectbox(tr("類型"), ["IN", "OUT", "ADJUST"])


# ================== 🔗 導航結構 ==================
# 依現有 OrdoLite 架構分大類；各頁面 title / icon / 檔名維持原本命名，不偷換名字。
nav_sections = {
    "首頁": [
        st.Page(
            dashboard,
            title=tr("儀表板"),
            icon="🏠",
            default=True,
        ),
    ],

    "主檔設定": [
        st.Page("P01_product.py", title=f"P01 {tr('產品主檔')}", icon="🧩"),
        st.Page("P02_product_materials.py", title=f"P02 {tr('產品所需物料')}", icon="🧱"),
        st.Page("P04_product_price_tier.py", title=f"P04 {_tt('產品價格級距設定')}", icon="💵"),
        st.Page("C01_material.py", title=f"C01 {tr('原料主檔')}", icon="🧱"),
        st.Page("C02_supplier.py", title=f"C02 {tr('供應商主檔')}", icon="🏭"),
        st.Page("C03_customer.py", title=f"C03 {tr('客戶主檔')}", icon="👤"),
        st.Page("OC01_our_company_settings.py", title=f"OC01 {tr('我方公司資料')}", icon="🏢"),
    ],

    "庫存作業": [
        st.Page("S01_material_stock_io.py", title=f"S01 {tr('原料進出庫')}", icon="📥"),
        st.Page("S03_product_stock_io.py", title=f"S03 {tr('產品進出庫')}", icon="📦"),
        st.Page("S04_product_inventory_summary.py", title=f"S04 {tr('產品庫存統計')}", icon="📊"),
        st.Page("S02_material_inventory_summary.py", title=f"S02 {tr('原料庫存統計')}", icon="📊"),
    ],

    "採購管理": [
        st.Page("B02_purchase_order_create.py", title=f"B02 {_tt('新建與查詢採購單')}", icon="🧾"),
        st.Page("B03_purchase_arrival_dashboard.py", title=f"B03 {_tt('採購到貨總覽')}", icon="🚚"),
    ],

    "訂單與出貨": [
        st.Page("E01_customer_order_create.py", title=f"E01 {tr('新建與查詢客戶訂單')}", icon="📝"),
        st.Page("SP01_sample_order_preview.py", title="SP01 樣品打樣與計價", icon="🧪"),
        st.Page("E02_customer_order_progress_dashboard.py", title=f"E02 {_tt('客戶訂單完成進度')}", icon="📈"),
        st.Page(
            str(Path(__file__).parent / "OT01_order_stock_tracking.py"),
            title=f"OT01 {tr('訂單狀況追蹤（庫存分配預覽）')}",
            icon="🔎",
        ),
        st.Page("D02_delivery_entry.py", title=f"D02 {tr('新建送貨單')}", icon="🧾"),
    ],

    "財務帳款": [
        st.Page("AP01_accounts_payable.py", title=f"AP01 {tr('應付帳款')}", icon="🧾"),
        st.Page("AP02_Statement_Page.py", title=f"AP02 {tr('供應商對帳單')}", icon="📑"),
        st.Page("AP03_batch_processing_payment_records.py", title=f"AP03 {tr('批量處理付款紀錄')}", icon="💳"),
        st.Page("AR01_Accounts Receivable.py", title=f"AR01 {tr('應收帳款')}", icon="💰"),
        st.Page("AR02_prepare_accounts_receivable.py", title=f"AR02 {tr('客戶對帳單')}", icon="📑"),
        st.Page("AR03_batch_processing_customer_payment_records.py", title=f"AR03 {tr('批量處理收款紀錄')}", icon="💳"),
    ],
}

# ================== 🚪 進入點 ==================
_me_is_admin = _is_admin(int(st.session_state['user_id']))
if _me_is_admin:
    nav_sections["系統管理"] = [
        st.Page('ST01_staff_admin.py', title=f'ST01 {tr("員工主檔")}', icon='🧑‍💼'),
        st.Page('Z99_permission_admin.py', title=tr('權限管理'), icon='🔐'),
        st.Page("Z98_user_admin.py", title=tr("使用者管理"), icon="👤"),
    ]

nav = st.navigation(nav_sections)
# 先補一次，避免載入時閃爍。
_inject_sidebar_theme_css(_selected_theme)
_inject_sidebar_group_header_black_css()
nav.run()
# Streamlit navigation 產生群組標題後，再補最後一次 CSS。
_inject_sidebar_final_patch_css(_selected_theme)
_inject_sidebar_group_header_black_css()
