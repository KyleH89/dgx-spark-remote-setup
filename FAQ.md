# FAQ — questions owners actually get stuck on

These are paraphrases of public NVIDIA forum threads, NVIDIA playbooks, and X field reports — not invented pain. Short answers only. Official docs still win.

## First-boot looks frozen. Did I brick it?

Usually no. First-boot downloads the image and may apply firmware. The box can sit there, reboot more than once, and look dead. Plug HDMI + a wired keyboard, leave power on, do not interrupt. Forum thread: [DGX Setup Support / First Boot Help](https://forums.developer.nvidia.com/t/dgx-setup-support-first-boot-help/368734). Official: [First boot](https://docs.nvidia.com/dgx/dgx-spark/first-boot.html).

## Can I use it from a coffee shop / hotel / phone?

Yes, if Tailscale is on the Spark and on the laptop (same account). Do not port-forward SSH or the model API on the router. NVIDIA playbook: [Set up Tailscale](https://build.nvidia.com/spark/tailscale/instructions). Forum: [Remote access over non-local network](https://forums.developer.nvidia.com/t/remote-access-over-non-local-network/363051). People who skip this notice it the first time they leave the house.

## Setup finished and I cannot SSH. I never got a password.

Write the Linux password down during first-boot. If the account was never created, NVIDIA’s recovery path may be the only fix, and recovery is destructive. Forum: [cannot access via SSH, no password](https://forums.developer.nvidia.com/t/dgx-spark-initial-setup-is-finished-but-i-cannot-access-the-dgx-via-ssh-as-i-don-not-have-the-password/360231). On a Mac, also check System Settings → Local Network permission for your terminal app ([FAQ](https://forums.developer.nvidia.com/t/dgx-spark-gb10-faq/347344)).

## Are two Sparks one 256 GB computer?

No. Each Spark is 128 GB unified memory. A QSFP cable lets distributed software **split** a job. It does not glue the memory into one GPU. Default: two independent workers. Cluster only for models that truly need two nodes. Forum owners ask this as “federated vs cluster.”

## Cluster Assistant passed. Is the big model running?

No. Cluster Assistant configures the ConnectX-7 network and inter-node SSH. It does not install vLLM or a model. A ~185 Gb/s pass means the cable is healthy.

The first speed test after plugging the cable can stall around 20–30 Gb/s. Reboot **both** boxes with the cable left in before editing system files.

## Which dashboard should I open?

| Tool | What it is |
| --- | --- |
| NVIDIA Sync | Add devices, Tailscale integration, Cluster Assistant, official resource monitor |
| DGX Dashboard on each Spark | Updates, Jupyter, NVIDIA’s own telemetry |
| Command Center in this repo | Nontechnical localhost page: up/down, what is serving, heat, speed |

The Command Center does not replace NVIDIA’s tools. Load it after SSH works: [command-center/README.md](command-center/README.md).

## Should I install Codex / Claude on the Spark itself?

You can. A lot of playbooks do. The path this repo encodes is the other way: finish first-boot + Tailscale, then let the agent **on the computer you already live in** SSH over. That is what Vectal Labs, Aoyama Life, and BOOTOSHI described, and what this snapshot used.

## Should I start with DeepSeek on two nodes?

Not on day one. Get a private single-node API answering first (the snapshot used a NVIDIA-published Qwen NVFP4 on one box). Flagship two-node recipes are a later job, and community tok/s numbers often mix **one-user decode** with **aggregate** speed across many users.

## How long does this take?

Public posts range from “Tailscale in 15–30 minutes” to “a few days / a couple of weeks” to get a real workflow. First-boot + Tailscale is hours if the download is left alone. The rest is the agent on the laptop, if SSH exists.

## Do I add my Linux user to the docker group?

No. Use a root-owned service and five words: status, start, stop, restart, logs.
