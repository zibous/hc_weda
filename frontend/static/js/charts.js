// static/js/charts.js – Chart.js Konfiguration und Helpers
'use strict';

export const C = {
  blue: '#3b82f6', teal: '#14b8a6', green: '#22c55e', orange: '#f97316',
  yellow: '#eab308', purple: '#a855f7', red: '#ef4444', muted: '#8892a4',
  grid: 'rgba(46,51,80,.6)',
};

// Chart-Defaults
Chart.defaults.color = C.muted;
Chart.defaults.borderColor = C.grid;
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.locale = 'de-DE';

export const CHART_OPTS_BASE = {
  responsive: true, maintainAspectRatio: false, animation: { duration: 400 },
  plugins: { legend: { labels: { boxWidth: 12, padding: 14 } }, tooltip: { backgroundColor: '#1a1d27', borderColor: '#2e3350', borderWidth: 1, padding: 10 } },
  scales: {
    x: {
      type: 'time',
      time: { tooltipFormat: 'dd.MM.yyyy HH:mm', displayFormats: { hour: 'HH:mm', day: 'dd.MM', month: 'MMM yyyy' } },
      grid: { color: C.grid },
      ticks: { maxRotation: 45, minRotation: 45, autoSkip: true, maxTicksLimit: 12, source: 'auto' }
    },
    y: { grid: { color: C.grid } }
  },
};

export function timeOpts(extra = {}) {
  return JSON.parse(JSON.stringify({ ...CHART_OPTS_BASE, ...extra }));
}

export function makeLine(ctx, datasets, yLabel = '', overrides = {}) {
  const opts = timeOpts();
  opts.scales.y.title = { display: !!yLabel, text: yLabel, color: C.muted };
  if (overrides.scales?.x?.time) {
    Object.assign(opts.scales.x.time, overrides.scales.x.time);
    if (overrides.scales.x.time.displayFormats) {
      Object.assign(opts.scales.x.time.displayFormats, overrides.scales.x.time.displayFormats);
    }
  }
  if (overrides.scales?.x?.ticks) {
    Object.assign(opts.scales.x.ticks, overrides.scales.x.ticks);
  }
  return new Chart(ctx, { type: 'line', data: { datasets }, options: opts });
}

export function makeBar(ctx, labels, data, color, yLabel = '') {
  return new Chart(ctx, {
    type: 'bar', data: { labels, datasets: [{ data, backgroundColor: color + 'cc', borderColor: color, borderWidth: 1 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: { duration: 400 }, plugins: { legend: { display: false } },
      scales: { x: { grid: { color: C.grid } }, y: { grid: { color: C.grid }, title: { display: !!yLabel, text: yLabel, color: C.muted } } }
    }
  });
}

export function toDataset(series, label, color, fill = false, yAxisID = 'y') {
  return {
    label, data: series.map(([t, v]) => ({ x: t, y: v })), borderColor: color,
    backgroundColor: fill ? color + '22' : color + '00', borderWidth: 1.5,
    pointRadius: series.length > 200 ? 0 : 1.5, pointHoverRadius: 4, tension: 0.3, fill, yAxisID
  };
}
