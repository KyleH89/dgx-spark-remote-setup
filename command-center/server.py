#!/usr/bin/env python3
"""Loopback-only executive dashboard for one or two NVIDIA DGX Sparks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlparse
import urllib.error
import urllib.request


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STATE_DIR = APP_DIR / "state"
DATABASE = STATE_DIR / "history.sqlite3"
PORTFOLIO_FILE = STATE_DIR / "portfolio.json"
CONFIG_FILE = APP_DIR / "config.json"
EXAMPLE_CONFIG_FILE = APP_DIR / "config.example.json"


def load_config() -> dict:
    path = CONFIG_FILE if CONFIG_FILE.exists() else EXAMPLE_CONFIG_FILE
    if not path.exists():
        raise SystemExit(
            "Missing command-center/config.json. Copy config.example.json and set your SSH aliases and metrics URL."
        )
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


_CFG = load_config()
HOST = str(_CFG.get("host", "127.0.0.1"))
PORT = int(_CFG.get("port", 8792))

MODEL_METRICS_URL = str(_CFG["metrics_url"])
MODEL_NAME = str(_CFG.get("model_name", "local-model"))
MODEL_REFERENCE_TPS = float(_CFG.get("model_reference_tps", 18.251))
MODEL_REFERENCE_SOURCE = str(
    _CFG.get("model_reference_source", "Replace with your measured or published baseline")
)
MODEL_SAMPLE_INTERVAL_SECONDS = 60
MODEL_SAMPLE_RETENTION_DAYS = 30
MODEL_METRICS_TIMEOUT_SECONDS = 8
MODEL_SAMPLE_LOCK = threading.Lock()
FLEET_SAMPLE_RETENTION_DAYS = 30
# GB10 / DGX Spark community bands, not a datacenter GPU datasheet.
# Green <75: normal sustained inference (conselara: 60–75°C).
# Yellow 75–84: watch; SW slowdown reported near ~83°C under sustained load.
# Red >=85: danger / shutdown territory on Spark chassis (wildpines and NVIDIA forum).
THERMAL_YELLOW_C = 75
THERMAL_RED_C = 85

PROMETHEUS_LINE = re.compile(
    r"^(?P<name>[A-Za-z_:][A-Za-z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|[-+]?Inf|NaN)$"
)
PROMETHEUS_LABEL = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)="((?:\\.|[^"\\])*)"')

WINDOWS_APP = Path("/Applications/Windows App.app")
WINDOWS_APP_BINARY = WINDOWS_APP / "Contents/MacOS/Windows App"
DESKTOP_BOOKMARKS = {
    str(key): str(value)
    for key, value in dict(_CFG.get("desktop_bookmarks") or {}).items()
    if value
}

NODES = {
    str(key): {
        "name": str(node.get("name", key)),
        "ssh": str(node["ssh"]),
        "role": str(node.get("role", "")),
    }
    for key, node in dict(_CFG["nodes"]).items()
}
DASHBOARD_LINKS = dict(_CFG.get("dashboard_links") or {})

REMOTE_SNAPSHOT = r"""
set -u
printf 'hostname='; hostname
printf 'uptime_seconds='; cut -d. -f1 /proc/uptime
printf 'memory_total_kib='; awk '/^MemTotal:/ {print $2}' /proc/meminfo
printf 'memory_available_kib='; awk '/^MemAvailable:/ {print $2}' /proc/meminfo
printf 'disk_total_kib='; df -Pk /srv 2>/dev/null | awk 'NR==2 {print $2}' || df -Pk / | awk 'NR==2 {print $2}'
printf 'disk_available_kib='; df -Pk /srv 2>/dev/null | awk 'NR==2 {print $4}' || df -Pk / | awk 'NR==2 {print $4}'
printf 'cluster_link='; ip -br link show enp1s0f0np0 2>/dev/null | awk '{print $2}' || true
printf 'tailscale_ip='; tailscale ip -4 2>/dev/null | head -1 || true
for service in dgx-model.service dgx-deepseek-head.service dgx-deepseek-worker.service dgx-qwen38-head.service dgx-qwen38-worker.service dgx-glm53-head.service dgx-glm53-worker.service; do
  printf 'service_%s=' "${service%.service}"
  systemctl is-active "${service}" 2>/dev/null || true
done
if systemctl is-active --quiet dgx-deepseek-head.service; then
  printf 'deepseek_ready='
  if sudo -n /usr/local/libexec/dgx-deepseek-health >/dev/null 2>&1; then echo yes; else echo no; fi
fi
if command -v nvidia-smi >/dev/null 2>&1; then
  printf 'gpu='; nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,power.draw,clocks_event_reasons.sw_thermal_slowdown,clocks_event_reasons.hw_thermal_slowdown --format=csv,noheader,nounits 2>/dev/null | head -1 || true
fi
""".strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_database() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fleet_samples (
                observed_at TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS model_metric_samples (
                observed_at TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )


def parse_prometheus(text: str) -> list[tuple[str, dict[str, str], float]]:
    """Parse the numeric subset of Prometheus exposition used by vLLM."""
    samples: list[tuple[str, dict[str, str], float]] = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        match = PROMETHEUS_LINE.match(line.strip())
        if not match:
            continue
        try:
            value = float(match.group("value"))
        except ValueError:
            continue
        labels = {
            label.group(1): bytes(label.group(2), "utf-8").decode("unicode_escape")
            for label in PROMETHEUS_LABEL.finditer(match.group("labels") or "")
        }
        samples.append((match.group("name"), labels, value))
    return samples


def prometheus_value(
    samples: list[tuple[str, dict[str, str], float]],
    name: str,
    labels: dict[str, str] | None = None,
    *,
    aggregate: bool = False,
) -> float | None:
    matches = [
        value
        for metric_name, metric_labels, value in samples
        if metric_name == name
        and all(metric_labels.get(key) == expected for key, expected in (labels or {}).items())
    ]
    if not matches:
        return None
    return sum(matches) if aggregate else matches[0]


def collect_model_metrics() -> dict[str, object]:
    request = urllib.request.Request(
        MODEL_METRICS_URL,
        headers={"Accept": "text/plain", "User-Agent": "DGX-Command-Center/1"},
    )
    with urllib.request.urlopen(request, timeout=MODEL_METRICS_TIMEOUT_SECONDS) as response:
        samples = parse_prometheus(response.read().decode("utf-8", errors="replace"))

    model = {"model_name": MODEL_NAME}
    stopped = {**model, "finished_reason": "stop"}
    length = {**model, "finished_reason": "length"}
    aborted = {**model, "finished_reason": "abort"}
    errored = {**model, "finished_reason": "error"}
    repeated = {**model, "finished_reason": "repetition"}

    def value(name: str, labels: dict[str, str] | None = None, *, aggregate: bool = False) -> float:
        result = prometheus_value(samples, name, labels or model, aggregate=aggregate)
        return float(result or 0.0)

    completed = sum(
        value("vllm:request_success_total", labels)
        for labels in (stopped, length, aborted, errored, repeated)
    )
    return {
        "observed_at": utc_now(),
        "source": "vLLM /metrics on Spark A",
        "model": MODEL_NAME,
        "engine_started_at": value("vllm:generation_tokens_created"),
        "generation_tokens_total": value("vllm:generation_tokens_total"),
        "prompt_tokens_total": value("vllm:prompt_tokens_total"),
        "completed_requests_total": completed,
        "stopped_requests_total": value("vllm:request_success_total", stopped),
        "length_requests_total": value("vllm:request_success_total", length),
        "aborted_requests_total": value("vllm:request_success_total", aborted),
        "error_requests_total": value("vllm:request_success_total", errored),
        "repetition_requests_total": value("vllm:request_success_total", repeated),
        "preemptions_total": value("vllm:num_preemptions_total"),
        "time_per_output_token_sum": value("vllm:request_time_per_output_token_seconds_sum"),
        "time_per_output_token_count": value("vllm:request_time_per_output_token_seconds_count"),
        "time_to_first_token_sum": value("vllm:time_to_first_token_seconds_sum"),
        "time_to_first_token_count": value("vllm:time_to_first_token_seconds_count"),
        "e2e_latency_sum": value("vllm:e2e_request_latency_seconds_sum"),
        "e2e_latency_count": value("vllm:e2e_request_latency_seconds_count"),
        "queue_time_sum": value("vllm:request_queue_time_seconds_sum"),
        "queue_time_count": value("vllm:request_queue_time_seconds_count"),
        "prefix_cache_queries_total": value("vllm:prefix_cache_queries_total"),
        "prefix_cache_hits_total": value("vllm:prefix_cache_hits_total"),
        "requests_running": value("vllm:num_requests_running"),
        "requests_waiting": value("vllm:num_requests_waiting"),
        "kv_cache_usage_percent": round(value("vllm:kv_cache_usage_perc") * 100, 1),
    }


def store_model_metrics(sample: dict[str, object]) -> None:
    boundary = datetime.fromtimestamp(
        time.time() - MODEL_SAMPLE_RETENTION_DAYS * 86400, timezone.utc
    ).isoformat(timespec="seconds")
    with sqlite3.connect(DATABASE, timeout=10) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO model_metric_samples(observed_at, payload) VALUES (?, ?)",
            (sample["observed_at"], json.dumps(sample, separators=(",", ":"))),
        )
        connection.execute("DELETE FROM model_metric_samples WHERE observed_at < ?", (boundary,))


def sample_model_metrics() -> dict[str, object] | None:
    if not MODEL_SAMPLE_LOCK.acquire(blocking=False):
        return None
    try:
        sample = collect_model_metrics()
        store_model_metrics(sample)
        return sample
    except (OSError, urllib.error.URLError, ValueError, sqlite3.Error) as error:
        print(f"Model metrics unavailable: {type(error).__name__}: {error}")
        return None
    finally:
        MODEL_SAMPLE_LOCK.release()


def model_metric_history(hours: int) -> list[dict[str, object]]:
    hours = min(max(hours, 1), MODEL_SAMPLE_RETENTION_DAYS * 24)
    boundary = datetime.fromtimestamp(time.time() - hours * 3600, timezone.utc).isoformat(
        timespec="seconds"
    )
    with sqlite3.connect(DATABASE, timeout=10) as connection:
        rows = connection.execute(
            "SELECT payload FROM model_metric_samples WHERE observed_at >= ? ORDER BY observed_at ASC",
            (boundary,),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def counter_delta(current: dict[str, object], previous: dict[str, object], key: str) -> float | None:
    try:
        delta = float(current[key]) - float(previous[key])
    except (KeyError, TypeError, ValueError):
        return None
    return delta if delta >= 0 else None


def performance_status(tokens_per_second: float | None) -> tuple[str, str]:
    if tokens_per_second is None:
        return "learning", "Waiting for enough completed local requests to establish a trend."
    ratio = tokens_per_second / MODEL_REFERENCE_TPS
    if ratio >= 0.8:
        return "healthy", "Decode speed is within the normal range for this exact two-Spark build."
    if ratio >= 0.6:
        return "warning", (
            "Recent live traffic is below the conservative published reference band. "
            "Prompt and response shape can explain this; watch the next few requests."
        )
    return "critical", "Decode speed is materially below normal and should be investigated."


def summarize_performance_samples(
    samples: list[dict[str, object]], hours: int
) -> dict[str, object]:
    valid = [sample for sample in samples if sample.get("model") == MODEL_NAME]
    if not valid:
        status, message = performance_status(None)
        return {
            "observed_at": utc_now(),
            "status": status,
            "message": message,
            "window_hours": hours,
            "baseline": {
                "decode_tokens_per_second": MODEL_REFERENCE_TPS,
                "healthy_floor": round(MODEL_REFERENCE_TPS * 0.8, 1),
                "source": MODEL_REFERENCE_SOURCE,
            },
            "summary": None,
            "series": [],
        }

    deltas: list[dict[str, object]] = []
    for previous, current in zip(valid, valid[1:]):
        if current.get("engine_started_at") != previous.get("engine_started_at"):
            continue
        tpot_sum = counter_delta(current, previous, "time_per_output_token_sum")
        tpot_count = counter_delta(current, previous, "time_per_output_token_count")
        if not tpot_sum or not tpot_count:
            continue
        point: dict[str, object] = {
            "observed_at": current["observed_at"],
            "decode_tokens_per_second": round(tpot_count / tpot_sum, 2),
            "completed_requests": int(counter_delta(current, previous, "completed_requests_total") or 0),
            "output_tokens": int(counter_delta(current, previous, "generation_tokens_total") or 0),
            "tpot_sum": tpot_sum,
            "tpot_count": tpot_count,
            "failures": int(
                (counter_delta(current, previous, "error_requests_total") or 0)
                + (counter_delta(current, previous, "aborted_requests_total") or 0)
                + (counter_delta(current, previous, "repetition_requests_total") or 0)
            ),
            "preemptions": int(counter_delta(current, previous, "preemptions_total") or 0),
        }
        for output_key, sum_key, count_key in (
            ("time_to_first_token_seconds", "time_to_first_token_sum", "time_to_first_token_count"),
            ("end_to_end_seconds", "e2e_latency_sum", "e2e_latency_count"),
            ("queue_seconds", "queue_time_sum", "queue_time_count"),
        ):
            metric_sum = counter_delta(current, previous, sum_key)
            metric_count = counter_delta(current, previous, count_key)
            point[f"{output_key}_sum"] = metric_sum
            point[f"{output_key}_count"] = metric_count
            point[output_key] = (
                round(metric_sum / metric_count, 3)
                if metric_sum is not None and metric_count
                else None
            )
        deltas.append(point)

    latest = valid[-1]
    if deltas:
        total_tpot_sum = sum(float(point["tpot_sum"]) for point in deltas)
        total_tpot_count = sum(float(point["tpot_count"]) for point in deltas)
        decode_tps = total_tpot_count / total_tpot_sum if total_tpot_sum else None
        completed_requests = sum(int(point["completed_requests"]) for point in deltas)
        output_tokens = sum(int(point["output_tokens"]) for point in deltas)
        def weighted_average(key: str) -> float | None:
            metric_sum = sum(float(point[f"{key}_sum"] or 0) for point in deltas)
            metric_count = sum(float(point[f"{key}_count"] or 0) for point in deltas)
            return metric_sum / metric_count if metric_count else None

        ttft = weighted_average("time_to_first_token_seconds")
        e2e = weighted_average("end_to_end_seconds")
        queue = weighted_average("queue_seconds")
        failures = sum(int(point["failures"]) for point in deltas)
        preemptions = sum(int(point["preemptions"]) for point in deltas)
        source_window = f"last {hours}h"
    else:
        tpot_sum = float(latest.get("time_per_output_token_sum") or 0)
        tpot_count = float(latest.get("time_per_output_token_count") or 0)
        decode_tps = tpot_count / tpot_sum if tpot_sum else None
        completed_requests = int(float(latest.get("completed_requests_total") or 0))
        output_tokens = int(float(latest.get("generation_tokens_total") or 0))
        ttft_sum = float(latest.get("time_to_first_token_sum") or 0)
        ttft_count = float(latest.get("time_to_first_token_count") or 0)
        e2e_sum = float(latest.get("e2e_latency_sum") or 0)
        e2e_count = float(latest.get("e2e_latency_count") or 0)
        queue_sum = float(latest.get("queue_time_sum") or 0)
        queue_count = float(latest.get("queue_time_count") or 0)
        ttft = ttft_sum / ttft_count if ttft_count else None
        e2e = e2e_sum / e2e_count if e2e_count else None
        queue = queue_sum / queue_count if queue_count else None
        failures = int(
            float(latest.get("error_requests_total") or 0)
            + float(latest.get("aborted_requests_total") or 0)
            + float(latest.get("repetition_requests_total") or 0)
        )
        preemptions = int(float(latest.get("preemptions_total") or 0))
        source_window = "since the current model service started"

    status, message = performance_status(decode_tps)
    prefix_queries = float(latest.get("prefix_cache_queries_total") or 0)
    prefix_hits = float(latest.get("prefix_cache_hits_total") or 0)
    return {
        "observed_at": latest["observed_at"],
        "status": status,
        "message": message,
        "window_hours": hours,
        "source_window": source_window,
        "baseline": {
            "decode_tokens_per_second": MODEL_REFERENCE_TPS,
            "healthy_floor": round(MODEL_REFERENCE_TPS * 0.8, 1),
            "source": MODEL_REFERENCE_SOURCE,
        },
        "summary": {
            "decode_tokens_per_second": round(decode_tps, 2) if decode_tps else None,
            "time_to_first_token_seconds": round(ttft, 2) if ttft is not None else None,
            "end_to_end_seconds": round(e2e, 2) if e2e is not None else None,
            "queue_seconds": round(queue, 3) if queue is not None else None,
            "completed_requests": completed_requests,
            "output_tokens": output_tokens,
            "failures": failures,
            "preemptions": preemptions,
            "prefix_cache_hit_percent": round(100 * prefix_hits / prefix_queries, 1)
            if prefix_queries
            else None,
            "kv_cache_usage_percent": latest.get("kv_cache_usage_percent"),
            "requests_running": int(float(latest.get("requests_running") or 0)),
            "requests_waiting": int(float(latest.get("requests_waiting") or 0)),
        },
        "series": [
            {
                key: value
                for key, value in point.items()
                if not key.endswith("_sum")
                and not key.endswith("_count")
                and key not in {"failures", "preemptions"}
            }
            for point in deltas
        ],
    }


def performance_state(hours: int) -> dict[str, object]:
    samples = model_metric_history(hours)
    if not samples:
        sample_model_metrics()
        samples = model_metric_history(hours)
    return summarize_performance_samples(samples, hours)


def model_sampler_loop() -> None:
    while True:
        sample_model_metrics()
        time.sleep(MODEL_SAMPLE_INTERVAL_SECONDS)


def parse_key_values(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key:
            result[key] = value.strip()
    return result


def integer(value: str | None) -> int | None:
    try:
        return int(value or "")
    except ValueError:
        return None


def collect_node(key: str, configuration: dict[str, str]) -> dict[str, object]:
    started = time.monotonic()
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=6",
        configuration["ssh"],
        REMOTE_SNAPSHOT,
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        raw = parse_key_values(completed.stdout)
        total_memory = integer(raw.get("memory_total_kib"))
        available_memory = integer(raw.get("memory_available_kib"))
        total_disk = integer(raw.get("disk_total_kib"))
        available_disk = integer(raw.get("disk_available_kib"))
        gpu_parts = [part.strip() for part in raw.get("gpu", "").split(",")]
        services = {
            name.removeprefix("service_"): value
            for name, value in raw.items()
            if name.startswith("service_")
        }
        return {
            "key": key,
            "name": configuration["name"],
            "role": configuration["role"],
            "online": True,
            "hostname": raw.get("hostname", "Unknown"),
            "tailscale_ip": raw.get("tailscale_ip", "Unknown"),
            "uptime_seconds": integer(raw.get("uptime_seconds")),
            "memory_used_percent": round(
                100 * (total_memory - available_memory) / total_memory, 1
            )
            if total_memory and available_memory is not None
            else None,
            "memory_total_gib": round(total_memory / 1024 / 1024, 1)
            if total_memory
            else None,
            "disk_free_gib": round(available_disk / 1024 / 1024, 1)
            if available_disk
            else None,
            "disk_total_gib": round(total_disk / 1024 / 1024, 1)
            if total_disk
            else None,
            "gpu_utilization_percent": integer(gpu_parts[0]) if gpu_parts else None,
            "gpu_temperature_c": integer(gpu_parts[1]) if len(gpu_parts) > 1 else None,
            "gpu_power_w": float(gpu_parts[2]) if len(gpu_parts) > 2 and gpu_parts[2] else None,
            "gpu_sw_thermal_slowdown": (
                gpu_parts[3].strip().lower() == "active" if len(gpu_parts) > 3 else False
            ),
            "gpu_hw_thermal_slowdown": (
                gpu_parts[4].strip().lower() == "active" if len(gpu_parts) > 4 else False
            ),
            "cluster_link": raw.get("cluster_link", "UNKNOWN"),
            "services": services,
            "deepseek_ready": raw.get("deepseek_ready") == "yes",
            "latency_ms": round((time.monotonic() - started) * 1000),
            "observed_at": utc_now(),
            "error": None,
        }
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return {
            "key": key,
            "name": configuration["name"],
            "role": configuration["role"],
            "online": False,
            "observed_at": utc_now(),
            "error": str(error)[:240],
        }


def load_portfolio() -> list[dict[str, object]]:
    if PORTFOLIO_FILE.exists():
        try:
            value = json.loads(PORTFOLIO_FILE.read_text())
            if isinstance(value, list):
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return [
        {"name": "DeepSeek V4 Flash Vision", "status": "Installing", "role": "Vision + long context"},
        {"name": "Qwen3.8 Flash-Next", "status": "Queued", "role": "Fast daily driver"},
        {"name": "GLM-5.3 Flash EXL3", "status": "Queued", "role": "Difficult reasoning"},
    ]


def fleet_state() -> dict[str, object]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            key: executor.submit(collect_node, key, configuration)
            for key, configuration in NODES.items()
        }
        nodes = {key: future.result() for key, future in futures.items()}

    a = nodes["spark_a"]
    b = nodes["spark_b"]
    alerts: list[dict[str, str]] = []
    if not a["online"]:
        alerts.append({"level": "critical", "message": "Spark A is unreachable."})
    if not b["online"]:
        alerts.append({"level": "critical", "message": "Spark B is unreachable."})
    if a.get("cluster_link") != "UP" or b.get("cluster_link") != "UP":
        alerts.append({"level": "warning", "message": "The high-speed two-Spark link needs attention."})
    for node in (a, b):
        if not node.get("online"):
            continue
        name = str(node.get("name") or "Spark")
        temp = node.get("gpu_temperature_c")
        if node.get("gpu_hw_thermal_slowdown") or node.get("gpu_sw_thermal_slowdown"):
            alerts.append(
                {
                    "level": "critical",
                    "message": f"{name} is thermally throttling. Stop heavy jobs and let it cool.",
                }
            )
        elif isinstance(temp, int) and temp >= THERMAL_RED_C:
            alerts.append(
                {
                    "level": "critical",
                    "message": (
                        f"{name} is at {temp}°C (red zone). Stop heavy jobs, check airflow, "
                        "and let it cool. If it vanishes, unplug, wait a minute, then power on."
                    ),
                }
            )
        elif isinstance(temp, int) and temp >= THERMAL_YELLOW_C:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"{name} is warm at {temp}°C. Keep vents clear. No need to stop work yet.",
                }
            )

    a_services = a.get("services", {})
    b_services = b.get("services", {})
    deepseek_services_active = (
        a_services.get("dgx-deepseek-head") == "active"
        and b_services.get("dgx-deepseek-worker") == "active"
    )
    if deepseek_services_active and a.get("deepseek_ready"):
        active_model = "DeepSeek V4 Flash Vision"
    elif deepseek_services_active:
        active_model = "DeepSeek V4 Flash Vision · loading"
        alerts.append({"level": "warning", "message": "DeepSeek is loading across both Sparks."})
    elif a_services.get("dgx-model") == "active":
        active_model = "Qwen3.6 rollback"
    else:
        active_model = "No model ready"

    status = "healthy" if not alerts else (
        "critical" if any(item["level"] == "critical" for item in alerts) else "warning"
    )
    if not alerts:
        alerts.append({"level": "ok", "message": "No action needed."})

    payload = {
        "observed_at": utc_now(),
        "status": status,
        "active_model": active_model,
        "nodes": nodes,
        "alerts": alerts,
        "models": load_portfolio(),
        "links": {
            "dashboard_a": DASHBOARD_LINKS.get("dashboard_a", "http://127.0.0.1:11101"),
            "dashboard_b": DASHBOARD_LINKS.get("dashboard_b", "http://127.0.0.1:11102"),
            "desktop_a": "/api/open-desktop/spark-a",
            "desktop_b": "/api/open-desktop/spark-b",
        },
    }
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO fleet_samples(observed_at, payload) VALUES (?, ?)",
            (payload["observed_at"], json.dumps(payload, separators=(",", ":"))),
        )
        boundary = datetime.fromtimestamp(
            time.time() - FLEET_SAMPLE_RETENTION_DAYS * 86400, timezone.utc
        ).isoformat(timespec="seconds")
        connection.execute("DELETE FROM fleet_samples WHERE observed_at < ?", (boundary,))
    return payload


def history(hours: int) -> list[dict[str, object]]:
    hours = min(max(hours, 1), 168)
    boundary = datetime.fromtimestamp(time.time() - hours * 3600, timezone.utc).isoformat(
        timespec="seconds"
    )
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            "SELECT payload FROM fleet_samples WHERE observed_at >= ? ORDER BY observed_at ASC",
            (boundary,),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def thermal_band(temp: int | float | None) -> str:
    if temp is None:
        return "learning"
    if temp >= THERMAL_RED_C:
        return "critical"
    if temp >= THERMAL_YELLOW_C:
        return "warning"
    return "healthy"


def downsample_series(points: list[dict[str, object]], limit: int = 160) -> list[dict[str, object]]:
    if len(points) <= limit or limit <= 1:
        return points
    last_index = len(points) - 1
    out: list[dict[str, object]] = []
    last_picked = -1
    for i in range(limit):
        index = round(i * last_index / (limit - 1))
        if index != last_picked:
            out.append(points[index])
            last_picked = index
    return out


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def hotter_of(left: object, right: object) -> int | None:
    values = [int(value) for value in (left, right) if isinstance(value, (int, float))]
    return max(values) if values else None


def summarize_thermal(samples: list[dict[str, object]], hours: int) -> dict[str, object]:
    series: list[dict[str, object]] = []
    yellow_samples = 0
    red_samples = 0
    peak: int | None = None
    peak_at: str | None = None
    peak_node: str | None = None
    current_a = current_b = None
    throttling = False

    for sample in samples:
        nodes = as_dict(sample.get("nodes"))
        spark_a = as_dict(nodes.get("spark_a"))
        spark_b = as_dict(nodes.get("spark_b"))
        temp_a = spark_a.get("gpu_temperature_c")
        temp_b = spark_b.get("gpu_temperature_c")
        if temp_a is None and temp_b is None:
            continue
        current_a, current_b = temp_a, temp_b
        throttling = throttling or bool(
            spark_a.get("gpu_sw_thermal_slowdown")
            or spark_a.get("gpu_hw_thermal_slowdown")
            or spark_b.get("gpu_sw_thermal_slowdown")
            or spark_b.get("gpu_hw_thermal_slowdown")
        )
        hotter = hotter_of(temp_a, temp_b)
        if hotter is not None:
            if peak is None or hotter > peak:
                peak = hotter
                peak_at = str(sample.get("observed_at") or "")
                if temp_a == hotter and temp_b == hotter:
                    peak_node = "both Sparks"
                elif temp_a == hotter:
                    peak_node = "Spark A"
                else:
                    peak_node = "Spark B"
            if hotter >= THERMAL_RED_C:
                red_samples += 1
            elif hotter >= THERMAL_YELLOW_C:
                yellow_samples += 1
        series.append(
            {
                "observed_at": sample.get("observed_at"),
                "spark_a": temp_a,
                "spark_b": temp_b,
            }
        )

    current = hotter_of(current_a, current_b)
    current_status = "critical" if throttling else thermal_band(current)
    if current_status == "critical":
        title = "Hot — act now"
        message = (
            "Stop heavy jobs. Check airflow on both Sparks. If a box vanishes, unplug it, "
            "wait a minute, then power on."
        )
        action = "Stop work and cool the machines."
    elif current_status == "warning":
        title = "Warm"
        message = "Keep vents clear. You can keep working."
        action = "No need to stop work yet."
    elif current_status == "learning":
        title = "Learning temperature"
        message = "Waiting for the next private temperature check."
        action = "No action yet."
    else:
        title = "Cool"
        if red_samples:
            message = "Cool now, but this window did hit the red zone."
        elif yellow_samples:
            message = "Cool now. This window touched yellow; nothing to do unless it stays there."
        else:
            message = "No action. These Sparks have stayed in the green."
        action = "No action."

    sample_minutes = max(hours * 60 / max(len(series), 1), 0.5) if series else 0
    return {
        "observed_at": series[-1]["observed_at"] if series else utc_now(),
        "status": current_status,
        "title": title,
        "message": message,
        "action": action,
        "window_hours": hours,
        "bands": {"yellow_c": THERMAL_YELLOW_C, "red_c": THERMAL_RED_C},
        "summary": {
            "spark_a_c": current_a,
            "spark_b_c": current_b,
            "peak_c": peak,
            "peak_at": peak_at,
            "peak_node": peak_node,
            "yellow_minutes": round(yellow_samples * sample_minutes),
            "red_minutes": round(red_samples * sample_minutes),
            "throttling": throttling,
            "samples": len(series),
        },
        "series": downsample_series(series),
    }


def thermal_state(hours: int) -> dict[str, object]:
    return summarize_thermal(history(hours), hours)


def open_desktop(node: str) -> tuple[bool, str]:
    """Open one fixed, preconfigured Spark bookmark in Windows App."""
    bookmark_id = DESKTOP_BOOKMARKS.get(node)
    if bookmark_id is None:
        return False, "Unknown desktop."
    if not WINDOWS_APP_BINARY.exists():
        return False, "Microsoft Windows App is not installed."

    try:
        exported = subprocess.run(
            [str(WINDOWS_APP_BINARY), "--script", "bookmark", "export", bookmark_id, "--uri"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        desktop_uri = exported.stdout.strip()
        if not desktop_uri.startswith("rdp://"):
            return False, "The saved desktop bookmark could not be read."
        subprocess.Popen(
            ["/usr/bin/open", "-a", str(WINDOWS_APP), desktop_uri],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, "Opening the private desktop in Microsoft Windows App."
    except (OSError, subprocess.SubprocessError):
        return False, "Microsoft Windows App could not open the saved desktop."


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def send_json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_json(fleet_state())
            return
        if parsed.path == "/api/history":
            query = parse_qs(parsed.query)
            try:
                hours = int(query.get("hours", ["24"])[0])
            except ValueError:
                hours = 24
            self.send_json(history(hours))
            return
        if parsed.path == "/api/performance":
            query = parse_qs(parsed.query)
            try:
                hours = int(query.get("hours", ["24"])[0])
            except ValueError:
                hours = 24
            self.send_json(performance_state(min(max(hours, 1), MODEL_SAMPLE_RETENTION_DAYS * 24)))
            return
        if parsed.path == "/api/thermal":
            query = parse_qs(parsed.query)
            try:
                hours = int(query.get("hours", ["24"])[0])
            except ValueError:
                hours = 24
            self.send_json(thermal_state(min(max(hours, 1), 168)))
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        prefix = "/api/open-desktop/"
        if parsed.path.startswith(prefix):
            expected_origin = f"http://{HOST}:{PORT}"
            if self.headers.get("Origin") != expected_origin:
                self.send_json({"error": "Forbidden."}, HTTPStatus.FORBIDDEN)
                return
            node = parsed.path.removeprefix(prefix)
            opened, message = open_desktop(node)
            self.send_json(
                {"opened": opened, "message": message},
                HTTPStatus.OK if opened else HTTPStatus.BAD_REQUEST,
            )
            return
        self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.address_string()} - {format_string % args}")


def main() -> None:
    init_database()
    threading.Thread(target=model_sampler_loop, name="model-metrics", daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"DGX Command Center: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
