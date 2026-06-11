"""求解引擎：编排建模 → 求解 → 提取结果。"""

from ortools.sat.python import cp_model
from config import AssignmentType, DAY_NAMES
from solver.variables import create_variables
from solver.hard_constraints import add_hard_constraints
from solver.soft_constraints import add_soft_constraints


def build_and_solve(num_people, params, num_days=7, timeout=30):
    """构建 CP-SAT 模型并求解。

    Args:
        num_people: 本周在岗人数
        params: 本周参数字典，包含:
            - rest_days: dict {p_index: int}  每人休息天数
            - office_quota: dict {p_index: int}  每人坐班天数
            - external_total: int  外派总天数
            - external_daily: dict {d: int}  每天外派人数（可选）
            - external_exclude: set of p_index  不可排外派的人
            - fixed_assignments: list of (p, d, t)  固定班次
            - no_office_days: set of d  禁止坐班的日期（默认{5,6}）
            - no_shift_days: set of d  禁止跟播的日期（如节假日）
            - max_consecutive_work: int  最大连续工作天数
            - prev_shift_counts: dict {p_index: {...}}  历史班次统计
            - priority_rest: list of p_index  优先休息的人
            - priority_rest_weight: int
        num_days: 排班天数（默认7，支持14天跨周）
        timeout: 求解超时秒数

    Returns:
        (status, solution, objective_value): solution 为 {(p, d): AssignmentType} 或 None
    """
    model = cp_model.CpModel()

    # 1. 创建决策变量
    x, shift_types = create_variables(model, num_people, num_days)

    # 2. 添加硬约束
    add_hard_constraints(model, x, num_people, num_days, shift_types, params)

    # 3. 添加软约束 + 目标函数
    obj_terms = add_soft_constraints(model, x, num_people, num_days, shift_types, params)

    if obj_terms:
        model.Minimize(sum(obj_terms))

    # 4. 求解
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = False

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        solution = _extract_solution(solver, x, num_people, num_days)
        status_str = 'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE'
        return status_str, solution, int(solver.ObjectiveValue())
    else:
        return 'INFEASIBLE', None, None


def _extract_solution(solver, x, num_people, num_days=7):
    """从求解器提取结果字典。"""
    all_types = [AssignmentType.REST, AssignmentType.EARLY, AssignmentType.MID,
                 AssignmentType.LATE, AssignmentType.OFFICE, AssignmentType.EXTERNAL]

    solution = {}
    for p in range(num_people):
        for d in range(num_days):
            for t in all_types:
                if solver.Value(x[(p, d, t)]) == 1:
                    solution[(p, d)] = t
                    break
    return solution


def validate_schedule(solution, num_people, num_days, shift_types, params):
    """验证排班结果是否满足所有硬约束。

    Returns:
        list of str: 违规描述列表，空列表表示通过
    """
    violations = []
    rest_days = params.get('rest_days', {})
    office_quota = params.get('office_quota', {})
    external_total = params.get('external_total', 0)
    external_exclude = params.get('external_exclude', set())
    fixed_assignments = params.get('fixed_assignments', [])
    max_consecutive = params.get('max_consecutive_work', 5)

    # H1: 每班次每天恰好1人
    for d in range(num_days):
        for t in shift_types:
            count = sum(1 for p in range(num_people) if solution.get((p, d)) == t)
            if count != 1:
                violations.append(f"周{['一二三四五六日'][d]} {t.name} 有{count}人（需1人）")

    # H2: 每人休息天数
    for p in range(num_people):
        actual_rest = sum(1 for d in range(num_days) if solution.get((p, d)) == AssignmentType.REST)
        expected_rest = rest_days.get(p, 2)
        if actual_rest != expected_rest:
            violations.append(f"人员{p} 休息{actual_rest}天（需{expected_rest}天）")

    # H3: 每人每天唯一安排 (自动满足由解的结构)

    # H4: 坐班配额
    for p in range(num_people):
        actual_office = sum(1 for d in range(num_days) if solution.get((p, d)) == AssignmentType.OFFICE)
        expected_office = office_quota.get(p, 0)
        if actual_office != expected_office:
            violations.append(f"人员{p} 坐班{actual_office}天（需{expected_office}天）")

    # H5: 防极限班次
    from config import LATE_SHIFT_TYPES, EARLY_SHIFT_TYPES
    for p in range(num_people):
        for d in range(num_days - 1):
            today = solution.get((p, d))
            tomorrow = solution.get((p, d + 1))
            if today in LATE_SHIFT_TYPES and tomorrow in EARLY_SHIFT_TYPES:
                violations.append(f"人员{p} 周{['一二三四五六日'][d]}晚班→次日早班（极限班次）")

    # H6: 周六日无坐班
    for p in range(num_people):
        if solution.get((p, 5)) == AssignmentType.OFFICE:
            violations.append(f"人员{p} 周六坐班（不允许）")
        if solution.get((p, 6)) == AssignmentType.OFFICE:
            violations.append(f"人员{p} 周日坐班（不允许）")

    # H7: 固定班次
    for (p, d, t) in fixed_assignments:
        if solution.get((p, d)) != t:
            violations.append(f"人员{p} 周{['一二三四五六日'][d]} 应为{t.name}，实际为{solution.get((p, d)).name}")

    # H8: 外派排除
    for p in external_exclude:
        for d in range(num_days):
            if solution.get((p, d)) == AssignmentType.EXTERNAL:
                violations.append(f"人员{p} 被排除外派但排了外派")

    # H9: 外派总天数
    actual_external = sum(1 for p in range(num_people) for d in range(num_days)
                          if solution.get((p, d)) == AssignmentType.EXTERNAL)
    if actual_external != external_total:
        violations.append(f"外派共{actual_external}天（需{external_total}天）")

    # H10: 连续工作≤N
    for p in range(num_people):
        is_working = [1 if solution.get((p, d)) != AssignmentType.REST else 0 for d in range(num_days)]
        consecutive = 0
        for w in is_working:
            if w == 1:
                consecutive += 1
                if consecutive > max_consecutive:
                    violations.append(f"人员{p} 连续工作{consecutive}天（上限{max_consecutive}天）")
            else:
                consecutive = 0

    return violations
