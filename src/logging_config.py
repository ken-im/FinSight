"""파일 로깅 설정.

`logs/` 디렉토리에 `finsight_{to일자}.log` 형식으로 로그를 남긴다.
콘솔과 파일에 동시 출력한다.
"""

from __future__ import annotations

import logging
from pathlib import Path

PROJECT_NAME = "finsight"
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# 한 로그 레코드의 최대 길이(바이트). 초과 시 잘라낸다(긴 traceback/SQL 덤프 방지).
MAX_LOG_BYTES = 1000
_TRUNCATE_MARKER = " ...[truncated]"


class TruncatingFormatter(logging.Formatter):
    """포맷된 로그가 `max_bytes`를 초과하면 UTF-8 기준으로 잘라낸다."""

    def __init__(self, fmt: str | None = None, max_bytes: int = MAX_LOG_BYTES) -> None:
        super().__init__(fmt)
        self.max_bytes = max_bytes

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        encoded = message.encode("utf-8")
        if len(encoded) <= self.max_bytes:
            return message
        keep = self.max_bytes - len(_TRUNCATE_MARKER.encode("utf-8"))
        return encoded[:keep].decode("utf-8", errors="ignore") + _TRUNCATE_MARKER


def setup_logging(to_date: str, level: int = logging.INFO) -> Path:
    """루트 로거에 콘솔/파일 핸들러를 설정하고 로그 파일 경로를 반환한다.

    파일명: `finsight_{to_date}.log` (to_date 형식: yyyymmdd)
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{PROJECT_NAME}_{to_date}.log"

    formatter = TruncatingFormatter(LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(level)
    # 중복 핸들러 방지 (재호출/재진입 대비)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return log_path


def append_trailing_blank_lines(count: int = 5) -> None:
    """로그 파일 끝에 공백 라인을 추가한다(콘솔 출력에는 영향 없음)."""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            handler.acquire()
            try:
                handler.stream.write("\n" * count)
                handler.flush()
            finally:
                handler.release()
