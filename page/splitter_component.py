"""Navigation-safe wrapper for the local vertical splitter."""
from pathlib import Path
from typing import Any
import streamlit.components.v1 as components
import streamlit as st

_component: Any = None

def render_vertical_splitter(
    top_height: int,
    *,
    key: str,
    min_top: int = 200,
    max_top: int = 600,
) -> Any:
    global _component
    if _component is None:
        _component = components.declare_component(
            "vertical_splitter",
            path=str(Path(__file__).resolve().parent / "components" / "vertical_splitter"),
        )
    return _component(
        top_height=int(top_height),
        min_top=int(min_top),
        max_top=int(max_top),
        default=None,
        key=key,
    )


def apply_vertical_splitter(state_key: str, component_key: str, *, default: int = 260, min_top: int = 150, max_top: int = 430) -> None:
    """Render a splitter immediately and persist its requested top-pane height."""
    st.session_state.setdefault(state_key, default)
    result = render_vertical_splitter(
        int(st.session_state[state_key]), key=component_key, min_top=min_top, max_top=max_top
    )
    if isinstance(result, dict) and "top_height" in result:
        next_height = max(min_top, min(max_top, int(result["top_height"])))
        if next_height != int(st.session_state[state_key]):
            st.session_state[state_key] = next_height
            st.rerun()
