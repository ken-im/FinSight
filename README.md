# FinSight

시장의 금융데이터(지수, 주가 등)를 수집·저장·시각화하는 개인 프로젝트.

- 아키텍처/기술 스택: [docs/PRD-20260323.md](docs/PRD-20260323.md)
- 파일럿(KS200 수집·적재) 계획: [docs/PLAN-pilot-20260617.md](docs/PLAN-pilot-20260617.md)

## 파일럿 범위

KOSPI 200(`KS200`) 최근 10년치 일별 시세를 FinanceDataReader로 수집하여 Neon DB(PostgreSQL)에 적재한다.

## 디렉토리 구조

```
src/
├── db/
│   ├── database.py      # Neon 엔진/세션 생성
│   └── models.py        # SymbolMaster, DailyPrice ORM
├── collectors/
│   └── fdr_collector.py # FinanceDataReader 수집기
├── init_db.py           # 테이블 생성 + 종목마스터 초기 등록
└── collect_ks200.py     # KS200 수집·적재 진입점
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

```bash
# 1) 테이블 생성 + 종목마스터(KS200) 등록
uv run python -m src.init_db

# 2) KS200 최근 10년치 수집 및 적재 (멱등 upsert)
uv run python -m src.collect_ks200
```

## 배포용 requirements.txt 갱신

```bash
uv export --no-hashes --no-dev -o requirements.txt
```
