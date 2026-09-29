# Pitfalls

## First-boot

- The Spark powers on when the PSU is connected. Attach network and peripherals first.
- Do not interrupt the factory image download.
- Captive-portal Wi-Fi and phone hotspots fail mid-download.
- Bluetooth-only keyboard/mouse: common failure. Keep wired USB around.
- Some USB-C/DisplayPort monitors need HDMI instead.
- Network-appliance setup: when the Spark joins home Wi-Fi, its hotspot dies. If your laptop does not follow it onto the LAN (mDNS, client isolation, corporate Wi-Fi), you need a display.
- Linux terminal paste on the Spark desktop is `Ctrl+Shift+V`, not `Ctrl+V`.

## Remote access

- Tailscale is not step zero. It needs a working OS, user, sudo, and network.
- Do not port-forward SSH, Jupyter, DGX Dashboard, or vLLM on the router.
- Do not enable Tailscale Funnel for the model API.
- Unenrolling Tailscale from NVIDIA Sync needs a direct LAN path.
- MagicDNS / SSH aliases beat memorized `100.x` addresses.
- Tailscale is the management plane. ConnectX-7 is the model/data plane. Mixing them makes people chase “slow Tailscale” when the model is just slow.

## Two-node

- Do not plug the QSFP cable before each node is independently healthy.
- One cable. Matching ports. Pull-tab up. No switch for two nodes.
- A second parallel cable does not add speed (NVIDIA).
- First speed test after hot-plug can stall around 20–30 Gb/s. Reboot both with the cable left connected before editing system files.
- Cluster Assistant does not install vLLM, NCCL tests, or models. A green cluster is not a working inference service.
- Community ConnectX “delete this file and reboot” posts are last-resort diagnostics. Verify current NVIDIA release notes first.
- Two 128 GB nodes are not 256 GB of one memory pool. Distributed runtimes must partition work.

## Models and Docker

- Do not start with the largest MoE you saw on X.
- Do not `usermod -aG docker` as a convenience. Use a root-owned unit and a narrow CLI.
- Do not `docker pull` an unpinned `latest` and call it a baseline.
- Do not bind `:8000` to `0.0.0.0` on the home LAN.
- Do not store the API key in git, chat, or process arguments. Pipe it or use a keychain.
- GB10 unified memory does not show up like a discrete GPU’s `nvidia-smi` VRAM. Do not panic-tune on that.
- Aggregate tok/s at C64 is not your single-user speed.
- “1M context” without measured TTFT, KV memory, and a retrieval check is a ceiling, not a day-one setting.

## Wrong trees

- AMD Strix Halo / ROCm articles.
- Mac Studio clustering guides applied as if they were GB10.
- Recovery-image flashing as a setup shortcut (destructive).
- Installing a coding agent *on* the Spark as the only operator. The point of this skill is the agent on the computer you already live in.
