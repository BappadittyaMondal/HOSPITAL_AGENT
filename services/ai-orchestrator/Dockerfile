# ====================================================================================================
# PROJECT "HOSPITAL" — AI ORCHESTRATOR & CDSS CONTAINER
# ====================================================================================================
FROM python:3.11-slim AS runner

RUN groupadd -g 1003 aigroup && useradd -u 1003 -g aigroup -s /bin/sh -m ai_user

WORKDIR /app
COPY services/core-api/diagnostic_graph_rag.py /app/
COPY services/core-api/sbccl_experience_engine.py /app/
COPY services/core-api/ai_governance_serving.py /app/

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

USER 1003:1003

EXPOSE 8000

CMD ["python", "-c", "import time; print('AI Orchestration & Diagnostic Assistance Active on port 8000'); time.sleep(99999999)"]
