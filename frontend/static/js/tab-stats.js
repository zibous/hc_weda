// static/js/tab-stats.js – Tab "Statistik"
'use strict';

import { C, CHART_OPTS_BASE, makeBar } from './charts.js';
import { API_PREFIX, showLoading } from './utils.js';

let statsCharts = {};

export async function loadStats(from, to) {
  const hide = showLoading('tab-stats');
  try {
    const [rows, monthly] = await Promise.all([
      fetch(`${API_PREFIX}/stats?from=${from}&to=${to}`).then(r => r.json()),
      fetch(`${API_PREFIX}/rain/monthly?from=${from}&to=${to}`).then(r => r.json()),
    ]);

    const destroy = id => { if (statsCharts[id]) { statsCharts[id].destroy(); delete statsCharts[id]; } };
    const daysDiff = Math.round((new Date(to) - new Date(from)) / (1000 * 60 * 60 * 24));

    const statsOpts = JSON.parse(JSON.stringify(CHART_OPTS_BASE));
    if (daysDiff > 180) {
      statsOpts.scales.x.time.unit = 'month';
      statsOpts.scales.x.time.displayFormats.month = 'MMM yyyy';
      statsOpts.scales.x.ticks.maxTicksLimit = 12;
    } else if (daysDiff > 60) {
      statsOpts.scales.x.time.unit = 'week';
      statsOpts.scales.x.ticks.maxTicksLimit = 10;
    } else {
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

    document.getElementById('stats-tbody').innerHTML = rows.slice().reverse().map(r =>
      `<tr><td>${r.day}</td><td style="color:${C.teal}">${r.temp_min ?? '–'}</td><td style="color:${C.red}">${r.temp_max ?? '–'}</td><td>${r.temp_avg ?? '–'}</td><td>${r.hum_min ?? '–'}</td><td>${r.hum_max ?? '–'}</td><td>${r.wind_max ?? '–'}</td><td>${r.gust_max ?? '–'}</td><td style="color:${C.blue}">${r.rain_day ?? '–'}</td><td>${r.solar_max ?? '–'}</td><td>${r.uv_max ?? '–'}</td></tr>`
    ).join('');
  } finally {
    hide();
  }
}
