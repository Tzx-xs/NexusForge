import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from .settings import Settings


class JsonFormatter(logging.Formatter):
    """结构化 JSON 日志格式化器。

    当 LOG_FORMAT=json 时使用，输出每行一个 JSON 对象，
    便于日志收集系统（如 ELK、Loki）解析。
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if record.exc_info and record.exc_info[0]:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    settings = Settings.get_instance()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logger = logging.getLogger("xingyuanbi")
    logger.setLevel(log_level)
    logger.handlers.clear()

    log_format = os.getenv("LOG_FORMAT", "text")
    formatter: logging.Formatter
    if log_format == "json":
        formatter = JsonFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = os.path.dirname(settings.log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "xingyuanbi") -> logging.Logger:
    return logging.getLogger(name)
