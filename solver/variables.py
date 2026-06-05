"""决策变量工厂。"""

from ortools.sat.python import cp_model
from config import AssignmentType


# 所有可能的班次类型（跟播 + 特殊）
_ALL_TYPES = [
    AssignmentType.REST,
    AssignmentType.EARLY,
    AssignmentType.MID,
    AssignmentType.LATE,
    AssignmentType.OFFICE,
    AssignmentType.EXTERNAL,
]

# 仅跟播班次
_SHIFT_TYPES = [AssignmentType.EARLY, AssignmentType.MID, AssignmentType.LATE]


def create_variables(model: cp_model.CpModel, num_people: int, num_days: int = 7):
    """创建决策变量。

    Args:
        model: CP-SAT 模型
        num_people: 本周在岗人数
        num_days: 天数（固定7天）

    Returns:
        x: dict, x[(p, d, t)] -> BoolVar
        shift_types: 跟播班次类型列表
    """
    x = {}
    for p in range(num_people):
        for d in range(num_days):
            for t in _ALL_TYPES:
                x[(p, d, t)] = model.NewBoolVar(f'x_p{p}_d{d}_t{t.value}')

    return x, _SHIFT_TYPES
