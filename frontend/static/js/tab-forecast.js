// static/js/tab-forecast.js – Tab "Vorhersage"
'use strict';

import { C, timeOpts, makeLine, toDataset } from './charts.js';
import { renderScale, tempColor, windColor, rainColor } from './gauges.js';
import { getAppleIcon } from './icons.js';
import { API_PREFIX, fmt1, isoToday } from './utils.js';

let forecastCharts = {};

export async function initForecastTab() {
  const data = await fetch(`${API_PREFIX}/forecast`).then(r => r.json()).catch(() => ({}));
  const container = document.getElementById('forecast-current');
  const strip = document.getElementById('forecast-hours');

  if (!data.hourly || !data.hourly.length) {
    container.innerHTML = '<div class="card"><div class="card-top"><div class="card-label">Vorhersage</div><div class="card-icon">⚠️</div></div><div class="card-sub">Keine Vorhersagedaten verfügbar</div></div>';
    return;
  }

  const cur = data.current || {};
  const h3 = data.hourly.slice(0, 6);
  const tempMin = Math.min(...h3.map(h => h.temp ?? 99));
  const tempMax = Math.max(...h3.map(h => h.temp ?? -99));
  const gustMax = Math.max(...h3.map(h => h.windGusts ?? 0));
  const rainMax = Math.max(...h3.map(h => h.precip ?? 0));
  const probMax = Math.max(...h3.map(h => h.precipProb ?? 0));

  container.innerHTML = `
    <div class="card">
      <div class="card-top"><div class="card-label">Temperatur</div><div class="card-icon">${cur.weatherIcon || getAppleIcon('thermometer', 20, 0.7)}</div></div>
      <div class="card-main"><div class="card-value">${fmt1(cur.temp)}<span class="unit">°C</span></div><span class="card-badge">${cur.weatherText || ''}</span></div>
      <div class="card-sub">Gefühlt <b>${fmt1(cur.feelsLike)} °C</b></div>
      <div class="card-sub">6h: ${fmt1(tempMin)}° … ${fmt1(tempMax)}°</div>
      <div class="scale-bar" id="scale-fc-temp"></div>
      <div class="scale-labels"><span>-10°</span><span>0°</span><span>20°</span><span>40°</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Feuchte</div><div class="card-icon">${getAppleIcon('droplet', 20, 0.7)}</div></div>
      <div class="card-main"><div class="card-value">${cur.humidity ?? '–'}<span class="unit">%</span></div></div>
      <div class="card-sub">Bewölkung <b>${cur.cloudCover ?? '–'} %</b></div>
      <div class="progress-bar"><div class="fill" style="width:${cur.humidity ?? 0}%;background:${(cur.humidity ?? 0) > 70 ? C.blue : C.teal}"></div></div>
      <div class="scale-labels"><span>0%</span><span>50%</span><span>100%</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Wind</div><div class="card-icon">${getAppleIcon('wind', 20, 0.7)}</div></div>
      <div class="card-main"><div class="card-value">${fmt1(cur.windSpeed)}<span class="unit">km/h</span></div></div>
      <div class="card-sub">Böen max <b>${fmt1(gustMax)} km/h</b> (6h)</div>
      <div class="scale-bar" id="scale-fc-wind"></div>
      <div class="scale-labels"><span>0</span><span>20</span><span>40</span><span>60+</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Niederschlag</div><div class="card-icon">${getAppleIcon('rain', 20, 0.7)}</div></div>
      <div class="card-main"><div class="card-value">${fmt1(rainMax)}<span class="unit">mm</span></div><span class="card-badge">${probMax}% Wahrsch.</span></div>
      <div class="card-sub">Max. nächste 6 Stunden</div>
      <div class="scale-bar" id="scale-fc-rain"></div>
      <div class="scale-labels"><span>0</span><span>5</span><span>10</span><span>20+</span></div>
    </div>
    <div class="card">
      <div class="card-top"><div class="card-label">Luftdruck</div><div class="card-icon">${getAppleIcon('gauge', 20, 0.7)}</div></div>
      <div class="card-main"><div class="card-value">${fmt1(cur.pressure)}<span class="unit">hPa</span></div></div>
      <div class="progress-bar"><div class="fill" style="width:${Math.max(0, Math.min(100, ((cur.pressure ?? 1013) - 980) / 60 * 100))}%;background:${C.purple}"></div></div>
      <div class="scale-labels"><span>980</span><span>1010</span><span>1040</span></div>
    </div>`;

  renderScale('scale-fc-temp', cur.temp, -10, 40, 10, tempColor);
  renderScale('scale-fc-wind', cur.windSpeed, 0, 60, 8, windColor);
  renderScale('scale-fc-rain', rainMax, 0, 20, 8, rainColor);

  const nowHour = new Date().getHours();
  strip.innerHTML = data.hourly.map(h => {
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

  const hourly = data.hourly;
  const destroy = id => { if (forecastCharts[id]) { forecastCharts[id].destroy(); delete forecastCharts[id]; } };
  destroy('ft'); destroy('fr'); destroy('fw');

  forecastCharts.ft = makeLine(document.getElementById('chart-forecast-temp'), [
    toDataset(hourly.map(h => [h.time, h.temp]), 'Temperatur °C', C.blue, true),
    toDataset(hourly.map(h => [h.time, h.feelsLike]), 'Gefühlt °C', C.orange)
  ], '°C');

  const rainOpts = timeOpts();
  rainOpts.scales.y = { grid: { color: C.grid }, title: { display: true, text: 'mm', color: C.muted }, position: 'left', min: 0 };
  rainOpts.scales.y1 = { grid: { display: false }, title: { display: true, text: '%', color: C.muted }, position: 'right', min: 0, max: 100 };
  forecastCharts.fr = new Chart(document.getElementById('chart-forecast-rain'), {
    type: 'line', data: {
      datasets: [
        toDataset(hourly.map(h => [h.time, h.precip]), 'Niederschlag mm', C.blue, true, 'y'),
        toDataset(hourly.map(h => [h.time, h.precipProb]), 'Wahrsch. %', C.teal, false, 'y1'),
      ]
    }, options: rainOpts
  });

  forecastCharts.fw = makeLine(document.getElementById('chart-forecast-wind'), [
    toDataset(hourly.map(h => [h.time, h.windSpeed]), 'Wind km/h', C.green),
    toDataset(hourly.map(h => [h.time, h.windGusts]), 'Böen km/h', C.yellow)
  ], 'km/h');
}
