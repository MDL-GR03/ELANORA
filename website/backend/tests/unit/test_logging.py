import logging

from app.core.logging import get_stream_logger


def test_logger_uses_one_stream_handler_and_never_creates_files() -> None:
    logger = get_stream_logger("elanora.tests.stream-only", level="INFO")
    same_logger = get_stream_logger("elanora.tests.stream-only", level="DEBUG")

    assert same_logger is logger
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert type(logger.handlers[0]) is logging.StreamHandler
    assert logger.propagate is False
