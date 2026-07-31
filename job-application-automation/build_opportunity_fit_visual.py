#!/usr/bin/env python3
import html
import json
from pathlib import Path

SOURCE = Path("/Users/admin/Claude/Projects/Korea Job Scraper/skeleton/data_overnight/jobs_scored.jsonl")
OUTPUT = Path(
    "/Users/admin/.codex/visualizations/2026/07/18/"
    "019f7628-e8bb-75a0-82e2-e5b114a277c4/opportunity-vs-fit.html"
)

jobs = []
with SOURCE.open(encoding="utf-8") as source:
    for line in source:
        row = json.loads(line)
        fit = row.get("fit")
        opportunity = row.get("opportunity")
        if not isinstance(fit, (int, float)) or not isinstance(opportunity, (int, float)):
            continue
        jobs.append(
            {
                "x": round(opportunity * 100, 2),
                "y": round(fit * 100, 2),
                "s": round(float(row.get("final") or 0), 2),
                "t": str(row.get("job_title") or "Untitled role")[:110],
                "c": str(row.get("company") or "Unknown company")[:70],
                "l": str(row.get("location") or "Location unspecified")[:70],
                "m": str(row.get("mapped_career") or "Other")[:60],
                "u": str(row.get("url") or ""),
            }
        )

jobs.sort(key=lambda job: job["s"], reverse=True)
for index, job in enumerate(jobs, start=1):
    job["r"] = index

data = json.dumps(jobs, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
fragment = r'''
<div id="opp-fit-root">
  <div class="plot-wrap">
    <svg role="img" aria-labelledby="opp-fit-title opp-fit-desc" viewBox="0 0 900 560">
      <title id="opp-fit-title">Opportunity versus fit for processed Market Aligner vacancies</title>
      <desc id="opp-fit-desc">Each selectable point is one vacancy. Opportunity is horizontal and personal fit is vertical.</desc>
      <g id="grid"></g>
      <g id="points"></g>
      <g id="axes"></g>
    </svg>
    <div id="tooltip" role="status" aria-live="polite"></div>
  </div>
  <div class="legend" aria-label="Legend">
    <span><i class="top"></i>Top 10 overall</span>
    <span><i class="strong"></i>Overall score 70+</span>
    <span><i class="standard"></i>Other processed vacancies</span>
  </div>
  <div id="selection" class="card" aria-live="polite">
    Select a dot to inspect the vacancy.
  </div>
</div>
<style>
  #opp-fit-root { color: var(--foreground); width: 100%; }
  #opp-fit-root .plot-wrap { position: relative; width: 100%; }
  #opp-fit-root svg { display: block; width: 100%; height: auto; overflow: visible; }
  #opp-fit-root .grid-line { stroke: var(--border); stroke-width: 1; opacity: .65; }
  #opp-fit-root .axis-line { stroke: var(--muted-foreground); stroke-width: 1.4; }
  #opp-fit-root .axis-text { fill: var(--muted-foreground); font-size: 12px; }
  #opp-fit-root .axis-label { fill: var(--foreground); font-size: 14px; font-weight: 500; }
  #opp-fit-root .job-point { cursor: pointer; stroke: var(--background); stroke-width: 1.2; opacity: .76; }
  #opp-fit-root .job-point:hover,
  #opp-fit-root .job-point:focus { opacity: 1; stroke: var(--foreground); stroke-width: 2.2; outline: none; }
  #opp-fit-root .job-point.selected { opacity: 1; stroke: var(--foreground); stroke-width: 3; }
  #opp-fit-root .tier-top { fill: var(--viz-series-2); }
  #opp-fit-root .tier-strong { fill: var(--viz-series-1); }
  #opp-fit-root .tier-standard { fill: var(--muted-foreground); }
  #opp-fit-root #tooltip {
    display: none; position: absolute; pointer-events: none; max-width: 280px;
    padding: 8px 10px; color: var(--popover-foreground); background: var(--popover);
    border: 1px solid var(--border); border-radius: 8px;
  }
  #opp-fit-root .legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0 12px; color: var(--muted-foreground); }
  #opp-fit-root .legend span { display: inline-flex; align-items: center; gap: 6px; }
  #opp-fit-root .legend i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  #opp-fit-root .legend .top { background: var(--viz-series-2); }
  #opp-fit-root .legend .strong { background: var(--viz-series-1); }
  #opp-fit-root .legend .standard { background: var(--muted-foreground); }
  #opp-fit-root #selection { padding: 12px 14px; }
  #opp-fit-root #selection a { color: var(--foreground); font-weight: 500; }
  @media (max-width: 520px) {
    #opp-fit-root .axis-text { font-size: 10px; }
    #opp-fit-root .axis-label { font-size: 12px; }
  }
</style>
<script>
(() => {
  const root = document.getElementById("opp-fit-root");
  const data = __DATA__;
  const svg = root.querySelector("svg");
  const ns = "http://www.w3.org/2000/svg";
  const grid = root.querySelector("#grid");
  const axes = root.querySelector("#axes");
  const points = root.querySelector("#points");
  const tooltip = root.querySelector("#tooltip");
  const selection = root.querySelector("#selection");
  const margin = { left: 72, right: 24, top: 22, bottom: 64 };
  const width = 900, height = 560;
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const x = value => margin.left + (value / 100) * innerW;
  const y = value => margin.top + innerH - (value / 100) * innerH;
  const make = (name, attrs = {}) => {
    const node = document.createElementNS(ns, name);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  };
  const addText = (parent, value, attrs) => {
    const node = make("text", attrs);
    node.textContent = value;
    parent.appendChild(node);
  };

  [0, 20, 40, 60, 80, 100].forEach(tick => {
    grid.appendChild(make("line", { x1: x(tick), y1: margin.top, x2: x(tick), y2: margin.top + innerH, class: "grid-line" }));
    grid.appendChild(make("line", { x1: margin.left, y1: y(tick), x2: margin.left + innerW, y2: y(tick), class: "grid-line" }));
    addText(axes, String(tick), { x: x(tick), y: height - 36, "text-anchor": "middle", class: "axis-text" });
    addText(axes, String(tick), { x: margin.left - 13, y: y(tick) + 4, "text-anchor": "end", class: "axis-text" });
  });
  axes.appendChild(make("line", { x1: margin.left, y1: margin.top + innerH, x2: margin.left + innerW, y2: margin.top + innerH, class: "axis-line" }));
  axes.appendChild(make("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: margin.top + innerH, class: "axis-line" }));
  addText(axes, "Opportunity →", { x: margin.left + innerW / 2, y: height - 5, "text-anchor": "middle", class: "axis-label" });
  addText(axes, "Fit →", { x: 19, y: margin.top + innerH / 2, transform: `rotate(-90 19 ${margin.top + innerH / 2})`, "text-anchor": "middle", class: "axis-label" });

  const showTooltip = (event, job) => {
    tooltip.style.display = "block";
    tooltip.textContent = `#${job.r} · ${job.c} — ${job.t} · Opportunity ${job.x.toFixed(1)} · Fit ${job.y.toFixed(1)}`;
    const bounds = root.querySelector(".plot-wrap").getBoundingClientRect();
    tooltip.style.left = `${Math.min(event.clientX - bounds.left + 12, bounds.width - 292)}px`;
    tooltip.style.top = `${Math.max(4, event.clientY - bounds.top - 52)}px`;
  };
  const hideTooltip = () => { tooltip.style.display = "none"; };
  const selectJob = (circle, job) => {
    points.querySelectorAll(".selected").forEach(node => node.classList.remove("selected"));
    circle.classList.add("selected");
    const safeUrl = /^https?:\/\//.test(job.u) ? job.u : "";
    selection.innerHTML =
      `<strong>#${job.r} ${escapeHtml(job.c)} — ${escapeHtml(job.t)}</strong><br>` +
      `${escapeHtml(job.l)} · ${escapeHtml(job.m)} · Opportunity ${job.x.toFixed(1)} · Fit ${job.y.toFixed(1)} · Overall ${job.s.toFixed(1)}` +
      (safeUrl ? ` · <a href="${escapeHtml(encodeURI(safeUrl))}" target="_blank" rel="noopener noreferrer">Open vacancy</a>` : "");
  };
  const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);

  [...data].reverse().forEach(job => {
    const tier = job.r <= 10 ? "tier-top" : job.s >= 70 ? "tier-strong" : "tier-standard";
    const circle = make("circle", {
      cx: x(job.x), cy: y(job.y), r: job.r <= 10 ? 6.5 : job.s >= 70 ? 5 : 3.7,
      class: `job-point ${tier}`, tabindex: "0",
      "aria-label": `Rank ${job.r}, ${job.c}, ${job.t}, opportunity ${job.x}, fit ${job.y}`
    });
    circle.addEventListener("mouseenter", event => showTooltip(event, job));
    circle.addEventListener("mousemove", event => showTooltip(event, job));
    circle.addEventListener("mouseleave", hideTooltip);
    circle.addEventListener("focus", event => {
      const box = circle.getBoundingClientRect();
      showTooltip({ clientX: box.left, clientY: box.top }, job);
    });
    circle.addEventListener("blur", hideTooltip);
    circle.addEventListener("click", () => selectJob(circle, job));
    circle.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectJob(circle, job);
      }
    });
    points.appendChild(circle);
  });
})();
</script>
'''.replace("__DATA__", data)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(fragment, encoding="utf-8")
print(f"{OUTPUT}\n{len(jobs)} jobs\n{OUTPUT.stat().st_size} bytes")
