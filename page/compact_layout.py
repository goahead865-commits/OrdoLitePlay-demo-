"""Shared compact layout rules for OrdoLite Streamlit pages.

These rules only affect presentation spacing and control sizing. They do not
change widget keys, labels, callbacks, data, or page flow.
"""

import streamlit as st


def apply_compact_layout() -> None:
    """Reduce excess vertical whitespace for desktop-sized screens."""
    st.markdown(
        """
        <style id="ordo-compact-layout">
        /* Streamlit reserves a header-height offset even when the toolbar is
           not useful to an operator.  Remove that offset so every page starts
           at the top edge of the available work area. */
        [data-testid="stHeader"] {
            height: 0 !important;
            min-height: 0 !important;
            background: transparent !important;
        }
        [data-testid="stHeader"] > div,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            display: none !important;
        }
        [data-testid="stAppViewContainer"] .main {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container,
        [data-testid="stMainBlockContainer"],
        section.main > div {
            padding-top: 0 !important;
            margin-top: 0 !important;
            padding-bottom: 0.65rem !important;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        [data-testid="stVerticalBlock"] {
            gap: 0.5rem;
        }
        [data-testid="stHorizontalBlock"] {
            gap: 0.65rem;
        }
        h1, h2, h3, h4, h5, h6 {
            margin-top: 0.15rem !important;
            margin-bottom: 0.35rem !important;
            line-height: 1.15 !important;
        }
        h1 { font-size: 1.65rem !important; }
        h2 { font-size: 1.35rem !important; }
        h3 { font-size: 1.15rem !important; }
        [data-testid="stMarkdownContainer"] p {
            margin-bottom: 0.3rem;
        }
        [data-testid="stTextInput"],
        [data-testid="stNumberInput"],
        [data-testid="stDateInput"],
        [data-testid="stSelectbox"],
        [data-testid="stMultiSelect"] {
            margin-bottom: 0.15rem;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input {
            height: 2.25rem !important;
            min-height: 2.25rem !important;
            padding-top: 0.1rem;
            padding-bottom: 0.1rem;
        }
        div[data-baseweb="select"] > div {
            height: 2.25rem !important;
            min-height: 2.25rem !important;
            background-color: #FFFFFF !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"],
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stDateInput"] div[data-baseweb="input"],
        [data-testid="stNumberInput"] div[data-baseweb="input"],
        [data-testid="stTextInput"] div[data-baseweb="input"] {
            height: 2.25rem !important;
            min-height: 2.25rem !important;
            box-sizing: border-box !important;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stSelectbox"] div[data-baseweb="select"] {
            line-height: 1.2 !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            align-items: center !important;
        }
        /* Keep every dropdown control and its opened option list on a white
           surface.  The app background is deliberately blue, so without an
           explicit fill BaseWeb selectboxes can look grey/transparent. */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
        }
        div[data-baseweb="popover"] [role="listbox"],
        div[data-baseweb="popover"] [role="option"],
        div[data-baseweb="menu"] {
            background-color: #FFFFFF !important;
            color: #111827 !important;
        }
        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button {
            height: 2.25rem !important;
            min-height: 2.25rem !important;
            padding-top: 0.1rem;
            padding-bottom: 0.1rem;
        }
        [data-testid="stDataFrame"] {
            margin-top: 0.15rem;
            margin-bottom: 0.25rem;
        }
        [data-testid="stExpander"] {
            margin-top: 0.2rem;
            margin-bottom: 0.2rem;
        }
        @media (max-width: 900px) {
            [data-testid="stAppViewContainer"] .main .block-container,
            [data-testid="stMainBlockContainer"],
            section.main > div {
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
