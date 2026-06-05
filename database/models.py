"""SQLAlchemy ORM 模型。"""

from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Date, Boolean, ForeignKey, UniqueConstraint,
    DateTime, func,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Staff(Base):
    """运营人员。"""
    __tablename__ = 'staff'

    id = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)       # 是否仍在团队中
    is_temporary = Column(Boolean, default=False)    # 是否为临时支援人员
    created_at = Column(DateTime, default=func.now())

    entries = relationship('ScheduleEntry', back_populates='staff', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Staff {self.name}>"


class WeeklySchedule(Base):
    """每周排班记录。"""
    __tablename__ = 'weekly_schedule'

    id = Column(Integer, primary_key=True)
    week_start = Column(Date, nullable=False, unique=True)   # 周一日期
    shift_model = Column(Integer, default=3)                  # 3 或 4
    status = Column(String(16), default='generated')          # generated / edited / locked
    solver_score = Column(Integer, nullable=True)             # 求解器目标值
    config_json = Column(String(4096), nullable=True)         # 本周参数 JSON（用于复现）
    created_at = Column(DateTime, default=func.now())

    entries = relationship('ScheduleEntry', back_populates='schedule', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<WeeklySchedule {self.week_start}>"


class ScheduleEntry(Base):
    """单条排班记录：某人某天的安排。"""
    __tablename__ = 'schedule_entry'

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey('weekly_schedule.id'), nullable=False)
    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=False)
    day_of_week = Column(Integer, nullable=False)             # 0=Mon .. 6=Sun
    assignment_type = Column(Integer, nullable=False)          # AssignmentType 枚举值
    is_manual_override = Column(Boolean, default=False)
    remark = Column(String(64), nullable=True)                 # 备注，如"待支援"

    __table_args__ = (
        UniqueConstraint('schedule_id', 'staff_id', 'day_of_week',
                         name='uq_entry_staff_day'),
    )

    schedule = relationship('WeeklySchedule', back_populates='entries')
    staff = relationship('Staff', back_populates='entries')

    def __repr__(self):
        return f"<Entry {self.staff_id} d{self.day_of_week} t{self.assignment_type}>"
