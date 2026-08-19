// static/js/utils.js – Gemeinsame Hilfsfunktionen
'use strict';

const PREFIX = window.__URL_PREFIX || '';
export const API_PREFIX = PREFIX ? PREFIX + '/api' : '/api';

export function isoToday() { return new Date().toISOString().slice(0, 10); }
export function isoAgo(days) { const d = new Date(); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10); }
export function fmt1(v) { return (v ?? 0).toFixed(1); }

// ── Loading Spinner ─────────────────────────────────────────
const SPINNER_SVG = `<svg class="loading-spinner" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
  <circle cx="25" cy="25" r="20" fill="none" stroke-width="4" stroke-linecap="round"
    stroke="url(#spinGrad)" stroke-dasharray="90 150" stroke-dashoffset="0">
    <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="0.9s" repeatCount="indefinite"/>
  </circle>
  <defs><linearGradient id="spinGrad"><stop offset="0%" stop-color="#3b82f6"/><stop offset="100%" stop-color="#14b8a6"/></linearGradient></defs>
</svg>`;

let _styleInjected = false;
function _injectStyle() {
    if (_styleInjected) return;
    _styleInjected = true;
    const s = document.createElement('style');
    s.textContent = `
    .loading-overlay {
      position: absolute; inset: 0; z-index: 50;
      display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 10px;
      background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(2px);
      border-radius: inherit; transition: opacity .25s;
    }
    .loading-overlay .loading-spinner { width: 44px; height: 44px; }
    .loading-overlay .loading-text { font-size: .78rem; color: #94a3b8; font-weight: 500; }
    [data-theme="light"] .loading-overlay { background: rgba(255,255,255,0.75); }
  `;
    document.head.appendChild(s);
}

/**
 * Zeigt einen Loading-Spinner über einem Tab-Content-Element.
 * @param {string} tabId - ID des Tab-Content-Elements (ohne #)
 * @returns {function} hide – Funktion zum Entfernen des Spinners
 */
export function showLoading(tabId) {
    _injectStyle();
    const tab = document.getElementById(tabId);
    if (!tab) return () => { };
    tab.style.position = 'relative';
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = SPINNER_SVG + '<span class="loading-text">Daten laden…</span>';
    tab.appendChild(overlay);
    return () => { overlay.style.opacity = '0'; setTimeout(() => overlay.remove(), 250); };
}
