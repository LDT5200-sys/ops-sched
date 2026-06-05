"""测试脚本：用本周参数验证求解器。"""

import sys
sys.path.insert(0, '/Users/tiexue/Desktop/Ops-Sched-Proj')

from datetime import date
from database.engine import init_db, get_session
from database.crud import seed_staff, get_active_staff
from solver.engine import build_and_solve, validate_schedule
from solver.balance import compute_balance_targets
from config import AssignmentType, DAY_NAMES, ASSIGNMENT_LABELS, SHIFT_TYPES


def main():
    # 初始化数据库
    init_db()
    session = get_session()
    staff_list = seed_staff(session)

    print("=" * 60)
    print("人员列表:")
    for i, s in enumerate(staff_list):
        print(f"  [{i}] {s.name}")

    # 本周参数（6.8-6.14）
    # 人员映射:
    # 0: 张佳林, 1: 张宇霆, 2: 吴家伟, 3: 邓安祺, 4: 贾明芳, 5: 邢世坦
    num_people = 6

    # 坐班配额: 吴家伟2, 张佳林2, 邓安祺1, 邢世坦1, 贾明芳1, 张宇霆1
    office_quota = {
        0: 2,  # 张佳林
        1: 1,  # 张宇霆
        2: 2,  # 吴家伟
        3: 1,  # 邓安祺
        4: 1,  # 贾明芳
        5: 1,  # 邢世坦
    }

    # 每人休息2天（工作5天）
    rest_days = {p: 2 for p in range(num_people)}

    # 外派参数
    external_total = 1
    external_exclude = {1, 3}  # 张宇霆(idx 1), 邓安祺(idx 3) 不能排外派

    # 固定班次: 邢世坦(idx 5) 周二(d=1) 外派
    fixed_assignments = [
        (5, 1, AssignmentType.EXTERNAL),
    ]

    # 优先休息: 邓安祺(idx 3), 贾明芳(idx 4)
    priority_rest = [3, 4]

    # 历史均衡数据（暂无历史，使用空数据测试）
    prev_shift_counts = {}

    params = {
        'rest_days': rest_days,
        'office_quota': office_quota,
        'external_total': external_total,
        'external_exclude': external_exclude,
        'fixed_assignments': fixed_assignments,
        'max_consecutive_work': 5,
        'prev_shift_counts': prev_shift_counts,
        'priority_rest': priority_rest,
        'priority_rest_weight': 50,
    }

    print("\n" + "=" * 60)
    print("求解中...")
    status, solution, score = build_and_solve(num_people, params, timeout=30)

    print(f"状态: {status}")
    print(f"目标值: {score}")

    if solution is None:
        print("❌ 无解！请检查参数是否矛盾")
        return

    # 打印排班矩阵
    print("\n" + "=" * 60)
    print("排班矩阵 (6.8 - 6.14):")
    print()

    # 表头
    header = f"{'姓名':<8}"
    for d in range(7):
        header += f"{DAY_NAMES[d]:<10}"
    print(header)
    print("-" * (8 + 7 * 10))

    # 每行
    for p in range(num_people):
        row = f"{staff_list[p].name:<8}"
        for d in range(7):
            t = solution.get((p, d))
            label = ASSIGNMENT_LABELS.get(t, '?')
            row += f"{label:<10}"
        print(row)

    # 工时对账
    print("\n" + "=" * 60)
    print("工时对账:")
    for p in range(num_people):
        name = staff_list[p].name
        work_days = sum(1 for d in range(7) if solution[(p, d)] != AssignmentType.REST)
        rest_count = sum(1 for d in range(7) if solution[(p, d)] == AssignmentType.REST)
        office_count = sum(1 for d in range(7) if solution[(p, d)] == AssignmentType.OFFICE)

        shift_breakdown = []
        for t in SHIFT_TYPES:
            count = sum(1 for d in range(7) if solution[(p, d)] == t)
            if count > 0:
                shift_breakdown.append(f"{ASSIGNMENT_LABELS[t]}×{count}")

        print(f"  {name}: 工作{work_days}天(休息{rest_count}天), 坐班{office_count}天, "
              f"跟播: {' '.join(shift_breakdown)}")

    # 验证
    print("\n" + "=" * 60)
    print("约束验证:")
    violations = validate_schedule(solution, num_people, 7, SHIFT_TYPES, params)
    if violations:
        print(f"❌ 发现 {len(violations)} 个违规:")
        for v in violations:
            print(f"  - {v}")
    else:
        print("✅ 所有硬约束通过！")

    session.close()


if __name__ == '__main__':
    main()
