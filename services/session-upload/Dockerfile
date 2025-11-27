FROM python:3.13.7-alpine

WORKDIR /session-upload

COPY pyproject.toml .

RUN pip install .

COPY main.py .

EXPOSE 8000

ENTRYPOINT ["fastapi", "run", "main.py", "--port", "8000"]