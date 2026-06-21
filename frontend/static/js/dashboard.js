/* ============================================================
   Dashboard JS – Wetterstation (v2 – Modular)
   ============================================================ */
'use strict';

import { initDateSelector } from './dateselector.js';
import { isoAgo, isoToday } from './utils.js';
import { initCurrentTab, refreshCurrent } from './tab-current.js';
import { initTodayTab } from './tab-today.js';
import { initForecastTab } from './tab-forecast.js';
import { loadRange } from './tab-history.js';
import { loadStats } from './tab-stats.js';
import { C } from './charts.js';
import { initCardIcons } from './card-icons.js';
import { getAppleIcon } from './icons.js';

// ── Theme Toggle ────────────────────────────────────────────
(function () {
  const btn = document.getElementById('theme-toggle');
  const saved = localStorage.getItem('theme') || 'dark';

  function setThemeIcon(theme) {
    // Zeige das Icon der "anderen" Seite als Hinweis wohin gewechselt wird
    btn.innerHTML = getAppleIcon(theme === 'dark' ? 'sun' : 'moon', 18, 1.0);
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.classList.toggle('light', theme === 'light');
    setThemeIcon(theme);
    Chart.defaults.color = theme === 'light' ? '#64748b' : '#8892a4';
    Chart.defaults.borderColor = theme === 'light' ? 'rgba(0,0,0,.08)' : 'rgba(46,51,80,.6)';
  }

  applyTheme(saved);

  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem('theme', next);
  });
})();

// ── Colorpicker ─────────────────────────────────────────────
(function () {
  const picker = document.getElementById('bg-picker');
  const pickerBtn = document.getElementById('bg-picker-btn');
  const savedBg = localStorage.getItem('dashboardBg');
  if (savedBg) { document.body.style.background = savedBg; picker.value = savedBg; }
  if (pickerBtn) {
    pickerBtn.innerHTML = getAppleIcon('palette', 18, 1.0);
    pickerBtn.addEventListener('click', () => picker.click());
  }  
})();

// ── DateSelector State ──────────────────────────────────────
let dsFrom = isoAgo(7);
let dsTo = isoToday();

function initNavDateSelector() {
  const container = document.getElementById('dateSelectorNav');
  if (!container) return;

  const activeTab = localStorage.getItem('activeTab') || 'current';
  container.style.display = (activeTab === 'history' || activeTab === 'stats') ? 'block' : 'none';

  initDateSelector(container, (from, to) => {
    dsFrom = from;
    dsTo = to;
    reloadActiveDateTab();
  });
}

function reloadActiveDateTab() {
  const activeTab = document.querySelector('.tab.active')?.dataset.tab;
  if (activeTab === 'history') loadRange(dsFrom, dsTo);
  else if (activeTab === 'stats') loadStats(dsFrom, dsTo);
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

  const dsContainer = document.getElementById('dateSelectorNav');
  if (dsContainer) {
    dsContainer.style.display = (name === 'history' || name === 'stats') ? 'block' : 'none';
  }

  if (!tabCharts[name]) { tabCharts[name] = true; initTab(name); }
  else if (name === 'history' || name === 'stats') { reloadActiveDateTab(); }
  localStorage.setItem('activeTab', name);
}

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ── Tab-Dispatcher ──────────────────────────────────────────
function initTab(name) {
  if (name === 'today') initTodayTab();
  if (name === 'forecast') initForecastTab();
  if (name === 'history') loadRange(dsFrom, dsTo);
  if (name === 'stats') loadStats(dsFrom, dsTo);
}

// ── Init ────────────────────────────────────────────────────
initCardIcons();
initNavDateSelector();
initCurrentTab();
refreshCurrent();

const savedTab = localStorage.getItem('activeTab');
if (savedTab && savedTab !== 'current') {
  switchTab(savedTab);
}

// ── Auto-Refresh ────────────────────────────────────────────
setInterval(async () => { await refreshCurrent(); await initCurrentTab(); }, 60_000);

// ─── App Info ───────────────────────────────────────────────
console.info(
  '%c ⚡ Wetterdaten Dashboard %c v2.5.0 ',
  'color:#fff;background:#e94560;padding:4px 8px;border-radius:4px 0 0 4px;font-size:11px',
  'color:#1a1a2e;background:#a8dadc;padding:4px 8px;border-radius:0 4px 4px 0;font-size:11px'
);
