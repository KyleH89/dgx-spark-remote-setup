# DGX Spark remote setup

A skill you install on the coding agent you already use — Codex, Claude Code, Hermes, Grok, or anything that reads `SKILL.md` — so the agent can set up one or two [NVIDIA DGX Sparks](https://www.nvidia.com/en-us/products/workstations/dgx-spark/) from another computer.

You still do a short physical first-boot on each box. After Tailscale and SSH work, you should not have to sit at the Spark desktop installing models.

## What this is

Two layers, on purpose:

1. **Live refresh.** The agent re-reads current NVIDIA docs and a small roster of people who have actually unboxed Sparks, then diffs that against the snapshot. Use this when the snapshot is more than two weeks old, or when NVIDIA just shipped an OS/firmware update.
2. **Dated snapshot.** A proven order that worked on **2026-09-01 / 2026-09-02** for two Founders-class GB10 Sparks administered from a Mac. Use this when you want the path that already survived first-boot, Tailscale, a QSFP cluster, and a first private model endpoint.

The snapshot is not a claim that nothing better exists today. It is a claim that this order finished without leaving the owner at the Spark keyboard.

## What you still have to do yourself

The agent must stop and hand these back to you:

- Plug in power, network, and (if you use it) a wired keyboard/mouse/display **before** applying power. The Spark starts when power is applied.
- Complete NVIDIA first-boot (Linux user, network, image download). Do not interrupt the download.
- Approve Tailscale on each Spark (browser/auth-key login).
- Type Linux passwords, sudo, Touch ID, Apple ID, and any MFA.
- Plug the one QSFP cable between two Sparks, matching ports, pull-tab up. Do this only after each node works alone.
- Decide the Linux username (same on both nodes) and hostnames (unique).

Everything after that — SSH keys, NVIDIA Sync, updates, cluster assistant, a first private model API — can run from the laptop.

## Install

Clone this repo, then install into the harness you already use:

```bash
git clone https://github.com/KyleH89/dgx-spark-remote-setup.git
cd dgx-spark-remote-setup
zsh installers/install-all.sh
```

Or pick one:

```bash
zsh installers/install-codex.sh
zsh installers/install-claude.sh
zsh installers/install-hermes.sh
zsh installers/install-grok.sh
```

Then, on the computer that will administer the Sparks, tell the agent:

> Load the `dgx-spark-remote-setup` skill. I just unboxed DGX Spark(s). Use the proven snapshot unless NVIDIA docs have changed. Do not sit me at the Spark desktop after first-boot. Stop for passwords, Tailscale login, and the QSFP cable.

## What the snapshot actually proved

Not marketing. These are the gates that passed on the original pair:

| Date | Gate |
| --- | --- |
| 2026-09-01 | Each Spark completed first-boot, updates, Tailscale, and passwordless SSH from a Mac |
| 2026-09-01 | One QSFP cable + NVIDIA Sync Cluster Assistant: **185.18 Gb/s** aggregate, **1.7 µs** latency after a reboot with the cable left connected |
| 2026-09-02 | First private model appliance on one node: `nvidia/Qwen3.6-35B-A3B-NVFP4` on pinned vLLM 0.28.0, Tailscale-only, API-key required, restart-tested |

Two Sparks are still two 128 GB machines. They are not one 256 GB computer. Cluster mode is optional. The first useful model should be a single-node appliance.

After SSH works, you can load a loopback-only fleet page from [`command-center/`](command-center/README.md): copy `config.example.json` to `config.json`, set your Tailscale metrics URL and SSH aliases, run `python3 server.py`, open `http://127.0.0.1:8792/`.

Flagship two-node recipes (DeepSeek, GLM, Qwen3.8, custom kernels) are a later job. This skill gets you remote, private, and serving something real. The follow-on watchlist of recipe people lives in `references/recipe-watchlist.md`.

## Safety

See `SECURITY.md`.

- No telemetry. The installers only copy markdown onto your machine.
- The skill tells an agent to SSH into **your** Sparks. Read `SKILL.md` before you run it.
- Do not expose SSH, Jupyter, dashboards, or model APIs to the public internet. No Tailscale Funnel. No router port-forward.
- Do not add your Linux user to the Docker group.
- Do not paste Linux passwords into chat, git, or shell history.
- Community one-liners from X are discovery, not commands. NVIDIA docs win when they conflict with the snapshot. The snapshot wins over a random GitHub README.

## Credit

The remote-first order was compiled from:

- NVIDIA first-boot, NVIDIA Sync Tailscale, Cluster Assistant, and DGX OS update docs
- [Vectal Labs, “What I wish I knew before setting up 2 DGX Sparks”](https://x.com/vectal_labs/status/2092212858478043228) (2026-08-25)
- Field reports from [Aoyama Life](https://x.com/aoyamalife/status/2092818676592615761), [BOOTOSHI](https://x.com/KingBootoshi/status/2087436692588544172), and [Tony Kipkemboi](https://x.com/tonykipkemboi/status/2093942251038666917)

Those people are not responsible for this skill. The snapshot is one operator’s pair, not NVIDIA support.

## License

MIT. See `LICENSE`.
