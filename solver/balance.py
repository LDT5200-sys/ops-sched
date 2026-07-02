"""历史均衡计算：读取历史排班，计算本周班次均衡目标。"""

from datetime import timedelta

from database.crud import get_staff_shift_stats
from config import AssignmentType


_SHIFT_COUNT_KEYS = {
    AssignmentType.EARLY: "early",
    AssignmentType.MID: "mid",
    AssignmentType.EARLY2: "early2",
    AssignmentType.LATE1: "late1",
    AssignmentType.LATE: "late",
}


def _blank_shift_counts():
    return {key: 0 for key in _SHIFT_COUNT_KEYS.values()}


def _count_solution_shifts(solution, staff_ids):
    counts_by_staff_id = {staff_id: _blank_shift_counts() for staff_id in staff_ids}
    for (p_idx, _day_idx), assignment_type in solution.items():
        if p_idx >= len(staff_ids):
            continue
        key = _SHIFT_COUNT_KEYS.get(AssignmentType(assignment_type))
        if key:
            counts_by_staff_id[staff_ids[p_idx]][key] += 1
    return counts_by_staff_id


def compute_balance_targets(session, staff_list, week_start,
                            override_prev_solution=None,
                            override_prev_staff_ids=None):
    """计算每个运营的跨周均衡数据。

    Args:
        session: DB 会话
        staff_list: list of (staff_id, name)
        week_start: 本周周一日期
        override_prev_solution: 可选，上周实际排班修正版 {(p, d): AssignmentType}
        override_prev_staff_ids: 可选，与 override_prev_solution 的 p 索引对应

    Returns:
        prev_shift_counts: dict {staff_index: {'early': N, 'mid': N, 'early2': N,
                                               'late1': N, 'late': N}}
    """
    prev_shift_counts = {}
    has_override = override_prev_solution is not None and override_prev_staff_ids is not None
    override_counts = {}
    stats_cutoff = week_start

    if has_override:
        stats_cutoff = week_start - timedelta(days=7)
        override_counts = _count_solution_shifts(
            override_prev_solution, list(override_prev_staff_ids)
        )

    for idx, (staff_id, name) in enumerate(staff_list):
        stats = get_staff_shift_stats(session, staff_id, before_week_start=stats_cutoff)
        counts = {
            key: stats.get(key, 0)
            for key in _SHIFT_COUNT_KEYS.values()
        }
        if has_override:
            for key, value in override_counts.get(staff_id, {}).items():
                counts[key] += value
        prev_shift_counts[idx] = counts

    return prev_shift_counts
