FROM python:3.13.7-alpine

WORKDIR /audio-extractor

RUN apk update && \
    apk add --no-cache ffmpeg

COPY pyproject.toml .

RUN pip install .

COPY main.py .


ENTRYPOINT ["python", "main.py"]