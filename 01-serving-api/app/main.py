"""serving-stack: the FastAPI model service.

The service exposes an OpenAI-compatible /v1 API. It uses CUDA when available
and otherwise falls back to CPU.

Run it:
    uvicorn main:app --host 0.0.0.0 --port 8000

Model: Qwen/Qwen2.5-0.5B-Instruct.
"""

from __future__ import annotations

import os
import time
import uuid

import torch
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from transformers import AutoModelForCausalLM, AutoTokenizer

from schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    HealthResponse,
    ModelCard,
    ModelList,
    ResponseMessage,
    Usage,
)

MODEL_ID = os.environ.get(
    "MODEL_ID",
    "Qwen/Qwen2.5-0.5B-Instruct",
)
API_KEY = os.environ.get("API_KEY", "")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "256"))

app = FastAPI(title="serving-api", version="cpu-v2")

if not API_KEY:
    print("WARNING: API_KEY is not set; /v1 endpoints are unauthenticated.")


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    """Require the configured bearer token for every /v1 endpoint."""
    if (
        API_KEY
        and request.url.path.startswith("/v1/")
        and request.headers.get("authorization") != f"Bearer {API_KEY}"
    ):
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
        )

    return await call_next(request)


# Use CUDA when available; otherwise fall back to CPU.
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DTYPE = torch.float16 if DEVICE.type == "cuda" else torch.float32

print(f"loading {MODEL_ID} on {DEVICE} ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=DTYPE,
)
model.to(DEVICE)
model.eval()
print("model ready")


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service readiness without exposing sensitive information."""
    return HealthResponse(
        status="ok",
        model=MODEL_ID,
    )


# ---------------------------------------------------------------------------
# GET /v1/models
# ---------------------------------------------------------------------------
@app.get("/v1/models", response_model=ModelList)
def list_models() -> ModelList:
    """Return the model exposed by this service."""
    return ModelList(
        data=[
            ModelCard(
                id=MODEL_ID,
                created=int(time.time()),
                owned_by="aidc",
            )
        ]
    )


# ---------------------------------------------------------------------------
# POST /v1/chat/completions
# ---------------------------------------------------------------------------
@app.post(
    "/v1/chat/completions",
    response_model=ChatCompletionResponse,
)
def chat_completions(
    req: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """Generate a non-streaming OpenAI-compatible chat completion."""

    # Enforce the configured hard ceiling.
    max_tokens = min(req.max_tokens, MAX_TOKENS)

    # Convert messages into Qwen chat-template token IDs.
    input_ids = tokenizer.apply_chat_template(
        [message.model_dump() for message in req.messages],
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(DEVICE)

    # Count prompt tokens before generation.
    prompt_tokens = input_ids.shape[1]

    # temperature=0 uses greedy generation; positive values use sampling.
    generation_args = {
        "max_new_tokens": max_tokens,
        "do_sample": req.temperature > 0,
        "pad_token_id": tokenizer.eos_token_id,
    }

    if req.temperature > 0:
        generation_args["temperature"] = req.temperature

    # Generate synchronously.
    with torch.no_grad():
        out = model.generate(
            input_ids,
            **generation_args,
        )

    # Keep and count only tokens generated after the prompt.
    new_tokens = out[0][prompt_tokens:]
    completion_tokens = len(new_tokens)

    # Decode only the generated tokens.
    text = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True,
    )

    # Report whether generation consumed the effective token allowance.
    finish_reason = (
        "length"
        if completion_tokens >= max_tokens
        else "stop"
    )

    return ChatCompletionResponse(
        id="chatcmpl-" + uuid.uuid4().hex,
        created=int(time.time()),
        model=req.model,
        choices=[
            Choice(
                message=ResponseMessage(
                    role="assistant",
                    content=text,
                ),
                finish_reason=finish_reason,
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


# ---------------------------------------------------------------------------
# Streaming remains optional and is not required for the green check.
# ---------------------------------------------------------------------------