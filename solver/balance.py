"""历史均衡计算：读取上周排班，计算本周班次均衡目标。"""

from database.crud import get_prev_schedule, get_staff_shift_stats
from config import AssignmentType


def compute_balance_targets(session, staff_list, week_start):
    """计算每个运营的跨周均衡数据。

    Args:
        session: DB 会话
        staff_list: list of (staff_id, name)
        week_start: 本周周一日期

    Returns:
        prev_shift_counts: dict {staff_index: {'early': N, 'mid': N, 'late': N}}
        rest_suggestions: list of staff_index 建议优先休息的人
    """
    prev_shift_counts = {}

    for idx, (staff_id, name) in enumerate(staff_list):
        stats = get_staff_shift_stats(session, staff_id, before_week_start=week_start)
        prev_shift_counts[idx] = {
            'early': stats['early'],
            'mid': stats['mid'],
            'late': stats['late'],
        }

    return prev_shift_counts
