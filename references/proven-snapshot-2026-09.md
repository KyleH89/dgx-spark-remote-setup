# Proven snapshot — 2026-09-01 / 2026-09-02

**Cutoff:** 2026-09-02  
**Hardware:** two NVIDIA DGX Spark / GB10, 128 GB unified memory each, ~4 TB NVMe  
**Admin computer:** Mac, Codex as the remote operator after SSH existed  
**Status:** this order finished. It is not a promise that every later DGX OS build looks identical.

If today is more than 14 days after this cutoff, run `live-refresh.md` first.

## Software that was live after updates (both nodes)

| Item | Value |
| --- | --- |
| OS | Ubuntu 24.04.4 LTS |
| DGX OTA | 7.5.0 |
| Kernel | `6.17.0-1031-nvidia` |
| NVIDIA driver | `580.173.02` |
| NVIDIA Sync (macOS) | 0.100.19-18 |

Re-read current NVIDIA release notes before copying these version numbers forward. They are evidence, not a pin you must force.

## Order that worked

1. **Factory first-boot on Spark A only.** Wired network/peripherals before power. Same planned Linux username. Unique hostname. Do not interrupt the image download.
2. **LAN SSH, then Tailscale, then NVIDIA Sync** on Spark A. Passwordless SSH from the Mac using a key. Tailscale name distinct from the Linux hostname is fine; put the Tailscale name in SSH config.
3. **Updates through DGX Dashboard.** Reboot. Confirm Tailscale SSH still works. Zero failed systemd units. Disable AC-power auto-suspend.
4. **Repeat 1–3 on Spark B.** Same username, different hostname. Still no QSFP cable. Still no models.
5. **Independent-node gate.** Both boxes reboot clean, remote SSH works, disk and thermals healthy, no public port-forward.
6. **One QSFP cable**, matching top ports, pull-tab up. Leave it connected.
7. **NVIDIA Sync Cluster Assistant.** It builds the ConnectX-7 netplan, cluster addresses, and bidirectional inter-node SSH. It does not install a model runtime.
8. **Speed test.** First hot-plug attempt stalled near **26.5 Gb/s** and timed out (ConnectX-7 not fully up). Coordinated reboot **with the cable left connected** then passed:
   - aggregate **185.18 Gb/s**
   - **1.7 µs** latency
   - NVIDIA’s 184 Gbit/s lower bound: pass
9. **Do not install models during base setup.** Prove remote ops and the cable first.
10. **First private appliance on one node only** (2026-09-02): `nvidia/Qwen3.6-35B-A3B-NVFP4` served by pinned vLLM **0.28.0**, OpenAI-compatible API, Tailscale bind only, API key required, user not in `docker` group, `status/start/stop/restart/logs` wrapper, live completion after restart.

## Operating model that stayed sane

- **Default:** two independent 128 GB workers. Tailscale = management. ConnectX = Spark-to-Spark data.
- **Cluster:** only for jobs that actually need two nodes.
- **Not true:** “two Sparks = 256 GB one GPU.”

## Security choices that were deliberate

- No router port-forward, no Tailscale Funnel.
- Model API not bound to the ordinary LAN IP.
- Linux user kept out of the Docker group. Routine controls were a narrow root-owned wrapper, not `sudo docker` for everything.
- Passwords rotated during setup and never stored in the project git.
- SSH password auth was left on until Cluster Assistant finished (it needed username/password + sudo once). Tighten later if you want key-only.

## What this snapshot does *not* include

- Two-node DeepSeek / GLM / Qwen3.8 serving
- Custom SM121 kernels
- Community NVFP4 derivatives as the first model
- Remote-desktop polish (nice later; not required to serve a model)

Those are recipe work. See `recipe-watchlist.md` after the first appliance responds.

## Sources that produced this order

Compiled 2026-08-31 from NVIDIA docs plus practitioner posts, then executed 2026-09-01 and 2026-09-02. Primary practitioner match: Vectal Labs, 2026-08-25, “What I wish I knew before setting up 2 DGX Sparks.” Corroboration: Aoyama Life (agent CLI + Tailscale + SSH, host agent finishes), BOOTOSHI (Codex + Tailscale), Tony Kipkemboi (Tailscale remote access). Official first-boot, Sync Tailscale, Cluster Assistant, and OS-update docs overruled any community step that contradicted them.
