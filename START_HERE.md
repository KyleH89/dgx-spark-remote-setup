# Start here (you do not need to be a Linux person)

This repo is for someone who just bought one or two NVIDIA DGX Sparks and does not want to live at the Spark keyboard.

NVIDIA already has first-boot, Tailscale, and Cluster Assistant docs. This does not replace them. It is the order a non-expert actually finished, plus a skill you drop into Codex / Claude / Hermes / Grok on the computer you already use.

## The only physical work

Do these yourself. An agent cannot.

1. Plug in **network and a wired keyboard/mouse/display before power**. The Spark starts when power is applied.
2. Finish NVIDIA first-boot. Create the Linux user. **Write the password down.** Do not interrupt the image download. If the box looks dead, it is often still updating — HDMI and wait.
3. Log into Tailscale on each Spark (browser approval).
4. If you have two Sparks: after **each** one works alone, plug **one** QSFP cable, matching ports, pull-tab up.

Same Linux username on both boxes. Different hostnames.

## Then leave the desktop

On your Mac or laptop, install the skill and tell your existing agent:

> Load `dgx-spark-remote-setup`. I just unboxed DGX Spark(s). Use the proven snapshot unless NVIDIA docs have changed. Stop for passwords, Tailscale login, and the QSFP cable.

```bash
git clone https://github.com/KyleH89/dgx-spark-remote-setup.git
cd dgx-spark-remote-setup
zsh installers/install-all.sh
```

When SSH works, you can load the loopback fleet page:

```bash
cd command-center
cp config.example.json config.json
# put your Tailscale metrics URL and SSH aliases in config.json
python3 server.py
```

Open http://127.0.0.1:8792/ — localhost only.

## What “done” means

- You can SSH from the laptop after a Spark reboot, including away from home, **without** opening router ports.
- If you asked for a model: a private API answers with a key and refuses without one.
- Two Sparks are still two 128 GB machines. A green cluster test is the cable, not DeepSeek.

Questions people actually get stuck on: [FAQ.md](FAQ.md).  
The dated order that already worked: [references/proven-snapshot-2026-09.md](references/proven-snapshot-2026-09.md).
