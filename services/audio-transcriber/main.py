"""
Audio Transcriber Service.

Entry point for the audio transcription service.
"""

from ddtrace import patch_all

from dependencies import get_worker

patch_all()


def main():
    """Starts the worker."""
    worker = get_worker()
    worker.start()


if __name__ == "__main__":
    main()
