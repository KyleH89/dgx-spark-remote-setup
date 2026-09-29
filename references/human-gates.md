# Human-only gates

The agent cannot complete these. Stop, name the exact click or cable, and wait.

## Before power

1. Place each Spark with unobstructed ventilation. Use the supplied power supply.
2. Attach **network and peripherals before power**. The Spark starts when power is applied.
3. Prefer Ethernet. Avoid captive portals and phone hotspots.
4. Have a wired USB keyboard, mouse, and a display or USB-C hub as fallback. Bluetooth-only input is a common first-boot failure.
5. Keep the QSFP / ConnectX cable **unplugged** until each node has Tailscale + SSH + updates.
6. Write down:
   - Linux username (same on every Spark)
   - unique hostnames
   - separate strong passwords (do not reuse, do not put them in chat)

## First-boot

Official guide: https://docs.nvidia.com/dgx/dgx-spark/first-boot.html

Two supported ways:

- **Local display:** wizard on a monitor.
- **Network appliance:** Spark raises a setup Wi-Fi hotspot; SSID/password are on the Quick Start sticker. After it joins your LAN, the hotspot goes away.

During first-boot the box downloads the software image and may reboot more than once. **Do not power off after the download starts.**

Create the Linux user here. This is the account the agent will SSH as.

If LAN discovery/mDNS fails, plug in the wired display and continue. Do not invent a recovery flash unless NVIDIA’s current recovery doc says so, and never flash recovery as a setup shortcut (it erases the SSD).

## Tailscale approval

Either:

- NVIDIA Sync → Settings → Tailscale → Enable, then **Add Device** with a Tailscale auth key, or
- SSH in on the LAN and run `sudo tailscale up`, then approve the URL in a browser.

The human must complete the Tailscale login. The agent must not paste auth keys into chat logs.

Unenrollment later requires a **direct** LAN connection, not Tailscale. Keep LAN access as a fallback.

## Passwords, MFA, Touch ID

The agent may prompt a native OS password dialog on the admin computer. It must not:

- echo the password
- store it in git, chat, `.env` committed to a repo, or shell history
- enable passwordless root SSH
- add the user to the `docker` group

NVIDIA Sync Cluster Assistant will ask for sudo once; it keeps the password in memory for that session only.

## QSFP cable (two Sparks only)

Do this only after **both** nodes independently survive reboot + Tailscale SSH.

- One supported QSFP112 / 400GbE DAC between matching ports.
- Pull-tab up.
- No switch for two nodes.
- No second cable in parallel. NVIDIA says it does not help.
- Leave it connected through reboots.

If the first Cluster Assistant speed test hangs near ~26 Gb/s: reboot both nodes with the cable left in, then retest. Do not start community sysfs workarounds on day one.

## What you can leave to the agent

Once `ssh spark-a` works from the admin computer:

- OS/driver updates via documented paths
- SSH config aliases
- Cluster Assistant clicks you approve on the Mac (or the documented CLI equivalent)
- First private model appliance
- Recording versions, hashes, and a baseline note
