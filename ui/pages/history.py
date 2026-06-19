"""历史记录 — 浏览与回看已保存的排班。"""

import pandas as pd
import streamlit as st

from database.engine import init_db, get_session
from database.crud import (
    get_all_schedules, seed_staff, get_staff_shift_stats, get_all_staff,
)
from config import AssignmentType
from ui.styles import apply_styles, page_header, section_title, kpi_row, note
from ui.components.schedule_grid import render_entries_grid, render_traditional_grid, build_traditional_text
from ui.components.summary_cards import render_summary_cards
from utils.dates import get_week_dates, format_date
from utils.export import export_to_excel

_STATUS_CN = {"generated": "已生成", "edited": "已编辑", "locked": "已锁定"}


def main():
    apply_styles()
    page_header("历史排班记录", "回看、对比并导出过往每周的排班结果")

    init_db()
    session = get_session()
    seed_staff(session)
    staff_map = {s.id: s.name for s in get_all_staff(session)}

    schedules = get_all_schedules(session)
    if not schedules:
        note("暂无历史记录。在「排班生成」中保存排班后，这里会出现对应记录。")
        session.close()
        return

    # ── 周次选择 ──────────────────────────────────
    section_title("选择周次", f"共 {len(schedules)} 条记录")
    labels = []
    for s in schedules:
        wd = get_week_dates(s.week_start)
        labels.append(f"{format_date(wd[0])} – {format_date(wd[-1])}　·　"
                      f"{s.shift_model} 班　·　{_STATUS_CN.get(s.status, s.status)}")
    idx = st.selectbox("排班周", range(len(schedules)),
                       format_func=lambda i: labels[i], label_visibility="collapsed")
    sched = schedules[idx]
    week_dates = get_week_dates(sched.week_start)

    if not sched.entries:
        note("该周排班数据为空。")
        session.close()
        return

    # ── 概览指标 ─────────────────────────────────
    staff_ids = sorted({e.staff_id for e in sched.entries})
    work_entries = [e for e in sched.entries if e.assignment_type != int(AssignmentType.REST)]
    created = sched.created_at.strftime("%Y-%m-%d %H:%M") if sched.created_at else "—"
    kpi_row([
        ("参与人数", len(staff_ids), ""),
        ("班次模式", f"{sched.shift_model} 班", ""),
        ("目标值", sched.solver_score if sched.solver_score is not None else "—", ""),
        ("生成时间", created, ""),
    ])

    # ── 排班矩阵 ─────────────────────────────────
    section_title("排班矩阵")

    # 显示格式切换（用 container 稳定包裹，避免切换时 DOM 冲突）
    if "hist_view_mode" not in st.session_state:
        st.session_state.hist_view_mode = "传统班表（行=班次，列=日期）"
    view_mode = st.radio("显示格式", ["传统班表（行=班次，列=日期）",
                                       "人员矩阵（行=人，列=日期）"],
                          horizontal=True, index=0, key="hist_view",
                          on_change=lambda: st.session_state.update(
                              hist_view_mode=st.session_state.hist_view))
    st.session_state.hist_view_mode = view_mode

    # 先重建 solution（供传统格式使用）
    id_to_idx = {sid: i for i, sid in enumerate(staff_ids)}
    names = [staff_map.get(sid, f"#{sid}") for sid in staff_ids]
    solution = {}
    for e in sched.entries:
        solution[(id_to_idx[e.staff_id], e.day_of_week)] = AssignmentType(e.assignment_type)

    if view_mode.startswith("传统"):
        with st.container(key="hist_trad_container"):
            render_traditional_grid(solution, names, week_dates=week_dates)
            trad_text = build_traditional_text(solution, names, week_dates=week_dates)
            st.text_area("📋 一键复制（粘贴到在线表格）", value=trad_text, height=140,
                         key=f"hist_copy_{sched.id}",
                         help="Cmd+A 全选 → Cmd+C 复制 → 粘贴到飞书/钉钉在线表格")
    else:
        with st.container(key="hist_matrix_container"):
            render_entries_grid(sched.entries, staff_map, week_dates=week_dates)

    # ── 工时对账 ─────────────────────────────────
    section_title("工时对账")
    render_summary_cards(solution, names)

    # ── 累计分布（跨周，含进度条） ────────────────
    section_title("累计班次分布", "截至目前所有已保存周次的合计")
    rows = []
    for sid in staff_ids:
        s = get_staff_shift_stats(session, sid)
        rows.append({
            "姓名": staff_map.get(sid, f"#{sid}"),
            "早班": s["early"], "中班": s["mid"], "晚班": s["late"],
            "坐班": s["office"], "外派": s["external"], "总班次": s["total_shifts"],
        })
    stats_df = pd.DataFrame(rows)
    max_total = max(int(stats_df["总班次"].max()), 1)
    st.dataframe(
        stats_df, use_container_width=True, hide_index=True,
        column_config={
            "总班次": st.column_config.ProgressColumn(
                "总班次", min_value=0, max_value=max_total, format="%d"),
        },
    )

    # ── 导出 ─────────────────────────────────────
    section_title("导出")
    st.download_button(
        "导出该周 Excel",
        data=export_to_excel(solution, names, sched.week_start),
        file_name=f"排班_{sched.week_start}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    session.close()


main()
