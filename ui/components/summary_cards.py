"""每人工时对账卡片组件。"""

import streamlit as st

from config import AssignmentType, ASSIGNMENT_LABELS
from ui.styles import get_badge_class

_DAY_CN = ["一", "二", "三", "四", "五", "六", "日"]
_SHIFT_ORDER = [AssignmentType.EARLY, AssignmentType.MID, AssignmentType.LATE,
                AssignmentType.OFFICE, AssignmentType.EXTERNAL]


def render_summary_cards(solution, staff_names, num_days=7, per_row=3):
    """渲染每人工时统计卡片。

    Args:
        per_row: 每行卡片数，默认 3，留白更宽松。
    """
    num_people = len(staff_names)
    if num_people == 0:
        return

    for start in range(0, num_people, per_row):
        cols = st.columns(per_row)
        for offset in range(per_row):
            p = start + offset
            if p >= num_people:
                # 占位空列，保持卡片宽度一致
                continue
            with cols[offset]:
                _render_one(solution, staff_names[p], p, num_days)


def _render_one(solution, name, p, num_days):
    work_days = sum(1 for d in range(num_days)
                    if solution.get((p, d)) != AssignmentType.REST)
    rest_list = [_DAY_CN[d] for d in range(num_days)
                 if solution.get((p, d)) == AssignmentType.REST]
    rest_str = "周" + "·".join(rest_list) if rest_list else "无"

    badges = []
    for t in _SHIFT_ORDER:
        count = sum(1 for d in range(num_days) if solution.get((p, d)) == t)
        if count > 0:
            label = ASSIGNMENT_LABELS[t]
            badges.append(
                f'<span class="staff-card-badge {get_badge_class(label)}">'
                f'{label} {count}</span>'
            )
    badges_html = "".join(badges) or '<span class="tip">本周无排班</span>'

    st.markdown(f"""
    <div class="staff-card">
        <div class="staff-card-name">{name}</div>
        <div class="staff-card-stats">
            <span class="staff-card-workdays">工作 {work_days} 天</span>
            &nbsp;·&nbsp;
            <span class="staff-card-rest">休 {rest_str}</span>
        </div>
        <div style="margin-top:4px;">{badges_html}</div>
    </div>
    """, unsafe_allow_html=True)
