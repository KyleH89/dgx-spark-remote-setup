# DGX Command Center

A loopback-only page that answers: are the Sparks up, what model is serving, how hot/fast they are, and whether you need to do anything.

It does **not** replace NVIDIA Sync or DGX Dashboard. It is the nontechnical summary.

Binds `127.0.0.1` only. No public URL. No passwords or API keys in this folder.

## Load it

From this directory:

```bash
cp config.example.json config.json
```

Edit `config.json`:

- `metrics_url` — your Spark’s Tailscale IP plus `:8000/metrics` (the OpenAI-compatible server)
- `nodes.*.ssh` — the SSH aliases from the remote-setup skill (`spark-a`, `spark-b`)
- `model_name` — the `--served-model-name` you actually run
- `desktop_bookmarks` — leave empty unless you have Microsoft Windows App bookmarks for the Spark desktops

Then:

```bash
python3 server.py
```

Open http://127.0.0.1:8792/

SSH must already work without a password. The page runs `ssh spark-a` / `ssh spark-b` collectors. If SSH is not set up, finish the [remote-setup skill](../README.md) first.

## What it stores

`state/history.sqlite3` on the admin computer: aggregate speed and temperature samples. Not prompts, not responses, not keys.

## What it will not do

- Bind to `0.0.0.0`
- Open router ports
- Talk to the public internet
- Ship with someone else’s Tailscale IP or Windows App bookmark IDs
