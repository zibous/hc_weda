// static/js/tab-history.js – Tab "Verlauf"
'use strict';

import { C, makeLine, toDataset } from './charts.js';
import { API_PREFIX } from './utils.js';

let rangeCharts = {};

export async function loadRange(from, to) {
  const data = await fetch(`${API_PREFIX}/range?from=${from}&to=${to}`).then(r => r.json());
  const destroy = id => { if (rangeCharts[id]) { rangeCharts[id].destroy(); delete rangeCharts[id]; } };
  destroy('rt'); destroy('rh'); destroy('rp'); destroy('rw'); destroy('rs');
  rangeCharts.rt = makeLine(document.getElementById('chart-range-temp'), [toDataset(data.temp, '°C', C.blue, true)], '°C');
  rangeCharts.rh = makeLine(document.getElementById('chart-range-hum'), [toDataset(data.humidity, '%', C.teal, true)], '%');
  rangeCharts.rp = makeLine(document.getElementById('chart-range-pressure'), [toDataset(data.pressure, 'hPa', C.purple, true)], 'hPa');
  rangeCharts.rw = makeLine(document.getElementById('chart-range-wind'), [toDataset(data.wind, 'km/h', C.green)], 'km/h');
  rangeCharts.rs = makeLine(document.getElementById('chart-range-solar'), [toDataset(data.solar, 'W/m²', C.yellow, true)], 'W/m²');
}
