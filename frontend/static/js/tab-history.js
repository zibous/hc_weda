// static/js/tab-history.js – Tab "Verlauf"
'use strict';

import { C, makeLine, toDataset } from './charts.js';
import { API_PREFIX, showLoading } from './utils.js';

let rangeCharts = {};

function _timeOverrides(from, to) {
  const days = Math.round((new Date(to) - new Date(from)) / (1000 * 60 * 60 * 24));
  if (days > 180) {
    return { unit: 'month', displayFormats: { month: 'MMM yyyy' }, maxTicksLimit: 12 };
  }
  if (days > 30) {
    return { unit: 'week', displayFormats: { week: 'dd.MM' }, maxTicksLimit: 12 };
  }
  if (days > 2) {
    return { unit: 'day', displayFormats: { day: 'dd.MM (EEE)' }, maxTicksLimit: days + 1 };
  }
  return { unit: 'hour', displayFormats: { hour: 'HH:mm' }, maxTicksLimit: 12 };
}

export async function loadRange(from, to) {
  const hide = showLoading('tab-history');
  try {
    const data = await fetch(`${API_PREFIX}/range?from=${from}&to=${to}`).then(r => r.json());
    const destroy = id => { if (rangeCharts[id]) { rangeCharts[id].destroy(); delete rangeCharts[id]; } };
    destroy('rt'); destroy('rh'); destroy('rp'); destroy('rw'); destroy('rs');

    const ovr = _timeOverrides(from, to);
    const timeOverride = { scales: { x: { time: { unit: ovr.unit, displayFormats: ovr.displayFormats }, ticks: { maxTicksLimit: ovr.maxTicksLimit } } } };

    rangeCharts.rt = makeLine(document.getElementById('chart-range-temp'), [toDataset(data.temp, '°C', C.blue, true)], '°C', timeOverride);
    rangeCharts.rh = makeLine(document.getElementById('chart-range-hum'), [toDataset(data.humidity, '%', C.teal, true)], '%', timeOverride);
    rangeCharts.rp = makeLine(document.getElementById('chart-range-pressure'), [toDataset(data.pressure, 'hPa', C.purple, true)], 'hPa', timeOverride);
    rangeCharts.rw = makeLine(document.getElementById('chart-range-wind'), [toDataset(data.wind, 'km/h', C.green)], 'km/h', timeOverride);
    rangeCharts.rs = makeLine(document.getElementById('chart-range-solar'), [toDataset(data.solar, 'W/m²', C.yellow, true)], 'W/m²', timeOverride);
  } finally {
    hide();
  }
}
