from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)

from collections.abc import Generator
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    tenant_id: Mapped[str] = mapped_column(String(100), index=True)
    lead_id: Mapped[str] = mapped_column(String(100), index=True)

    customer_name: Mapped[str] = mapped_column(String(200))
    customer_phone: Mapped[str] = mapped_column(String(50))

    source: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime)
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    conversation_json: Mapped[str] = mapped_column(Text)


class LeadAnalysis(Base):
    __tablename__ = "lead_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    tenant_id: Mapped[str] = mapped_column(String(100), index=True)
    lead_id: Mapped[str] = mapped_column(String(100), index=True)

    lead_score: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String(50))
    intent: Mapped[str] = mapped_column(String(100))
    stage: Mapped[str] = mapped_column(String(100))

    summary: Mapped[str] = mapped_column(Text)
    next_best_action: Mapped[str] = mapped_column(Text)

    follow_up_channel: Mapped[str] = mapped_column(String(50))
    follow_up_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    tenant_id: Mapped[str] = mapped_column(String(100), index=True)
    event_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)

    lead_id: Mapped[str] = mapped_column(String(100), index=True)

    status: Mapped[str] = mapped_column(String(50), default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


connect_args = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
