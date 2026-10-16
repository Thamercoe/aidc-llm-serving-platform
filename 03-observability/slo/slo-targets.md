# Service indicators and proposed targets

Team: Team 13
Use case: OpenAI-compatible LLM serving platform for paired Agentic AI cohort agents executing multi-turn reasoning, tool calling, and structured completions
Service measured: vLLM engine, endpoint `https://t13.aidc.nadir.sh` (`team-serving:8000`), namespace `team`
Workload: Outside-in verification suite and client completions, max_tokens clamped to 2048, prompt sizes up to 1024 tokens
Measurement period: 2026-09-10 11:00 UTC+3 to 11:30 UTC+3
Instrumentation gaps: External edge transit and Cloudflare tunnel latency; Prometheus scrapes in-cluster at `team-serving:8000`, measuring engine-internal execution rather than external client round-trip transit
## SLI 1

Indicator: 95th percentile Time to First Token (TTFT)
Panel: Time to First Token (TTFT)
Unit: seconds
Target: < 0.120 seconds (diagnostic threshold: warn at >= 0.080 seconds, breach at > 0.120 seconds)
Window: 5 minutes rate query window, 24-hour rolling SLO window
Observed: 0.039 seconds (~39 ms) sustained plateau; trough of 0.028 seconds (28 ms) during initial ramp-up
Evidence: `histogram_quantile(0.95, sum(rate(vllm:time_to_first_token_seconds_bucket[5m])) by (le))` recorded between 11:23 and 11:30 UTC+3
Why it fits: Direct measure of engine scheduling latency and prompt prefill time before streaming output tokens to agentic clients
Limitations: Captured strictly at the pod scrape interface; excludes Caddy proxy processing and Cloudflare tunnel edge transit

## SLI 2

Indicator: Sustained successful request completion rate
Panel: Completed Requests per Minute
Unit: requests/min
Target: >= 20 requests/min during active traffic windows (diagnostic threshold: < 5 requests/min under active load indicates worker starvation)
Window: 5 minutes rate query window, evaluated during active service traffic
Observed: Sustained plateau of 24.3 requests/min between 11:25 and 11:28 UTC+3; 0 requests/min at idle
Evidence: `sum(rate(vllm:request_success_total[5m])) * 60` recorded between 11:20 and 11:30 UTC+3
Why it fits: Validates that the vLLM batch scheduler and KV cache successfully finish and retire requests with 2xx status without hanging or stalling
Limitations: Tracks only requests that increment `vllm:request_success_total`; does not capture unauthenticated rejections or client disconnects prior to generation completion