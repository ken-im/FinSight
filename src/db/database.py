"""Neon DB(PostgreSQL) 연결 및 세션 관리 모듈."""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

load_dotenv()

# Neon 콜드 스타트 재시도 설정
_HEALTHCHECK_RETRIES = 3
_HEALTHCHECK_RETRY_DELAY = 5  # 초


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


def create_db_engine(echo: bool = False, url: str | None = None) -> Engine:
    """SQLAlchemy Engine을 생성한다.

    Neon(서버리스)의 콜드 스타트/유휴 연결 종료에 대비해
    `pool_pre_ping`으로 끊어진 커넥션을 자동 감지·재연결한다.

    `url`이 주어지면 해당 연결 문자열을 사용하고, 생략하면 환경변수에서 읽는다.
    (Streamlit Cloud 등 `st.secrets` 기반 URL 주입을 위해 인자를 받는다.)
    """
    return create_engine(
        url or get_database_url(),
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


def healthcheck(retries: int = _HEALTHCHECK_RETRIES, delay: int = _HEALTHCHECK_RETRY_DELAY) -> bool:
    """`SELECT 1`로 DB 접속 가능 여부를 확인한다.

    Neon 서버리스 특성상 콜드 스타트 시 첫 연결이 실패할 수 있으므로
    `retries`회까지 `delay`초 간격으로 재시도한다.
    """
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("DB 접속 확인 완료 (시도 %d/%d)", attempt, retries)
            return True
        except Exception:
            if attempt < retries:
                logger.warning(
                    "DB 접속 실패 (시도 %d/%d) — %d초 후 재시도...",
                    attempt, retries, delay,
                )
                time.sleep(delay)
            else:
                logger.exception("DB 접속 최종 실패 (시도 %d/%d)", attempt, retries)
    return False
