"""数据库引擎和会话管理。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'scheduling.db')

# 确保 data 目录存在
os.makedirs(DB_DIR, exist_ok=True)

_engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
_SessionFactory = sessionmaker(bind=_engine)


def get_session() -> Session:
    """获取一个新的数据库会话。"""
    return _SessionFactory()


def init_db():
    """创建所有表。"""
    from database.models import Base
    Base.metadata.create_all(_engine)
