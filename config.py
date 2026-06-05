"""
固定配置：班次定义、默认人员名单等。
每周可变参数在 UI 中配置，不写在这里。
"""

from enum import IntEnum


class AssignmentType(IntEnum):
    """班次类型枚举 — 固定不变"""
    REST = 0       # 休息
    EARLY = 1      # 早班 06:00-14:00
    MID = 2        # 中班 12:00-20:00
    LATE = 3       # 晚班 18:00-02:00
    OFFICE = 4     # 坐班（不限时）
    EXTERNAL = 5   # 外派支援
    # 4人模式扩展（备用）
    EARLY2 = 6     # 08:00-16:00
    LATE1 = 7      # 16:00-00:00


# 3人模式班次定义
SHIFT_DEFS_3 = [
    {"name": "早班", "type": AssignmentType.EARLY, "start": "06:00", "end": "14:00",
     "is_early": True, "is_late": False},
    {"name": "中班", "type": AssignmentType.MID, "start": "12:00", "end": "20:00",
     "is_early": False, "is_late": False},
    {"name": "晚班", "type": AssignmentType.LATE, "start": "18:00", "end": "02:00",
     "is_early": False, "is_late": True},
]

# 4人模式班次定义（备用，禁止12-20班次）
SHIFT_DEFS_4 = [
    {"name": "早班", "type": AssignmentType.EARLY, "start": "06:00", "end": "14:00",
     "is_early": True, "is_late": False},
    {"name": "白班", "type": AssignmentType.EARLY2, "start": "08:00", "end": "16:00",
     "is_early": True, "is_late": False},
    {"name": "午班", "type": AssignmentType.LATE1, "start": "16:00", "end": "00:00",
     "is_early": False, "is_late": True},
    {"name": "晚班", "type": AssignmentType.LATE, "start": "18:00", "end": "02:00",
     "is_early": False, "is_late": True},
]

# 默认人员名单
DEFAULT_STAFF = ["张佳林", "张宇霆", "吴家伟", "邓安祺", "贾明芳", "邢世坦"]

# 班次类型中文名
ASSIGNMENT_LABELS = {
    AssignmentType.REST: "休息",
    AssignmentType.EARLY: "早班",
    AssignmentType.MID: "中班",
    AssignmentType.LATE: "晚班",
    AssignmentType.OFFICE: "坐班",
    AssignmentType.EXTERNAL: "外派",
    AssignmentType.EARLY2: "白班",
    AssignmentType.LATE1: "午班",
}

# 班次颜色（用于表格展示）
ASSIGNMENT_COLORS = {
    AssignmentType.REST: "#F5F5F5",     # 浅灰
    AssignmentType.EARLY: "#FFF9C4",    # 浅黄
    AssignmentType.MID: "#BBDEFB",      # 浅蓝
    AssignmentType.LATE: "#E1BEE7",     # 浅紫
    AssignmentType.OFFICE: "#C8E6C9",   # 浅绿
    AssignmentType.EXTERNAL: "#FFE0B2", # 浅橙
    AssignmentType.EARLY2: "#FFECB3",   # 暖黄
    AssignmentType.LATE1: "#D1C4E9",    # 深紫
}

# 周几中文名
DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 上班类型（跟播班次，非休息/坐班/外派）
SHIFT_TYPES = {AssignmentType.EARLY, AssignmentType.MID, AssignmentType.LATE}
# 4人模式上班类型
SHIFT_TYPES_4 = {AssignmentType.EARLY, AssignmentType.EARLY2, AssignmentType.LATE1, AssignmentType.LATE}

# 晚班类型（用于防极限班次）
LATE_SHIFT_TYPES = {AssignmentType.LATE, AssignmentType.LATE1}
# 早班类型（用于防极限班次）
EARLY_SHIFT_TYPES = {AssignmentType.EARLY, AssignmentType.EARLY2}
