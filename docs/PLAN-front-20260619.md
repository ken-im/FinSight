# FinSight 프런트엔드(Streamlit) 실행 계획 (PLAN-front-20260619)

> 본 문서는 [PRD-front-20260619](./PRD-front-20260619.md)를 구현하기 위한 계획이다.
> 백엔드([PRD-20260323](./PRD-20260323.md), [PLAN-backend-20260617](./PLAN-backend-20260617.md))에서 구축한
> Neon DB·ORM(`symbol_master`, `daily_price`)을 그대로 재사용하여 **Streamlit 대시보드/관리자 화면**을 구현한다.

## 1. 목표
- 수집된 금융데이터를 조회·분석·시각화하는 **Streamlit 웹앱**을 구현한다.
- **관리자 화면**: 종목마스터(CRUD) 및 종목종가내역(페이징 조회) 관리 기능 제공.
- **Streamlit Community Cloud** 무료 배포(Neon 연결은 Secrets로 주입).
- 대시보드(시각화) 화면은 후속(PRD 8장 "추후 확정")으로 분리.

## 2. 범위

### 2.1. 포함 (In Scope)
| 영역 | 기능 |
| --- | --- |
| 관리자 — 종목마스터 | 목록 조회/필터, 선택 바인딩, 신규/수정/삭제(중복 검증·삭제 확인) |
| 관리자 — 종가내역 | 선택 종목(symbol_id)의 종가내역 일자 DESC, 30행/페이지 페이징 |
| 관리자 — 인증 | 공유 비밀번호 기반 간단 보호(관리자 페이지 접근 차단) |
| 공통 | Neon DB 연결(캐싱), 데이터 접근 계층, 기본 레이아웃/네비게이션, 배포 |

### 2.2. 제외 (Out of Scope, 후속)
- 대시보드(인터랙티브 차트) 화면 — PRD 8장에서 확정 후 별도 계획.
  - 참고 디자인: `reference/market_indicators/Market_Indicators_Dashboard.png`
- 다중 사용자/역할 기반 권한, 계정 관리 — 1차는 단일 공유 비밀번호로 충분(6.0 참조).
- 데이터 수집/적재 로직 변경(백엔드 완료분 그대로 사용).

## 3. 아키텍처 / 기술
- **Streamlit + Plotly**(시각화는 후속), Python 3.12, 기존 SQLAlchemy ORM 재사용.
- DB 접근은 백엔드 모듈 재사용: `src/db/models.py`(ORM), `src/db/database.py`(엔진/세션).
- 연결 문자열은 환경에 따라 다음 우선순위로 해석:
  1. **로컬**: `.env`의 `DATABASE_URL` (기존 방식)
  2. **Streamlit Cloud**: `st.secrets["DATABASE_URL"]`
- Streamlit 실행 모델 특성상 **엔진은 `st.cache_resource`로 1회 생성·재사용**, 조회 결과는 필요 시 `st.cache_data`(TTL)로 캐싱.

```
Streamlit (Community Cloud) ──(SQLAlchemy)──▶ Neon DB (PostgreSQL)
  - 관리자: symbol_master CRUD / daily_price 페이징 조회
  - 대시보드(후속): Plotly 차트
```

## 4. 디렉토리 구조 (frontend 추가분)
```
FinSight/
├── src/                         # (기존) 백엔드 — 수집·적재·모델
│   └── db/{database.py, models.py}   # 프런트에서 재사용
├── dashboard/                   # [신규] Streamlit 앱
│   ├── app.py                   # 엔트리포인트(홈/네비게이션, 대시보드 placeholder)
│   ├── pages/
│   │   ├── 1_admin_symbols.py   # 7.1 종목마스터 관리
│   │   └── 2_admin_prices.py    # 7.2 종가내역 조회(페이징)
│   ├── services/
│   │   ├── connection.py        # DATABASE_URL 해석 + 엔진(st.cache_resource)
│   │   ├── auth.py              # 관리자 비밀번호 보호(require_admin)
│   │   ├── symbol_service.py    # symbol_master CRUD + 중복 검증
│   │   └── price_service.py     # daily_price 페이징 조회/카운트
│   └── components/              # (선택) 공통 UI 헬퍼
├── .streamlit/
│   ├── config.toml              # 테마/서버 설정(선택)
│   └── secrets.toml             # 로컬 secrets (gitignore 대상)
└── requirements.txt             # streamlit, plotly 포함하여 재생성
```
- `.gitignore`에 `.streamlit/secrets.toml` 추가 필요.
- Streamlit 멀티페이지 규칙상 `dashboard/app.py`가 엔트리, `dashboard/pages/*.py`가 자동 페이지로 노출된다.

## 5. 데이터 접근 계층 (services)

### 5.1. connection.py
- `get_database_url()`: `st.secrets` → 환경변수(`DATABASE_URL`) 순으로 조회(없으면 명확한 에러).
- `get_engine()`: `@st.cache_resource`로 엔진 1회 생성(기존 `create_db_engine` 재사용, `pool_pre_ping`).
- 세션은 요청 단위로 `with Session(engine)` 사용.

### 5.2. symbol_service.py (symbol_master)
| 함수 | 설명 |
| --- | --- |
| `list_symbols(filters)` | 목록 조회. `symbol_id/source/symbol/symbol_nm` 부분일치 필터(좌변 미가공으로 인덱스 고려) |
| `get_symbol(symbol_id)` | 단건 조회(폼 바인딩용) |
| `create_symbol(...)` | 신규 등록. `(source, symbol)` 중복 시 저장 불가(사전 체크 + `IntegrityError` 방어) |
| `update_symbol(symbol_id, ...)` | 수정. 자기 자신 제외 `(source, symbol)` 중복 시 저장 불가 |
| `delete_symbol(symbol_id)` | 삭제. (주의: `daily_price` FK 참조 → 5.4 참조) |

### 5.3. price_service.py (daily_price)
| 함수 | 설명 |
| --- | --- |
| `count_prices(symbol_id)` | 총 건수(페이지 수 계산) |
| `list_prices(symbol_id, page, page_size=30)` | `trade_dt DESC`, `LIMIT 30 OFFSET (page-1)*30` |

### 5.4. 삭제와 FK 정합성 (설계 결정 필요)
`daily_price.symbol_id`가 `symbol_master`를 FK 참조하므로, 종가내역이 있는 종목을 삭제하면 FK 위반이 발생한다. 처리 방안(택1, 권장안 먼저):
- **(권장) 가드**: 종가내역이 존재하면 삭제를 막고 "종가내역 N건 존재로 삭제 불가" 안내.
- (대안) 종가내역까지 함께 삭제(cascade) — 사용자에게 영향 범위를 명확히 고지 후 진행.

> 본 계획은 권장안(가드)으로 진행하되, 사용자 확정에 따라 조정한다.

## 6. 화면 설계

### 6.0. 관리자 인증 (간단 보호)
가장 단순한 방식: **단일 공유 비밀번호**를 Secrets에 두고, 관리자 페이지 진입 시 비밀번호를 확인한다.
- Secret: `ADMIN_PASSWORD` (Streamlit Cloud Secrets / 로컬 `.streamlit/secrets.toml`).
- `dashboard/services/auth.py`의 `require_admin()`을 각 관리자 페이지 **최상단**에서 호출.
  - 미인증 상태면 비밀번호 입력 폼을 표시하고 `st.stop()`으로 이후 렌더링 차단.
  - 입력값이 `ADMIN_PASSWORD`와 일치하면 `st.session_state["admin_authed"] = True`로 저장(세션 유지).
  - 사이드바에 "로그아웃" 버튼(세션 플래그 해제) 제공.
- 구현 스케치:
```python
import streamlit as st

def require_admin() -> None:
    if st.session_state.get("admin_authed"):
        return
    pw = st.text_input("관리자 비밀번호", type="password")
    if st.button("로그인"):
        if pw and pw == st.secrets.get("ADMIN_PASSWORD"):
            st.session_state["admin_authed"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()
```
> 비밀번호는 코드/로그에 남기지 않고 Secrets로만 관리한다. 대시보드(조회 전용) 페이지는 무인증 공개, 관리자 페이지만 보호한다.

### 6.1. 종목마스터 관리 (7.1)
- **상단 목록**: `st.dataframe`(행 선택 활성화) 또는 `st.data_editor`(읽기 표시). 컬럼: symbol_id/source/symbol/symbol_nm/remark.
- **필터**: symbol_id/source/symbol/symbol_nm 입력 → 부분일치 검색.
- **선택 바인딩**: 목록에서 행 선택 시 `st.session_state["selected_symbol_id"]`에 저장하고, 하단 입력 폼에 값 채움.
- **입력 폼**(하단): source, symbol, symbol_nm, remark 편집 필드.
- **버튼**:
  - `[신규]`: 폼 내용으로 신규 등록(symbol_id 자동 채번). `(source, symbol)` 중복 시 에러 토스트.
  - `[수정]`: 선택 symbol_id를 폼 내용으로 갱신. 중복 시 에러.
  - `[삭제]`: **확인 다이얼로그**(`st.dialog` 또는 2단계 확인) 후 삭제. 5.4 가드 적용.
- 저장/삭제 성공 시 목록 새로고침 및 안내 메시지.

### 6.2. 종목종가내역 관리 (7.2)
- 종목마스터에서 선택한 `selected_symbol_id` 기준 종가내역 조회.
- 정렬: `trade_dt DESC`, **30행/페이지** 페이징(이전/다음, 현재 페이지/총 페이지 표시).
- 컬럼: trade_dt, close/open/high/low, volume, trade_amount, change_rate.
- 선택 종목이 없으면 안내(먼저 종목 선택 요청).

## 7. 비기능 요구
- **연결 캐싱**: 엔진 `st.cache_resource`, 무거운 조회는 `st.cache_data(ttl=...)`로 캐싱(쓰기 후 캐시 무효화).
- **에러 처리**: DB 예외는 사용자 친화 메시지 + `logging`(traceback 포함, `.cursorrules`).
- **입력 검증**: 필수값(source/symbol/symbol_nm) 체크, 공백 트림.
- **쿼리**: 인덱스를 타도록 좌변 미가공 조건 우선(`.cursorrules`).

## 8. 단계별 실행 계획
### 단계 0. 의존성/스캐폴딩
- [ ] `uv add streamlit plotly` (plotly 명시적 추가) 및 `requirements.txt` 재생성
- [ ] `dashboard/` 스캐폴딩 및 `.streamlit/secrets.toml` 로컬 작성, `.gitignore`에 추가

### 단계 1. 데이터 접근 계층
- [ ] `connection.py`: secrets/env 기반 DATABASE_URL 해석 + 캐시 엔진
- [ ] `symbol_service.py`: 목록/필터/단건/CRUD + 중복 검증
- [ ] `price_service.py`: 카운트/페이징 조회

### 단계 2. 관리자 — 종목마스터 (7.1)
- [ ] `auth.py` 작성 및 관리자 페이지 상단 `require_admin()` 적용(공유 비밀번호 게이트)
- [ ] 목록 + 필터 + 행 선택 → 폼 바인딩
- [ ] 신규/수정(중복 검증)/삭제(확인·FK 가드) 동작

### 단계 3. 관리자 — 종가내역 (7.2)
- [ ] 선택 symbol_id 종가 30행/페이지 페이징(일자 DESC)

### 단계 4. 엔트리/네비게이션
- [ ] `app.py` 홈 + 페이지 구성, 대시보드 placeholder

### 단계 5. 배포
- [ ] Streamlit Community Cloud 앱 생성(엔트리: `dashboard/app.py`)
- [ ] Cloud Secrets에 `DATABASE_URL` 등록, 동작 확인

## 9. 배포 (Streamlit Community Cloud)
- 엔트리포인트: `dashboard/app.py`, Python 3.12, 의존성: `requirements.txt`.
- **Secrets**: 앱 설정 → Secrets에 아래 형식 입력
  ```toml
  DATABASE_URL = "postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"
  ADMIN_PASSWORD = "관리자_비밀번호"
  ```
- 로컬 실행: `uv run streamlit run dashboard/app.py` (로컬은 `.env` 또는 `.streamlit/secrets.toml`).

## 10. 완료 기준 (Definition of Done)
- 종목마스터 목록/필터/선택 바인딩이 동작한다.
- 신규/수정 시 `(source, symbol)` 중복은 저장이 차단된다.
- 삭제는 확인 절차를 거치며, FK 정합성(5.4 정책)이 보장된다.
- 선택 종목의 종가내역이 일자 DESC·30행 페이징으로 조회된다.
- 관리자 페이지는 공유 비밀번호 인증 없이는 접근/조작이 불가하다.
- Streamlit Community Cloud에서 Neon 연결로 정상 동작한다.

## 11. 리스크 및 고려사항
| 항목 | 내용 | 대응 |
| --- | --- | --- |
| 삭제 FK 위반 | 종가내역 보유 종목 삭제 시 오류 | 가드(권장) 또는 cascade 정책 확정(5.4) |
| Streamlit 재실행 모델 | 스크립트 전체 재실행으로 상태 유실 | `st.session_state`로 선택/페이지 유지, 엔진 캐시 |
| Neon 콜드 스타트 | 유휴 후 첫 쿼리 지연 | `pool_pre_ping`, 사용자 안내(스피너) |
| Secrets 관리 | 연결 문자열·비밀번호 노출 | `.streamlit/secrets.toml` gitignore, Cloud Secrets 사용 |
| 인증 수준 | 단일 공유 비밀번호(간단) | 개인 프로젝트엔 충분, 다중 사용자 필요 시 OIDC/계정제로 후속 확장 |
| 대용량 종가 조회 | 전체 로드 시 부하 | 페이징(30행) + 카운트 분리 쿼리 |
| import 경로 | Cloud에서 `src` 모듈 인식 | 리포 루트 기준 import, 필요 시 경로 설정 |

## 12. 대시보드 (후속, PRD 8장)
- 시각화 화면은 PRD 확정 후 별도 계획으로 진행.
- 참고 이미지(`reference/market_indicators/Market_Indicators_Dashboard.png`)를 기준으로 지표 카드·시계열 차트(Plotly) 구성 예정.
