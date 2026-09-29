# First private model appliance (single node)

Do this only after Tailscale SSH works and, if you have two boxes, after you have decided whether today needs a cluster. The first model should run on **one** Spark.

NVIDIA’s current vLLM playbooks live under https://build.nvidia.com/spark — re-fetch in refresh mode. The snapshot below is what actually served a live completion on 2026-09-02.

## Product, not a science project

The user should get:

1. An OpenAI-compatible endpoint on the Tailscale address (or localhost + SSH tunnel)
2. A model name they can put in Codex / Claude / Hermes / any OpenAI client
3. A 401 without the API key
4. A real completion with the key
5. `status | start | stop | restart | logs` without joining the Docker group
6. The same completion after `restart`

If any of those fail, the appliance is not done. A container that “started” is not enough.

## Snapshot recipe (2026-09-02)

Proven on one GB10 Spark:

| Knob | Snapshot value |
| --- | --- |
| Model | `nvidia/Qwen3.6-35B-A3B-NVFP4` |
| Revision | pin the current NVIDIA revision; do not float `main` |
| Runtime | vLLM 0.28.0, linux/arm64, imported by digest not `latest` |
| Bind | Tailscale IPv4 only, port 8000 |
| Auth | generated API key; unauthenticated `/v1/models` → 401 |
| Context | 262144 |
| GPU memory util | start conservative (snapshot used 0.50) |
| KV | FP8 |
| Attention | FlashInfer |
| Linux user | **not** in `docker` |
| Control | root-owned systemd unit + `/usr/local/bin/<name>` wrapper |

Re-check NVIDIA’s current recommended starter model during a live refresh. If NVIDIA has replaced this checkpoint, prefer the new official starter over nostalgia.

## How to build it without turning the Mac into a model library

- Download weights **on the Spark**, or stage one payload at a time on the admin computer only if the user’s own security policy requires an airlock scan.
- Prefer official NVIDIA / Hugging Face `nvidia/` artifacts.
- Record SHA-256 of the image and the model snapshot in the baseline note.
- Mount weights read-only into the container.
- Hugging Face offline + telemetry off in the unit file if the box should not call home at serve time.

## Bind and firewall

- Listen on the Tailscale IP or `127.0.0.1`.
- If you listen on `127.0.0.1`, the admin computer uses `ssh -L 8000:127.0.0.1:8000 spark-a`.
- UFW (or equivalent): default deny inbound; allow SSH and the API port **only** on `tailscale0`.
- Prove the ordinary LAN IP does **not** answer on the API port.

## Control surface

Do not give the user `sudo docker run`. Give them five words:

```bash
ssh spark-a dgx-model status
ssh spark-a dgx-model restart
ssh spark-a dgx-model stop
ssh spark-a dgx-model start
ssh spark-a dgx-model logs
```

Passwordless sudo, if any, should be scoped to that unit. Not `docker`, not `/bin/bash`.

## Acceptance commands (from the admin computer)

Do not print the key.

```bash
# must fail without a key
curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 http://<tailscale-ip>:8000/v1/models

# must list the served name (key via stdin or env, not ps)
curl -sS --max-time 20 http://<tailscale-ip>:8000/v1/models \
  -H "Authorization: Bearer ${DGX_API_KEY}"

# must return a short completion, then again after restart
```

Restart the unit, wait until health is up, repeat the completion.

## What not to do on day one

- Two-node tensor parallel
- Unofficial NVFP4 derivatives
- 1M context
- Adding the user to `docker`
- Binding `0.0.0.0`
- Calling the cluster “ready for DeepSeek” because Cluster Assistant passed

After this appliance responds, the user can follow `recipe-watchlist.md` on the same admin harness.
