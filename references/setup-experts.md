# Setup experts (day-one remote control)

This roster is for **unboxing, Tailscale, SSH, and clustering**. It is not the recipe/tuner bench.

Last reviewed: 2026-09-04. Re-verify handles and URLs during a live refresh. Do not invent a person from a similar handle.

## Primary, in the order to trust them

| Who | Why they matter for setup | How to use |
| --- | --- | --- |
| **NVIDIA DGX Spark docs** | First-boot, updates, NVIDIA Sync, Cluster Assistant, known issues | Source of truth. If a tweet disagrees, keep the tweet as a troubleshooting lead only. |
| **Vectal Labs** (`@vectal_labs`) | [What I wish I knew before setting up 2 DGX Sparks](https://x.com/vectal_labs/status/2092212858478043228) (2026-08-25). Tailscale while physically at each box, then work from the laptop. Wired keyboard/mouse. Same Linux username. QSFP after both nodes are alive. Keep the API private. | Strongest firsthand “don’t live at the desktop” writeup found in the original research. |
| **Aoyama Life** (`@aoyamalife`) | [Aug 26 report](https://x.com/aoyamalife/status/2092818676592615761): install an agent CLI, Tailscale, SSH, let the host-side agent finish. Under an hour after a ~20-minute first-boot update. | Confirms the remote-agent pattern. Still needs model cookbooks later. |
| **BOOTOSHI** (`@KingBootoshi`) | [Codex one-shot + Tailscale](https://x.com/KingBootoshi/status/2087436692588544172); [remote SSH while traveling](https://x.com/KingBootoshi/status/2093354078709404137) | Confirms Codex-from-elsewhere, not “install everything in the Spark GUI.” |
| **Tony Kipkemboi** (`@tonykipkemboi`) | [Tailscale for remote DGX Spark access](https://x.com/tonykipkemboi/status/2093942251038666917) | Short confirmation of the management plane. |

## Useful, but not first-boot gospel

| Who | Why | Limit |
| --- | --- | --- |
| **AI少年** (`@aehyok`) | Agent-over-SSH can do most deploy work | Model-specific kernels still break agents. Do not expect the setup skill to solve every runtime. |
| **jvr0x** (`@jvr0x`) | Two-Spark NFS over the direct link | Later optimization. Not day one. Automount must not hang boot if the peer is down. |
| **Mike Gannotti** (`@MichaelGannotti`) | Two-node serving is operationally fragile | Treat as a warning, not a first-boot sequence. |
| **eugr** | `spark-vllm-docker`, NVIDIA Spark team (forum-announced May 2026) | Runtime/packaging after SSH exists. GitHub + NVIDIA forum; do not assume an X handle. |
| **NVIDIA DGX Spark forum** | Regressions, exact flags, new Sync/OS issues | Self-reported until you reproduce. |

## Do not mix these into first-boot

- AMD Strix Halo / ROCm writeups. Wrong vendor stack.
- “Ollama is one terminal command” posts. Fine as a later app; they skip networking, Tailscale, and two-node reality.
- Recipe tuners (MiaAI-Lab, Plot Armor, Sapid Labs, LibertAI, veloGB10, etc.). Follow them **after** the box is remote. See `recipe-watchlist.md`.

## Attribution rules

- Store URL, author, date, and a one-line paraphrase for every claim you act on.
- Label evidence: `official`, `primary_repo`, `independent_reproduction`, `self_report`, `forum`, `discovery_only`.
- A protected or unverified lookalike handle is not an expert. Skip it.
- Do not quote private X, DMs, or authenticated-only pages into a public baseline note.
