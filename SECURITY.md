# Security

This repository is markdown plus copy-only installers. The installers do not execute remote commands. They copy `SKILL.md` and `references/` into a local harness skills folder.

## What the skill asks an agent to do

After you load it, the agent may SSH into **your** DGX Sparks and change **your** machines: SSH config, Tailscale enrollment (with your approval), updates, NVIDIA Sync Cluster Assistant, firewall rules, and a private model service.

That is L2/L3 on hardware you own. It is not a license to touch anyone else’s box.

## Review before first run

- Read `SKILL.md` and `references/human-gates.md`.
- Confirm the agent will stop for passwords, MFA, Tailscale login, and the QSFP cable.
- Confirm it will not enable Tailscale Funnel or router port-forwarding.
- Confirm it will not add your Linux user to the `docker` group.
- Confirm it will not write passwords or API keys to git or chat.

## What this repo must never contain

- Passwords, sudo, Tailscale auth keys, API keys
- Operator overlay IPs, home LAN addresses, serial numbers
- Private X/DMs, mailbox content, or unpublished weights

If you fork this and add a personal baseline, keep that baseline out of the public tree.

## Updates

Do not enable auto-update from an unreviewed fork. Treat every upstream change as a new review.
