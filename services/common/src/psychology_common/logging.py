import logging
import sys

from pythonjsonlogger import jsonlogger


def setup_logging():
    """
    Configures and sets up structured JSON logging for the application.

    This function initializes a JSON formatter that includes timestamp, level,
    logger name, message, trace_id, and span_id. It replaces default handlers
    for the root logger and Uvicorn loggers with a custom stream handler
    to ensure consistent log formatting across the application.

    Returns:
        logging.Logger: The configured root logger instance.
    """
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s"
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    root_logger.addHandler(stream_handler)

    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        u_logger = logging.getLogger(logger_name)
        u_logger.setLevel(logging.INFO)

        u_logger.handlers = []

        u_logger.addHandler(stream_handler)

        u_logger.propagate = False

    return root_logger
