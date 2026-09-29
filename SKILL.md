---
name: dgx-spark-remote-setup
description: >-
  Set up one or two NVIDIA DGX Sparks from another computer over Tailscale/SSH.
  Use when the user just unboxed DGX Spark(s) and wants Codex, Claude Code,
  Hermes, Grok, or another SKILL.md harness on a laptop/Mac to finish setup
  instead of sitting at the Spark desktop. Covers first-boot order, Tailscale,
  SSH, updates, optional two-node Cluster Assistant, and a first private
  single-node model endpoint. Includes a live expert refresh and a dated
  proven snapshot. Stop for passwords, MFA, Tailscale login, and the QSFP cable.
---

# DGX Spark remote setup

Run this from the computer that will administer the Sparks (laptop or Mac), not from the Spark desktop after first-boot.

This skill does **not** turn two Sparks into one 256 GB machine. It does **not** apply random X/GitHub speed recipes. It does **not** expose APIs to the public internet.

Read `references/human-gates.md` before any SSH. The human still owns first-boot, Tailscale login, passwords, and the QSFP cable.

## When to use

- User just bought one or two DGX Sparks / GB10 boxes and wants a simple remote setup.
- User already has Codex, Claude Code, Hermes, Grok, or similar on another computer.
- User asks to avoid living in the Spark GUI after the factory wizard.

Do not use this skill to:

- jailbreak, expose, or publicly share a model endpoint
- download untrusted weights onto the operator’s daily-driver laptop as the permanent library
- replace NVIDIA first-boot, recovery, or firmware tools
- deploy flagship two-node DeepSeek/GLM/Qwen recipes (see `references/recipe-watchlist.md` only after the first private appliance works)

## Mode

Pick one, then say it out loud to the user:

1. **Snapshot** — follow `references/proven-snapshot-2026-09.md`. Default if the snapshot is ≤14 days old and the user wants the path that already worked.
2. **Refresh, then apply** — run `references/live-refresh.md`, diff against the snapshot, then apply. Default if the snapshot is older than 14 days, NVIDIA just shipped an OS/firmware update, or first-boot UI does not match the snapshot.

NVIDIA docs win over the snapshot when they conflict. The snapshot wins over a forum/X one-liner. A forum/X one-liner is a troubleshooting lead, not a command.

## Prerequisites

On the **admin computer**:

- SSH client
- The user’s existing agent harness, with this skill installed
- NVIDIA Sync (recommended) **or** plain OpenSSH + Tailscale
- Tailscale account the user controls
- Stable home/office network. No captive portal. No phone hotspot.

On each **Spark**, after first-boot:

- Linux user with sudo
- Network
- SSH reachable on the LAN at least once, so Tailscale can be enrolled

Decide before power:

- Same Linux **username** on every Spark
- Unique **hostnames** (`spark-a`, `spark-b`, …)
- Separate strong passwords; do not reuse
- QSFP cable stays **disconnected** until each node works alone

## Procedure

Each step ends with a checkable gate. Do not mark a step done on intent.

### 0. Refresh gate

- If snapshot date in `references/proven-snapshot-2026-09.md` is older than 14 days, or the user asked for latest: run `references/live-refresh.md`.
- Write a short delta: what NVIDIA changed, what experts still agree on, what you will **not** copy from X.
- Gate: user has seen the delta and chosen Snapshot or Refresh-apply.

### 1. Human first-boot (per Spark, one at a time)

Hand `references/human-gates.md` to the user. Do not try to click through first-boot over VNC you have not set up.

Order for two machines: finish and verify Spark A, then Spark B, then cable.

Official current docs (re-check in refresh mode):

- First-boot: https://docs.nvidia.com/dgx/dgx-spark/first-boot.html
- OS/firmware updates: https://docs.nvidia.com/dgx/dgx-spark/os-and-component-update.html
- NVIDIA Sync + Tailscale: https://docs.nvidia.com/sync/latest/tailscale.html
- Cluster Assistant: https://docs.nvidia.com/sync/latest/cluster-assistant.html

Gate: Linux login works locally or via NVIDIA network-appliance setup; hostname and username match the plan; the factory image download was not interrupted.

### 2. Make SSH and Tailscale the remote control plane

From the admin computer:

1. Add the Spark to NVIDIA Sync on the LAN, **or** copy an SSH public key and confirm `ssh user@lan-ip`.
2. Enroll Tailscale (Sync integration or `tailscale up`). The human must approve the browser/auth-key step.
3. Confirm `tailscale status` shows a **direct** peer when possible. MagicDNS name beats memorizing overlay IPs.
4. Put a durable SSH host alias in the admin computer’s SSH config (`Host spark-a`, Tailscale name or IP, user, identity file).
5. Prove SSH from the admin computer **and once from off the home LAN** if the user cares about travel. Do not open router ports. Do not enable Tailscale Funnel.

Gate: `ssh spark-a` (and `ssh spark-b` if present) works without the LAN IP; Tailscale survives a Spark reboot; no public port-forward exists.

### 3. Updates and independent-node health

On each Spark, through the remote shell or DGX Dashboard:

- Apply current DGX OS, driver, and firmware updates. Stable power. Do not interrupt.
- Disable AC-power auto-suspend so an unattended box does not disappear.
- Record hostname, OS/kernel/driver, free disk, GPU visible, failed systemd units = 0.
- Confirm SSH + Tailscale return after reboot.

Gate: both nodes (or the one node) reboot clean, remote SSH still works, pending updates are not blocking, QSFP still unplugged.

### 4. Optional two-node cluster (only if the user has two Sparks and a supported cable)

Do not do this on day one if the user only needs two independent workers.

1. Human plugs **one** supported QSFP112/400GbE DAC between matching ports, pull-tab up. No switch for two nodes. No second parallel cable.
2. Leave the cable connected. If the first speed test is ~20–30 Gb/s or times out, reboot **both** nodes with the cable left in. Do not start editing ConnectX sysfs as a first fix.
3. Run NVIDIA Sync Cluster Assistant. It configures the ConnectX-7 network and inter-node SSH. It does **not** install vLLM, NCCL workloads, or models.
4. Save the generated cluster addresses. Management stays on Tailscale/LAN. Workload traffic stays on the ConnectX network.
5. Assistant lower-bound speed test is 184 Gbit/s. A pass in the mid-180 Gb/s class is good. Record the number.

Gate: Cluster Assistant overall pass; bidirectional SSH over the cluster addresses; Tailscale SSH still works; both RDMA links up after reboot.

### 5. First private model appliance (single node)

Follow `references/first-model-appliance.md`. This is the first useful outcome, not a two-node flagship recipe.

Minimum product:

- Pinned vLLM (or NVIDIA’s current supported serving playbook) on **one** Spark
- A public NVIDIA-published starter checkpoint, pinned by revision
- OpenAI-compatible API bound only to localhost or the Tailscale address
- API key required
- Linux user is **not** in the `docker` group
- Narrow commands only: status / start / stop / restart / logs
- Live completion after a controlled restart

Gate: unauthenticated request is rejected; LAN bind is not public; authenticated completion returns a real string; restart recovers.

### 6. Close-out

Write a local baseline note (not in chat as a password dump):

- hostnames, Tailscale names, SSH aliases
- OS/kernel/driver versions
- cluster yes/no and the speed-test number
- model name, revision, image pin, bind address (no API key)
- what the human still has to do

Gate: user can SSH from the admin computer and get a model response without sitting at the Spark.

## Pitfalls

Read `references/pitfalls.md`. The expensive ones:

- Tailscale cannot precede factory first-boot. It is the first **post-setup** tool.
- Bluetooth-only keyboard during first-boot is fragile. Wired USB is the fallback.
- Do not cluster before each node works alone.
- Do not treat Tailscale as the 200 Gb/s model data plane.
- Do not paste `Ctrl+V` into a Linux terminal; it is `Ctrl+Shift+V` on the Spark desktop if you must.
- Hot-plug QSFP then immediately chasing sysctl/modprobe “fixes” from X is how people brick a day. Reboot with cable connected first.
- Aggregate tok/s across many users is not single-user speed. Ignore that class of claim during setup.
- Two Sparks ≠ 256 GB unified memory.

## Verification

A setup is done only if all of these are true:

1. `ssh <alias>` from the admin computer works after a Spark reboot.
2. No SSH, dashboard, Jupyter, or model port is forwarded on the router or via Tailscale Funnel.
3. If clustered: Cluster Assistant (or equivalent) recorded a ≥184 Gb/s-class pass, or an evidence-backed blocker is written down.
4. If a model was requested: authenticated completion works; unauthenticated fails; restart recovers.
5. No password, API key, or auth cookie was written to git, chat, or a world-readable file.

## Source rules

- Setup experts: `references/setup-experts.md`
- Recipe people (later, not day one): `references/recipe-watchlist.md`
- Live search queries: `references/live-refresh.md`
