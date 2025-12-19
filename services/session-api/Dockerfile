FROM python:3.13.7-alpine

WORKDIR /app

# Copy common package
COPY services/common /app/services/common

WORKDIR /app/services/session-api

# Copy service
COPY services/session-api/pyproject.toml pyproject.toml

# Update dependency path to be absolute inside the container
# Replaces ${PROJECT_ROOT}/.. with /app/services to point to the common package
RUN sed -i 's|\${PROJECT_ROOT}/..|/app/services|g' pyproject.toml

# Install the service (will automatically install common from the path)
RUN pip install .

# Copy application code
COPY services/session-api/main.py .
COPY services/session-api/config.py .
COPY services/session-api/dependencies.py .
COPY services/session-api/exceptions.py .
COPY services/session-api/response_models.py .
COPY services/session-api/routes/ ./routes/
COPY services/session-api/repositories/ ./repositories/

EXPOSE 8080

ENTRYPOINT ["fastapi", "run", "main.py", "--port", "8080"]
