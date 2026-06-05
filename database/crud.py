"""数据库 CRUD 操作。"""

from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import Staff, WeeklySchedule, ScheduleEntry
from config import AssignmentType, DEFAULT_STAFF


# ---- Staff ----

def seed_staff(session: Session) -> list[Staff]:
    """初始化默认人员（如果表为空）。"""
    existing = session.query(Staff).all()
    if existing:
        return existing
    staff_list = [Staff(name=name) for name in DEFAULT_STAFF]
    session.add_all(staff_list)
    session.commit()
    return staff_list


def get_active_staff(session: Session) -> list[Staff]:
    """获取所有在职人员。"""
    return session.query(Staff).filter(Staff.is_active == True).all()


def get_all_staff(session: Session) -> list[Staff]:
    """获取所有人员（含已离职）。"""
    return session.query(Staff).all()


def add_staff(session: Session, name: str, is_temporary: bool = False) -> Staff:
    """添加新人员。"""
    s = Staff(name=name, is_temporary=is_temporary)
    session.add(s)
    session.commit()
    return s


def remove_staff(session: Session, staff_id: int):
    """软删除人员（标记为不活跃）。"""
    s = session.query(Staff).filter(Staff.id == staff_id).first()
    if s:
        s.is_active = False
        session.commit()


def update_staff(session: Session, staff_id: int, name: str = None,
                 is_active: bool = None, is_temporary: bool = None):
    """更新人员信息。"""
    s = session.query(Staff).filter(Staff.id == staff_id).first()
    if not s:
        return None
    if name is not None:
        s.name = name
    if is_active is not None:
        s.is_active = is_active
    if is_temporary is not None:
        s.is_temporary = is_temporary
    session.commit()
    return s


def restore_staff(session: Session, staff_id: int):
    """恢复已删除人员。"""
    s = session.query(Staff).filter(Staff.id == staff_id).first()
    if s:
        s.is_active = True
        session.commit()
        return s
    return None


def permanently_delete_staff(session: Session, staff_id: int) -> bool:
    """永久删除人员（仅当该人员没有任何排班记录时）。"""
    entry_count = session.query(ScheduleEntry).filter(
        ScheduleEntry.staff_id == staff_id
    ).count()
    if entry_count > 0:
        return False  # 有历史记录，不能删除
    s = session.query(Staff).filter(Staff.id == staff_id).first()
    if s:
        session.delete(s)
        session.commit()
        return True
    return False


# ---- WeeklySchedule ----

def get_schedule_by_week(session: Session, week_start: date) -> Optional[WeeklySchedule]:
    """查询某周的排班。"""
    return session.query(WeeklySchedule).filter(
        WeeklySchedule.week_start == week_start
    ).first()


def get_prev_schedule(session: Session, week_start: date) -> Optional[WeeklySchedule]:
    """获取上周排班。"""
    prev_start = week_start - timedelta(days=7)
    return get_schedule_by_week(session, prev_start)


def save_schedule(session: Session, week_start: date, entries_data: list[dict],
                  shift_model: int = 3, config_json: str = None,
                  solver_score: int = None) -> WeeklySchedule:
    """保存一周排班（先删旧数据再写入）。"""
    # 删除旧记录
    old = get_schedule_by_week(session, week_start)
    if old:
        session.query(ScheduleEntry).filter(
            ScheduleEntry.schedule_id == old.id
        ).delete()
        session.delete(old)
        session.flush()

    # 创建新记录
    sched = WeeklySchedule(
        week_start=week_start,
        shift_model=shift_model,
        config_json=config_json,
        solver_score=solver_score,
    )
    session.add(sched)
    session.flush()  # 获取 sched.id

    for e in entries_data:
        entry = ScheduleEntry(
            schedule_id=sched.id,
            staff_id=e['staff_id'],
            day_of_week=e['day_of_week'],
            assignment_type=e['assignment_type'],
            remark=e.get('remark'),
        )
        session.add(entry)

    session.commit()
    return sched


def get_all_schedules(session: Session) -> list[WeeklySchedule]:
    """获取所有历史排班（按日期倒序）。"""
    return session.query(WeeklySchedule).order_by(
        WeeklySchedule.week_start.desc()
    ).all()


# ---- Statistics ----

def get_staff_shift_stats(session: Session, staff_id: int,
                          before_week_start: date = None) -> dict:
    """统计某人在指定日期之前的所有班次次数。

    Returns: {'early': N, 'mid': N, 'late': N, 'office': N, 'external': N, 'total_shifts': N}
    """
    query = session.query(ScheduleEntry).filter(
        ScheduleEntry.staff_id == staff_id
    )
    if before_week_start:
        query = query.join(WeeklySchedule).filter(
            WeeklySchedule.week_start < before_week_start
        )

    entries = query.all()
    stats = {'early': 0, 'mid': 0, 'late': 0, 'office': 0, 'external': 0, 'total_shifts': 0}

    for e in entries:
        t = AssignmentType(e.assignment_type)
        if t == AssignmentType.EARLY:
            stats['early'] += 1
        elif t == AssignmentType.MID:
            stats['mid'] += 1
        elif t == AssignmentType.LATE:
            stats['late'] += 1
        elif t == AssignmentType.OFFICE:
            stats['office'] += 1
        elif t == AssignmentType.EXTERNAL:
            stats['external'] += 1

        if t != AssignmentType.REST:
            stats['total_shifts'] += 1

    return stats


def get_external_history(session: Session) -> list[dict]:
    """获取外派历史记录，用于轮流判断。

    Returns: [{staff_id, name, week_start, day_of_week}, ...]
    """
    results = session.query(ScheduleEntry, Staff.name, WeeklySchedule.week_start).join(
        Staff
    ).join(
        WeeklySchedule
    ).filter(
        ScheduleEntry.assignment_type == AssignmentType.EXTERNAL.value
    ).order_by(
        WeeklySchedule.week_start.desc()
    ).all()

    return [
        {'staff_id': e.staff_id, 'name': name, 'week_start': ws, 'day_of_week': e.day_of_week}
        for e, name, ws in results
    ]
