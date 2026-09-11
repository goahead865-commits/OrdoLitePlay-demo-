import streamlit as st
from compact_layout import apply_compact_layout
from db import run_query, run_execute

apply_compact_layout()

st.title("Material Master（物料主檔）")
df = run_query("SELECT * FROM material ORDER BY id DESC LIMIT 200")
st.dataframe(df, use_container_width=True)
