# Live refresh

Run this when the snapshot is older than 14 days, NVIDIA shipped an OS/firmware update, or first-boot UI does not match `proven-snapshot-2026-09.md`.

This is **research**. It must not download weights, flash recovery, expose ports, or apply a community kernel workaround.

## Output

A short delta the user can accept or reject:

1. NVIDIA docs that changed (link + what it changes in the order)
2. Setup-expert posts newer than the snapshot (link + paraphrase + evidence lane)
3. What you will keep from the snapshot
4. What you will **not** copy from X
5. Recommendation: Snapshot as-is / Snapshot with N doc substitutions / Hold

## Official lane (required)

Fetch, do not assume:

- https://docs.nvidia.com/dgx/dgx-spark/first-boot.html
- https://docs.nvidia.com/dgx/dgx-spark/os-and-component-update.html
- https://docs.nvidia.com/dgx/dgx-spark/release-notes.html
- https://docs.nvidia.com/dgx/dgx-spark/known-issues.html
- https://docs.nvidia.com/sync/latest/tailscale.html
- https://docs.nvidia.com/sync/latest/cluster-assistant.html
- https://docs.nvidia.com/dgx/dgx-spark/spark-clustering.html
- https://build.nvidia.com/spark

Record the page’s last-updated date if shown. If first-boot now prefers network-appliance vs local display, follow NVIDIA, not the snapshot’s hardware fallback story.

## Setup-expert lane

Search public X / the web (not DMs) for the last 21 days:

```
DGX Spark first boot Tailscale
DGX Spark NVIDIA Sync Cluster Assistant
from:vectal_labs DGX Spark
from:aoyamalife DGX Spark
from:KingBootoshi (DGX OR Spark) (Tailscale OR Codex)
from:tonykipkemboi DGX Spark Tailscale
site:forums.developer.nvidia.com DGX Spark first boot
site:forums.developer.nvidia.com Cluster Assistant QSFP
```

Also open the current NVIDIA Spark forum category:
https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719

Keep only posts about **setup, Tailscale, SSH, Sync, clustering, updates, first-boot regressions**. Discard tok/s leaderboard posts; those belong to `recipe-watchlist.md`.

## Rules of evidence

- NVIDIA doc change → update the order.
- Two independent firsthand setup reports agreeing, and no NVIDIA contradiction → optional note in the delta.
- One self-report of a sysctl/modprobe “fix” → troubleshooting lead only. Do not apply on a healthy first-boot.
- ConnectX ports missing after hot-plug → try reboot with cable connected (snapshot lesson) before any community file edit.
- Do not follow AMD/ROCm, Windows, or Mac-Studio-as-if-it-were-GB10 instructions.

## Stop conditions

Stop the refresh and apply nothing if:

- you cannot fetch NVIDIA first-boot
- the only “new method” is an unaudited bash pipe from a random gist
- the user has not accepted the delta

Then fall back to the snapshot plus NVIDIA docs you *did* fetch.
