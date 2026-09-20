FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CREDITPILOT_DEPLOYMENT_MODE=synthetic_demo \
    CREDITPILOT_HOST=0.0.0.0 \
    CREDITPILOT_PORT=8000

WORKDIR /app

RUN addgroup --system creditpilot && adduser --system --ingroup creditpilot creditpilot

COPY pyproject.toml README.md ./
COPY src ./src
COPY reports ./reports

RUN pip install --no-cache-dir .

USER creditpilot
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"

CMD ["python", "-m", "creditpilot.interface.run"]
