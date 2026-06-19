"""软约束 — 罚分最小化目标。"""

from ortools.sat.python import cp_model
from config import AssignmentType, SHIFT_TYPES, LATE_SHIFT_TYPES, EARLY_SHIFT_TYPES


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
            prev_early = prev.get('early', 0)
            prev_mid = prev.get('mid', 0)
            prev_late = prev.get('late', 0)
            prev_total = prev_early + prev_mid + prev_late

            if prev_total == 0:
                continue

            # 累计（含本周）目标：各类型尽可能接近平均
            this_early = sum(x[(p, d, AssignmentType.EARLY)] for d in range(num_days))
            this_mid = sum(x[(p, d, AssignmentType.MID)] for d in range(num_days))
            this_late = sum(x[(p, d, AssignmentType.LATE)] for d in range(num_days))
            this_total = this_early + this_mid + this_late

            # 如果本周有跟播班次，均衡累计分布
            total_early = prev_early + this_early
            total_mid = prev_mid + this_mid
            total_late = prev_late + this_late
            total_all = prev_total + this_total

            if total_all > 0:
                target = total_all / 3.0
                # 偏离目标的程度
                for total_x, name in [(total_early, 'early'), (total_mid, 'mid'), (total_late, 'late')]:
                    # 用两个变量表示正负偏差
                    over = model.NewIntVar(0, num_days * 10, f'over_{name}_p{p}')
                    under = model.NewIntVar(0, num_days * 10, f'under_{name}_p{p}')
                    target_int = model.NewIntVar(0, num_days * 10, f'target_{name}_p{p}')

                    # target_int = round(target) -- 简化：直接用 int(target)
                    # 由于 CP-SAT 只支持整数，用缩放
                    scaled_total = total_x * 10  # 乘10保留一位小数精度
                    scaled_target = int(target * 10)

                    model.Add(scaled_total - scaled_target == over - under)
                    objective_terms.append(over * 2)  # 权重 2/每0.1偏差
                    objective_terms.append(under * 2)

    # ---- S4: 周期内班次均衡（每人早/中/晚偏离最小化）----
    for p in range(num_people):
        this_early = sum(x[(p, d, AssignmentType.EARLY)] for d in range(num_days))
        this_mid = sum(x[(p, d, AssignmentType.MID)] for d in range(num_days))
        this_late = sum(x[(p, d, AssignmentType.LATE)] for d in range(num_days))
        # 惩罚 max(早,中,晚) - min(早,中,晚)，值越大越不均衡
        max_val = model.NewIntVar(0, num_days, f'bal_max_p{p}')
        min_val = model.NewIntVar(0, num_days, f'bal_min_p{p}')
        model.AddMaxEquality(max_val, [this_early, this_mid, this_late])
        model.AddMinEquality(min_val, [this_early, this_mid, this_late])
        spread = model.NewIntVar(0, num_days, f'bal_spread_p{p}')
        model.Add(spread == max_val - min_val)
        objective_terms.append(spread * 15)  # 惩罚不均衡

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
