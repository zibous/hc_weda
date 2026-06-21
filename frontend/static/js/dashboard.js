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

// ── Theme Toggle & Synchronisation ──────────────────────────
(function () {
  // Synchronisierter Start über das projektweite health-theme oder Altwert
  const saved = localStorage.getItem('health-theme') || localStorage.getItem('theme') || 'dark';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.classList.toggle('light', theme === 'light');

    // Text im Footer absolut null-pointer-sicher aktualisieren
    const footerBtn = document.getElementById('themeToggleFooter');
    if (footerBtn) {
      footerBtn.innerHTML = theme === 'dark' ? '☀️ Helles Design' : '🌙 Dunkles Design';
    }

    // Chart.js defaults für beide Farbwelten optimieren
    if (typeof Chart !== 'undefined') {
      Chart.defaults.color = theme === 'light' ? '#64748b' : '#8892a4';
      Chart.defaults.borderColor = theme === 'light' ? 'rgba(0,0,0,.08)' : 'rgba(46,51,80,.6)';

      // Bestehende Diagramme bei Bedarf direkt aktualisieren
      Object.values(Chart.instances || {}).forEach(chart => chart.update('none'));
    }
  }

  // Initial beim App-Start ausführen
  applyTheme(saved);

  // 🌟 FIX: Globaler Klick-Abfänger registrieren (Fehlersicher bei dynamischen DOM-Wechseln)
  document.addEventListener('click', (event) => {
    if (event.target && event.target.id === 'themeToggleFooter') {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem('theme', next);
      localStorage.setItem('health-theme', next); // Projektweite Brücke
    }
  });

  // Text-Zustand beim fertigen Laden absichern
  document.addEventListener('DOMContentLoaded', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const footerBtn = document.getElementById('themeToggleFooter');
    if (footerBtn) {
      footerBtn.innerHTML = current === 'dark' ? '☀️ Helles Design' : '🌙 Dunkles Design';
    }
  });
})();

// ── Colorpicker (Bereinigt von gelöschten DOM-Elementen) ─────
(function () {
  const savedBg = localStorage.getItem('dashboardBg');
  if (savedBg) { document.body.style.background = savedBg; }
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
