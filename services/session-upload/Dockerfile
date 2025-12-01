FROM python:3.13.7-alpine

WORKDIR /app

# Copy common package
COPY services/common /app/services/common

WORKDIR /app/services/session-upload

# Copy service
COPY services/session-upload/pyproject.toml pyproject.toml

# Update dependency path to be absolute inside the container
# Replaces ${PROJECT_ROOT}/.. with /app/services to point to the common package
RUN sed -i 's|\${PROJECT_ROOT}/..|/app/services|g' pyproject.toml

# Install the service (will automatically install common from the path)
RUN pip install .

COPY services/session-upload/main.py .

EXPOSE 8000

ENTRYPOINT ["fastapi", "run", "main.py", "--port", "8000"]