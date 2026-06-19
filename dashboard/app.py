"""FinSight Streamlit 엔트리포인트.

실행: `uv run streamlit run dashboard/app.py`
"""

# --- sys.path 부트스트랩 (다른 import보다 먼저) ---
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --------------------------------------------------

import streamlit as st

st.set_page_config(page_title="FinSight", page_icon="📈", layout="wide")

st.title("📈 FinSight")
st.caption("금융데이터 수집·저장·시각화 대시보드")

st.markdown(
    """
    수집된 금융데이터(지수·주가·암호화폐 등)를 조회·관리하는 웹앱입니다.

    **왼쪽 사이드바**에서 페이지를 선택하세요.

    - **admin symbols**: 종목마스터 관리(목록/필터/신규·수정·삭제)
    - **admin prices**: 종목 종가내역 조회(페이징)

    > 관리자 페이지는 비밀번호 보호가 적용되어 있습니다.
    > 대시보드(시각화) 화면은 추후 추가될 예정입니다.
    """
)
