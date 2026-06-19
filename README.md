# FinSight

시장의 금융데이터(지수, 주가 등)를 수집·저장·시각화하는 개인 프로젝트.

- 아키텍처/기술 스택: [docs/PRD-20260323.md](docs/PRD-20260323.md)
- 파일럿(KS200 수집·적재) 계획: [docs/PLAN-pilot-20260617.md](docs/PLAN-pilot-20260617.md)
- 백엔드 수집 배치 계획: [docs/PLAN-backend-20260617.md](docs/PLAN-backend-20260617.md)
- 정기 수집 자동화 계획: [docs/PLAN-cron-20260618.md](docs/PLAN-cron-20260618.md)
- 프런트엔드(관리자/대시보드) 계획: [docs/PLAN-front-20260619.md](docs/PLAN-front-20260619.md)

## 기능 범위

- **수집·적재(백엔드)**: PRD 2.1 전체 종목을 FinanceDataReader/yfinance로 수집해 Neon DB(PostgreSQL)에 일괄 적재. 수집 원천은 종목마스터의 `source` 컬럼으로 분기(`FDR`, `YAHOO`), GitHub Actions cron으로 매일 자동 실행.
- **관리자 화면(프런트엔드, 1차 완료)**: Streamlit 기반. 종목마스터 CRUD(중복 검증·삭제 가드)와 종목 종가내역 페이징 조회. 공유 비밀번호 인증으로 보호.
- 대시보드(시각화) 화면은 후속 예정.

## 디렉토리 구조

```
src/
├── db/
│   ├── database.py        # Neon 엔진/세션 생성
│   └── models.py          # SymbolMaster, DailyPrice ORM
├── collectors/
│   ├── fdr_collector.py   # FinanceDataReader 수집기
│   └── yahoo_collector.py # yfinance 수집기 (^N225, GC=F 등)
├── loader.py              # daily_price 적재 공통 로직 (멱등 upsert)
├── logging_config.py      # logs/ 파일 로깅 설정
├── init_db.py             # 테이블 생성 + 종목마스터 초기 등록
├── symbols_seed.py        # 종목마스터 전체 시드(seed) 등록
├── collect.py             # 범용 일괄 수집·적재 배치 진입점
└── collect_ks200.py       # (파일럿) KS200 단일 수집·적재
logs/                      # 실행 로그 finsight_{to일자}.log (gitignore)

dashboard/                 # Streamlit 프런트엔드
├── app.py                 # 엔트리(홈/네비게이션)
├── pages/
│   ├── 1_admin_symbols.py # 종목마스터 관리(CRUD)
│   └── 2_admin_prices.py  # 종가내역 조회(페이징)
└── services/              # connection / auth / symbol_service / price_service
```

## 사전 준비

1. [uv](https://docs.astral.sh/uv/) 설치
2. 의존성 설치

```bash
uv sync
```

3. Neon DB 연결 문자열을 `.env`에 설정 (`.env.example` 참고)

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
```

## 실행

### 1) 테이블 생성 + 종목마스터 시드

```bash
uv run python -m src.init_db        # 테이블 생성
uv run python -m src.symbols_seed   # 종목마스터 전체 종목 등록(멱등)
```

### 2) 일괄 수집·적재 배치 (`src.collect`)

전 종목을 일괄 수집한 뒤 수집에 성공한 종목만 멱등 upsert로 적재한다.

```bash
# 전체 종목, 최근 1개월(기본값)
uv run python -m src.collect

# 전체 종목, to일자 지정 (해당일 기준 1개월 전 ~ to일자)
uv run python -m src.collect --to-date 20260617

# 전체 종목, 기간만 지정
uv run python -m src.collect --from-date 20260101 --to-date 20260617

# 특정 종목(symbol_id)만, 기간 지정 (초기 백필 등)
uv run python -m src.collect --symbol-id 3 --from-date 20160101 --to-date 20260617
```

| 옵션 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `--to-date` | `yyyymmdd` | 현재일자 | 수집 종료일(to) |
| `--from-date` | `yyyymmdd` | to일자 − 1개월 | 수집 시작일(from) |
| `--symbol-id` | 정수 | 전체 | 특정 종목만 수집 |

- 실행 로그는 `logs/finsight_{to일자}.log`에 기록되며, 종료 시 종목별 요약(명칭·from·to·총건수·상태)을 남긴다.

### 3) 관리자 대시보드 (Streamlit)

```bash
uv run streamlit run dashboard/app.py
```

- 로컬 URL: http://localhost:8501
- 배포 URL(Streamlit Community Cloud): `<배포 후 URL>`
- 관리자 페이지는 비밀번호 인증 필요(`ADMIN_PASSWORD`).
  - 로컬: `.streamlit/secrets.toml`, 배포: Cloud Secrets에 `DATABASE_URL`·`ADMIN_PASSWORD` 설정.

### (참고) 파일럿 단일 수집

```bash
uv run python -m src.collect_ks200   # KS200 최근 10년치 수집·적재
```

## 배포용 requirements.txt 갱신

```bash
uv export --no-hashes --no-dev -o requirements.txt
```
