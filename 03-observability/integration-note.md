# Integration note: PaLLMs (v1, go-live)

- **base_url** (client form, ends in `/v1`):
  `https://t13.aidc.nadir.sh/v1`
- **service root** (no `/v1`):
  `https://t13.aidc.nadir.sh`
- **model id:** `Qwen/Qwen2.5-1.5B-Instruct-AWQ`
- **auth:** bearer key, handed over via Discord DM
- **modalities:** text in, text out, tool calls per the OpenAI schema.
- **example call:**
  curl -s https://t13.aidc.nadir.sh/v1/chat/completions \
    -H "Authorization: Bearer $API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"model":"Qwen/Qwen2.5-1.5B-Instruct-AWQ","messages":[{"role":"user","content":"hello from outside"}]}'
- **SLOs we publish:** availability 95% over the window · TTFT p95 < 350 ms (tier 1) · error rate < 5%
- **limits, declared honestly:** no server-enforced max_tokens clamp — bounded only by `--max-model-len 4096` (total context + output combined) · concurrency knee ~16 (from week 3's bench, sweep-bounded, real ceiling untested past 16) · single GPU shared across the whole cohort, no isolation between callers
- **on-call:** Thamer · Discord DM · response within 15 minutes during the window
