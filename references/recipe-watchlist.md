# Recipe watchlist (after the box is remote)

Not day-one setup. Use this when the first private appliance already answers, and the user wants to know **who is actually publishing GB10 / two-Spark recipes**.

Last reviewed: 2026-09-04. Handles rot. Re-verify. This is a monitored bench, not a hire list and not an endorsement.

## How to use this from the admin harness

Once `ssh spark-a` works, you can synthesize these people on the computer you already live in:

1. Follow / search the seats below on X, GitHub, Hugging Face, and the NVIDIA Spark forum.
2. Normalize every claim to: model revision, quant, KV, context, TP/EP, runtime image digest, flags, thinking/sampler, speculation, concurrency, and a quality check.
3. Keep single-user tok/s separate from aggregate tok/s.
4. Do not replace a working appliance because a tweet was faster on unlike hardware.

A weekly loop that does this is more valuable than sitting in each Spark’s GUI.

## Runtime and integration

| Who | Surface | Seat |
| --- | --- | --- |
| **eugr** | [spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) | Two-node vLLM packaging, ConnectX/NCCL, launchers |
| **Plot Armor / netrunner** (`@plotarmordev`) | [X](https://x.com/plotarmordev) | Two-Spark DeepSeek/GLM runtime fixes |
| **MiaAI-Lab** (`@MiaAI_lab`) | [GitHub](https://github.com/MiaAI-Lab), [X](https://x.com/MiaAI_lab) | Fast model-specific dual-Spark recipes. Builder/scout, not independent quality proof |
| **0rand** | GitHub + NVIDIA forum | Exact dual-Spark FP8/TP flags and failure notes |

## Weights / kernels (ingredients, not a full appliance)

| Who | Surface | Seat |
| --- | --- | --- |
| **LibertAI** | Hugging Face `LibertAIDAI/*` | Provenance-heavy NVFP4; says what is *not* quantized |
| **Sapid Labs** | Spark Arena repos | Aggressive GB10 compression; experimental |
| **Blake Ledden / Second Nature** | [sm121-kernels](https://github.com/blake-snc/sm121-kernels) | Hand-written SM121 kernels |
| **Stav Katsoulis / veloGB10** | [veloGB10](https://github.com/sf-stav/veloGB10) | Custom GB10 engine, TP=2. Challenger lane |

## Independent measurement (do not let a builder mark their own homework)

| Who | Surface | Seat |
| --- | --- | --- |
| **Mike Gannotti / SMF Works** (`@MichaelGannotti`) | X bakeoffs, strict harness | Same-pair model comparisons |
| **Wäsche** (`@WescheNex1q`) | X | Multi-Spark stress; aggregate vs per-stream |
| **Heitor Mocelin** | [dgx-spark-research](https://github.com/heitor-mocelin/dgx-spark-research) | Reproducible measurement, failed runs |
| **Makoto Watanabe** (`@nabe2030`) | two-node RPC/RDMA repo | TTFT, concurrency traps |
| **PixelML**, **r0b0tlab**, **sfxnz**, **shige0501** | GitHub Vision-Exp recipes | Replication / correctness / conservative control |

## Scouts and hubs

- NVIDIA DGX Spark forum
- Spark Arena (`@spark_arena`)
- 0xSero (`@0xSero`) Local AI Registry — scout, not a pin
- Adam Kerr (`@zero_to_seed`) — real deployment/use-case, not a kernel proof
- David Ondrej / Vectal — strong communicator/scout; not automatically the runtime/weight specialist

## Disqualifiers

- Aggregate tok/s sold as single-user speed
- “1M context” with no TTFT / retrieval / failure rate
- Unpinned `latest` images
- No quality comparison against a less-compressed checkpoint
- Cannot be reproduced on two GB10s

Identity hygiene: there is no verified public `@eugr_nv` for the `eugr` GitHub work. X `@ToNYD2WiLD` is an unrelated entertainment account; GitHub `tonyd2wild` is a different identity. Do not merge them.
