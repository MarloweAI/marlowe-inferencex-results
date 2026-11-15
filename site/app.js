"use strict";

// One curve per (source, hardware, framework, parallel configuration), points ordered by concurrency.
// The view (model, axes, percentile, filters) lives in the URL hash, so a link reproduces it.

const METRICS = {
  intvty: { label: "Interactivity (tok/s/user)", p50: "median_intvty", p90: "p90_intvty", digits: 1 },
  tput: { label: "Throughput per GPU (tok/s/GPU)", key: "tput_per_gpu", digits: 0 },
  ttft: { label: "Time to first token (s)", p50: "median_ttft", p90: "p90_ttft", digits: 3 },
  tpot: { label: "Time per output token (ms)", p50: "median_tpot", p90: "p90_tpot", scale: 1000, digits: 3 },
  out_tput: { label: "Output throughput per GPU (tok/s/GPU)", key: "output_tput_per_gpu", digits: 1 },
  in_tput: { label: "Input throughput per GPU (tok/s/GPU)", key: "input_tput_per_gpu", digits: 0 },
  conc: { label: "Concurrency (simultaneous agent sessions)", top: "conc", digits: 0 },
};
const HW_LABEL = {
  mi355x: "MI355X", mi325x: "MI325X", mi300x: "MI300X", b200: "B200", b300: "B300",
  gb200: "GB200", gb300: "GB300", h100: "H100", h200: "H200",
};
const AMD = new Set(["mi355x", "mi325x", "mi300x"]);
const FW_LABEL = {
  sglang: "SGLang", vllm: "vLLM", atom: "ATOM", tilert: "TileRT",
  "dynamo-sglang": "Dynamo SGLang", "dynamo-vllm": "Dynamo vLLM",
};
const SOURCES = { marlowe: "Marlowe measured", published: "InferenceX published" };

const state = {
  model: "dsv41flash", x: "intvty", y: "tput", pct: "p50", logx: false, logy: false,
  source: new Set(["marlowe", "published"]), hardware: new Set(["mi355x"]), framework: null,
};
let DATA = null;
let chart = null;
const hidden = new Set();

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const hwLabel = (h) => HW_LABEL[h] || h.toUpperCase();
const fwLabel = (f) => FW_LABEL[f] || f;

function metricKey(m) {
  const d = METRICS[m];
  return d.key || d.top || d[state.pct];
}
function value(p, m) {
  const d = METRICS[m];
  const v = d.top ? p[d.top] : p.metrics[d.key || d[state.pct]];
  return typeof v === "number" ? v * (d.scale || 1) : null;
}
function fmt(v, digits) {
  return typeof v === "number" ? v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "–";
}

function configLabel(r) {
  if (r.disagg) return `disagg ${r.num_prefill_gpu}P+${r.num_decode_gpu}D GPUs`;
  let s = `TP${r.decode_tp}`;
  if (r.decode_ep > 1) s += ` EP${r.decode_ep}`;
  if (r.decode_dp_attention) s += " DPA";
  if (r.offload_mode === "on") s += " offload";
  return s;
}
function gpus(r) {
  return r.disagg ? r.num_prefill_gpu + r.num_decode_gpu : r.num_decode_gpu;
}

function points(model) {
  const ix = DATA.inferencex.models[model];
  const pub = (ix ? ix.rows : []).map((r) => ({
    ...r, source: "published", url: r.run_url,
    curve: `published|${r.hardware}|${r.framework}|${r.spec_method}|${configLabel(r)}`,
    curveLabel: `${hwLabel(r.hardware)} · ${fwLabel(r.framework)} · ${configLabel(r)}`,
  }));
  const ours = DATA.marlowe.filter((p) => p.model === model && p.status === "final").map((p) => ({
    ...p, source: "marlowe", url: p.recipe,
    curve: `marlowe|${p.series}|${configLabel(p)}`,
    curveLabel: `Marlowe · ${hwLabel(p.hardware)} · ${configLabel(p)}${p.series === "main" ? "" : " · interactivity-leaning"}`,
  }));
  return ours.concat(pub);
}

function visible(all) {
  return all.filter((p) => state.source.has(p.source) && state.hardware.has(p.hardware) &&
    (p.source === "marlowe" || state.framework.has(p.framework)));
}

function color(p) {
  if (p.source === "marlowe") return css("--s-marlowe");
  return css(`--s-${p.framework}`) || css("--s-other");
}
function symbol(p) {
  return { 2: "circle", 4: "rect", 8: "triangle" }[gpus(p)] || "diamond";
}

function tooltip(p) {
  const rows = [
    ["Concurrency", p.conc],
    ["GPUs", `${gpus(p)} × ${hwLabel(p.hardware)}`],
    ["Interactivity P50 / P90", `${fmt(p.metrics.median_intvty, 1)} / ${fmt(p.metrics.p90_intvty, 1)} tok/s/user`],
    ["TTFT P50 / P90", `${fmt(p.metrics.median_ttft, 3)} / ${fmt(p.metrics.p90_ttft, 3)} s`],
    ["TPOT P50 / P90", `${fmt(p.metrics.median_tpot * 1e3, 3)} / ${fmt(p.metrics.p90_tpot * 1e3, 3)} ms`],
    ["Throughput", `${fmt(p.metrics.tput_per_gpu, 0)} tok/s/GPU`],
    ["Output throughput", `${fmt(p.metrics.output_tput_per_gpu, 1)} tok/s/GPU`],
  ];
  if (p.source === "marlowe") {
    rows.push(["Configuration", p.label], ["Request cap", p.server.max_running_requests ?? "default"],
      ["Engram host table", p.server.engram_host_table ? "on" : "off"], ["Date", p.date], ["Image", p.image.split(" ")[0]]);
  } else {
    rows.push(["Framework", fwLabel(p.framework)], ["Date", p.date], ["Image", (p.image || "").split("@")[0]]);
  }
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const head = `<div class="tt-h"><span class="swatch" style="background:${color(p)}"></span><b>${esc(p.curveLabel)}</b></div>`;
  const src = p.source === "marlowe" ? "Measured by Marlowe · click for the recipe" :
    "Published by InferenceX (SemiAnalysis) · click for the run";
  const body = rows.map(([k, v]) => `<tr><td style="color:${css("--ink-2")};padding-right:12px">${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");
  return `${head}<table style="font-size:12px;margin-top:4px">${body}</table><div style="margin-top:4px;color:${css("--muted")}">${src}</div>`;
}

function render() {
  const all = points(state.model);
  const vis = visible(all);
  $("empty").hidden = vis.length > 0;
  const curves = new Map();
  for (const p of vis) {
    const x = value(p, state.x), y = value(p, state.y);
    if (x === null || y === null) continue;
    if (!curves.has(p.curve)) curves.set(p.curve, []);
    curves.get(p.curve).push({ p, x, y });
  }
  // Marlowe curves first in the legend, then published curves by hardware, framework, configuration.
  const keys = [...curves.keys()].sort((a, b) => (a.startsWith("marlowe") ? 0 : 1) - (b.startsWith("marlowe") ? 0 : 1) || a.localeCompare(b));
  const narrow = window.innerWidth < 640;
  const series = keys.map((k) => {
    const pts = curves.get(k).sort((a, b) => a.p.conc - b.p.conc);
    const p0 = pts[0].p;
    const ours = p0.source === "marlowe";
    const lean = ours && p0.series !== "main";
    const c = color(p0);
    return {
      name: p0.curveLabel,
      type: "line",
      data: pts.map((d) => ({ value: [d.x, d.y], p: d.p })),
      symbol: lean ? "emptyCircle" : symbol(p0),
      symbolSize: ours ? 11 : 8,
      z: ours ? 10 : 2,
      lineStyle: { width: ours ? 3 : 1.5, color: c, type: lean ? "dotted" : AMD.has(p0.hardware) ? "solid" : "dashed",
        opacity: ours ? 1 : 0.85 },
      itemStyle: { color: lean ? css("--surface") : c, borderColor: lean ? c : css("--surface"), borderWidth: lean ? 2.5 : 1.5 },
      emphasis: { focus: "series", lineStyle: { width: ours ? 4 : 3 } },
      endLabel: ours && !narrow ? { show: true, formatter: () => `Marlowe ${configLabel(p0)}${lean ? " interactivity-leaning" : ""}`,
        color: css("--ink"), fontSize: 12, fontWeight: 600, distance: 8 } : undefined,
      labelLayout: { hideOverlap: true },
    };
  });
  const axis = (m, log) => ({
    type: log ? "log" : "value",
    name: METRICS[m].label + (METRICS[m].p50 ? ` · ${state.pct.toUpperCase()}` : ""),
    nameLocation: "middle",
    nameGap: 38,
    nameTextStyle: { color: css("--ink-2"), fontSize: 13 },
    scale: true,
    axisLine: { lineStyle: { color: css("--axis") } },
    axisLabel: { color: css("--muted"), hideOverlap: true },
    splitLine: { lineStyle: { color: css("--grid") } },
  });
  chart.setOption({
    backgroundColor: "transparent",
    textStyle: { fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif" },
    animationDuration: 300,
    grid: { left: 72, right: narrow ? 24 : 150, top: 24, bottom: 56, containLabel: false },
    xAxis: { ...axis(state.x, state.logx), nameGap: 30 },
    yAxis: { ...axis(state.y, state.logy), nameGap: 58 },
    tooltip: {
      trigger: "item", confine: true, backgroundColor: css("--surface"), borderColor: css("--border"),
      textStyle: { color: css("--ink"), fontSize: 12 }, extraCssText: "box-shadow:0 4px 16px rgba(0,0,0,.12);max-width:360px;white-space:normal",
      formatter: (prm) => tooltip(prm.data.p),
    },
    legend: { show: false, selected: Object.fromEntries(series.map((s) => [s.name, !hidden.has(s.name)])) },
    series,
  }, { notMerge: true });
  renderLegend(series);
}

// Curve legend under the chart: wraps instead of paging; a click hides or shows that curve.
function renderLegend(series) {
  const box = $("legend");
  box.innerHTML = "";
  for (const s of series) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "lg";
    b.setAttribute("aria-pressed", !hidden.has(s.name));
    const ls = s.lineStyle;
    const dash = ls.type === "dashed" ? "5 3" : ls.type === "dotted" ? "1.5 2.5" : "";
    const filled = s.symbol !== "emptyCircle";
    const mark = { circle: '<circle cx="13" cy="6" r="3.5"/>', emptyCircle: '<circle cx="13" cy="6" r="3"/>',
      rect: '<rect x="9.5" y="2.5" width="7" height="7"/>', triangle: '<path d="M13 2 L17 10 L9 10 Z"/>',
      diamond: '<path d="M13 1.5 L17.5 6 L13 10.5 L8.5 6 Z"/>' }[s.symbol];
    b.innerHTML = `<svg width="26" height="12" aria-hidden="true"><line x1="1" y1="6" x2="25" y2="6" stroke="${ls.color}"
      stroke-width="${Math.min(ls.width, 2.5)}" stroke-dasharray="${dash}"/><g fill="${filled ? ls.color : css("--surface")}"
      stroke="${ls.color}" stroke-width="${filled ? 0 : 2}">${mark}</g></svg><span></span>`;
    b.querySelector("span").textContent = s.name;
    b.onclick = () => {
      hidden.has(s.name) ? hidden.delete(s.name) : hidden.add(s.name);
      b.setAttribute("aria-pressed", !hidden.has(s.name));
      chart.dispatchAction({ type: hidden.has(s.name) ? "legendUnSelect" : "legendSelect", name: s.name });
    };
    b.onmouseenter = () => chart.dispatchAction({ type: "highlight", seriesName: s.name });
    b.onmouseleave = () => chart.dispatchAction({ type: "downplay", seriesName: s.name });
    box.appendChild(b);
  }
}

function renderTable() {
  const rows = DATA.marlowe.filter((p) => p.model === state.model)
    .sort((a, b) => (a.series === b.series ? 0 : a.series === "main" ? -1 : 1) || a.decode_tp - b.decode_tp || a.conc - b.conc);
  const tb = $("points").querySelector("tbody");
  tb.innerHTML = "";
  for (const p of rows) {
    const m = p.metrics;
    const tr = document.createElement("tr");
    if (p.status !== "final") tr.className = "pending";
    const lean = p.series !== "main";
    tr.innerHTML = `
      <th scope="row"><span class="swatch${lean ? " hollow" : ""}" style="background:var(--s-marlowe)"></span>MI355X TP${p.decode_tp} C${p.conc}</th>
      <td>${p.series === "main" ? "main" : "interactivity-leaning"}${p.status !== "final" ? " · <em>candidate, not charted</em>" : ""}</td>
      <td class="num">${p.num_decode_gpu}</td><td class="num">${p.conc}</td>
      <td class="num">${fmt(m.median_intvty, 1)} / ${fmt(m.p90_intvty, 1)}</td>
      <td class="num">${fmt(m.median_ttft, 3)} / ${fmt(m.p90_ttft, 3)}</td>
      <td class="num">${fmt(m.median_tpot * 1e3, 3)} / ${fmt(m.p90_tpot * 1e3, 3)}</td>
      <td class="num">${fmt(m.tput_per_gpu, 0)}</td>
      <td>${p.label}</td>
      <td><a href="${p.recipe}">recipe</a></td>`;
    tb.appendChild(tr);
  }
  const cands = rows.filter((p) => p.status !== "final");
  $("pending").textContent = cands.length ?
    `The main-series TP2 C64 point is still being chosen between ${cands.map((p) => p.label.split(", ").pop()).join(" and ")}; both candidate runs are listed above and not charted.` : "";
}

function chips(id, dim, values, labels) {
  const box = $(id);
  box.innerHTML = "";
  for (const v of values) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.textContent = labels(v);
    b.setAttribute("aria-pressed", state[dim].has(v));
    b.onclick = () => {
      state[dim].has(v) ? state[dim].delete(v) : state[dim].add(v);
      b.setAttribute("aria-pressed", state[dim].has(v));
      update();
    };
    box.appendChild(b);
  }
}

function dims() {
  const all = points(state.model);
  const hw = [...new Set(all.map((p) => p.hardware))].sort((a, b) => (AMD.has(b) - AMD.has(a)) || a.localeCompare(b));
  const fw = [...new Set(all.filter((p) => p.source === "published").map((p) => p.framework))].sort();
  return { hardware: hw, framework: fw };
}

function buildFilters() {
  const d = dims();
  if (!state.framework) state.framework = new Set(d.framework);
  chips("f-source", "source", Object.keys(SOURCES), (v) => SOURCES[v]);
  chips("f-hardware", "hardware", d.hardware, hwLabel);
  chips("f-framework", "framework", d.framework, fwLabel);
}

function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  for (const k of ["model", "x", "y", "pct"]) if (h.get(k)) state[k] = h.get(k);
  for (const k of ["logx", "logy"]) if (h.has(k)) state[k] = h.get(k) === "1";
  for (const k of ["source", "hardware", "framework"]) if (h.has(k)) state[k] = new Set(h.get(k).split(",").filter(Boolean));
  if (!METRICS[state.x]) state.x = "intvty";
  if (!METRICS[state.y]) state.y = "tput";
  if (!["p50", "p90"].includes(state.pct)) state.pct = "p50";
}
function writeHash() {
  const h = new URLSearchParams({
    model: state.model, x: state.x, y: state.y, pct: state.pct, logx: state.logx ? 1 : 0, logy: state.logy ? 1 : 0,
    source: [...state.source].join(","), hardware: [...state.hardware].join(","), framework: [...state.framework].join(","),
  });
  history.replaceState(null, "", "#" + h.toString());
}

function syncControls() {
  $("x").value = state.x;
  $("y").value = state.y;
  $("model").value = state.model;
  $("logx").checked = state.logx;
  $("logy").checked = state.logy;
  $("pct-p50").setAttribute("aria-pressed", state.pct === "p50");
  $("pct-p90").setAttribute("aria-pressed", state.pct === "p90");
  const name = (DATA.inferencex.models[state.model] || {}).api_model || state.model;
  $("model-title").textContent = name;
}

function update() {
  syncControls();
  writeHash();
  render();
}

function init(data) {
  DATA = data;
  readHash();
  const models = new Set(Object.keys(DATA.inferencex.models).concat(DATA.marlowe.map((p) => p.model)));
  for (const m of models) {
    const o = document.createElement("option");
    o.value = m;
    o.textContent = (DATA.inferencex.models[m] || {}).api_model || DATA.marlowe.find((p) => p.model === m).model_name;
    $("model").appendChild(o);
  }
  for (const id of ["x", "y"]) {
    for (const [k, d] of Object.entries(METRICS)) {
      const o = document.createElement("option");
      o.value = k;
      o.textContent = d.label;
      $(id).appendChild(o);
    }
  }
  $("model").onchange = (e) => { state.model = e.target.value; state.framework = null; buildFilters(); renderTable(); update(); };
  $("x").onchange = (e) => { state.x = e.target.value; update(); };
  $("y").onchange = (e) => { state.y = e.target.value; update(); };
  $("pct-p50").onclick = () => { state.pct = "p50"; update(); };
  $("pct-p90").onclick = () => { state.pct = "p90"; update(); };
  $("logx").onchange = (e) => { state.logx = e.target.checked; update(); };
  $("logy").onchange = (e) => { state.logy = e.target.checked; update(); };
  document.querySelectorAll("[data-all]").forEach((b) => b.onclick = () => {
    state[b.dataset.all] = new Set(dims()[b.dataset.all]); buildFilters(); update();
  });
  document.querySelectorAll("[data-none]").forEach((b) => b.onclick = () => {
    state[b.dataset.none] = new Set(); buildFilters(); update();
  });

  const ix = DATA.inferencex;
  const credit = $("credit");
  credit.innerHTML = "";
  credit.append("Published results: published by ");
  const a = document.createElement("a");
  a.href = ix.site;
  a.rel = "noopener";
  a.textContent = "InferenceX (SemiAnalysis)";
  credit.append(a, `, from its public API, snapshot of ${ix.snapshot}. Marlowe points: measured by Marlowe, ${
    [...new Set(DATA.marlowe.map((p) => p.date))].sort().join(", ")}.`);

  chart = echarts.init($("chart"), null, { renderer: "canvas" });
  chart.on("click", (prm) => {
    const p = prm.data && prm.data.p;
    if (!p || !p.url) return;
    if (p.source === "marlowe") location.href = p.url;
    else window.open(p.url, "_blank", "noopener");
  });
  window.addEventListener("resize", () => { chart.resize(); render(); });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
  buildFilters();
  renderTable();
  update();
}

fetch("data/site.json").then((r) => r.json()).then(init).catch((e) => {
  $("empty").hidden = false;
  $("empty").textContent = `Could not load the results (${e}).`;
});
