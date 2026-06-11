"""硬约束 — CP-SAT 强制满足的约束。"""

from ortools.sat.python import cp_model
from config import AssignmentType


def add_hard_constraints(model, x, num_people, num_days, shift_types, params):
    """添加所有硬约束。

    Args:
        model: CpModel
        x: 决策变量字典 {(p, d, t): BoolVar}
        num_people: 在岗人数
        num_days: 天数 (7)
        shift_types: 跟播班次类型列表
        params: 本周参数字典，包含:
            - rest_days: dict {p: int} 每人休息天数
            - office_quota: dict {p: int} 每人坐班天数
            - external_total: int 外派总天数
            - external_exclude: set of p 不可排外派的人
            - fixed_assignments: list of (p, d, t) 固定班次
            - max_consecutive_work: int 最大连续工作天数
    """
    # ---- H1: 每班次每天恰好1人 ----
    for d in range(num_days):
        for t in shift_types:
            model.AddExactlyOne(x[(p, d, t)] for p in range(num_people))

    # ---- H2: 每人休息天数（总天数；跨周时可选分周参数）----
    rest_days = params.get('rest_days', {})
    weekly_rest = params.get('weekly_rest', None)  # 分周休息 {p: [w1_rest, w2_rest, ...]}
    if weekly_rest:
        num_weeks = num_days // 7
        for p in range(num_people):
            wr = weekly_rest.get(p, [2]*num_weeks)
            for w in range(min(num_weeks, len(wr))):
                start, end = w * 7, (w + 1) * 7
                model.Add(sum(x[(p, d, AssignmentType.REST)] for d in range(start, end)) == wr[w])
    else:
        for p in range(num_people):
            r = rest_days.get(p, 2)
            model.Add(sum(x[(p, d, AssignmentType.REST)] for d in range(num_days)) == r)

    # ---- H3: 每人每天恰好一个安排 ----
    all_types = [AssignmentType.REST, AssignmentType.EARLY, AssignmentType.MID,
                 AssignmentType.LATE, AssignmentType.OFFICE, AssignmentType.EXTERNAL]
    for p in range(num_people):
        for d in range(num_days):
            model.AddExactlyOne(x[(p, d, t)] for t in all_types)

    # ---- H4: 坐班配额 ----
    office_quota = params.get('office_quota', {})
    for p in range(num_people):
        q = office_quota.get(p, 0)
        model.Add(sum(x[(p, d, AssignmentType.OFFICE)] for d in range(num_days)) == q)

    # ---- H5: 防极限班次 (晚班→次日禁早班) ----
    # 3人模式：LATE(18-02) → 次日禁 EARLY(06-14)
    # 4人模式额外加上 LATE1(16-00) → 次日禁 EARLY2(08-16)
    # 这里始终禁止 LATE→EARLY（两个模式通用）
    for p in range(num_people):
        for d in range(num_days - 1):
            model.Add(x[(p, d, AssignmentType.LATE)] + x[(p, d + 1, AssignmentType.EARLY)] <= 1)
            # 如果使用了4人模式类型，也禁止
            # LATE1(7)→EARLY(1), LATE(3)→EARLY2(6), LATE1(7)→EARLY2(6)
            if any(t == AssignmentType.EARLY2 for t in shift_types):
                model.Add(x[(p, d, AssignmentType.LATE)] + x[(p, d + 1, AssignmentType.EARLY2)] <= 1)
                model.Add(x[(p, d, AssignmentType.LATE1)] + x[(p, d + 1, AssignmentType.EARLY)] <= 1)
                model.Add(x[(p, d, AssignmentType.LATE1)] + x[(p, d + 1, AssignmentType.EARLY2)] <= 1)

    # ---- H6: 禁坐班日（默认周六日 d=5,6；可传入 no_office_days 覆盖）----
    no_office_days = params.get('no_office_days', {5, 6})
    for p in range(num_people):
        for d in no_office_days:
            if 0 <= d < num_days:
                model.Add(x[(p, d, AssignmentType.OFFICE)] == 0)

    # ---- H7: 固定班次锁定 ----
    fixed_assignments = params.get('fixed_assignments', [])
    for (p, d, t) in fixed_assignments:
        model.Add(x[(p, d, t)] == 1)

    # ---- H8: 外派排除 ----
    external_exclude = params.get('external_exclude', set())
    for p in external_exclude:
        model.Add(sum(x[(p, d, AssignmentType.EXTERNAL)] for d in range(num_days)) == 0)

    # ---- H9a: 每人外派上限（默认无限制）----
    external_max_pp = params.get('external_max_per_person', None)
    if external_max_pp is not None:
        for p in range(num_people):
            model.Add(sum(x[(p, d, AssignmentType.EXTERNAL)] for d in range(num_days)) <= external_max_pp)

    # ---- H9: 外派总天数 + 每日配额（可选）----
    external_total = params.get('external_total', 0)
    external_daily = params.get('external_daily', None)
    if external_total > 0:
        model.Add(sum(x[(p, d, AssignmentType.EXTERNAL)]
                      for p in range(num_people)
                      for d in range(num_days)) == external_total)
        if external_daily:
            for d, cnt in external_daily.items():
                model.Add(sum(x[(p, d, AssignmentType.EXTERNAL)]
                             for p in range(num_people)) == cnt)
    else:
        # 无外派周：所有人外派=0
        for p in range(num_people):
            for d in range(num_days):
                model.Add(x[(p, d, AssignmentType.EXTERNAL)] == 0)

    # ---- H11a: 指定人指定日强制休息（如端午只留3人）----
    must_rest = params.get('must_rest_days', {})  # {p: set of days}
    for p, days in must_rest.items():
        for d in days:
            if 0 <= d < num_days:
                model.Add(x[(p, d, AssignmentType.REST)] == 1)

    # ---- H11: 禁跟播日（如节假日，自动全员休息）----
    no_shift_days = params.get('no_shift_days', set())
    for d in no_shift_days:
        if 0 <= d < num_days:
            for p in range(num_people):
                for t in shift_types:
                    model.Add(x[(p, d, t)] == 0)

    # ---- H12: 连续不同跟播班次抑制（中→早、晚→中最低休息不足12h）----
    no_consecutive_diff = params.get('no_consecutive_diff_shifts', True)
    if no_consecutive_diff:
        for p in range(num_people):
            for d in range(num_days - 1):
                # 中班(12-20) → 次日禁早班(6-14)：休息仅10h
                model.Add(x[(p, d, AssignmentType.MID)] + x[(p, d + 1, AssignmentType.EARLY)] <= 1)
                # 晚班(18-2) → 次日禁中班(12-20)：休息仅10h
                model.Add(x[(p, d, AssignmentType.LATE)] + x[(p, d + 1, AssignmentType.MID)] <= 1)

    # ---- H10: 连续工作 ≤ N 天 ----
    max_consecutive = params.get('max_consecutive_work', 5)
    for p in range(num_people):
        # is_working[p][d] = 1 - x[p][d][REST]
        is_working = []
        for d in range(num_days):
            w = model.NewBoolVar(f'working_p{p}_d{d}')
            model.Add(w == 1 - x[(p, d, AssignmentType.REST)])
            is_working.append(w)

        # 禁止 (max_consecutive+1) 个连续 True
        if max_consecutive < num_days:
            for start in range(num_days - max_consecutive):
                model.Add(sum(is_working[start + i]
                             for i in range(max_consecutive + 1)) <= max_consecutive)
