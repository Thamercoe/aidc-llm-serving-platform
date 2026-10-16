# 01 · Serving API

A FastAPI service that serves `Qwen/Qwen2.5-0.5B-Instruct` through the same `/v1` contract as the OpenAI API, so any OpenAI client works against it by changing only `base_url`. It ships as a slim CPU image and a CUDA image that uses a GPU when one is present and falls back to CPU when not.

Published images: [`thameralotaibi/aidc-serving`](https://hub.docker.com/r/thameralotaibi/aidc-serving) (`cpu-v1`, `cpu-v2` with API-key auth, `gpu-v1`)

## Files

| File | Purpose |
| --- | --- |
| [`app/main.py`](app/main.py) | The API: health, model list, chat completions, bearer-token check |
| [`app/schemas.py`](app/schemas.py) | OpenAI-compatible request and response models |
| [`app/requirements.txt`](app/requirements.txt) | Pinned dependencies |
| [`Dockerfile`](Dockerfile) | CPU image, the one deployed on Kubernetes |
| [`Dockerfile.gpu`](Dockerfile.gpu) | CUDA image with automatic CPU fallback |
| [`compose.yaml`](compose.yaml) + [`.env.example`](.env.example) | Run the published image with one command |

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Readiness and the served model ID (open, for probes) |
| `GET` | `/v1/models` | Lists the model in OpenAI format |
| `POST` | `/v1/chat/completions` | Non-streaming completion with token usage |

A completion applies Qwen's chat template, counts prompt tokens, generates up to `max_tokens` (clamped to the server's `MAX_TOKENS` ceiling), and returns only the new tokens with `finish_reason` and usage.

**Security:** when `API_KEY` is set, every `/v1/*` request needs `Authorization: Bearer <key>` (401 otherwise), while `/health` stays open for Docker and Kubernetes probes. `MAX_TOKENS` caps the cost of any single request.

## Images

- **CPU image:** `python:3.11-slim`, dependencies installed before code for layer caching, CPU-only PyTorch wheels, no pip cache, non-root user, and model weights kept in a persistent `hf-cache` volume instead of an image layer. These choices brought the image from 3.49 GB to 1.61 GB.
- **GPU image:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04` with CUDA PyTorch. The app selects `cuda` when available and `cpu` otherwise, so the same image runs on a laptop and on a GPU. On a Tesla T4 it generated about 16.7× faster than on CPU.

## Run it

```bash
cp .env.example .env        # set a real API_KEY
docker compose up -d
docker compose ps           # wait for "healthy"

curl -s http://localhost:8000/health
curl -s -H "Authorization: Bearer $API_KEY" http://localhost:8000/v1/models
```

Build the images yourself:

```bash
docker build -t aidc-serving:cpu .
docker build -f Dockerfile.gpu -t aidc-serving:gpu .
docker run -d --gpus all -p 8000:8000 aidc-serving:gpu
```

Generation is synchronous, so this service handles one request at a time. Concurrency belongs to a serving engine, which is why the GPU deployments in [`02-kubernetes`](../02-kubernetes/) use vLLM.
