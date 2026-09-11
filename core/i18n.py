from pathlib import Path
from functools import lru_cache
import pandas as pd
import streamlit as st


DICT_SHEET = "Dictionary_v1"


def get_project_root() -> Path:
    """
    core/i18n.py -> project root
    e.g. D:/Python_Plactice/OrdoLitePlay/core/i18n.py
      => D:/Python_Plactice/OrdoLitePlay
    """
    return Path(__file__).resolve().parent.parent


def get_dictionary_path() -> Path:
    """
    Find term_dictionary.xlsx in a robust order.
    Priority:
    1) project_root / data / term_dictionary.xlsx
    2) project_root / term_dictionary.xlsx
    3) same folder as i18n.py
    4) cwd / data / term_dictionary.xlsx
    5) cwd / term_dictionary.xlsx
    """
    project_root = get_project_root()
    current_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()

    candidates = [
        project_root / "data" / "term_dictionary.xlsx",
        project_root / "term_dictionary.xlsx",
        current_dir / "term_dictionary.xlsx",
        cwd / "data" / "term_dictionary.xlsx",
        cwd / "term_dictionary.xlsx",
    ]

    for path in candidates:
        if path.exists() and path.is_file():
            return path

    searched = "\n".join([f"- {str(p)}" for p in candidates])
    raise FileNotFoundError(
        "找不到字典檔：term_dictionary.xlsx\n"
        "請確認字典檔放在以下其中一處：\n"
        f"{searched}"
    )


@lru_cache(maxsize=1)
def load_dictionary() -> dict:
    dict_path = get_dictionary_path()
    df = pd.read_excel(dict_path, sheet_name=DICT_SHEET).fillna("")

    result = {}
    for _, row in df.iterrows():
        zh = str(row.get("中文", "")).strip()
        if not zh:
            continue

        result[zh] = {
            "zh": zh,
            "vi": str(row.get("標準越文（建議）", "")).strip(),
            "en": str(row.get("標準英文（建議）", "")).strip(),
            "category": str(row.get("類別", "")).strip(),
            "status": str(row.get("狀態", "")).strip(),
        }

    return result


def init_language(default_lang: str = "zh") -> None:
    if "lang" not in st.session_state:
        st.session_state.lang = default_lang


def set_language(lang: str) -> None:
    st.session_state.lang = normalize_lang(lang)


def get_language() -> str:
    return normalize_lang(st.session_state.get("lang", "zh"))


def normalize_lang(lang: str | None) -> str:
    value = str(lang or "zh").strip().lower()
    if value in {"zh", "tc", "zh-tw", "traditional chinese", "中文"}:
        return "zh"
    if value in {"vi", "vn", "vi-vn", "vietnamese", "越文", "越南文"}:
        return "vi"
    if value in {"en", "en-us", "en-gb", "english", "英文"}:
        return "en"
    return "zh"


def tr(term: str, lang: str | None = None) -> str:
    dictionary = load_dictionary()
    current_lang = normalize_lang(lang or get_language())

    item = dictionary.get(term)
    if not item:
        return f"[MISS:{term}]"

    if current_lang == "zh":
        return term

    value = item.get(current_lang, "").strip()
    return value if value else term
