/* ============================================================
   Dashboard JS – Wetterstation (v2 – Gauge-Kacheln)
   ============================================================ */
'use strict';

const PREFIX = window.__URL_PREFIX || '';
const API_PREFIX = PREFIX ? PREFIX + '/api' : '/api';

// ── Theme Toggle ────────────────────────────────────────────
(function () {
  const btn = document.getElementById('theme-toggle');
  const saved = localStorage.getItem('theme') || 'dark';
  if (saved === 'light') { document.body.classList.add('light'); btn.textContent = '☀️'; }
  btn.addEventListener('click', () => {
    const isLight = document.body.classList.toggle('light');
    btn.textContent = isLight ? '☀️' : '🌙';
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    Chart.defaults.color = isLight ? '#64748b' : '#8892a4';
    Chart.defaults.borderColor = isLight ? 'rgba(0,0,0,.08)' : 'rgba(46,51,80,.6)';
  });
})();

// ── Colorpicker ─────────────────────────────────────────────
(function () {
  const picker = document.getElementById('bg-picker');
  const savedBg = localStorage.getItem('dashboardBg');
  if (savedBg) { document.body.style.background = savedBg; picker.value = savedBg; }
  picker.addEventListener('input', e => {
    document.body.style.background = e.target.value;
    localStorage.setItem('dashboardBg', e.target.value);
  });
})();

// ── Farben ──────────────────────────────────────────────────
const C = {
  blue: '#3b82f6', teal: '#14b8a6', green: '#22c55e', orange: '#f97316',
  yellow: '#eab308', purple: '#a855f7', red: '#ef4444', muted: '#8892a4',
  grid: 'rgba(46,51,80,.6)',
};

// ── Chart-Defaults ──────────────────────────────────────────
Chart.defaults.color = C.muted;
Chart.defaults.borderColor = C.grid;
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 11;

// Deutsche Lokalisierung für Chart.js (24h Format)
Chart.defaults.locale = 'de-DE';

const CHART_OPTS_BASE = {
  responsive: true, maintainAspectRatio: false, animation: { duration: 400 },
  plugins: { legend: { labels: { boxWidth: 12, padding: 14 } }, tooltip: { backgroundColor: '#1a1d27', borderColor: '#2e3350', borderWidth: 1, padding: 10 } },
  scales: {
    x: {
      type: 'time',
      time: {
        tooltipFormat: 'dd.MM.yyyy HH:mm',
        displayFormats: {
          hour: 'HH:mm',
          day: 'dd.MM',
          month: 'MMM yyyy'
        }
      },
      grid: { color: C.grid },
      ticks: {
        maxRotation: 45,
        minRotation: 45,
        autoSkip: true,
        maxTicksLimit: 12,
        source: 'auto'
      }
    },
    y: { grid: { color: C.grid } }
  },
};
function timeOpts(extra = {}) { return JSON.parse(JSON.stringify({ ...CHART_OPTS_BASE, ...extra })); }
function makeLine(ctx, datasets, yLabel = '') {
  const opts = timeOpts();
  opts.scales.y.title = { display: !!yLabel, text: yLabel, color: C.muted };
  return new Chart(ctx, { type: 'line', data: { datasets }, options: opts });
}
function makeBar(ctx, labels, data, color, yLabel = '') {
  return new Chart(ctx, {
    type: 'bar', data: { labels, datasets: [{ data, backgroundColor: color + 'cc', borderColor: color, borderWidth: 1 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: { duration: 400 }, plugins: { legend: { display: false } },
      scales: { x: { grid: { color: C.grid } }, y: { grid: { color: C.grid }, title: { display: !!yLabel, text: yLabel, color: C.muted } } }
    }
  });
}
function toDataset(series, label, color, fill = false, yAxisID = 'y') {
  return {
    label, data: series.map(([t, v]) => ({ x: t, y: v })), borderColor: color,
    backgroundColor: fill ? color + '22' : color + '00', borderWidth: 1.5,
    pointRadius: series.length > 200 ? 0 : 1.5, pointHoverRadius: 4, tension: 0.3, fill, yAxisID
  };
}

// ── Tabs ────────────────────────────────────────────────────
const tabCharts = {};

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  const btn = document.querySelector(`.tab[data-tab="${name}"]`);
  if (btn) btn.classList.add('active');
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.classList.add('active');
  if (!tabCharts[name]) { tabCharts[name] = true; initTab(name); }
  localStorage.setItem('activeTab', name);
}

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ── Hilfsfunktionen ─────────────────────────────────────────
function isoToday() { return new Date().toISOString().slice(0, 10); }
function isoAgo(days) { const d = new Date(); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10); }
function fmt1(v) { return (v ?? 0).toFixed(1); }

// ══════════════════════════════════════════════════════════════
// SKALEN-FUNKTIONEN für die Gauge-Kacheln
// ══════════════════════════════════════════════════════════════

/** Segment-Balken: füllt N Segmente basierend auf Wert in einem Bereich */
function renderScale(id, value, min, max, segments, colorFn) {
  const el = document.getElementById(id);
  if (!el || value == null) return;
  el.innerHTML = '';
  const range = max - min;
  const pos = Math.max(0, Math.min(1, (value - min) / range));
  const activeCount = Math.round(pos * segments);
  for (let i = 0; i < segments; i++) {
    const seg = document.createElement('div');
    seg.className = 'seg' + (i < activeCount ? ' active ' + (colorFn ? colorFn(i, segments) : '') : '');
    el.appendChild(seg);
  }
}

// Farb-Funktionen für verschiedene Skalen
function tempColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'blue';
  if (p < 0.5) return 'teal';
  if (p < 0.7) return 'green';
  if (p < 0.85) return 'orange';
  return 'red';
}
function humColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'orange';   // trocken
  if (p < 0.6) return 'green';    // normal
  if (p < 0.8) return 'teal';     // feucht
  return 'blue';                   // sehr feucht
}
function windColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'green';
  if (p < 0.5) return 'teal';
  if (p < 0.7) return 'yellow';
  if (p < 0.85) return 'orange';
  return 'red';
}
function rainColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'teal';
  if (p < 0.6) return 'blue';
  return 'purple';
}
function uvColor(i, n) {
  const p = i / n;
  if (p < 0.25) return 'green';
  if (p < 0.5) return 'yellow';
  if (p < 0.7) return 'orange';
  return 'red';
}

/** Progress-Bar: setzt Breite + Farbe */
function setProgress(id, value, min, max, color) {
  const el = document.getElementById(id);
  if (!el) return;
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  el.style.width = pct + '%';
  if (color) el.style.background = color;
}

// ══════════════════════════════════════════════════════════════
// TAB: AKTUELL
// ══════════════════════════════════════════════════════════════
let chartTodayTemp = null;

async function initCurrentTab() {
  const data = await fetch(`${API_PREFIX}/today`).then(r => r.json());
  const ctx = document.getElementById('chart-today-temp');
  if (!ctx) return;
  if (chartTodayTemp) chartTodayTemp.destroy();
  chartTodayTemp = makeLine(ctx, [
    toDataset(data.temp, 'Außen °C', C.blue, true),
    toDataset(data.indoor_temp, 'Innen °C', C.orange),
  ], '°C');
}

async function refreshCurrent() {
  const [d, s, summary] = await Promise.all([
    fetch(`${API_PREFIX}/current`).then(r => r.json()),
    fetch(`${API_PREFIX}/dbstats`).then(r => r.json()),
    fetch(`${API_PREFIX}/today/summary`).then(r => r.json()).catch(() => ({})),
  ]);

  // Werte setzen
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.childNodes[0].textContent = val; };
  set('c-temp', fmt1(d.temp_c));
  set('c-indoor-temp', fmt1(d.indoor_temp_c));
  set('c-hum', d.humidity ?? 0);
  set('c-wind', fmt1(d.windspeed_kmh));
  set('c-pressure', fmt1(d.pressure_hpa));
  set('c-rain', fmt1(d.daily_rain_mm));
  set('c-solar', fmt1(d.solar_klux));
  set('c-feels', fmt1(d.feels_like_c));

  // Zusätzliche Felder
  const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setText('c-indoor-hum', `${d.indoorhumidity ?? 0} %`);
  setText('c-abs-pressure', fmt1(d.abs_pressure_hpa));
  setText('c-feels-sub', `${fmt1(d.feels_like_c)} °C`);
  setText('c-dewpoint', `${fmt1(d.dewpoint_c)} °C`);
  setText('c-uv', d.uv ?? 0);
  setText('c-uv-text', d.uv < 3 ? 'niedrig' : d.uv < 6 ? 'mittel' : d.uv < 8 ? 'hoch' : 'sehr hoch');
  setText('c-rain-week', fmt1(d.weekly_rain_mm));
  setText('c-rain-month', fmt1(d.monthly_rain_mm));
  setText('c-windchill', `${fmt1(d.windchill_c)} °C`);
  setText('c-frost-text', d.frost_text || '–');
  setText('c-gust-text', d.beaufort_text || '–');
  setText('c-bft-text', d.beaufort_text || '–');
  setText('c-bft-badge', `Bft ${d.beaufort ?? 0}`);
  setText('c-gust', `${fmt1(d.windgust_kmh)} km/h`);
  setText('c-wind-dir-text', d.wind_dir_text || '–');
  setText('c-wind-dir-deg', d.winddir ?? 0);
  setText('c-compare', d.temp_diff_c ? `${d.temp_diff_c > 0 ? '+' : ''}${fmt1(d.temp_diff_c)} °C Differenz` : '–');
  setText('c-climate', d.climate_advice || '–');
  setText('c-ventilation', d.humidity > 60 ? 'Lüften empfohlen' : d.humidity < 30 ? 'Luftbefeuchter empfohlen' : 'Luftfeuchte optimal');

  const needle = document.getElementById('compass-needle');
  if (needle) needle.style.transform = `rotate(${d.winddir ?? 0}deg)`;
  const lu = document.getElementById('last-update');
  if (lu) lu.textContent = d.dateutc ?? '';
  const dbInfo = document.querySelector('.db-info');
  if (dbInfo) dbInfo.textContent = `${s.total ?? 0} Messungen \u00a0|\u00a0 seit ${(s.oldest ?? '').slice(0, 10) || '\u2013'}`;

  // Trends
  updateTrend('c-temp-trend', summary.temp_trend);
  updateTrend('c-hum-trend', summary.hum_trend);
  updateTrend('c-pressure-trend', summary.pressure_trend);

  // Min/Max
  updateMinMax('c-temp-minmax', summary.temp_min, summary.temp_max, summary.temp_avg);
  updateMinMax('c-hum-minmax', summary.hum_min, summary.hum_max, summary.hum_avg);
  updateMinMax('c-wind-minmax', null, summary.wind_max, summary.wind_avg);
  updateMinMax('c-pressure-minmax', summary.pressure_min, summary.pressure_max, summary.pressure_avg);

  // ── Skalen aktualisieren ──
  renderScale('scale-temp', d.temp_c, -20, 45, 12, tempColor);
  renderScale('scale-hum', d.humidity, 0, 100, 10, humColor);
  renderScale('scale-wind', d.windspeed_kmh, 0, 80, 10, windColor);
  renderScale('scale-rain', d.daily_rain_mm, 0, 50, 10, rainColor);
  renderScale('scale-uv', d.uv, 0, 12, 10, uvColor);

  // Progress-Bars
  setProgress('bar-indoor', d.indoor_temp_c ?? 20, 15, 30, d.indoor_temp_c > 25 ? C.red : d.indoor_temp_c < 18 ? C.blue : C.orange);
  setProgress('bar-pressure', d.pressure_hpa ?? 1013, 980, 1040, C.purple);
  setProgress('bar-feels', d.feels_like_c ?? 15, -10, 45, d.feels_like_c < 0 ? C.blue : d.feels_like_c > 30 ? C.red : C.teal);

  // Feuchte-Badge
  const humBadge = document.getElementById('c-hum-badge');
  if (humBadge) {
    const h = d.humidity ?? 0;
    if (h < 30) humBadge.textContent = 'trocken';
    else if (h < 60) humBadge.textContent = 'normal';
    else if (h < 80) humBadge.textContent = 'feucht';
    else humBadge.textContent = 'sehr feucht';
  }

  // Lüftung + Kartenfarbe
  updateVentilation(d.humidity > 60 ? 'Lüften empfohlen' : d.humidity < 30 ? 'Luftbefeuchter empfohlen' : 'Luftfeuchte optimal');

  // Innen/Außen Vergleich
  const cmp = document.getElementById('c-compare');
  if (cmp) cmp.textContent = d.temp_diff_c ? `${d.temp_diff_c > 0 ? '+' : ''}${fmt1(d.temp_diff_c)} °C Differenz` : '–';
  const clm = document.getElementById('c-climate');
  if (clm) clm.innerHTML = '<b>' + (d.climate_advice ?? '') + '</b>';
}

function updateTrend(id, trend) {
  const el = document.getElementById(id);
  if (!el || !trend) return;
  el.textContent = trend;
  el.className = 'card-trend';
  if (trend === '↑') el.classList.add('up');
  else if (trend === '↓') el.classList.add('down');
}

function updateMinMax(id, min, max, avg) {
  const el = document.getElementById(id);
  if (!el) return;
  const parts = [];
  if (min != null) parts.push(`<span>Min <span class="val">${min}</span></span>`);
  if (max != null) parts.push(`<span>Max <span class="val">${max}</span></span>`);
  if (avg != null) parts.push(`<span>⌀ <span class="val">${avg}</span></span>`);
  el.innerHTML = parts.join('');
}

function updateVentilation(text) {
  const el = document.getElementById('c-ventilation');
  if (el && text) el.textContent = text;
}

// ══════════════════════════════════════════════════════════════
// TAB: HEUTE
// ══════════════════════════════════════════════════════════════
async function initTodayTab() {
  const [data, summary] = await Promise.all([
    fetch(`${API_PREFIX}/today`).then(r => r.json()),
    fetch(`${API_PREFIX}/today/summary`).then(r => r.json()).catch(() => ({})),
  ]);
  const bar = document.getElementById('today-summary');
  if (bar && summary.count) {
    bar.innerHTML = `
      <div class="summary-item"><div class="summary-label">Temperatur</div><div class="summary-value" style="color:${C.blue}">${summary.temp_avg ?? '–'} °C</div><div class="summary-detail">${summary.temp_min ?? '–'} … ${summary.temp_max ?? '–'} °C ${summary.temp_trend ?? '→'}</div></div>
      <div class="summary-item"><div class="summary-label">Feuchte</div><div class="summary-value" style="color:${C.teal}">${summary.hum_avg ?? '–'} %</div><div class="summary-detail">${summary.hum_min ?? '–'} … ${summary.hum_max ?? '–'} % ${summary.hum_trend ?? '→'}</div></div>
      <div class="summary-item"><div class="summary-label">Luftdruck</div><div class="summary-value" style="color:${C.purple}">${summary.pressure_avg ?? '–'} hPa</div><div class="summary-detail">${summary.pressure_min ?? '–'} … ${summary.pressure_max ?? '–'} ${summary.pressure_trend ?? '→'}</div></div>
      <div class="summary-item"><div class="summary-label">Wind max</div><div class="summary-value" style="color:${C.green}">${summary.wind_max ?? '–'} km/h</div><div class="summary-detail">⌀ ${summary.wind_avg ?? '–'} km/h | Böe ${summary.gust_max ?? '–'}</div></div>
      <div class="summary-item"><div class="summary-label">Regen</div><div class="summary-value" style="color:${C.blue}">${summary.rain_total ?? '0'} mm</div><div class="summary-detail">&nbsp;</div></div>
      <div class="summary-item"><div class="summary-label">Solar max</div><div class="summary-value" style="color:${C.yellow}">${summary.solar_max ?? '–'} W/m²</div><div class="summary-detail">UV max ${summary.uv_max ?? '–'}</div></div>`;
  }
  const optsDouble = timeOpts();
  optsDouble.scales.y = { grid: { color: C.grid }, title: { display: true, text: '°C', color: C.muted }, position: 'left' };
  optsDouble.scales.y1 = { grid: { display: false }, title: { display: true, text: '%', color: C.muted }, position: 'right' };
  new Chart(document.getElementById('chart-today-full'), {
    type: 'line', data: {
      datasets: [
        toDataset(data.temp, 'Außen °C', C.blue, true, 'y'), toDataset(data.indoor_temp, 'Innen °C', C.orange, false, 'y'),
        toDataset(data.humidity, 'Feuchte %', C.teal, false, 'y1'), toDataset(data.indoor_hum, 'Innen %', C.muted, false, 'y1'),
      ]
    }, options: optsDouble
  });
  // Wind-Chart: Wind als Fläche, Böen als deutliche Linie
  const windDataset1 = toDataset(data.wind, 'Wind km/h', C.green, true);
  windDataset1.order = 2; // Hinter Böen
  windDataset1.pointRadius = 0;
  const windDataset2 = toDataset(data.gust, 'Böen km/h', C.orange, false);
  windDataset2.borderWidth = 2.5;
  windDataset2.pointRadius = 0;
  windDataset2.order = 1; // Vor Wind
  windDataset2.tension = 0.4; // Glattere Linie
  makeLine(document.getElementById('chart-today-wind'), [windDataset1, windDataset2], 'km/h');
  makeLine(document.getElementById('chart-today-pressure'), [toDataset(data.pressure, 'hPa', C.purple, true)], 'hPa');
  makeLine(document.getElementById('chart-today-solar'), [toDataset(data.solar, 'W/m²', C.yellow, true)], 'W/m²');
  makeLine(document.getElementById('chart-today-rain'), [toDataset(data.rain, 'Regen mm', C.blue, true)], 'mm');
}

// ══════════════════════════════════════════════════════════════
// TAB: VORHERSAGE
// ══════════════════════════════════════════════════════════════
let forecastCharts = {};
async function initForecastTab() {
  const data = await fetch(`${API_PREFIX}/forecast`).then(r => r.json()).catch(() => ({}));
  const container = document.getElementById('forecast-current');
  const strip = document.getElementById('forecast-hours');

  if (!data.hourly || !data.hourly.length) {
    container.innerHTML = '<div class="card"><div class="card-top"><div class="card-label">Vorhersage</div><div class="card-icon">⚠️</div></div><div class="card-sub">Keine Vorhersagedaten verfügbar</div></div>';
    return;
  }

  // ── Gauge-Kacheln (gleicher Stil wie Aktuell) ──
  const cur = data.current || {};
  const h3 = data.hourly.slice(0, 6);  // nächste 6h für Min/Max
  const tempMin = Math.min(...h3.map(h => h.temp ?? 99));
  const tempMax = Math.max(...h3.map(h => h.temp ?? -99));
  const windMax = Math.max(...h3.map(h => h.windSpeed ?? 0));
  const gustMax = Math.max(...h3.map(h => h.windGusts ?? 0));
  const rainMax = Math.max(...h3.map(h => h.precip ?? 0));
  const probMax = Math.max(...h3.map(h => h.precipProb ?? 0));

  container.innerHTML = `
    <div class="card">
      <div class="card-top"><div class="card-label">Temperatur</div><div class="card-icon">${cur.weatherIcon || '🌡️'}</div></div>
      <div class="card-main"><div class="card-value">${fmt1(cur.temp)}<span class="unit">°C</span></div><span class="card-badge">${cur.weatherText || ''}</span></div>
      <div class="card-sub">Gefühlt <b>${fmt1(cur.feelsLike)} °C</b></div>
      <div class="card-sub">6h: ${fmt1(tempMin)}° … ${fmt1(tempMax)}°</div>
      <div class="scale-bar" id="scale-fc-temp"></div>
      <div class="scale-labels"><span>-10°</span><span>0°</span><span>20°</span><span>40°</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Feuchte</div><div class="card-icon">💧</div></div>
      <div class="card-main"><div class="card-value">${cur.humidity ?? '–'}<span class="unit">%</span></div></div>
      <div class="card-sub">Bewölkung <b>${cur.cloudCover ?? '–'} %</b></div>
      <div class="progress-bar"><div class="fill" style="width:${cur.humidity ?? 0}%;background:${(cur.humidity ?? 0) > 70 ? C.blue : C.teal}"></div></div>
      <div class="scale-labels"><span>0%</span><span>50%</span><span>100%</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Wind</div><div class="card-icon">🌬️</div></div>
      <div class="card-main"><div class="card-value">${fmt1(cur.windSpeed)}<span class="unit">km/h</span></div></div>
      <div class="card-sub">Böen max <b>${fmt1(gustMax)} km/h</b> (6h)</div>
      <div class="scale-bar" id="scale-fc-wind"></div>
      <div class="scale-labels"><span>0</span><span>20</span><span>40</span><span>60+</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Niederschlag</div><div class="card-icon">🌧️</div></div>
      <div class="card-main"><div class="card-value">${fmt1(rainMax)}<span class="unit">mm</span></div><span class="card-badge">${probMax}% Wahrsch.</span></div>
      <div class="card-sub">Max. nächste 6 Stunden</div>
      <div class="scale-bar" id="scale-fc-rain"></div>
      <div class="scale-labels"><span>0</span><span>5</span><span>10</span><span>20+</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Luftdruck</div><div class="card-icon">📊</div></div>
      <div class="card-main"><div class="card-value">${fmt1(cur.pressure)}<span class="unit">hPa</span></div></div>
      <div class="progress-bar"><div class="fill" style="width:${Math.max(0, Math.min(100, ((cur.pressure ?? 1013) - 980) / 60 * 100))}%;background:${C.purple}"></div></div>
      <div class="scale-labels"><span>980</span><span>1010</span><span>1040</span></div>
    </div>`;

  // Skalen für Forecast-Kacheln
  renderScale('scale-fc-temp', cur.temp, -10, 40, 10, tempColor);
  renderScale('scale-fc-wind', cur.windSpeed, 0, 60, 8, windColor);
  renderScale('scale-fc-rain', rainMax, 0, 20, 8, rainColor);

  // ── Stündliche Scroll-Leiste (kompakt) ──
  const nowHour = new Date().getHours();
  const hours48 = data.hourly;
  strip.innerHTML = hours48.map(h => {
    const hh = h.time ? parseInt(h.time.slice(11, 13)) : -1;
    const day = h.time ? h.time.slice(8, 10) : '';
    const isNow = (hh === nowHour && h.time && h.time.slice(0, 10) === isoToday());
    const showDay = hh === 0;
    const rain = (h.precip ?? 0) > 0 ? `${h.precip}mm` : `${h.precipProb ?? 0}%`;
    return `<div class="hh${isNow ? ' now' : ''}">
      <div class="hh-time">${showDay ? day + '.' : ''}${String(hh).padStart(2, '0')}:00</div>
      <div class="hh-icon">${h.weatherIcon || ''}</div>
      <div class="hh-temp">${fmt1(h.temp)}°</div>
      <div class="hh-rain">${rain}</div>
    </div>`;
  }).join('');

  // ── Charts ──
  const hourly = data.hourly;
  const destroy = id => { if (forecastCharts[id]) { forecastCharts[id].destroy(); delete forecastCharts[id]; } };
  destroy('ft'); destroy('fr'); destroy('fw');
  forecastCharts.ft = makeLine(document.getElementById('chart-forecast-temp'), [toDataset(hourly.map(h => [h.time, h.temp]), 'Temperatur °C', C.blue, true), toDataset(hourly.map(h => [h.time, h.feelsLike]), 'Gefühlt °C', C.orange)], '°C');
  const rainOpts = timeOpts();
  rainOpts.scales.y = { grid: { color: C.grid }, title: { display: true, text: 'mm', color: C.muted }, position: 'left', min: 0 };
  rainOpts.scales.y1 = { grid: { display: false }, title: { display: true, text: '%', color: C.muted }, position: 'right', min: 0, max: 100 };
  forecastCharts.fr = new Chart(document.getElementById('chart-forecast-rain'), {
    type: 'line', data: {
      datasets: [
        toDataset(hourly.map(h => [h.time, h.precip]), 'Niederschlag mm', C.blue, true, 'y'), toDataset(hourly.map(h => [h.time, h.precipProb]), 'Wahrsch. %', C.teal, false, 'y1'),
      ]
    }, options: rainOpts
  });
  forecastCharts.fw = makeLine(document.getElementById('chart-forecast-wind'), [toDataset(hourly.map(h => [h.time, h.windSpeed]), 'Wind km/h', C.green), toDataset(hourly.map(h => [h.time, h.windGusts]), 'Böen km/h', C.yellow)], 'km/h');
}

// ══════════════════════════════════════════════════════════════
// TAB: VERLAUF
// ══════════════════════════════════════════════════════════════
let rangeCharts = {};
async function loadRange() {
  const from = document.getElementById('range-from').value || isoAgo(7);
  const to = document.getElementById('range-to').value || isoToday();
  const data = await fetch(`${API_PREFIX}/range?from=${from}&to=${to}`).then(r => r.json());
  const destroy = id => { if (rangeCharts[id]) { rangeCharts[id].destroy(); delete rangeCharts[id]; } };
  destroy('rt'); destroy('rh'); destroy('rp'); destroy('rw'); destroy('rs');
  rangeCharts.rt = makeLine(document.getElementById('chart-range-temp'), [toDataset(data.temp, '°C', C.blue, true)], '°C');
  rangeCharts.rh = makeLine(document.getElementById('chart-range-hum'), [toDataset(data.humidity, '%', C.teal, true)], '%');
  rangeCharts.rp = makeLine(document.getElementById('chart-range-pressure'), [toDataset(data.pressure, 'hPa', C.purple, true)], 'hPa');
  rangeCharts.rw = makeLine(document.getElementById('chart-range-wind'), [toDataset(data.wind, 'km/h', C.green)], 'km/h');
  rangeCharts.rs = makeLine(document.getElementById('chart-range-solar'), [toDataset(data.solar, 'W/m²', C.yellow, true)], 'W/m²');
}
function initHistoryTab() {
  document.getElementById('range-from').value = isoAgo(7);
  document.getElementById('range-to').value = isoToday();
  document.getElementById('btn-load-range').addEventListener('click', loadRange);
  document.querySelectorAll('.btn-preset').forEach(b => {
    b.addEventListener('click', () => {
      // Entferne "active" von allen Buttons
      document.querySelectorAll('.btn-preset').forEach(btn => btn.classList.remove('active'));
      // Setze "active" auf geklickten Button
      b.classList.add('active');

      document.getElementById('range-from').value = isoAgo(+b.dataset.days);
      document.getElementById('range-to').value = isoToday();
      loadRange();
    });
  });
  // Setze 7 Tage als Standard-aktiv
  document.querySelector('.btn-preset[data-days="7"]')?.classList.add('active');
  loadRange();
}

// ══════════════════════════════════════════════════════════════
// TAB: STATISTIK
// ══════════════════════════════════════════════════════════════
let statsCharts = {};
async function loadStats() {
  const from = document.getElementById('stats-from').value || isoAgo(30);
  const to = document.getElementById('stats-to').value || isoToday();
  const [rows, monthly] = await Promise.all([
    fetch(`${API_PREFIX}/stats?from=${from}&to=${to}`).then(r => r.json()),
    fetch(`${API_PREFIX}/rain/monthly`).then(r => r.json()),
  ]);
  const days = rows.map(r => r.day);
  const destroy = id => { if (statsCharts[id]) { statsCharts[id].destroy(); delete statsCharts[id]; } };

  // Berechne Zeitraum in Tagen
  const daysDiff = Math.round((new Date(to) - new Date(from)) / (1000 * 60 * 60 * 24));

  // Dynamische X-Achsen-Konfiguration basierend auf Zeitraum
  const statsOpts = JSON.parse(JSON.stringify(CHART_OPTS_BASE));
  if (daysDiff > 180) {
    // > 6 Monate: Monatliche Labels
    statsOpts.scales.x.time.unit = 'month';
    statsOpts.scales.x.time.displayFormats.month = 'MMM yyyy';
    statsOpts.scales.x.ticks.maxTicksLimit = 12;
  } else if (daysDiff > 60) {
    // > 2 Monate: Wöchentliche Labels
    statsOpts.scales.x.time.unit = 'week';
    statsOpts.scales.x.ticks.maxTicksLimit = 10;
  } else {
    // <= 2 Monate: Tägliche Labels (Standard)
    statsOpts.scales.x.time.unit = 'day';
    statsOpts.scales.x.ticks.maxTicksLimit = 15;
  }

  destroy('st');
  statsCharts.st = new Chart(document.getElementById('chart-stats-temp'), {
    type: 'line', data: {
      datasets: [
        { label: 'Max', data: rows.map(r => ({ x: r.day, y: r.temp_max })), borderColor: C.red, backgroundColor: C.red + '11', borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: false },
        { label: 'Avg', data: rows.map(r => ({ x: r.day, y: r.temp_avg })), borderColor: C.blue, backgroundColor: C.blue + '22', borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: '-1' },
        { label: 'Min', data: rows.map(r => ({ x: r.day, y: r.temp_min })), borderColor: C.teal, backgroundColor: C.teal + '11', borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: false },
      ]
    }, options: statsOpts
  });

  // Bar-Charts mit gleicher X-Achsen-Konfiguration
  const barOpts = JSON.parse(JSON.stringify(statsOpts));
  barOpts.plugins.legend = { display: false };
  barOpts.scales.y.title = { display: true, text: 'mm', color: C.muted };

  destroy('sr');
  statsCharts.sr = new Chart(document.getElementById('chart-stats-rain'), {
    type: 'bar',
    data: { datasets: [{ data: rows.map(r => ({ x: r.day, y: r.rain_day ?? 0 })), backgroundColor: C.blue + 'cc', borderColor: C.blue, borderWidth: 1 }] },
    options: barOpts
  });

  destroy('sw');
  const windOpts = JSON.parse(JSON.stringify(statsOpts));
  windOpts.plugins.legend = { display: false };
  windOpts.scales.y.title = { display: true, text: 'km/h', color: C.muted };
  statsCharts.sw = new Chart(document.getElementById('chart-stats-wind'), {
    type: 'bar',
    data: { datasets: [{ data: rows.map(r => ({ x: r.day, y: r.wind_max ?? 0 })), backgroundColor: C.green + 'cc', borderColor: C.green, borderWidth: 1 }] },
    options: windOpts
  });

  destroy('sm');
  const mM = monthly.map(r => r.month).reverse();
  statsCharts.sm = makeBar(document.getElementById('chart-monthly-rain'), mM, monthly.map(r => r.rain_total ?? 0).reverse(), C.teal, 'mm');
  document.getElementById('stats-tbody').innerHTML = rows.slice().reverse().map(r => `<tr><td>${r.day}</td><td style="color:${C.teal}">${r.temp_min ?? '–'}</td><td style="color:${C.red}">${r.temp_max ?? '–'}</td><td>${r.temp_avg ?? '–'}</td><td>${r.hum_min ?? '–'}</td><td>${r.hum_max ?? '–'}</td><td>${r.wind_max ?? '–'}</td><td>${r.gust_max ?? '–'}</td><td style="color:${C.blue}">${r.rain_day ?? '–'}</td><td>${r.solar_max ?? '–'}</td><td>${r.uv_max ?? '–'}</td></tr>`).join('');
}
function initStatsTab() {
  document.getElementById('stats-from').value = isoAgo(30);
  document.getElementById('stats-to').value = isoToday();
  document.getElementById('btn-load-stats').addEventListener('click', loadStats);
  document.querySelectorAll('.btn-preset-stats').forEach(b => {
    b.addEventListener('click', () => {
      // Entferne "active" von allen Buttons
      document.querySelectorAll('.btn-preset-stats').forEach(btn => btn.classList.remove('active'));
      // Setze "active" auf geklickten Button
      b.classList.add('active');

      const days = +b.dataset.days;
      document.getElementById('stats-from').value = isoAgo(days);
      document.getElementById('stats-to').value = isoToday();
      loadStats();
    });
  });
  // Setze 30 Tage als Standard-aktiv
  document.querySelector('.btn-preset-stats[data-days="30"]')?.classList.add('active');
  loadStats();
}

// ── Tab-Dispatcher ──────────────────────────────────────────
function initTab(name) {
  if (name === 'today') initTodayTab();
  if (name === 'forecast') initForecastTab();
  if (name === 'history') initHistoryTab();
  if (name === 'stats') initStatsTab();
}

// ── Init ────────────────────────────────────────────────────
initCurrentTab();
refreshCurrent();

// Gespeicherten Tab wiederherstellen
const savedTab = localStorage.getItem('activeTab');
if (savedTab && savedTab !== 'current') {
  switchTab(savedTab);
}

// ─── App Info ───────────────────────────────────────────
console.info(
  '%c ⚡ Wetterdaten Dashboard %c ESM v2.3.0 ',
  'color:#fff;background:#e94560;padding:4px 8px;border-radius:4px 0 0 4px;font-size:11px',
  'color:#1a1a2e;background:#a8dadc;padding:4px 8px;border-radius:0 4px 4px 0;font-size:11px'
);

setInterval(async () => { await refreshCurrent(); await initCurrentTab(); }, 60_000);
