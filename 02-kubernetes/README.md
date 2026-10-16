# 02 · Kubernetes

Deploys the serving API from [`01-serving-api`](../01-serving-api/) with Helm, and runs vLLM on the team's k3s GPU node.

| File | Purpose |
| --- | --- |
| [`helm/serving-chart/`](helm/serving-chart/) | Helm chart for the serving API: Deployment, Service and an optional HorizontalPodAutoscaler |
| [`metrics-server.yaml`](metrics-server.yaml) | metrics-server, required by the HPA (upstream manifest with `--kubelet-insecure-tls` for kind) |
| [`gpu/vllm-gpu.yaml`](gpu/vllm-gpu.yaml) | vLLM serving `Qwen/Qwen2.5-1.5B-Instruct-AWQ` on the GPU, behind the `team-serving` Service |

## Serving API with Helm

The chart runs the CPU image with:

- **Zero-downtime rolling updates:** `maxUnavailable: 0`, `maxSurge: 1`, and a 5-second `preStop` sleep so a pod keeps serving while its endpoint is removed from the Service.
- **Readiness and liveness probes** on `/health`, so traffic only reaches pods whose model has loaded.
- **Autoscaling:** an optional HPA from 1 to 3 replicas at a 50% CPU target.
- **Secrets:** the API key comes from a Kubernetes Secret (`apiKeySecret`), not a `--set` literal that would leak into shell history.

```bash
kubectl create secret generic serving-keys --from-literal=api-key=<key>
kubectl apply -f metrics-server.yaml
helm install demo helm/serving-chart --set hpa.enabled=true --set apiKeySecret=serving-keys
kubectl port-forward svc/demo-serving 8000:8000
```

CPU autoscaling suits this CPU service, but not a GPU engine. Under load, vLLM pushed the GPU to 94% while CPU stayed at about 27% of its request, so a CPU target would never add a replica. For vLLM the right signal is queue depth (`vllm_num_requests_waiting`).

## vLLM on the GPU node

```bash
kubectl -n team create secret generic serving-keys --from-literal=api-key=<key>
kubectl -n team apply -f gpu/vllm-gpu.yaml
```

- **Guaranteed QoS:** 4 CPU, 16Gi and 1 GPU, with requests equal to limits.
- **Startup probe** with a 10-minute budget, so liveness never kills the engine while it downloads the model.
- **API key** from the `serving-keys` Secret, and the Hugging Face cache on a hostPath so restarts skip the download.
- **Service named `team-serving`, not `vllm`:** Kubernetes injects `VLLM_PORT=tcp://…` for a Service called `vllm`, and vLLM crashes reading it as its own config.

At go-live the Service was switched to NodePort 30800 behind a tunnel and handed to a partner team ([integration note](../03-observability/integration-note.md)). The benchmark's larger models use the manifests in [`04-rfp-llm-benchmark/k8s`](../04-rfp-llm-benchmark/k8s/).

---
Some manifests started from SDA bootcamp templates; I completed, deployed and operated them on the team cluster.
