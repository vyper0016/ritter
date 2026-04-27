from __future__ import annotations
import enum
from datetime import date, datetime
from sqlalchemy import (
    Boolean, Date, Double, Enum, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP as PG_TIMESTAMP
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db import Base


class OcrStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class SplitType(str, enum.Enum):
    equal = "equal"
    percentage = "percentage"
    fraction = "fraction"


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    profile_picture_path: Mapped[str | None] = mapped_column(Text)
    profile_picture_filename: Mapped[str | None] = mapped_column(String(255))
    profile_picture_mimetype: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    receipts_created: Mapped[list[ReceiptORM]] = relationship(
        back_populates="created_by", foreign_keys="ReceiptORM.created_by_id"
    )
    receipts_paid: Mapped[list[ReceiptORM]] = relationship(
        back_populates="payer", foreign_keys="ReceiptORM.payer_id"
    )
    allocations: Mapped[list[ItemAllocationORM]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ReceiptORM(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    participant_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )
    ocr_status: Mapped[OcrStatus] = mapped_column(
        Enum(OcrStatus, name="ocr_status"), nullable=False, default=OcrStatus.pending
    )
    date: Mapped[date | None] = mapped_column(Date)
    total: Mapped[float | None] = mapped_column(Double)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    raw_ocr_data: Mapped[dict | None] = mapped_column(JSONB)
    settled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settled_at: Mapped[datetime | None] = mapped_column(PG_TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    image_path: Mapped[str | None] = mapped_column(Text)
    image_filename: Mapped[str | None] = mapped_column(String(255))
    image_mimetype: Mapped[str | None] = mapped_column(String(100))

    created_by: Mapped[UserORM] = relationship(
        back_populates="receipts_created", foreign_keys=[created_by_id]
    )
    payer: Mapped[UserORM] = relationship(
        back_populates="receipts_paid", foreign_keys=[payer_id]
    )
    line_items: Mapped[list[LineItemORM]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )

    @property
    def vendor_logo_url(self) -> str | None:
        if not self.raw_ocr_data:
            return None

        direct = self.raw_ocr_data.get("vendor_logo_url")
        if isinstance(direct, str) and direct:
            return direct

        vendor = self.raw_ocr_data.get("vendor")
        if isinstance(vendor, dict):
            logo = vendor.get("logo")
            if isinstance(logo, str) and logo:
                return logo

        return None


class LineItemORM(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[int] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Double)
    price: Mapped[float | None] = mapped_column(Double)
    total: Mapped[float] = mapped_column(Double, nullable=False)
    item_order: Mapped[int | None] = mapped_column("order", Integer)
    type: Mapped[str | None] = mapped_column(String(100))

    receipt: Mapped[ReceiptORM] = relationship(back_populates="line_items")
    allocations: Mapped[list[ItemAllocationORM]] = relationship(
        back_populates="line_item", cascade="all, delete-orphan"
    )


class ItemAllocationORM(Base):
    __tablename__ = "item_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    line_item_id: Mapped[int] = mapped_column(ForeignKey("line_items.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    split_type: Mapped[SplitType] = mapped_column(
        Enum(SplitType, name="split_type"), nullable=False
    )
    split_value: Mapped[float | None] = mapped_column(Double)
    amount: Mapped[float] = mapped_column(Double, nullable=False)

    line_item: Mapped[LineItemORM] = relationship(back_populates="allocations")
    user: Mapped[UserORM] = relationship(back_populates="allocations")
