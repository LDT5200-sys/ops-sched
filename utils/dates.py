"""日期工具函数。"""

from datetime import date, datetime, timedelta


def get_week_start(d: date) -> date:
    """返回 d 所在周的周一日期。"""
    return d - timedelta(days=d.weekday())


def get_week_end(week_start: date) -> date:
    """返回周日的日期。"""
    return week_start + timedelta(days=6)


def get_week_dates(week_start: date) -> list[date]:
    """返回周一到周日的日期列表。"""
    return [week_start + timedelta(days=i) for i in range(7)]


def format_date(d: date) -> str:
    """格式化日期为 M月D日。"""
    return f"{d.month}月{d.day}日"


def parse_week_start(date_str: str) -> date:
    """解析 '2026-06-08' 格式的日期字符串。"""
    return datetime.strptime(date_str, "%Y-%m-%d").date()
