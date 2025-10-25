import os
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Date, ForeignKey, Boolean, Numeric, Text
from datetime import date

_engine = None
_async_session: Optional[async_sessionmaker[AsyncSession]] = None

class Base(DeclarativeBase):
    pass

class Pot(Base):
    __tablename__ = "pots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    cycle: Mapped[str] = mapped_column(String(10))  # 'tuan' or 'thang'
    start_date: Mapped[date] = mapped_column(Date)
    slots: Mapped[int] = mapped_column(Integer)
    face_value: Mapped[int] = mapped_column(Integer)  # e.g., 10000000
    floor_pct: Mapped[int] = mapped_column(Integer)   # sàn %
    cap_pct: Mapped[int] = mapped_column(Integer)     # trần %
    fee_pct: Mapped[int] = mapped_column(Integer)     # đầu thảo %
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

class Member(Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

class Bid(Base):
    __tablename__ = "bids"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pot_id: Mapped[int] = mapped_column(ForeignKey("pots.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer)  # số tiền thâm
    bid_date: Mapped[date] = mapped_column(Date)

class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pot_id: Mapped[int] = mapped_column(ForeignKey("pots.id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[str] = mapped_column(String(32), index=True)
    time_hhmm: Mapped[str] = mapped_column(String(5))  # '07:45'

async def init_engine():
    global _engine, _async_session
    if _engine:
        return
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is required")
    _engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    _async_session = async_sessionmaker(_engine, expire_on_commit=False)

async def get_session() -> AsyncSession:
    global _async_session
    if _async_session is None:
        await init_engine()
    return _async_session()

async def run_migrations():
    # very light migration: create tables if not exist
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
