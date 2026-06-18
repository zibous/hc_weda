// static/js/utils.js – Gemeinsame Hilfsfunktionen
'use strict';

const PREFIX = window.__URL_PREFIX || '';
export const API_PREFIX = PREFIX ? PREFIX + '/api' : '/api';

export function isoToday() { return new Date().toISOString().slice(0, 10); }
export function isoAgo(days) { const d = new Date(); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10); }
export function fmt1(v) { return (v ?? 0).toFixed(1); }
