"""SQLAlchemy ORM 모델 정의 (종목마스터 / 종목종가내역)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SymbolMaster(Base):
    """종목마스터: 지수/국내·해외 종목/암호화폐 등 종목 정의."""

    __tablename__ = "symbol_master"
    __table_args__ = (
        UniqueConstraint("source", "symbol", name="uq_symbol_master_source_symbol"),
        {"comment": "종목마스터 (지수/국내·해외 종목/암호화폐 등 종목 정의)"},
    )

    symbol_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="종목 식별자 (시퀀스 자동 채번, PK)",
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="데이터 원천 (예: FDR, YAHOO)"
    )
    symbol: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="종목/지수/코인 코드 (예: KS200)"
    )
    symbol_nm: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="종목 명칭 (예: KOSPI 200)"
    )
    remark: Mapped[str | None] = mapped_column(
        String(255), comment="비고 (설명, 분류 등)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="등록 일시"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="수정 일시",
    )


class DailyPrice(Base):
    """종목종가내역: 일별 시세 시계열."""

    __tablename__ = "daily_price"
    __table_args__ = ({"comment": "종목종가내역 (일별 시세 시계열)"},)

    symbol_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("symbol_master.symbol_id"),
        primary_key=True,
        comment="종목 식별자 (FK → symbol_master.symbol_id)",
    )
    trade_dt: Mapped[str] = mapped_column(
        String(8), primary_key=True, comment="거래 일자 (YYYYMMDD)"
    )
    close_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="종가(지수)"
    )
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), comment="시가")
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), comment="고가")
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), comment="저가")
    volume: Mapped[int | None] = mapped_column(BigInteger, comment="거래량")
    trade_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), comment="거래금액"
    )
    change_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), comment="전일 대비 등락률"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="적재 일시"
    )
