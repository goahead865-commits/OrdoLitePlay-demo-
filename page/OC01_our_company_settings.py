from typing import Optional

import pandas as pd
import streamlit as st
from compact_layout import apply_compact_layout
import auth
from sqlalchemy import text

from db import get_engine

apply_compact_layout()

st.markdown(
    """
    <style>
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
      min-height: 1.55rem !important; padding-top: .1rem !important; padding-bottom: .1rem !important;
    }
    [data-testid="stTextArea"] textarea { min-height: 2.4rem !important; }
    [data-testid="stTextInput"], [data-testid="stNumberInput"], [data-testid="stSelectbox"], [data-testid="stTextArea"] { margin-bottom: 0 !important; }
    hr { margin: .25rem 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================
# I18N Helper
# =========================================
TRANSLATIONS = {
    "我方公司資料設定": {"vi": "Thiết lập thông tin công ty chúng tôi", "en": "Our Company Settings"},
    "維護 our_company 與 our_bank。先把公司資料放整齊，後面 AR/AP 才不會像一桌沒對齊的報表。": {
        "vi": "Quản lý our_company và our_bank. Hãy sắp xếp dữ liệu công ty cho gọn gàng trước, để AR/AP sau này không lộn xộn như một chồng báo cáo lệch hàng.",
        "en": "Maintain our_company and our_bank. Keep company data organized first, so AR/AP won't look like a pile of misaligned reports later."
    },
    "公司": {"vi": "Công ty", "en": "Company"},
    "＋ 新增公司": {"vi": "＋ Thêm công ty", "en": "＋ Add Company"},
    "未命名公司": {"vi": "Công ty chưa đặt tên", "en": "Unnamed Company"},
    "公司基本資料": {"vi": "Thông tin cơ bản công ty", "en": "Company Basic Information"},
    "公司代號": {"vi": "Mã công ty", "en": "Company Code"},
    "公司名稱(外文)": {"vi": "Tên công ty (ngoại ngữ)", "en": "Company Name (Foreign Language)"},
    "公司簡稱": {"vi": "Tên viết tắt công ty", "en": "Company Short Name"},
    "公司中文名稱": {"vi": "Tên công ty tiếng Trung", "en": "Company Chinese Name"},
    "公司稅率(%)": {"vi": "Thuế suất công ty (%)", "en": "Company Tax Rate (%)"},
    "公司電話": {"vi": "Điện thoại công ty", "en": "Company Phone"},
    "統編 / 稅號": {"vi": "Mã số thuế", "en": "Tax ID / Tax Number"},
    "負責人": {"vi": "Người phụ trách", "en": "Person in Charge"},
    "公司地址": {"vi": "Địa chỉ công ty", "en": "Company Address"},
    "新增公司資料": {"vi": "Thêm dữ liệu công ty", "en": "Add Company Data"},
    "儲存公司資料": {"vi": "Lưu dữ liệu công ty", "en": "Save Company Data"},
    "公司名稱(外文)不能空白。先有公司，再談帝國。": {
        "vi": "Tên công ty (ngoại ngữ) không được để trống. Phải có công ty trước rồi mới nói chuyện đế chế.",
        "en": "Company Name (Foreign Language) cannot be blank. Build the company first, then talk about the empire."
    },
    "公司資料已更新。": {"vi": "Dữ liệu công ty đã được cập nhật.", "en": "Company data updated."},
    "已新增公司資料，ID = ": {"vi": "Đã thêm dữ liệu công ty, ID = ", "en": "Company data added, ID = "},
    "儲存失敗：": {"vi": "Lưu thất bại: ", "en": "Save failed: "},
    "先新增或選擇一家公司，下面的銀行資料區才會啟用。": {
        "vi": "Vui lòng thêm mới hoặc chọn một công ty trước, khu vực dữ liệu ngân hàng bên dưới mới được kích hoạt.",
        "en": "Please add or select a company first to enable the bank information section below."
    },
    "我方銀行資訊": {"vi": "Thông tin ngân hàng của chúng tôi", "en": "Our Bank Information"},
    "銀行ID": {"vi": "ID ngân hàng", "en": "Bank ID"},
    "銀行代號": {"vi": "Mã ngân hàng", "en": "Bank Code"},
    "銀行名稱": {"vi": "Tên ngân hàng", "en": "Bank Name"},
    "戶名": {"vi": "Tên tài khoản", "en": "Account Name"},
    "帳號": {"vi": "Số tài khoản", "en": "Account Number"},
    "預設": {"vi": "Mặc định", "en": "Default"},
    "是": {"vi": "Có", "en": "Yes"},
    "＋ 新增銀行帳戶": {"vi": "＋ Thêm tài khoản ngân hàng", "en": "＋ Add Bank Account"},
    "銀行帳戶": {"vi": "Tài khoản ngân hàng", "en": "Bank Account"},
    "銀行帳號": {"vi": "Số tài khoản ngân hàng", "en": "Bank Account Number"},
    "儲存銀行資料": {"vi": "Lưu dữ liệu ngân hàng", "en": "Save Bank Data"},
    "設為預設銀行": {"vi": "Đặt làm ngân hàng mặc định", "en": "Set as Default Bank"},
    "刪除銀行資料": {"vi": "Xóa dữ liệu ngân hàng", "en": "Delete Bank Data"},
    "銀行名稱或銀行帳號至少要填一個，不然這筆資料存了也像空箱。": {
        "vi": "Ít nhất phải nhập tên ngân hàng hoặc số tài khoản, nếu không bản ghi này lưu lại cũng như một cái thùng rỗng.",
        "en": "Enter at least a bank name or bank account number, otherwise this record is just an empty box."
    },
    "銀行資料已儲存。": {"vi": "Dữ liệu ngân hàng đã được lưu.", "en": "Bank data saved."},
    "要先選一筆既有銀行資料，才能設為預設。": {
        "vi": "Phải chọn một dữ liệu ngân hàng hiện có trước thì mới có thể đặt làm mặc định.",
        "en": "Select an existing bank record before setting it as default."
    },
    "已設為預設銀行。": {"vi": "Đã đặt làm ngân hàng mặc định.", "en": "Default bank set."},
    "設定預設銀行失敗：": {"vi": "Đặt ngân hàng mặc định thất bại: ", "en": "Set default bank failed: "},
    "目前沒有選到可刪除的銀行資料。": {
        "vi": "Hiện chưa chọn được dữ liệu ngân hàng nào để xóa.",
        "en": "No bank record selected for deletion."
    },
    "銀行資料已刪除。": {"vi": "Dữ liệu ngân hàng đã bị xóa.", "en": "Bank data deleted."},
    "儲存銀行資料失敗：": {"vi": "Lưu dữ liệu ngân hàng thất bại: ", "en": "Save bank data failed: "},
    "刪除銀行資料失敗：": {"vi": "Xóa dữ liệu ngân hàng thất bại: ", "en": "Delete bank data failed: "},
}

def get_lang() -> str:
    lang = st.session_state.get("lang", "zh")
    return lang if lang in {"zh", "vi", "en"} else "zh"

def _t(text: str) -> str:
    lang = get_lang()
    if lang == "zh":
        return text
    return TRANSLATIONS.get(text, {}).get(lang, text)

PAGE_KEY = "OC01_our_company_settings"
auth.require_read(PAGE_KEY)


@st.cache_resource
def get_db_engine():
    return get_engine()


@st.cache_data(ttl=300)
def load_company_master() -> pd.DataFrame:
    sql = """
        SELECT
            oc.our_company_id,
            oc.our_company_code,
            oc.our_company_name,
            oc.our_company_chinese_nam,
            oc.our_company_short_name,
            oc.our_company_add,
            oc.our_company_boss,
            oc.our_company_tax_rate,
            oc.our_company_phone,
            oc.our_company_tax_num,
            oc.our_company_bank_id,
            s.stuff_name AS boss_name
        FROM our_company oc
        LEFT JOIN stuff s ON s.stuff_id = oc.our_company_boss
        ORDER BY oc.our_company_id
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


@st.cache_data(ttl=300)
def load_staff_master() -> pd.DataFrame:
    sql = """
        SELECT
            stuff_id,
            stuff_name
        FROM stuff
        ORDER BY stuff_name
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


@st.cache_data(ttl=300)
def load_company_bank_rows(company_id: int) -> pd.DataFrame:
    sql = """
        SELECT
            ob.our_bank_id,
            ob.our_company_id,
            ob.our_company_bank_num,
            ob.our_company_bank_name,
            ob.our_company_account_name,
            ob.our_company_account_code,
            CASE WHEN oc.our_company_bank_id = ob.our_bank_id THEN 1 ELSE 0 END AS is_default
        FROM our_bank ob
        LEFT JOIN our_company oc ON oc.our_company_id = ob.our_company_id
        WHERE ob.our_company_id = :company_id
        ORDER BY is_default DESC, ob.our_bank_id
    """
    with get_db_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params={"company_id": int(company_id)})


@st.cache_data(ttl=300)
def get_company_detail(company_id: int) -> Optional[dict]:
    df = load_company_master()
    row = df.loc[df["our_company_id"] == int(company_id)]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


@st.cache_data(ttl=300)
def get_bank_detail(bank_id: int) -> Optional[dict]:
    sql = """
        SELECT
            our_bank_id,
            our_company_id,
            our_company_bank_num,
            our_company_bank_name,
            our_company_account_name,
            our_company_account_code
        FROM our_bank
        WHERE our_bank_id = :bank_id
    """
    with get_db_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params={"bank_id": int(bank_id)})
    if df.empty:
        return None
    return df.iloc[0].to_dict()



def clear_all_cache() -> None:
    st.cache_data.clear()



def normalize_optional_int(value):
    if value in (None, ""):
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return int(value)



def save_company(payload: dict) -> None:
    auth.require_edit(PAGE_KEY)
    sql = text(
        """
        UPDATE our_company
        SET
            our_company_code = :our_company_code,
            our_company_name = :our_company_name,
            our_company_chinese_nam = :our_company_chinese_nam,
            our_company_short_name = :our_company_short_name,
            our_company_add = :our_company_add,
            our_company_boss = :our_company_boss,
            our_company_tax_rate = :our_company_tax_rate,
            our_company_phone = :our_company_phone,
            our_company_tax_num = :our_company_tax_num,
            our_company_bank_id = :our_company_bank_id
        WHERE our_company_id = :our_company_id
        """
    )
    with get_db_engine().begin() as conn:
        conn.execute(sql, payload)
    clear_all_cache()



def insert_company(payload: dict) -> int:
    auth.require_edit(PAGE_KEY)
    sql = text(
        """
        INSERT INTO our_company (
            our_company_code,
            our_company_name,
            our_company_chinese_nam,
            our_company_short_name,
            our_company_add,
            our_company_boss,
            our_company_tax_rate,
            our_company_phone,
            our_company_tax_num,
            our_company_bank_id
        ) VALUES (
            :our_company_code,
            :our_company_name,
            :our_company_chinese_nam,
            :our_company_short_name,
            :our_company_add,
            :our_company_boss,
            :our_company_tax_rate,
            :our_company_phone,
            :our_company_tax_num,
            :our_company_bank_id
        )
        """
    )
    with get_db_engine().begin() as conn:
        result = conn.execute(sql, payload)
        new_id = int(result.lastrowid)
    clear_all_cache()
    return new_id



def upsert_bank(bank_id: Optional[int], payload: dict) -> int:
    auth.require_edit(PAGE_KEY)
    if bank_id:
        sql = text(
            """
            UPDATE our_bank
            SET
                our_company_bank_num = :our_company_bank_num,
                our_company_bank_name = :our_company_bank_name,
                our_company_account_name = :our_company_account_name,
                our_company_account_code = :our_company_account_code
            WHERE our_bank_id = :our_bank_id
            """
        )
        params = dict(payload)
        params["our_bank_id"] = int(bank_id)
        with get_db_engine().begin() as conn:
            conn.execute(sql, params)
        clear_all_cache()
        return int(bank_id)

    sql = text(
        """
        INSERT INTO our_bank (
            our_company_id,
            our_company_bank_num,
            our_company_bank_name,
            our_company_account_name,
            our_company_account_code
        ) VALUES (
            :our_company_id,
            :our_company_bank_num,
            :our_company_bank_name,
            :our_company_account_name,
            :our_company_account_code
        )
        """
    )
    with get_db_engine().begin() as conn:
        result = conn.execute(sql, payload)
        new_id = int(result.lastrowid)
    clear_all_cache()
    return new_id



def set_default_bank(company_id: int, bank_id: int) -> None:
    auth.require_edit(PAGE_KEY)
    sql = text(
        """
        UPDATE our_company
        SET our_company_bank_id = :bank_id
        WHERE our_company_id = :company_id
        """
    )
    with get_db_engine().begin() as conn:
        conn.execute(sql, {"bank_id": int(bank_id), "company_id": int(company_id)})
    clear_all_cache()



def delete_bank(company_id: int, bank_id: int) -> None:
    auth.require_delete(PAGE_KEY)
    with get_db_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE our_company
                SET our_company_bank_id = NULL
                WHERE our_company_id = :company_id AND our_company_bank_id = :bank_id
                """
            ),
            {"company_id": int(company_id), "bank_id": int(bank_id)},
        )
        conn.execute(text("DELETE FROM our_bank WHERE our_bank_id = :bank_id"), {"bank_id": int(bank_id)})
    clear_all_cache()



def build_company_options(company_df: pd.DataFrame) -> list[str]:
    options = [_t("＋ 新增公司")]
    for _, row in company_df.iterrows():
        code = "" if pd.isna(row.get("our_company_code")) else str(row.get("our_company_code"))
        short_name = row.get("our_company_short_name") or ""
        company_name = row.get("our_company_chinese_nam") or row.get("our_company_name") or _t("未命名公司")
        label = f"{int(row['our_company_id'])}｜{company_name}"
        if short_name:
            label += f"｜{short_name}"
        if code:
            label += f"｜Code:{code}"
        options.append(label)
    return options



def resolve_selected_company_id(label: str) -> Optional[int]:
    if not label or label.startswith("＋"):
        return None
    try:
        return int(label.split("｜", 1)[0])
    except Exception:
        return None



def main() -> None:
    st.title(f"🏢 {_t('我方公司資料設定')}")
    st.caption(_t("維護 our_company 與 our_bank。先把公司資料放整齊，後面 AR/AP 才不會像一桌沒對齊的報表。"))

    company_df = load_company_master()
    staff_df = load_staff_master()

    company_options = build_company_options(company_df)
    default_index = 0
    if st.session_state.get("oc01_selected_company_id"):
        selected_company_id = int(st.session_state["oc01_selected_company_id"])
        for idx, label in enumerate(company_options):
            if label.startswith(f"{selected_company_id}｜"):
                default_index = idx
                break

    selected_label = st.selectbox(
        _t("公司"),
        options=company_options,
        index=default_index,
        key="oc01_company_picker",
    )
    selected_company_id = resolve_selected_company_id(selected_label)
    st.session_state["oc01_selected_company_id"] = selected_company_id

    selected_company = get_company_detail(selected_company_id) if selected_company_id else None

    with st.form("oc01_company_form"):
        st.subheader(_t("公司基本資料"))
        col1, col2, col3 = st.columns(3)
        with col1:
            company_code = st.text_input(_t("公司代號"), value="" if not selected_company or pd.isna(selected_company.get("our_company_code")) else str(int(selected_company.get("our_company_code"))))
            company_name = st.text_input(_t("公司名稱(外文)"), value="" if not selected_company else str(selected_company.get("our_company_name") or ""))
            company_short_name = st.text_input(_t("公司簡稱"), value="" if not selected_company else str(selected_company.get("our_company_short_name") or ""))
        with col2:
            company_name_zh = st.text_input(_t("公司中文名稱"), value="" if not selected_company else str(selected_company.get("our_company_chinese_nam") or ""))
            tax_rate = st.number_input(
                _t("公司稅率(%)"),
                min_value=0,
                max_value=100,
                value=0 if not selected_company or pd.isna(selected_company.get("our_company_tax_rate")) else int(selected_company.get("our_company_tax_rate") or 0),
                step=1,
            )
            company_phone = st.text_input(_t("公司電話"), value="" if not selected_company else str(selected_company.get("our_company_phone") or ""))
        with col3:
            company_tax_num = st.text_input(_t("統編 / 稅號"), value="" if not selected_company else str(selected_company.get("our_company_tax_num") or ""))
            staff_options = [""] + staff_df["stuff_name"].astype(str).tolist()
            default_boss_name = ""
            if selected_company and selected_company.get("boss_name") and not pd.isna(selected_company.get("boss_name")):
                default_boss_name = str(selected_company.get("boss_name"))
            boss_name = st.selectbox(
                _t("負責人"),
                options=staff_options,
                index=staff_options.index(default_boss_name) if default_boss_name in staff_options else 0,
            )
        company_add = st.text_area(_t("公司地址"), value="" if not selected_company else str(selected_company.get("our_company_add") or ""), height=48)

        submit_label = _t("新增公司資料") if not selected_company_id else _t("儲存公司資料")
        company_submit = st.form_submit_button(submit_label, type="primary")

    if company_submit:
        company_name_clean = company_name.strip()
        if not company_name_clean:
            st.error(_t("公司名稱(外文)不能空白。先有公司，再談帝國。"))
            st.stop()

        boss_id = None
        if boss_name:
            match = staff_df.loc[staff_df["stuff_name"] == boss_name, "stuff_id"]
            if not match.empty:
                boss_id = int(match.iloc[0])

        payload = {
            "our_company_code": normalize_optional_int(company_code.strip()),
            "our_company_name": company_name_clean,
            "our_company_chinese_nam": company_name_zh.strip() or None,
            "our_company_short_name": company_short_name.strip() or None,
            "our_company_add": company_add.strip() or None,
            "our_company_boss": boss_id,
            "our_company_tax_rate": int(tax_rate),
            "our_company_phone": company_phone.strip() or None,
            "our_company_tax_num": company_tax_num.strip() or None,
            "our_company_bank_id": int(selected_company.get("our_company_bank_id")) if selected_company and selected_company.get("our_company_bank_id") and not pd.isna(selected_company.get("our_company_bank_id")) else None,
        }

        try:
            if selected_company_id:
                payload["our_company_id"] = int(selected_company_id)
                save_company(payload)
                st.success(_t("公司資料已更新。"))
            else:
                new_company_id = insert_company(payload)
                st.session_state["oc01_selected_company_id"] = new_company_id
                st.success(f"{_t('已新增公司資料，ID = ')}{new_company_id}。")
            st.rerun()
        except Exception as exc:
            st.error(f"{_t('儲存失敗：')}{exc}")

    if not selected_company_id:
        st.info(_t("先新增或選擇一家公司，下面的銀行資料區才會啟用。"))
        return

    bank_df = load_company_bank_rows(int(selected_company_id))
    st.divider()
    st.subheader(_t("我方銀行資訊"))

    display_bank_df = bank_df.rename(
        columns={
            "our_bank_id": _t("銀行ID"),
            "our_company_bank_num": _t("銀行代號"),
            "our_company_bank_name": _t("銀行名稱"),
            "our_company_account_name": _t("戶名"),
            "our_company_account_code": _t("帳號"),
            "is_default": _t("預設"),
        }
    )[[_t("銀行ID"), _t("銀行代號"), _t("銀行名稱"), _t("戶名"), _t("帳號"), _t("預設")]]
    if not display_bank_df.empty:
        display_bank_df[_t("預設")] = display_bank_df[_t("預設")].map({1: _t("是"), 0: ""})
    st.dataframe(display_bank_df, use_container_width=True, hide_index=True, height=120)

    bank_options = [_t("＋ 新增銀行帳戶")] + [
        f"{int(row['our_bank_id'])}｜{row['our_company_bank_name'] or ''}｜{row['our_company_bank_num'] or ''}｜{row['our_company_account_code'] or ''}"
        for _, row in bank_df.iterrows()
    ]
    default_bank_index = 0
    if st.session_state.get("oc01_selected_bank_id"):
        selected_bank_id_from_state = int(st.session_state["oc01_selected_bank_id"])
        for idx, label in enumerate(bank_options):
            if label.startswith(f"{selected_bank_id_from_state}｜"):
                default_bank_index = idx
                break

    bank_label = st.selectbox(_t("銀行帳戶"), options=bank_options, index=default_bank_index, key="oc01_bank_picker")
    selected_bank_id = None if bank_label.startswith("＋") else int(bank_label.split("｜", 1)[0])
    st.session_state["oc01_selected_bank_id"] = selected_bank_id
    selected_bank = get_bank_detail(selected_bank_id) if selected_bank_id else None

    with st.form("oc01_bank_form"):
        col1, col2 = st.columns(2)
        with col1:
            bank_num = st.text_input(_t("銀行代號"), value="" if not selected_bank else str(selected_bank.get("our_company_bank_num") or ""))
            bank_name = st.text_input(_t("銀行名稱"), value="" if not selected_bank else str(selected_bank.get("our_company_bank_name") or ""))
        with col2:
            account_name = st.text_input(_t("戶名"), value="" if not selected_bank else str(selected_bank.get("our_company_account_name") or ""))
            account_code = st.text_input(_t("銀行帳號"), value="" if not selected_bank else str(selected_bank.get("our_company_account_code") or ""))

        c1, c2, c3 = st.columns([1, 1, 1.4])
        save_bank_btn = c1.form_submit_button(_t("儲存銀行資料"), type="primary")
        set_default_btn = c2.form_submit_button(_t("設為預設銀行"))
        delete_bank_btn = c3.form_submit_button(_t("刪除銀行資料"))

    if save_bank_btn:
        if not bank_name.strip() and not account_code.strip():
            st.error(_t("銀行名稱或銀行帳號至少要填一個，不然這筆資料存了也像空箱。"))
            st.stop()
        payload = {
            "our_company_id": int(selected_company_id),
            "our_company_bank_num": bank_num.strip() or None,
            "our_company_bank_name": bank_name.strip() or None,
            "our_company_account_name": account_name.strip() or None,
            "our_company_account_code": account_code.strip() or None,
        }
        try:
            saved_bank_id = upsert_bank(selected_bank_id, payload)
            st.session_state["oc01_selected_bank_id"] = saved_bank_id
            st.success(_t("銀行資料已儲存。"))
            st.rerun()
        except Exception as exc:
            st.error(f"{_t('儲存銀行資料失敗：')}{exc}")

    if set_default_btn:
        if not selected_bank_id:
            st.error(_t("要先選一筆既有銀行資料，才能設為預設。"))
        else:
            try:
                set_default_bank(int(selected_company_id), int(selected_bank_id))
                st.success(_t("已設為預設銀行。"))
                st.rerun()
            except Exception as exc:
                st.error(f"{_t('設定預設銀行失敗：')}{exc}")

    if delete_bank_btn:
        if not selected_bank_id:
            st.error(_t("目前沒有選到可刪除的銀行資料。"))
        else:
            try:
                delete_bank(int(selected_company_id), int(selected_bank_id))
                st.session_state["oc01_selected_bank_id"] = None
                st.success(_t("銀行資料已刪除。"))
                st.rerun()
            except Exception as exc:
                st.error(f"{_t('刪除銀行資料失敗：')}{exc}")


if __name__ == "__main__":
    main()
