"""软约束 — 罚分最小化目标。"""

from ortools.sat.python import cp_model
from config import AssignmentType

_SHIFT_COUNT_KEYS = {
    AssignmentType.EARLY: "early",
    AssignmentType.MID: "mid",
    AssignmentType.EARLY2: "early2",
    AssignmentType.LATE1: "late1",
    AssignmentType.LATE: "late",
}


def add_soft_constraints(model, x, num_people, num_days, shift_types, params):
    """添加软约束，返回目标函数项列表。

    Args:
        params 中的软约束参数:
            - prev_shift_counts: dict {p: {'early': N, 'mid': N, 'late': N}}
            - priority_rest: list of p 需要优先休息的人
            - priority_rest_weight: int 优先休息权重 (默认50)

    Returns:
        objective_terms: list of (IntVar 或乘积) 待求和最小化
    """
    objective_terms = []

    # ---- S1: 不连续同班次 ----
    for p in range(num_people):
        for d in range(num_days - 1):
            for t in shift_types:
                penalty = model.NewBoolVar(f'penalty_same_p{p}_d{d}_t{t.value}')
                model.Add(penalty >= x[(p, d, t)] + x[(p, d + 1, t)] - 1)
                objective_terms.append(penalty * 10)

    # ---- S2: 跨周班次均衡 ----
    prev_counts = params.get('prev_shift_counts', {})
    if prev_counts:
        for p in range(num_people):
            prev = prev_counts.get(p, {})
            prev_total = sum(prev.get(key, 0) for key in _SHIFT_COUNT_KEYS.values())
            if prev_total == 0 and not shift_types:
                continue

            cumulative_counts = []
            for t in shift_types:
                key = _SHIFT_COUNT_KEYS.get(t)
                if key is None:
                    continue
                total_var = model.NewIntVar(0, prev_total + num_days,
                                            f'cum_{key}_p{p}')
                this_count = sum(x[(p, d, t)] for d in range(num_days))
                model.Add(total_var == prev.get(key, 0) + this_count)
                cumulative_counts.append(total_var)

            if cumulative_counts:
                max_val = model.NewIntVar(0, prev_total + num_days, f'cum_max_p{p}')
                min_val = model.NewIntVar(0, prev_total + num_days, f'cum_min_p{p}')
                model.AddMaxEquality(max_val, cumulative_counts)
                model.AddMinEquality(min_val, cumulative_counts)
                spread = model.NewIntVar(0, prev_total + num_days, f'cum_spread_p{p}')
                model.Add(spread == max_val - min_val)
                objective_terms.append(spread * 8)

    # ---- S4: 周期内班次均衡（每人各跟播班次偏离最小化）----
    for p in range(num_people):
        shift_counts = [
            sum(x[(p, d, t)] for d in range(num_days))
            for t in shift_types
        ]
        if not shift_counts:
            continue
        # 惩罚 max - min，值越大越不均衡
        max_val = model.NewIntVar(0, num_days, f'bal_max_p{p}')
        min_val = model.NewIntVar(0, num_days, f'bal_min_p{p}')
        model.AddMaxEquality(max_val, shift_counts)
        model.AddMinEquality(min_val, shift_counts)
        spread = model.NewIntVar(0, num_days, f'bal_spread_p{p}')
        model.Add(spread == max_val - min_val)
        objective_terms.append(spread * 15)  # 惩罚不均衡

    # ---- S5: 建议坐班尽量贴近，但不作为硬约束 ----
    office_quota = params.get('office_quota', {})
    for p in range(num_people):
        suggested = int(office_quota.get(p, 0))
        actual = sum(x[(p, d, AssignmentType.OFFICE)] for d in range(num_days))
        over = model.NewIntVar(0, num_days, f'office_over_p{p}')
        under = model.NewIntVar(0, num_days, f'office_under_p{p}')
        model.Add(actual - suggested == over - under)
        objective_terms.append(over * 6)
        objective_terms.append(under * 6)

    # ---- S3: 优先休息（指定人尽早休息） ----
    priority_rest = params.get('priority_rest', [])
    priority_rest_weight = params.get('priority_rest_weight', 50)

    for p in priority_rest:
        # 奖励周一或周二休息（给负罚分 = 奖励）
        # 如果周一(d=0)休息，减罚分
        objective_terms.append(x[(p, 0, AssignmentType.REST)] * (-priority_rest_weight))
        # 如果周二(d=1)休息，也减（但权重稍低）
        objective_terms.append(x[(p, 1, AssignmentType.REST)] * (-priority_rest_weight // 2))

    return objective_terms
