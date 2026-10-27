FROM python:3.12-slim-bookworm
ARG INSTALL_EVAL=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY . .
RUN if [ "$INSTALL_EVAL" = "true" ]; then python -m pip install --no-cache-dir -r requirements-eval.txt; else python -m pip install --no-cache-dir -r requirements.txt; fi
RUN python -m pip install --no-cache-dir --no-deps .
RUN useradd --uid 10001 --create-home evaluator && mkdir -p reports && chown -R evaluator:evaluator /app
USER evaluator
ENTRYPOINT ["rag-gate"]
CMD ["demo"]
