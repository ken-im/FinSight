# FinSight 데이터 수집 배치 실행 계획 (PLAN-backend-20260617)

> 본 문서는 [PRD-20260323](./PRD-20260323.md)과 파일럿 계획 [PLAN-pilot-20260617](./PLAN-pilot-20260617.md)을 기반으로,
> 단일 종목(KS200) 파일럿을 **전체 금융데이터 대상의 파라미터 기반 일괄 수집·적재 배치**로 확장하는 계획이다.
> 데이터 모델(`symbol_master`, `daily_price`), Neon 연결, 멱등 upsert 등 파일럿에서 검증된 구조를 그대로 재사용한다.

## 1. 목표
- 수집 대상을 PRD 2.1의 **전체 종목(16종)** 으로 확장한다.
- 여러 종목을 한 번의 실행으로 처리하는 **일괄 수집 → 일괄 적재** 구조를 만든다.
- 실행 파라미터(**from일자 / to일자 / Symbol_id**)로 수집 범위와 대상을 제어한다.
- 실행 결과를 **`logs/` 디렉토리에 파일 로그**로 남기고, 종목별 요약(명칭·기간·건수)을 기록한다.

## 2. 범위

### 2.1. 수집 대상 종목 (종목마스터 초기 데이터)
PRD 2.1 표를 그대로 종목마스터(`symbol_master`)에 시드(seed)로 등록한다. `source`는 수집 원천을 의미하며, 종목별 수집기 분기 기준이 된다.

| source | symbol  | symbol_nm       | remark                 |
| ------ | ------- | --------------- | ---------------------- |
| FDR    | KS11    | KOSPI 지수      | 코스피 종합지수        |
| FDR    | KQ11    | KOSDAQ 지수     | 코스닥 종합지수        |
| FDR    | KS200   | KOSPI 200       | 코스피 200개 기업 지수 |
| FDR    | DJI     | 다우존스 지수   | 미국 우량주 30개 종목  |
| FDR    | IXIC    | 나스닥 종합지수 | 미국 기술주 중심       |
| FDR    | US500   | S&P 500 지수    | 미국 대표 500개 기업   |
| FDR    | VIX     | 공포 지수       | S&P 500 변동성 지수    |
| YAHOO  | ^N225   | 닛케이 225      | 일본 대표 지수 (Yahoo) |
| FDR    | SSEC    | 상해 종합지수   | 중국 본토 시장         |
| FDR    | HSI     | 항셍 지수       | 홍콩 시장              |
| YAHOO  | GC=F    | 금 선물         | 금 선물 (Yahoo)        |
| FDR    | CL      | WTI 선물        | WTI 선물               |
| FDR    | AAPL    | Apple           | 애플 종가              |
| FDR    | 005930  | 삼성전자        | 삼성전자 종가          |
| FDR    | BTC/USD | 비트코인/달러   | 비트코인 달러 가격     |
| FDR    | ETH/USD | 이더리움/달러   | 이더리움 달러 가격     |

> 참고: 1차 원천은 `FDR`(FinanceDataReader)를 기본으로 하되, FDR가 미지원/표기 불일치인 종목은 `YAHOO`(yfinance)로 수집한다. 실제 검증 결과 **닛케이(`JP225`)와 금 선물(`GC`)이 FDR에서 실패**하여 각각 Yahoo 심볼 `^N225`, `GC=F`로 전환했다(2026-06-17 적용, 8.1 참조). `source` 컬럼 기반 분기 구조이므로 종목별 원천을 데이터로만 조정한다.

### 2.2. 파일럿 대비 변경점
| 구분 | 파일럿 (PLAN-pilot) | 본 계획 (PLAN) |
| --- | --- | --- |
| 대상 | KS200 단일 | 종목마스터 전체(또는 지정 1종) |
| 실행 | 고정 10년 수집 | 파라미터(from일자/to일자/Symbol_id) 기반 |
| 처리 | 단건 수집·적재 | 일괄 수집 → 일괄 적재 |
| 로깅 | 콘솔 로그 | `logs/` 파일 로그 + 종목별 요약 |
| 진입점 | `collect_ks200.py` | `collect.py` (범용 배치) |

### 2.3. 제외 (Out of Scope)
- Streamlit 대시보드 / 시각화
- GitHub Actions 자동 스케줄링 (본 배치를 호출하는 형태로 추후 연계)

## 3. 종목마스터 시드(seed)
- 2.1 표를 `(source, symbol)` 기준 멱등 등록(`get_or_create_symbol`)한다. 이미 존재하면 건너뛰고, 신규만 채번한다.
- 파일럿에서 등록된 `KS200`은 그대로 유지된다(중복 등록 없음).
- 진입점: `src/symbols_seed.py` (실행: `uv run python -m src.symbols_seed`)

## 4. 실행 파라미터
| 파라미터 | CLI 옵션 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| to일자 | `--to-date` | `yyyymmdd` | 현재일자(`today`) | 수집 종료일(to) |
| from일자 | `--from-date` | `yyyymmdd` | to일자 − 1개월 | 수집 시작일(from) |
| Symbol_id | `--symbol-id` | 정수 | 미지정 시 **전체 대상** | 특정 종목만 수집 |

- 수집 구간은 **[from일자, to일자]** (양끝 포함)로 해석한다.
- `--symbol-id` 미지정 시 종목마스터 전체를 대상으로 한다.
- 유효성 검증: 날짜 형식(`yyyymmdd`), `from일자 ≤ to일자`, 존재하지 않는 `symbol_id` 처리.

### 실행 예시
```bash
# 1) 전체 종목, 최근 1개월(기본값)
uv run python -m src.collect

# 2) 전체 종목, to일자 지정 (해당일 기준 1개월 전 ~ to일자)
uv run python -m src.collect --to-date 20260617

# 3) 전체 종목, 기간만 지정 (--symbol-id 미지정 → 전체 대상)
uv run python -m src.collect --from-date 20260101 --to-date 20260617

# 4) 특정 종목(symbol_id=3)만, 기간 지정 (초기 백필 등)
uv run python -m src.collect --symbol-id 3 --from-date 20160101 --to-date 20260617
```

## 5. 처리 구조 (전 종목 일괄 수집 → 성공 종목만 일괄 적재)

> **2단계 분리**: 모든 종목의 수집을 먼저 완료한 뒤, **수집에 성공한 종목만** DB에 일괄 적재한다.
> 수집(외부 API)과 적재(DB)를 분리하여, 일부 종목의 수집 실패가 DB 적재 단계에 섞이지 않도록 한다.

```
[파라미터 파싱]
   │  to_date(기본 today), from_date(기본 to-1M), symbol_id(기본 전체)
   ▼
[대상 선정]  symbol_master 조회 → 대상 종목 리스트(symbol_id, source, symbol, symbol_nm)
   ▼
[1단계: 일괄 수집]  전 종목을 source별 수집기로 수집 → 성공 종목의 정규화 DataFrame을 메모리에 수집
   │                 (DB 미접근, 실패 종목은 FAIL_COLLECT로 기록 후 제외)
   ▼
[2단계: 일괄 적재]  수집 성공 종목만 (symbol_id, trade_dt) 멱등 upsert
   │                 (종목별 savepoint로 격리 후 일괄 커밋)
   ▼
[요약 로깅]  종목별 명칭/from/to/총건수/상태 + 합계를 logs 파일에 기록
```

### 5.1. 대상 선정
- `--symbol-id` 지정 시 단건, 미지정 시 `symbol_master` 전체를 조회한다.
- 결과가 없으면(시드 미적재 등) 경고 로그 후 종료한다.
- `source` 기반 수집기 매핑: `FDR` → `fdr_collector`, `YAHOO` → `yahoo_collector`.

### 5.2. 1단계 — 전 종목 일괄 수집 (DB 미접근)
- 종목별로 `source` 값에 따라 수집기를 분기한다.
- 수집기는 `collect_daily_prices(symbol, start, end)` 인터페이스를 공통으로 따른다(파일럿과 동일).
- 파라미터 `yyyymmdd`를 수집기 입력 형식(`YYYY-MM-DD`)으로 변환해 전달한다.
- 개별 종목 수집 실패는 **해당 종목만 제외**(`FAIL_COLLECT`)하고 traceback을 로깅한 뒤 다음 종목으로 진행한다(전체 배치 중단 방지).
- 이 단계에서는 **DB에 접근하지 않으며**, 성공 종목의 DataFrame만 메모리에 모은다.

### 5.3. 2단계 — 수집 성공 종목만 일괄 적재
- 1단계에서 수집에 성공한 종목만 대상으로 적재한다.
- 종목별 정규화 결과에 `symbol_id`를 부여해 `daily_price` 레코드로 변환한다.
- `(symbol_id, trade_dt)` 충돌 시 갱신하는 멱등 upsert(파일럿 `upsert_daily_prices` 재사용), `BATCH_SIZE=500` chunk 처리.
- 종목별 **savepoint(`begin_nested`)** 로 격리하여 한 종목의 적재 실패(`FAIL_LOAD`)가 다른 종목에 영향을 주지 않게 하고, 마지막에 한 번 커밋한다.

## 6. 로깅
- 출력 위치: 프로젝트 루트의 **`logs/`** 디렉토리(실행 시 없으면 생성).
- 파일명: **`finsight_{to일자}.log`** (예: `finsight_20260617.log`). 프로젝트명은 `pyproject.toml`의 `finsight`를 사용한다.
- 콘솔과 파일에 동시 출력(`StreamHandler` + `FileHandler`), 포맷: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`.
- `.cursorrules` 준수: `print()` 대신 `logging` 사용, 에러 시 `logger.exception()`으로 traceback 포함.
- 설정 모듈: `src/logging_config.py` (`setup_logging(to_date)` 형태).

### 종목별 요약 로그(예시)
```
======== 수집 요약 (to일자: 20260617) ========
symbol_id  명칭            from        to          총건수
        3  KOSPI 200       20260517    20260617         21
        1  KOSPI 지수      20260517    20260617         21
        2  KOSDAQ 지수     20260517    20260617         21
        ...
------------------------------------------------
대상 16종목 / 적재 합계 336건 / 실패 0종목
================================================
```
- 각 행: 종목 명칭(`symbol_nm`), 요청 구간(from일자~to일자), 해당 종목 적재 건수.
- 합계: 대상 종목 수, 적재 총건수, 실패 종목 수.

## 7. 디렉토리 구조 (추가/변경분)
```
FinSight/
├── src/
│   ├── collect.py             # [신규] 배치 진입점 (argparse 파라미터)
│   ├── symbols_seed.py        # [신규] 종목마스터 전체 시드 등록
│   ├── logging_config.py      # [신규] logs 파일 로거 설정
│   ├── collect_ks200.py       # (파일럿 잔존, collect.py로 일반화)
│   ├── collectors/
│   │   ├── fdr_collector.py
│   │   └── yahoo_collector.py # [신규] yfinance 수집기 (^N225, GC=F 등)
│   └── db/ ...                # 변경 없음 (database.py, models.py)
├── logs/                      # [신규] 실행 로그 (*.log → gitignore)
│   └── finsight_20260617.log
└── ...
```
> `logs/`는 런타임 생성이며 `*.log`는 이미 `.gitignore`에 포함. 빈 디렉토리 추적이 필요하면 `logs/.gitkeep` 추가.

## 8. 단계별 실행 계획
### 단계 0. 종목마스터 시드
- [x] `src/symbols_seed.py` 작성: 2.1 표 16종을 멱등 등록
- [x] 실행 후 `symbol_master` 16건 확인

### 단계 1. 로깅 구성
- [x] `src/logging_config.py` 작성: `logs/finsight_{to_date}.log` 파일+콘솔 핸들러
- [x] 포맷·레벨 설정 및 디렉토리 자동 생성

### 단계 2. 파라미터 처리
- [x] `src/collect.py`에 `argparse`로 `--to-date/--from-date/--symbol-id` 구현
- [x] 기본값 계산(to일자=today, from=to−1개월) 및 유효성 검증

### 단계 3. 일괄 수집·적재 (2단계 분리)
- [x] 대상 종목 조회(전체/단건) 로직
- [x] 1단계: `source` 기반 수집기 분기 + 전 종목 수집(실패 격리, DB 미접근)
- [x] 2단계: 수집 성공 종목만 멱등 upsert(배치) + savepoint 격리 후 일괄 커밋

### 단계 4. 요약 로깅
- [x] 종목별 명칭/from/to/총건수 집계 및 요약 출력
- [x] 합계(대상 수/적재 합계/실패 수) 기록

### 단계 5. 검증
- [x] 전체 실행 시 16종 모두 처리, `logs/finsight_*.log` 생성 확인
- [x] `--symbol-id` 지정 시 단건만 처리 확인
- [x] 동일 파라미터 재실행 시 중복 없이 건수 유지(멱등성)
- [x] FDR 미지원 종목 식별 및 `source` 조정 여부 결정

## 8.1. 실행 결과 (2026-06-17)

### 시드
- `symbol_master`에 16종 등록 완료 (KS200은 파일럿 등록분 `symbol_id=1` 유지, 나머지 15종 신규 채번 2~16).

### 일괄 수집·적재 (기본 파라미터: `from=20260517 ~ to=20260617`, 전체 종목)
- 2단계(전 종목 수집 → 성공 종목만 일괄 적재) 구조로 실행.
- 대상 16종목 / **적재 합계 363건 / 성공 16종 / 실패 0종**
- 로그 파일 생성: `logs/finsight_20260617.log`

| symbol_id | source | 명칭 | 총건수 | 상태 |
| --- | --- | --- | --- | --- |
| 1 | FDR | KOSPI 200 | 21 | OK |
| 2 | FDR | KOSPI 지수 | 21 | OK |
| 3 | FDR | KOSDAQ 지수 | 21 | OK |
| 4 | FDR | 다우존스 지수 | 21 | OK |
| 5 | FDR | 나스닥 종합지수 | 21 | OK |
| 6 | FDR | S&P 500 지수 | 21 | OK |
| 7 | FDR | 공포 지수 | 22 | OK |
| 8 | YAHOO | 닛케이 225 (`^N225`) | 23 | OK |
| 9 | FDR | 상해 종합지수 | 22 | OK |
| 10 | FDR | 항셍 지수 | 21 | OK |
| 11 | YAHOO | 금 선물 (`GC=F`) | 22 | OK |
| 12 | FDR | WTI 선물 | 21 | OK |
| 13 | FDR | Apple | 21 | OK |
| 14 | FDR | 삼성전자 | 21 | OK |
| 15 | FDR | 비트코인/달러 | 32 | OK |
| 16 | FDR | 이더리움/달러 | 32 | OK |

### 초기 실패 → YAHOO 전환 (적용 완료)
최초 전 종목 FDR 수집 시 2종이 실패하여 원인 분석 후 Yahoo 원천으로 전환했고, 재실행에서 전 종목 성공을 확인했다.

| symbol | 초기 원인(FDR) | 조치(적용) |
| --- | --- | --- |
| `JP225` → `^N225` | FDR가 Yahoo 조회 시 `404 Not Found` (심볼 불일치) | `source=YAHOO`, 심볼 `^N225` (23건 수집) |
| `GC` → `GC=F` | Yahoo 응답에 데이터 없음 (`KeyError: 'timestamp'`) | `source=YAHOO`, 심볼 `GC=F` (22건 수집) |

> `yahoo_collector`(yfinance) 추가 + 종목마스터의 `source`/`symbol`만 조정해 해결했다(공통 인터페이스라 배치 코드 변경 없음). 1단계에서 개별 실패 격리가 동작해, 초기 실패 시에도 나머지 14종 적재에는 영향이 없었다.

### 검증
- 단건 실행(`--symbol-id 13`): 대상 1종목만 처리 확인.
- 멱등성: 동일 파라미터 재실행 시 중복 적재 없이 건수 유지.
- DB 상태: `symbol_master` 16종, `daily_price` **데이터 보유 16종**(전 종목).

## 9. 완료 기준 (Definition of Done)
- 종목마스터에 PRD 16종이 등록되어 있다.
- 파라미터 없이 실행 시 전체 종목의 최근 1개월 데이터가 일괄 수집·적재된다.
- `--to-date/--from-date/--symbol-id`가 의도대로 동작한다.
- `logs/finsight_{to일자}.log`에 종목별 요약(명칭·from·to·총건수)과 합계가 남는다.
- 재실행 시 중복 적재가 없다(멱등 upsert).

## 10. 리스크 및 고려사항
| 항목 | 내용 | 대응 |
| --- | --- | --- |
| 원천별 심볼 표기/지원 차이 | FDR가 일부 종목(VIX/선물 등) 미지원 가능 | `source` 컬럼 기반 분기, 미지원 시 yfinance 전환 |
| 개별 종목 수집 실패 | 네트워크/심볼 오류로 일부 실패 | 종목 단위 try/except + 스킵, traceback 로깅, 배치 지속 |
| 레이트리밋 | 다종목 연속 호출 시 제한 | 종목 간 지연(옵션), 실패 재시도 |
| 대량 백필 | from일자를 과거로 지정 시 대용량 | `chunksize`/배치 upsert, 종목별 savepoint 후 일괄 커밋 |
| 기간 경계 | 휴장일로 실제 건수 < 달력일 | 요청 구간과 실제 적재 건수를 분리 기록 |
