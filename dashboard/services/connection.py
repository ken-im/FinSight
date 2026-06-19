"""DB 연결 해석 및 엔진 제공.

연결 문자열 우선순위: `st.secrets["DATABASE_URL"]` → 환경변수 `DATABASE_URL`.
백엔드 `src.db.database.create_db_engine`을 재사용하되, `src.db.database` 모듈이
import 시점에 환경변수를 읽으므로 그 전에 secrets 값을 환경변수로 브리지한다.
"""

from __future__ import annotations

import os

import streamlit as st


def _secret(key: str) -> str | None:
    try:
        value = st.secrets.get(key)
    except Exception:
        # secrets 파일이 없으면 st.secrets 접근이 예외를 던질 수 있음
        return None
    return str(value) if value else None


def _bridge_secrets_to_env() -> None:
    """st.secrets 값을 환경변수로 복사한다(이미 설정된 환경변수는 보존).

    Streamlit Cloud처럼 `.env`가 없고 secrets만 있는 환경에서,
    `src.db.database` 모듈 로드 시 환경변수에서 연결 문자열을 읽을 수 있게 한다.
    """
    for key in ("DATABASE_URL", "ADMIN_PASSWORD"):
        value = _secret(key)
        if value and not os.getenv(key):
            os.environ[key] = value


# src.db.database import 이전에 브리지 수행 (모듈 로드 시 엔진 생성)
_bridge_secrets_to_env()

from src.db.database import create_db_engine  # noqa: E402


@st.cache_resource(show_spinner="DB 연결 준비 중...")
def get_engine():
    """Neon 엔진을 1회 생성·캐시한다(드라이버 정규화는 create_db_engine 내부에서 처리)."""
    return create_db_engine()
