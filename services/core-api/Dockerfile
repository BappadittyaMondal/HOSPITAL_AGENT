# ====================================================================================================
# PROJECT "HOSPITAL" — CORE API SERVICE CONTAINER
# ====================================================================================================
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final minimal production runtime
FROM python:3.11-slim AS runner

# Hardening: Run as unprivileged non-root user
RUN groupadd -g 1001 hospital && useradd -u 1001 -g hospital -s /bin/sh -m hospital_user

WORKDIR /app
COPY --from=builder /root/.local /home/hospital_user/.local
COPY services/core-api /app

ENV PATH=/home/hospital_user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=8080

USER 1001:1001

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
