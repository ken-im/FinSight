"""관리자 화면 간단 보호(단일 공유 비밀번호).

각 관리자 페이지 최상단에서 `require_admin()`을 호출한다.
비밀번호는 `st.secrets["ADMIN_PASSWORD"]`(또는 환경변수)로만 관리한다.
"""

from __future__ import annotations

import os

import streamlit as st

_SESSION_KEY = "admin_authed"


def _expected_password() -> str | None:
    try:
        pw = st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        pw = None
    return str(pw) if pw else os.getenv("ADMIN_PASSWORD")


def _render_logout() -> None:
    with st.sidebar:
        if st.button("로그아웃"):
            st.session_state.pop(_SESSION_KEY, None)
            st.rerun()


def require_admin() -> None:
    """미인증이면 비밀번호 입력 폼을 표시하고 이후 렌더링을 중단한다."""
    if st.session_state.get(_SESSION_KEY):
        _render_logout()
        return

    st.title("🔒 관리자 로그인")
    expected = _expected_password()
    if not expected:
        st.error("ADMIN_PASSWORD가 설정되지 않았습니다. Secrets 또는 환경변수를 확인하세요.")
        st.stop()

    pw = st.text_input("관리자 비밀번호", type="password")
    if st.button("로그인", type="primary"):
        if pw == expected:
            st.session_state[_SESSION_KEY] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()
