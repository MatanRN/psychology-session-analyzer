FROM python:3.13.7-alpine

WORKDIR /app

# Copy common package
COPY services/common /app/services/common

WORKDIR /app/services/transcript-analyzer

# Copy service
COPY services/transcript-analyzer/pyproject.toml pyproject.toml

# Update dependency path to be absolute inside the container
# Replaces ${PROJECT_ROOT}/.. with /app/services to point to the common package
RUN sed -i 's|\${PROJECT_ROOT}/..|/app/services|g' pyproject.toml

# Install common package explicitly
RUN pip install .

COPY services/transcript-analyzer/system.txt .
COPY services/transcript-analyzer/main.py .
COPY services/transcript-analyzer/domain domain/
COPY services/transcript-analyzer/infrastructure infrastructure/
COPY services/transcript-analyzer/handlers handlers/
COPY services/transcript-analyzer/repositories repositories/
COPY services/transcript-analyzer/worker.py .
COPY services/transcript-analyzer/dependencies.py .
COPY services/transcript-analyzer/exceptions.py .
COPY services/transcript-analyzer/config.py .

ENTRYPOINT ["python", "main.py"]
