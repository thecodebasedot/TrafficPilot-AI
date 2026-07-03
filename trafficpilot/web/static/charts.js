/* Tiny dependency-free canvas charts for TrafficPilot AI. */
(function (global) {
  "use strict";

  function setup(canvas) {
    const dpr = global.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || canvas.width;
    const h = canvas.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    return { ctx, w, h };
  }

  function niceMax(v) {
    if (v <= 0) return 1;
    const pow = Math.pow(10, Math.floor(Math.log10(v)));
    return Math.ceil(v / pow) * pow;
  }

  /* Multi-series line/area chart.
     series: [{ name, color, data:[numbers], fill:bool }]  */
  function lineChart(canvas, labels, series, opts) {
    opts = opts || {};
    const { ctx, w, h } = setup(canvas);
    const padL = 46, padR = 12, padT = 12, padB = 24;
    const plotW = w - padL - padR, plotH = h - padT - padB;

    let max = 0;
    series.forEach((s) => s.data.forEach((v) => { if (v != null) max = Math.max(max, v); }));
    max = niceMax(max);
    const n = labels.length;
    const x = (i) => padL + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW);
    const y = (v) => padT + plotH - (v / max) * plotH;

    ctx.clearRect(0, 0, w, h);

    // grid + y labels
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.fillStyle = "#8b98ad";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (let g = 0; g <= 4; g++) {
      const gy = padT + (g / 4) * plotH;
      ctx.beginPath();
      ctx.moveTo(padL, gy);
      ctx.lineTo(w - padR, gy);
      ctx.stroke();
      const val = max * (1 - g / 4);
      ctx.fillText(fmtShort(val), padL - 8, gy);
    }

    // x labels (first, middle, last)
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    [0, Math.floor(n / 2), n - 1].forEach((i) => {
      if (labels[i]) ctx.fillText(String(labels[i]).slice(5), x(i), h - padB + 6);
    });

    series.forEach((s) => {
      // indices of the values that are actually present (skip null gaps)
      const pts = s.data.map((v, i) => (v == null ? null : i)).filter((i) => i != null);
      if (!pts.length) return;

      if (s.fill) {
        const grad = ctx.createLinearGradient(0, padT, 0, padT + plotH);
        grad.addColorStop(0, hexA(s.color, 0.35));
        grad.addColorStop(1, hexA(s.color, 0));
        ctx.beginPath();
        ctx.moveTo(x(pts[0]), y(s.data[pts[0]]));
        pts.forEach((i) => ctx.lineTo(x(i), y(s.data[i])));
        ctx.lineTo(x(pts[pts.length - 1]), padT + plotH);
        ctx.lineTo(x(pts[0]), padT + plotH);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();
      }

      ctx.beginPath();
      let started = false;
      s.data.forEach((v, i) => {
        if (v == null) { started = false; return; }
        if (!started) { ctx.moveTo(x(i), y(v)); started = true; }
        else ctx.lineTo(x(i), y(v));
      });
      ctx.strokeStyle = s.color;
      ctx.lineWidth = s.dashed ? 2 : 2.2;
      if (s.dashed) ctx.setLineDash([6, 5]);
      ctx.stroke();
      ctx.setLineDash([]);
    });
  }

  /* Circular gauge for a 0-100 score. */
  function gauge(canvas, value, label) {
    const { ctx, w, h } = setup(canvas);
    const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 12;
    const start = Math.PI * 0.75, end = Math.PI * 2.25;
    const frac = Math.max(0, Math.min(1, value / 100));

    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 12;
    ctx.lineCap = "round";

    ctx.beginPath();
    ctx.arc(cx, cy, r, start, end);
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.stroke();

    const grad = ctx.createLinearGradient(0, 0, w, h);
    grad.addColorStop(0, "#4f8cff");
    grad.addColorStop(1, "#22d3a6");
    ctx.beginPath();
    ctx.arc(cx, cy, r, start, start + (end - start) * frac);
    ctx.strokeStyle = grad;
    ctx.stroke();

    ctx.fillStyle = "#e6ebf2";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "bold 34px sans-serif";
    ctx.fillText(Math.round(value), cx, cy - 4);
    ctx.font = "12px sans-serif";
    ctx.fillStyle = "#8b98ad";
    ctx.fillText(label || "", cx, cy + 22);
  }

  function fmtShort(v) {
    if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
    if (v >= 1e3) return (v / 1e3).toFixed(0) + "k";
    return String(Math.round(v));
  }

  function hexA(hex, a) {
    const c = hex.replace("#", "");
    const n = parseInt(c.length === 3 ? c.replace(/(.)/g, "$1$1") : c, 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }

  global.TPCharts = { lineChart, gauge, fmtShort };
})(window);
