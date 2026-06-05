"""直播间跟播运营排班系统 — Streamlit 入口。"""

import streamlit as st
from ui.styles import apply_styles

st.set_page_config(
    page_title="直播排班系统",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"about": "直播间跟播运营排班系统 · 基于 OR-Tools CP-SAT"},
)

apply_styles()

generator_page = st.Page("ui/pages/generator.py", title="排班生成", icon="🗓️")
staff_page = st.Page("ui/pages/staff_mgmt.py", title="人员花名册", icon="👥")
history_page = st.Page("ui/pages/history.py", title="历史记录", icon="🗂️")

pg = st.navigation({
    "排班": [generator_page],
    "管理": [staff_page, history_page],
})
pg.run()
