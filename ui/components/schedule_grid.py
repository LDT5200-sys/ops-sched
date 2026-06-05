"""排班矩阵组件。

- render_readonly_grid: 带颜色编码的只读 HTML 表（生成结果 / 历史查看）。
- render_schedule_editor: 可编辑数据编辑器（手动微调）。
- render_entries_grid: 把数据库 entries 还原成只读表，供历史页与上周预览复用。
"""

import streamlit as st
import pandas as pd

from config import DAY_NAMES, ASSIGNMENT_LABELS, AssignmentType
from ui.styles import get_cell_class

# 标准展示/编辑用的班次顺序
_DISPLAY_TYPES = [
    AssignmentType.REST, AssignmentType.EARLY, AssignmentType.MID,
    AssignmentType.LATE, AssignmentType.OFFICE, AssignmentType.EXTERNAL,
]


def render_readonly_grid(solution, staff_names, num_days=7, week_dates=None):
    """渲染带颜色编码的只读排班表。

    Args:
        solution: {(p, d): AssignmentType}
        staff_names: 人员姓名列表，索引对应 p
        week_dates: 可选，长度为 num_days 的 date 列表，用于在表头显示日期
    """
    html = ['<table class="schedule-table"><thead><tr><th>姓名</th>']
    for d in range(num_days):
        date_html = ""
        if week_dates and d < len(week_dates):
            wd = week_dates[d]
            date_html = f'<div class="th-date">{wd.month}/{wd.day}</div>'
        html.append(f'<th><div class="th-day">{DAY_NAMES[d]}</div>{date_html}</th>')
    html.append('</tr></thead><tbody>')

    for p in range(len(staff_names)):
        html.append(f'<tr><td>{staff_names[p]}</td>')
        for d in range(num_days):
            t = solution.get((p, d))
            label = ASSIGNMENT_LABELS.get(t, "—")
            html.append(f'<td class="{get_cell_class(label)}">{label}</td>')
        html.append('</tr>')
    html.append('</tbody></table>')

    st.markdown("".join(html), unsafe_allow_html=True)


def render_schedule_editor(solution, staff_names, num_days=7, key_prefix="grid"):
    """渲染可编辑排班矩阵，返回编辑后的 solution dict {(p, d): AssignmentType}。"""
    options = [ASSIGNMENT_LABELS[t] for t in _DISPLAY_TYPES]
    label_to_type = {ASSIGNMENT_LABELS[t]: t for t in _DISPLAY_TYPES}

    data = {}
    for p, name in enumerate(staff_names):
        data[name] = {DAY_NAMES[d]: ASSIGNMENT_LABELS.get(solution.get((p, d)), "休息")
                      for d in range(num_days)}
    df = pd.DataFrame(data).T

    column_config = {
        DAY_NAMES[d]: st.column_config.SelectboxColumn(
            DAY_NAMES[d], options=options, required=True, width="small"
        )
        for d in range(num_days)
    }

    edited = st.data_editor(
        df, column_config=column_config, use_container_width=True,
        hide_index=False, key=f"{key_prefix}_editor",
    )

    new_solution = {}
    for p, name in enumerate(staff_names):
        for d in range(num_days):
            new_solution[(p, d)] = label_to_type.get(edited.loc[name, DAY_NAMES[d]],
                                                      AssignmentType.REST)
    return new_solution


def render_entries_grid(entries, staff_map, num_days=7, week_dates=None):
    """把数据库 entries 渲染成只读表。

    Args:
        entries: ScheduleEntry 列表
        staff_map: {staff_id: name}
    Returns:
        (solution, staff_names)：重映射为连续索引的解和姓名列表。
    """
    staff_ids = sorted({e.staff_id for e in entries})
    id_to_idx = {sid: i for i, sid in enumerate(staff_ids)}
    names = [staff_map.get(sid, f"#{sid}") for sid in staff_ids]

    solution = {}
    for e in entries:
        solution[(id_to_idx[e.staff_id], e.day_of_week)] = AssignmentType(e.assignment_type)

    render_readonly_grid(solution, names, num_days, week_dates)
    return solution, names

def _build_traditional_rows(num_days=7):
    """传统格式的行定义：(标签, 匹配的AssignmentType列表, css class)。"""
    return [
        ("06:00-14:00", [AssignmentType.EARLY], "cell-early"),
        ("12:00-20:00", [AssignmentType.MID], "cell-mid"),
        ("18:00-02:00", [AssignmentType.LATE], "cell-late"),
        ("坐班 (不限时)", [AssignmentType.OFFICE], "cell-office"),
        ("休息 (全天)", [AssignmentType.REST], "cell-rest"),
    ]


def build_traditional_text(solution, staff_names, num_days=7, week_dates=None,
                           remarks=None):
    """构建传统格式纯文本（tab分隔，复制到在线表格用）。"""
    from config import DAY_NAMES

    if remarks is None:
        remarks = {}

    rows_def = _build_traditional_rows()

    lines = []
    header = "班次时段"
    for d in range(num_days):
        if week_dates and d < len(week_dates):
            wd = week_dates[d]
            header += f"\t{wd.month}月{wd.day}日({DAY_NAMES[d]})"
        else:
            header += f"\t{DAY_NAMES[d]}"
    lines.append(header)

    for row_label, row_types, _css in rows_def:
        row = row_label
        for d in range(num_days):
            matched = []
            for p in range(len(staff_names)):
                t = solution.get((p, d))
                if t in row_types:
                    name = staff_names[p]
                    r = remarks.get((p, d), "")
                    if r:
                        name += f"({r})"
                    matched.append(name)
            if matched:
                row += "\t" + "、".join(matched)
            else:
                row += "\t-"
        lines.append(row)

    return "\n".join(lines)


def render_traditional_grid(solution, staff_names, num_days=7, week_dates=None,
                             remarks=None):
    """传统排班格式 HTML 彩色表格：行=班次时段，列=日期。"""
    from config import DAY_NAMES

    if remarks is None:
        remarks = {}

    rows_def = _build_traditional_rows()

    html = ['<table class="schedule-table"><thead><tr><th>班次时段</th>']
    for d in range(num_days):
        date_html = ""
        if week_dates and d < len(week_dates):
            wd = week_dates[d]
            date_html = f'<div class="th-date">{wd.month}/{wd.day}</div>'
        html.append(f'<th><div class="th-day">{DAY_NAMES[d]}</div>{date_html}</th>')
    html.append('</tr></thead><tbody>')

    for row_label, row_types, css_cls in rows_def:
        html.append(f'<tr><td>{row_label}</td>')
        for d in range(num_days):
            matched = []
            for p in range(len(staff_names)):
                t = solution.get((p, d))
                if t in row_types:
                    name = staff_names[p]
                    r = remarks.get((p, d), "")
                    if r:
                        name += f"({r})"
                    matched.append(name)
            if matched:
                cell_text = "、".join(matched)
            else:
                cell_text = "-"
            html.append(f'<td class="{css_cls}">{cell_text}</td>')
        html.append('</tr>')
    html.append('</tbody></table>')

    st.markdown("".join(html), unsafe_allow_html=True)
