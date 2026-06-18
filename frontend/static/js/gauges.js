// static/js/gauges.js – Skalen- und Gauge-Funktionen
'use strict';

export function renderScale(id, value, min, max, segments, colorFn) {
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

export function setProgress(id, value, min, max, color) {
  const el = document.getElementById(id);
  if (!el) return;
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  el.style.width = pct + '%';
  if (color) el.style.background = color;
}

export function tempColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'blue';
  if (p < 0.5) return 'teal';
  if (p < 0.7) return 'green';
  if (p < 0.85) return 'orange';
  return 'red';
}

export function humColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'orange';
  if (p < 0.6) return 'green';
  if (p < 0.8) return 'teal';
  return 'blue';
}

export function windColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'green';
  if (p < 0.5) return 'teal';
  if (p < 0.7) return 'yellow';
  if (p < 0.85) return 'orange';
  return 'red';
}

export function rainColor(i, n) {
  const p = i / n;
  if (p < 0.3) return 'teal';
  if (p < 0.6) return 'blue';
  return 'purple';
}

export function uvColor(i, n) {
  const p = i / n;
  if (p < 0.25) return 'green';
  if (p < 0.5) return 'yellow';
  if (p < 0.7) return 'orange';
  return 'red';
}
