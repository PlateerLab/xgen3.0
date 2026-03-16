FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 설치 (캐시 활용)
COPY pyproject.toml .
COPY src/ src/
COPY cli.py .
COPY agents/ agents/
COPY tools/ tools/

RUN pip install --no-cache-dir .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
