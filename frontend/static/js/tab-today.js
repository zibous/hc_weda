// static/js/tab-today.js – Tab "Heute"
'use strict';

import { C, timeOpts, makeLine, toDataset } from './charts.js';
import { API_PREFIX, fmt1 } from './utils.js';

export async function initTodayTab() {
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

  const windDs1 = toDataset(data.wind, 'Wind km/h', C.green, true);
  windDs1.order = 2; windDs1.pointRadius = 0;
  const windDs2 = toDataset(data.gust, 'Böen km/h', C.orange, false);
  windDs2.borderWidth = 2.5; windDs2.pointRadius = 0; windDs2.order = 1; windDs2.tension = 0.4;
  makeLine(document.getElementById('chart-today-wind'), [windDs1, windDs2], 'km/h');
  makeLine(document.getElementById('chart-today-pressure'), [toDataset(data.pressure, 'hPa', C.purple, true)], 'hPa');
  makeLine(document.getElementById('chart-today-solar'), [toDataset(data.solar, 'W/m²', C.yellow, true)], 'W/m²');
  makeLine(document.getElementById('chart-today-rain'), [toDataset(data.rain, 'Regen mm', C.blue, true)], 'mm');
}
