"""Entry point for the transcript-analyzer service."""

from ddtrace import patch_all
from psychology_common.logging import setup_logging

from dependencies import get_worker

logger = setup_logging()
patch_all()


def main():
    """Starts the transcript analyzer worker."""
    logger.info("Starting transcript-analyzer service")
    worker = get_worker()
    worker.start()


if __name__ == "__main__":
    main()
