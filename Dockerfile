# Built and run locally on 2026-11-08 (image 697MB, runs as non-root uid 10001, migrates and serves /health and /app). Not yet run on a real host.
# Free-pilot container. No secrets are baked in; everything comes from environment variables at run time.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend_requirements.txt .
RUN pip install --no-cache-dir -r backend_requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 app && mkdir -p /data/private /data/journal && chown -R app /app /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
