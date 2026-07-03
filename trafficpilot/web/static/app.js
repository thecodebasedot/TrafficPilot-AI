/* TrafficPilot AI dashboard front-end. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const fmt = (n) => Number(n).toLocaleString();
  const money = (n) => "$" + Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 });

  const KPI_DEFS = [
    { key: "total_traffic", label: "Total Traffic", fmt: fmt },
    { key: "organic_traffic", label: "Organic", fmt: fmt },
    { key: "paid_traffic", label: "Paid", fmt: fmt },
    { key: "referral_traffic", label: "Referral", fmt: fmt },
    { key: "conversion_rate", label: "Conversion Rate", fmt: (v) => v + "%" },
    { key: "bounce_rate", label: "Bounce Rate", fmt: (v) => v + "%", invert: true },
    { key: "page_speed", label: "Page Speed", fmt: (v) => v + "s", invert: true },
    { key: "avg_keyword_rank", label: "Avg Keyword Rank", fmt: (v) => "#" + v, invert: true },
  ];

  function deltaClass(delta, invert) {
    if (!delta) return "flat";
    const good = invert ? delta < 0 : delta > 0;
    return good ? "up" : "down";
  }
  function deltaText(delta) {
    const arrow = delta > 0 ? "▲" : delta < 0 ? "▼" : "→";
    return `${arrow} ${Math.abs(delta)}%`;
  }

  function renderKpis(k) {
    $("live-visitors").textContent = fmt(k.live_visitors);
    const grid = $("kpi-grid");
    grid.innerHTML = "";
    KPI_DEFS.forEach((d) => {
      const item = k[d.key];
      if (!item) return;
      const el = document.createElement("div");
      el.className = "kpi";
      el.innerHTML =
        `<div class="label">${d.label}</div>` +
        `<div class="value">${d.fmt(item.value)}</div>` +
        `<div class="delta ${deltaClass(item.delta, d.invert)}">${deltaText(item.delta)} vs last week</div>`;
      grid.appendChild(el);
    });
  }

  function legend(el, items) {
    el.innerHTML = items
      .map((i) => `<span><span class="dot" style="background:${i.color}"></span>${i.name}</span>`)
      .join("");
  }

  function renderTraffic(ts) {
    const series = [
      { name: "Organic", color: "#22d3a6", data: ts.organic, fill: true },
      { name: "Paid", color: "#4f8cff", data: ts.paid },
      { name: "Referral", color: "#b28dff", data: ts.referral },
      { name: "Direct", color: "#ffb020", data: ts.direct },
    ];
    TPCharts.lineChart($("trafficChart"), ts.dates, series);
    legend($("trafficLegend"), series);
  }

  function renderSales(sf) {
    const histLabels = sf.history_dates.map((d) => d.slice(5));
    const fcLabels = sf.forecast_days.map((d) => "+" + d + "d");
    const labels = histLabels.concat(fcLabels);
    const H = histLabels.length, F = fcLabels.length;
    const lastActual = sf.history_sales[H - 1];

    // actual: real history, then nothing. forecast: starts at the seam (last
    // actual point) so the dashed line connects cleanly to the solid line.
    const actual = sf.history_sales.concat(new Array(F).fill(null));
    const forecast = new Array(H - 1).fill(null).concat([lastActual], sf.forecast_sales);

    const series = [
      { name: "Sales (actual)", color: "#22d3a6", data: actual, fill: true },
      { name: "Sales (forecast)", color: "#4f8cff", data: forecast, dashed: true },
    ];
    TPCharts.lineChart($("salesChart"), labels, series);
    legend($("salesLegend"), series);
  }

  function renderSeo(seo) {
    TPCharts.gauge($("seoGauge"), seo.breakdown.overall, "Grade " + seo.breakdown.grade);
    const comp = seo.breakdown.components;
    $("seoComponents").innerHTML = Object.keys(comp)
      .map(
        (k) =>
          `<div class="seo-row"><span class="name">${k.replace(/_/g, " ")}</span>` +
          `<span class="track"><span class="fill" style="width:${comp[k]}%"></span></span>` +
          `<span>${comp[k]}</span></div>`
      )
      .join("");
    const idx = seo.index_status;
    const badge = idx.status === "healthy" ? "ok" : "warn";
    $("indexStatus").innerHTML =
      `<b>Google Index:</b> <span class="badge ${badge}">${idx.status}</span> — ` +
      `${fmt(idx.indexed_pages)} pages indexed (${idx.coverage_pct}% coverage)` +
      (idx.warnings.length ? `<ul>${idx.warnings.map((w) => `<li>${w}</li>`).join("")}</ul>` : "");
  }

  function renderDrivers(drivers) {
    const max = Math.max.apply(null, drivers.map((d) => d.importance));
    $("drivers").innerHTML = drivers
      .map(
        (d) =>
          `<div class="bar-row"><span class="bname">${d.feature.replace(/_/g, " ")}</span>` +
          `<span class="btrack"><span class="bfill" style="width:${(d.importance / max) * 100}%"></span></span>` +
          `<span class="bval">${(d.importance * 100).toFixed(0)}%</span></div>`
      )
      .join("");
  }

  function renderSegments(segments) {
    $("segments").innerHTML = segments
      .map(
        (s) =>
          `<div class="segment"><div class="stitle">${s.label}</div>` +
          `<div class="sshare">${fmt(s.visitors)} visitors · ${s.share_pct}%</div>` +
          `<div class="srow"><span>Sessions</span><b>${s.sessions}</b></div>` +
          `<div class="srow"><span>Avg duration</span><b>${Math.round(s.avg_session_duration)}s</b></div>` +
          `<div class="srow"><span>Pages/session</span><b>${s.pages_per_session}</b></div>` +
          `<div class="srow"><span>Total spend</span><b>${money(s.total_spend)}</b></div>` +
          `<div class="srow"><span>Recency</span><b>${Math.round(s.recency_days)}d</b></div></div>`
      )
      .join("");
  }

  function renderKeywords(rows) {
    const head =
      "<tr><th>Keyword</th><th class='num'>Volume</th><th class='num'>Rank</th>" +
      "<th class='num'>Difficulty</th><th>Priority</th></tr>";
    const body = rows
      .map(
        (r) =>
          `<tr><td>${r.keyword}</td><td class="num">${fmt(r.search_volume)}</td>` +
          `<td class="num">#${r.current_rank}</td><td class="num">${r.difficulty}</td>` +
          `<td><span class="pill ${r.priority}">${r.priority}</span></td></tr>`
      )
      .join("");
    $("keywordTable").innerHTML = head + body;
  }

  function renderCompetitors(c) {
    const rows = c.table;
    const head =
      "<tr><th>Site</th><th class='num'>Traffic/mo</th><th class='num'>DA</th>" +
      "<th class='num'>Backlinks</th><th class='num'>Avg Rank</th><th class='num'>Speed</th></tr>";
    const body = rows
      .map(
        (r) =>
          `<tr class="${r.site === "Your Site" ? "you" : ""}"><td>${r.site}</td>` +
          `<td class="num">${fmt(r.monthly_traffic)}</td><td class="num">${r.domain_authority}</td>` +
          `<td class="num">${fmt(r.backlinks)}</td><td class="num">#${r.avg_keyword_rank}</td>` +
          `<td class="num">${r.page_speed}s</td></tr>`
      )
      .join("");
    $("competitorTable").innerHTML = head + body;
  }

  function renderRecs(recs) {
    $("recommendations").innerHTML = recs
      .map(
        (r) =>
          `<div class="rec ${r.priority}"><div class="rtop">` +
          `<span class="rtitle">${r.title}</span><span class="pill ${r.priority}">${r.priority}</span></div>` +
          `<div class="rcat">${r.category}</div>` +
          `<div class="rdetail">${r.detail}</div>` +
          `<div class="rimpact">↗ ${r.expected_impact}</div></div>`
      )
      .join("");
  }

  function renderMeta(m) {
    const p = m.predictor;
    $("modelMeta").textContent =
      `Models — Traffic R²=${p.total_traffic.r2.toFixed(2)} · ` +
      `Conversion R²=${p.conversion_rate.r2.toFixed(2)} · ` +
      `Sales R²=${p.sales.r2.toFixed(2)} · ` +
      `Segmentation silhouette=${(m.segmenter_silhouette || 0).toFixed(2)}`;
  }

  async function load() {
    try {
      const res = await fetch("/api/dashboard");
      const d = await res.json();
      renderKpis(d.kpis);
      renderTraffic(d.traffic_series);
      renderSales(d.sales_forecast);
      renderSeo(d.seo);
      renderDrivers(d.drivers);
      renderSegments(d.segments);
      renderKeywords(d.keywords);
      renderCompetitors(d.competitors);
      renderRecs(d.recommendations);
      renderMeta(d.model_metrics);
      $("loading").hidden = true;
      $("content").hidden = false;
    } catch (e) {
      $("loading").textContent = "Failed to load analytics: " + e.message;
      console.error(e);
    }
  }

  window.addEventListener("DOMContentLoaded", load);
  window.addEventListener("resize", () => {
    // re-fetch is cheap here; simply reload data to redraw at new size
    if (!$("content").hidden) load();
  });
})();
