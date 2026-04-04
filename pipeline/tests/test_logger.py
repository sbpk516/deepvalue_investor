import pytest
import logging
import os
from unittest.mock import patch
from pipeline.utils.logger import get_logger


class TestLogger:
    def test_returns_logger(self, tmp_path):
        with patch("pipeline.config.LOG_DIR", str(tmp_path)):
            logger = get_logger("test_module")
            assert isinstance(logger, logging.Logger)

    def test_logger_name(self, tmp_path):
        with patch("pipeline.config.LOG_DIR", str(tmp_path)):
            logger = get_logger("my_module")
            assert logger.name == "my_module"

    def test_creates_log_file(self, tmp_path):
        with patch("pipeline.config.LOG_DIR", str(tmp_path)):
            logger = get_logger("test_file_creation")
            logger.info("test message")
            log_files = list(tmp_path.glob("*.log"))
            assert len(log_files) >= 1

    def test_no_duplicate_handlers(self, tmp_path):
        with patch("pipeline.config.LOG_DIR", str(tmp_path)):
            logger1 = get_logger("dup_test")
            handler_count = len(logger1.handlers)
            logger2 = get_logger("dup_test")
            assert len(logger2.handlers) == handler_count
