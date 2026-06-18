// static/js/tab-current.js – Tab "Aktuell"
'use strict';

import { C, makeLine, toDataset } from './charts.js';
import { renderScale, setProgress, tempColor, humColor, windColor, rainColor, uvColor } from './gauges.js';
import { API_PREFIX, fmt1, isoToday } from './utils.js';

let chartTodayTemp = null;

export async function initCurrentTab() {
  const data = await fetch(`${API_PREFIX}/today`).then(r => r.json());
  const ctx = document.getElementById('chart-today-temp');
  if (!ctx) return;
  if (chartTodayTemp) chartTodayTemp.destroy();
  chartTodayTemp = makeLine(ctx, [
    toDataset(data.temp, 'Außen °C', C.blue, true),
    toDataset(data.indoor_temp, 'Innen °C', C.orange),
  ], '°C');
}

export async function refreshCurrent() {
  const [d, s, summary] = await Promise.all([
    fetch(`${API_PREFIX}/current`).then(r => r.json()),
    fetch(`${API_PREFIX}/dbstats`).then(r => r.json()),
    fetch(`${API_PREFIX}/today/summary`).then(r => r.json()).catch(() => ({})),
  ]);

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.childNodes[0].textContent = val; };
  set('c-temp', fmt1(d.temp_c));
  set('c-indoor-temp', fmt1(d.indoor_temp_c));
  set('c-hum', d.humidity ?? 0);
  set('c-wind', fmt1(d.windspeed_kmh));
  set('c-pressure', fmt1(d.pressure_hpa));
  set('c-rain', fmt1(d.daily_rain_mm));
  set('c-solar', fmt1(d.solar_klux));
  set('c-feels', fmt1(d.feels_like_c));

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

  updateTrend('c-temp-trend', summary.temp_trend);
  updateTrend('c-hum-trend', summary.hum_trend);
  updateTrend('c-pressure-trend', summary.pressure_trend);
  updateMinMax('c-temp-minmax', summary.temp_min, summary.temp_max, summary.temp_avg);
  updateMinMax('c-hum-minmax', summary.hum_min, summary.hum_max, summary.hum_avg);
  updateMinMax('c-wind-minmax', null, summary.wind_max, summary.wind_avg);
  updateMinMax('c-pressure-minmax', summary.pressure_min, summary.pressure_max, summary.pressure_avg);

  renderScale('scale-temp', d.temp_c, -20, 45, 12, tempColor);
  renderScale('scale-hum', d.humidity, 0, 100, 10, humColor);
  renderScale('scale-wind', d.windspeed_kmh, 0, 80, 10, windColor);
  renderScale('scale-rain', d.daily_rain_mm, 0, 50, 10, rainColor);
  renderScale('scale-uv', d.uv, 0, 12, 10, uvColor);

  setProgress('bar-indoor', d.indoor_temp_c ?? 20, 15, 30, d.indoor_temp_c > 25 ? C.red : d.indoor_temp_c < 18 ? C.blue : C.orange);
  setProgress('bar-pressure', d.pressure_hpa ?? 1013, 980, 1040, C.purple);
  setProgress('bar-feels', d.feels_like_c ?? 15, -10, 45, d.feels_like_c < 0 ? C.blue : d.feels_like_c > 30 ? C.red : C.teal);

  const humBadge = document.getElementById('c-hum-badge');
  if (humBadge) {
    const h = d.humidity ?? 0;
    humBadge.textContent = h < 30 ? 'trocken' : h < 60 ? 'normal' : h < 80 ? 'feucht' : 'sehr feucht';
  }
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
