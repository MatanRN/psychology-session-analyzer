FROM python:3.13.7-alpine

WORKDIR /app

RUN apk update && \
    apk add --no-cache ffmpeg

# Copy common package
COPY services/common /app/services/common

WORKDIR /app/services/audio-extractor

# Copy service
COPY services/audio-extractor/pyproject.toml pyproject.toml

# Update dependency path to be absolute inside the container
# Replaces ${PROJECT_ROOT}/.. with /app/services to point to the common package
RUN sed -i 's|\${PROJECT_ROOT}/..|/app/services|g' pyproject.toml

# Install common package explicitly
RUN pip install .

COPY services/audio-extractor/main.py .

ENTRYPOINT ["python", "main.py"]
