FROM python:3.11-slim

# Non-root runtime user and writable Hugging Face cache mount point.
RUN useradd --create-home app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app/.cache

ENV HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

# Dependencies first so code edits reuse this expensive layer.
COPY app/requirements.txt .

# Force CPU-only Torch and avoid retaining pip's download cache.
RUN pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      --extra-index-url https://pypi.org/simple \
      -r requirements.txt

# Application code changes more frequently, so copy it second.
COPY app/ .

USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]