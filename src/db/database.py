"""Neon DB(PostgreSQL) 연결 및 세션 관리 모듈."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

load_dotenv()


def get_database_url() -> str:
    """환경변수에서 DB 연결 문자열을 읽어 psycopg(v3) 드라이버로 정규화해 반환한다.

    Neon 콘솔이 제공하는 `postgresql://...` 형식을 그대로 넣어도
    psycopg2 대신 설치된 psycopg(v3)를 사용하도록 드라이버를 보정한다.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요."
        )

    parsed = make_url(url)
    if parsed.drivername in ("postgresql", "postgres"):
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


def create_db_engine(echo: bool = False) -> Engine:
    """SQLAlchemy Engine을 생성한다.

    Neon(서버리스)의 콜드 스타트/유휴 연결 종료에 대비해
    `pool_pre_ping`으로 끊어진 커넥션을 자동 감지·재연결한다.
    """
    return create_engine(
        get_database_url(),
        echo=echo,
        pool_pre_ping=True,
        pool_recycle=300,
        # 네트워크/호스트 문제 시 무한 대기 방지 (psycopg connect 타임아웃)
        connect_args={"connect_timeout": 15},
    )


# 모듈 전역에서 재사용하는 엔진/세션 팩토리
engine: Engine = create_db_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


def healthcheck() -> bool:
    """`SELECT 1`로 DB 접속 가능 여부를 확인한다."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("DB 접속 확인 완료")
        return True
    except Exception:
        logger.exception("DB 접속 실패")
        return False
