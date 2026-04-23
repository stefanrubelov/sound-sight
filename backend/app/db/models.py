from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    room: Mapped[str] = mapped_column(String(128), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    events: Mapped[list["Event"]] = relationship("Event", back_populates="device")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    raw_features: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="events")


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    time_start: Mapped[str | None] = mapped_column(String(8), nullable=True)  # "HH:MM"
    time_end: Mapped[str | None] = mapped_column(String(8), nullable=True)  # "HH:MM"
    priority: Mapped[str] = mapped_column(String(16), default="info")
    alert_type: Mapped[str] = mapped_column(String(32), default="led")
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    home_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled_classes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array
    quiet_hours: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stats_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON blob
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
