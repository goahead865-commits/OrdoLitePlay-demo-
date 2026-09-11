import streamlit as st
from compact_layout import apply_compact_layout
from db import run_query, run_execute

apply_compact_layout()

st.title("Customer Master（客戶主檔）")

df = run_query("SELECT * FROM customer ORDER BY id DESC LIMIT 200")
st.dataframe(df, use_container_width=True)

st.subheader("➕ 新增客戶")
with st.form("add_customer"):
    name = st.text_input("客戶名稱 *")
    submitted = st.form_submit_button("儲存")
    if submitted and name:
        run_execute(
            "INSERT INTO customer (name) VALUES (:name)",
            {"name": name},
        )
        st.success("已新增客戶。")
        st.rerun()
