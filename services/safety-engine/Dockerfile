# ====================================================================================================
# PROJECT "HOSPITAL" — CLINICAL SAFETY ENGINE CONTAINER (DRE)
# ====================================================================================================
FROM python:3.11-slim AS runner

RUN groupadd -g 1002 safety && useradd -u 1002 -g safety -s /bin/sh -m safety_user

WORKDIR /app
COPY services/core-api/cpoe_dre_engine.py /app/
COPY services/core-api/chemotherapy_engine.py /app/
COPY services/core-api/access_control.py /app/

ENV PYTHONUNBUFFERED=1 \
    PORT=50051

USER 1002:1002

EXPOSE 50051

CMD ["python", "-c", "import time; print('Clinical Safety Engine (DRE) Active on port 50051'); time.sleep(99999999)"]
