"""人员花名册 — 新增、改名、停用、恢复、临时支援标记。"""

import pandas as pd
import streamlit as st

from database.engine import init_db, get_session
from database.crud import (
    seed_staff, get_all_staff, add_staff, update_staff,
    remove_staff, restore_staff, permanently_delete_staff,
)
from ui.styles import apply_styles, page_header, section_title, kpi_row, note, divider


def main():
    apply_styles()
    page_header("人员花名册", "维护运营人员名单 · 停用不影响历史排班记录")

    init_db()
    session = get_session()
    seed_staff(session)
    all_staff = get_all_staff(session)

    active = [s for s in all_staff if s.is_active]
    inactive = [s for s in all_staff if not s.is_active]
    temp = [s for s in all_staff if s.is_temporary]
    kpi_row([
        ("在职", len(active), "good"),
        ("已停用", len(inactive), "" if not inactive else "warn"),
        ("临时支援", len(temp), ""),
    ])

    # ── 新增人员 ─────────────────────────────────
    section_title("新增人员")
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1.2, 1])
        with c1:
            new_name = st.text_input("姓名", placeholder="输入姓名",
                                     label_visibility="collapsed")
        with c2:
            is_temp = st.checkbox("临时支援", value=False)
        with c3:
            if st.button("添加人员", type="primary", use_container_width=True):
                name = new_name.strip()
                if not name:
                    st.warning("请输入姓名")
                elif name in {s.name for s in all_staff}:
                    st.error(f"「{name}」已存在")
                else:
                    add_staff(session, name, is_temporary=is_temp)
                    st.success(f"已添加「{name}」")
                    st.rerun()

    # ── 当前花名册 ───────────────────────────────
    section_title("当前花名册", f"共 {len(all_staff)} 人")
    if not all_staff:
        note("暂无人员，请先添加。")
        session.close()
        return

    df = pd.DataFrame([{
        "姓名": s.name,
        "状态": "在职" if s.is_active else "已停用",
        "类型": "临时支援" if s.is_temporary else "正式运营",
        "加入日期": s.created_at.strftime("%Y-%m-%d") if s.created_at else "—",
    } for s in all_staff])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── 编辑 / 状态操作 ──────────────────────────
    section_title("编辑与状态", "改名、停用、恢复或永久删除")
    options = {f"{s.name}　·　{'在职' if s.is_active else '已停用'}": s for s in all_staff}
    with st.container(border=True):
        label = st.selectbox("选择人员", list(options.keys()))
        target = options[label]

        ec1, ec2 = st.columns(2)
        with ec1:
            st.markdown("**修改信息**")
            rename = st.text_input("姓名", value=target.name, key="rename")
            edit_temp = st.checkbox("临时支援", value=target.is_temporary, key="edit_temp")
            if st.button("保存修改", use_container_width=True):
                changed = False
                new = rename.strip()
                if new and new != target.name:
                    if new in {s.name for s in all_staff if s.id != target.id}:
                        st.error(f"「{new}」已被占用")
                    else:
                        update_staff(session, target.id, name=new)
                        changed = True
                if edit_temp != target.is_temporary:
                    update_staff(session, target.id, is_temporary=edit_temp)
                    changed = True
                if changed:
                    st.success("已保存")
                    st.rerun()
                else:
                    st.info("未做修改")

        with ec2:
            st.markdown("**状态操作**")
            if target.is_active:
                st.markdown('<div class="tip">停用后该人员不再出现在排班的在岗列表，'
                            '但历史记录保留。</div>', unsafe_allow_html=True)
                if st.button("停用此人", use_container_width=True):
                    remove_staff(session, target.id)
                    st.rerun()
            else:
                if st.button("恢复在职", use_container_width=True):
                    restore_staff(session, target.id)
                    st.rerun()
                if st.button("永久删除", use_container_width=True):
                    if permanently_delete_staff(session, target.id):
                        st.success("已永久删除")
                        st.rerun()
                    else:
                        st.error("该人员有历史排班记录，无法永久删除，请改用「停用」。")

    session.close()


main()
