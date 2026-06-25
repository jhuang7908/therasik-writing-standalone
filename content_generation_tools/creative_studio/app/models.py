"""SQLAlchemy models."""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (Column, DateTime, Enum, ForeignKey, Integer, JSON,
                        String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def _now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    plan = Column(String(32), default="free")   # free|pro|enterprise
    credits = Column(Integer, default=200)
    created_at = Column(DateTime(timezone=True), default=_now)
    jobs = relationship("Job", back_populates="user", lazy="dynamic")


class JobStatus(str, PyEnum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    doc_type = Column(String(32), nullable=False)      # ppt|xhs|wechat|whitepaper
    template_id = Column(String(64))
    status = Column(Enum(JobStatus), default=JobStatus.queued)
    credit_estimate = Column(Integer, default=0)
    credit_actual = Column(Integer, default=0)
    request_summary = Column(Text)
    content_doc = Column(JSON)                         # ContentDoc payload
    result_url = Column(String(1024))                  # object storage URL
    qa_report = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    user = relationship("User", back_populates="jobs")


class UsageLedger(Base):
    __tablename__ = "usage_ledger"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    delta = Column(Integer, nullable=False)            # negative = spend
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=_now)


class CreditOrder(Base):
    __tablename__ = "credit_orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(String(32))                      # stripe|wechat
    external_id = Column(String(255))                  # Stripe PaymentIntent / wx out_trade_no
    amount_usd = Column(Integer)                       # in cents
    credits = Column(Integer)
    status = Column(String(32), default="pending")     # pending|paid|failed|refunded
    created_at = Column(DateTime(timezone=True), default=_now)
