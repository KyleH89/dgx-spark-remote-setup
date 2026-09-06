const $ = (selector) => document.querySelector(selector);
let selectedPerformanceHours = 24;

const fmt = {
  percent(value) { return value == null ? "Unknown" : `${value}%`; },
  gib(value) { return value == null ? "Unknown" : `${Math.round(value)} GiB`; },
  temp(value) { return value == null ? "Unknown" : `${value}°C`; },
  uptime(seconds) {
    if (seconds == null) return "Unknown";
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return days ? `${days}d ${hours}h` : `${hours}h`;
  },
  age(date) {
    const seconds = Math.max(0, Math.round((Date.now() - new Date(date).getTime()) / 1000));
    return seconds < 60 ? "just now" : `${Math.floor(seconds / 60)} min ago`;
  },
  tps(value) { return value == null ? "Learning…" : `${value.toFixed(1)} tok/s`; },
  seconds(value) { return value == null ? "Learning…" : `${value.toFixed(value < 1 ? 2 : 1)}s`; },
  number(value) { return new Intl.NumberFormat("en-US", {notation: value >= 10000 ? "compact" : "standard", maximumFractionDigits: 1}).format(value || 0); },
};

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function tempClass(value) {
  if (value == null) return "";
  if (value >= 85) return "bad";
  if (value >= 75) return "temp-warm";
  return "good";
}

function nodeCard(node, dashboardUrl, desktopUrl) {
  if (!node.online) {
    return `<article class="node-card offline">
      <div class="node-title"><div><p class="eyebrow">${node.role}</p><h3>${node.name}</h3></div><span class="badge offline">Offline</span></div>
      <p class="muted">The last private check could not reach this Spark.</p>
    </article>`;
  }
  const service = Object.entries(node.services || {}).find(([, state]) => state === "active");
  return `<article class="node-card">
    <div class="node-title">
      <div><p class="eyebrow">${node.role} · ${node.hostname}</p><h3>${node.name}</h3></div>
      <span class="badge">Online</span>
    </div>
    <div class="metrics">
      ${metric("Memory used", fmt.percent(node.memory_used_percent))}
      ${metric("GPU use", fmt.percent(node.gpu_utilization_percent))}
      ${metric("Storage free", fmt.gib(node.disk_free_gib))}
      ${metric("Uptime", fmt.uptime(node.uptime_seconds))}
      ${metric("GPU temperature", `<span class="${tempClass(node.gpu_temperature_c)}">${fmt.temp(node.gpu_temperature_c)}</span>`)}
      ${metric("Model service", service ? "Running" : "Idle")}
    </div>
    <div class="node-actions">
      <a class="button" href="${dashboardUrl}" target="_blank" rel="noreferrer">Open NVIDIA Dashboard</a>
      <button class="button" type="button" data-desktop-url="${desktopUrl}">Open Desktop</button>
    </div>
  </article>`;
}

function performanceChart(series, baseline) {
  if (!series.length) {
    return `<div class="chart-empty"><strong>History starts now</strong><span>The current lifetime average is shown above. Trend points appear as your client completes new requests.</span></div>`;
  }

  const width = 760;
  const height = 220;
  const padding = {left: 42, right: 18, top: 20, bottom: 28};
  const values = series.map((point) => point.decode_tokens_per_second);
  const low = Math.max(0, Math.min(...values, baseline) * 0.75);
  const high = Math.max(...values, baseline) * 1.2;
  const x = (index) => padding.left + (series.length === 1 ? (width - padding.left - padding.right) / 2 : index * (width - padding.left - padding.right) / (series.length - 1));
  const y = (value) => padding.top + (high - value) * (height - padding.top - padding.bottom) / Math.max(high - low, 0.1);
  const path = series.map((point, index) => `${index ? "L" : "M"} ${x(index).toFixed(1)} ${y(point.decode_tokens_per_second).toFixed(1)}`).join(" ");
  const first = new Date(series[0].observed_at);
  const last = new Date(series[series.length - 1].observed_at);
  const timeLabel = (date) => date.toLocaleTimeString([], {hour: "numeric", minute: "2-digit"});

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Measured decode speed over time">
    <line class="grid-line" x1="${padding.left}" y1="${y(high)}" x2="${width - padding.right}" y2="${y(high)}"></line>
    <line class="grid-line" x1="${padding.left}" y1="${y(low)}" x2="${width - padding.right}" y2="${y(low)}"></line>
    <line class="baseline-path" x1="${padding.left}" y1="${y(baseline)}" x2="${width - padding.right}" y2="${y(baseline)}"></line>
    <path class="speed-path" d="${path}"></path>
    ${series.map((point, index) => `<circle class="speed-point" cx="${x(index)}" cy="${y(point.decode_tokens_per_second)}" r="4"><title>${point.decode_tokens_per_second.toFixed(1)} tok/s · ${new Date(point.observed_at).toLocaleString()}</title></circle>`).join("")}
    <text class="chart-axis" x="4" y="${y(high) + 4}">${high.toFixed(0)}</text>
    <text class="chart-axis" x="4" y="${y(low) + 4}">${low.toFixed(0)}</text>
    <text class="chart-axis" x="${padding.left}" y="${height - 5}">${timeLabel(first)}</text>
    <text class="chart-axis" text-anchor="end" x="${width - padding.right}" y="${height - 5}">${timeLabel(last)}</text>
  </svg>`;
}

function seriesPath(series, key, x, y) {
  let started = false;
  const parts = [];
  series.forEach((point, index) => {
    if (point[key] == null) return;
    parts.push(`${started ? "L" : "M"} ${x(index).toFixed(1)} ${y(point[key]).toFixed(1)}`);
    started = true;
  });
  return parts.join(" ");
}

function thermalChart(series, bands) {
  if (!series.length) {
    return `<div class="chart-empty"><strong>History starts now</strong><span>Temperature points appear as the Command Center checks both Sparks.</span></div>`;
  }

  const width = 760;
  const height = 220;
  const padding = {left: 42, right: 18, top: 20, bottom: 28};
  const values = series.flatMap((point) => [point.spark_a, point.spark_b]).filter((value) => value != null);
  const low = 35;
  const high = Math.max(95, ...values, bands.red_c + 5);
  const x = (index) => padding.left + (series.length === 1 ? (width - padding.left - padding.right) / 2 : index * (width - padding.left - padding.right) / (series.length - 1));
  const y = (value) => padding.top + (high - value) * (height - padding.top - padding.bottom) / Math.max(high - low, 1);
  const first = new Date(series[0].observed_at);
  const last = new Date(series[series.length - 1].observed_at);
  const timeLabel = (date) => date.toLocaleTimeString([], {hour: "numeric", minute: "2-digit"});
  const yellowTop = y(Math.min(high, bands.red_c));
  const yellowBottom = y(Math.max(low, bands.yellow_c));
  const redTop = y(high);
  const redBottom = y(Math.max(low, bands.red_c));

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="GPU temperature over time">
    <rect class="thermal-band-yellow" x="${padding.left}" y="${yellowTop}" width="${width - padding.left - padding.right}" height="${Math.max(0, yellowBottom - yellowTop)}"></rect>
    <rect class="thermal-band-red" x="${padding.left}" y="${redTop}" width="${width - padding.left - padding.right}" height="${Math.max(0, redBottom - redTop)}"></rect>
    <line class="grid-line" x1="${padding.left}" y1="${y(high)}" x2="${width - padding.right}" y2="${y(high)}"></line>
    <line class="grid-line" x1="${padding.left}" y1="${y(low)}" x2="${width - padding.right}" y2="${y(low)}"></line>
    <path class="temp-path-a" d="${seriesPath(series, "spark_a", x, y)}"></path>
    <path class="temp-path-b" d="${seriesPath(series, "spark_b", x, y)}"></path>
    <text class="chart-axis" x="4" y="${y(high) + 4}">${high.toFixed(0)}°</text>
    <text class="chart-axis" x="4" y="${y(low) + 4}">${low.toFixed(0)}°</text>
    <text class="chart-axis" x="${padding.left}" y="${height - 5}">${timeLabel(first)}</text>
    <text class="chart-axis" text-anchor="end" x="${width - padding.right}" y="${height - 5}">${timeLabel(last)}</text>
  </svg>`;
}

function renderThermal(payload) {
  const status = $("#thermal-status");
  status.className = `performance-status ${payload.status}`;
  $("#thermal-title").textContent = payload.title;
  $("#thermal-message").textContent = payload.message;
  const badge = $("#thermal-badge");
  badge.className = `badge ${payload.status}`;
  badge.textContent = payload.status === "healthy" ? "Cool" : payload.status === "warning" ? "Warm" : payload.status === "critical" ? "Hot" : "Checking";
  const summary = payload.summary || {};
  const peakBits = summary.peak_c == null
    ? "No temperature samples yet"
    : `Peak ${summary.peak_c}°C${summary.peak_node ? ` on ${summary.peak_node}` : ""} · yellow ${summary.yellow_minutes || 0} min · red ${summary.red_minutes || 0} min`;
  $("#thermal-peak").textContent = peakBits;
  $("#thermal-window").textContent = `Same window as speed history · now A ${fmt.temp(summary.spark_a_c)} · B ${fmt.temp(summary.spark_b_c)}`;
  $("#thermal-chart").innerHTML = thermalChart(payload.series || [], payload.bands || {yellow_c: 75, red_c: 85});
}

function renderPerformance(payload) {
  const status = $("#performance-status");
  status.className = `performance-status ${payload.status}`;
  $("#performance-title").textContent = payload.status === "healthy" ? "Running at normal speed" : payload.status === "warning" ? "Running slower than normal" : payload.status === "critical" ? "Performance needs attention" : "Learning your normal speed";
  $("#performance-message").textContent = payload.message;
  const badge = $("#performance-badge");
  badge.className = `badge ${payload.status}`;
  badge.textContent = payload.status === "healthy" ? "Normal" : payload.status === "warning" ? "Watch" : payload.status === "critical" ? "Slow" : "Learning";

  const summary = payload.summary;
  if (!summary) return;
  const speedDelta = summary.decode_tokens_per_second == null ? null : 100 * (summary.decode_tokens_per_second / payload.baseline.decode_tokens_per_second - 1);
  const reference = payload.baseline.decode_tokens_per_second;
  const speedContext = speedDelta == null ? "Waiting for completed requests" : `${Math.abs(speedDelta).toFixed(0)}% ${speedDelta >= 0 ? "above" : "below"} the ${reference.toFixed(1)} reference`;
  $("#performance-cards").innerHTML = `
    <div class="performance-card ${payload.status}"><span>Decode speed</span><strong>${fmt.tps(summary.decode_tokens_per_second)}</strong><small>${speedContext}</small></div>
    <div class="performance-card"><span>Average first token</span><strong>${fmt.seconds(summary.time_to_first_token_seconds)}</strong><small>Long prompts take longer to start</small></div>
    <div class="performance-card"><span>Completed requests</span><strong>${fmt.number(summary.completed_requests)}</strong><small>${fmt.number(summary.output_tokens)} output tokens · ${payload.source_window}</small></div>
    <div class="performance-card ${summary.failures || summary.preemptions ? "warning" : "healthy"}"><span>Reliability</span><strong>${summary.failures + summary.preemptions === 0 ? "Clean" : "Needs attention"}</strong><small>${summary.failures} failures · ${summary.preemptions} preemptions</small></div>`;

  $("#performance-window").textContent = `${payload.series.length} measured interval${payload.series.length === 1 ? "" : "s"} · ${payload.source_window}`;
  $("#performance-chart").innerHTML = performanceChart(payload.series, payload.baseline.decode_tokens_per_second);
  $("#performance-reference").textContent = `${reference.toFixed(1)} tok/s published reference`;
  $("#performance-diagnostics").innerHTML = `
    <div class="metric-line"><span>Average full response</span><strong>${fmt.seconds(summary.end_to_end_seconds)}</strong></div>
    <div class="metric-line"><span>Queue delay</span><strong class="${summary.queue_seconds > 1 ? "bad" : "good"}">${fmt.seconds(summary.queue_seconds)}</strong></div>
    <div class="metric-line"><span>Requests waiting now</span><strong class="${summary.requests_waiting ? "bad" : "good"}">${summary.requests_waiting}</strong></div>
    <div class="metric-line"><span>KV cache in use</span><strong>${fmt.percent(summary.kv_cache_usage_percent)}</strong></div>
    <div class="metric-line"><span>Prompt cache hit rate</span><strong>${fmt.percent(summary.prefix_cache_hit_percent)}</strong></div>`;
}

function render(payload) {
  const summary = $("#summary");
  summary.className = `summary ${payload.status}`;
  $("#summary-title").textContent = payload.status === "healthy" ? "Everything is healthy" : payload.status === "warning" ? "One item needs attention" : "The fleet needs attention";
  $("#summary-detail").textContent = payload.alerts[0]?.message || "No action needed.";
  $("#active-model").textContent = payload.active_model;
  $("#freshness").textContent = `Fresh private check ${fmt.age(payload.observed_at)}`;

  $("#node-grid").innerHTML = [
    nodeCard(payload.nodes.spark_a, payload.links.dashboard_a, payload.links.desktop_a),
    nodeCard(payload.nodes.spark_b, payload.links.dashboard_b, payload.links.desktop_b),
  ].join("");

  const a = payload.nodes.spark_a;
  const b = payload.nodes.spark_b;
  const linked = a.online && b.online && a.cluster_link === "UP" && b.cluster_link === "UP";
  $("#cluster").innerHTML = `
    <div class="metric-line"><span>Direct ConnectX-7 link</span><strong class="${linked ? "good" : "bad"}">${linked ? "Connected" : "Needs attention"}</strong></div>
    <div class="metric-line"><span>Management path</span><strong>Tailscale</strong></div>
    <div class="metric-line"><span>Model data path</span><strong>Private 200 Gb/s class link</strong></div>
    <div class="metric-line"><span>Current operating mode</span><strong>${payload.active_model}</strong></div>`;

  $("#alerts").innerHTML = payload.alerts.map((alert) => `<div class="alert ${alert.level}">${alert.message}</div>`).join("");
  $("#models").innerHTML = payload.models.map((model) => `<article class="model-card">
    <div><h3>${model.name}</h3><p>${model.role}</p></div>
    <span class="badge ${String(model.status).toLowerCase()}">${model.status}</span>
  </article>`).join("");

  document.querySelectorAll("[data-desktop-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      const original = button.textContent;
      button.disabled = true;
      button.textContent = "Opening…";
      try {
        const response = await fetch(button.dataset.desktopUrl, {method: "POST"});
        const result = await response.json();
        if (!response.ok || !result.opened) throw new Error(result.message || "Could not open desktop");
        button.textContent = "Opened in Windows App";
      } catch (error) {
        button.textContent = "Could not open — retry";
      } finally {
        window.setTimeout(() => {
          button.disabled = false;
          button.textContent = original;
        }, 3000);
      }
    });
  });
}

async function refresh() {
  const button = $("#refresh");
  button.disabled = true;
  button.textContent = "Checking…";
  try {
    const [statusResponse, performanceResponse, thermalResponse] = await Promise.all([
      fetch("/api/status", {cache: "no-store"}),
      fetch(`/api/performance?hours=${selectedPerformanceHours}`, {cache: "no-store"}),
      fetch(`/api/thermal?hours=${selectedPerformanceHours}`, {cache: "no-store"}),
    ]);
    if (!statusResponse.ok) throw new Error(`Status ${statusResponse.status}`);
    render(await statusResponse.json());
    if (performanceResponse.ok) renderPerformance(await performanceResponse.json());
    if (thermalResponse.ok) renderThermal(await thermalResponse.json());
  } catch (error) {
    const summary = $("#summary");
    summary.className = "summary critical";
    $("#summary-title").textContent = "Command Center could not refresh";
    $("#summary-detail").textContent = "The Sparks were not changed. Try Refresh now.";
  } finally {
    button.disabled = false;
    button.textContent = "Refresh now";
  }
}

$("#refresh").addEventListener("click", refresh);
document.querySelectorAll("[data-hours]").forEach((button) => {
  button.addEventListener("click", () => {
    selectedPerformanceHours = Number(button.dataset.hours);
    document.querySelectorAll("[data-hours]").forEach((candidate) => candidate.classList.toggle("selected", candidate === button));
    refresh();
  });
});
refresh();
setInterval(refresh, 30000);
