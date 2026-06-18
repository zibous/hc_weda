// static/js/dateselector.js
import { getAppleIcon } from './icons.js';

const RELATIVE_PERIODS = {
    'Letzte 7 Tage': '7tage',
    'Letzte 30 Tage': '30tage',
    'Letzte 90 Tage': '90tage',
    'Dieser Monat': 'monat'
};

const STORAGE_KEY = 'weda-period-label';

function calcRange(key) {
    const now = new Date();
    let f = new Date(), t = new Date();
    f.setHours(0, 0, 0, 0);
    t.setHours(23, 59, 59, 999);

    switch (key) {
        case '7tage': f.setDate(now.getDate() - 6); break;
        case '30tage': f.setDate(now.getDate() - 29); break;
        case '90tage': f.setDate(now.getDate() - 89); break;
        case 'monat': f.setDate(1); break;
    }
    return { from: fmtDate(f), to: fmtDate(t) };
}

function fmtDate(d) {
    return d.getFullYear() + '-' +
        String(d.getMonth() + 1).padStart(2, '0') + '-' +
        String(d.getDate()).padStart(2, '0');
}

export function initDateSelector(container, onPeriodChange) {
    let savedLabel = localStorage.getItem(STORAGE_KEY) || 'Letzte 7 Tage';

    if (!RELATIVE_PERIODS[savedLabel] && !savedLabel.startsWith('Jahr ') && savedLabel !== 'Individuell') {
        savedLabel = 'Letzte 7 Tage';
    }

    const currentYear = new Date().getFullYear();
    let yearOptions = '';
    for (let y = currentYear; y >= 2024; y--) {
        yearOptions += `<option value="${y}">Jahr ${y}</option>`;
    }

    if (!document.getElementById('ds-styles')) {
        const style = document.createElement('style');
        style.id = 'ds-styles';
        style.textContent = `
            .ds-wrap { position: relative; display: inline-flex; align-items: center; gap: 8px; }
            .ds-label { font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; }
            .ds-btn {
                padding: 6px 14px; border-radius: 8px;
                border: 1px solid var(--border, #334155); background: var(--bg2, #1e293b);
                color: var(--text, #e2e8f0); cursor: pointer; font-size: .82rem; font-weight: 600; font-family: inherit;
            }
            .ds-btn::after { content: " ▾"; opacity: .6; }
            .ds-dropdown {
                position: absolute;
                top: calc(100% + 6px);
                right: 0;
                min-width: 220px;
                border-radius: 12px;
                padding: 6px;
                z-index: 9999;
                max-height: 420px;
                overflow-y: auto;
                box-shadow: 0 16px 48px rgba(0,0,0,.6);
                background: var(--bg2, #1e293b);
                border: 1px solid var(--border, #334155);
            }
            .ds-dropdown.hidden { display: none; }
            .ds-section { font-size: .7rem; font-weight: 700; color: var(--text-muted); padding: 8px 12px 2px; text-transform: uppercase; letter-spacing: .5px; }
            .ds-item { padding: 8px 12px; border-radius: 8px; font-size: .85rem; color: var(--text, #e2e8f0); cursor: pointer; }
            .ds-item:hover { background: rgba(255,255,255,.05); }
            .ds-item.active { background: var(--accent-blue, #3b82f6); color: #fff; font-weight: 600; }
            .ds-select { width: calc(100% - 24px); margin: 4px 12px; padding: 6px; border-radius: 6px; border: 1px solid var(--border, #334155); background: var(--bg3, #0f172a); color: var(--text, #e2e8f0); font-size: .82rem; }
            .ds-custom { padding: 8px 12px; display: none; }
            .ds-custom.show { display: flex; flex-direction: column; gap: 6px; }
            .ds-custom input { padding: 6px; border-radius: 6px; border: 1px solid var(--border, #334155); background: var(--bg3, #0f172a); color: var(--text, #e2e8f0); font-size: .82rem; font-family: inherit; }
            .ds-custom button { padding: 6px; border-radius: 6px; border: none; background: var(--accent-blue, #3b82f6); color: #fff; font-size: .82rem; cursor: pointer; font-weight: 600; }
        `;
        document.head.appendChild(style);
    }

    const wrap = document.createElement('div');
    wrap.className = 'ds-wrap';
    wrap.innerHTML = `
        <span class="ds-label">${getAppleIcon('calendar', 14, 0.7, 5)} Zeitraum</span>
        <button class="ds-btn" id="dsBtn">${savedLabel}</button>
        <div class="ds-dropdown hidden" id="dsDrop">
            <div class="ds-section">Zeitraum</div>
            <div class="ds-item" data-key="7tage">Letzte 7 Tage</div>
            <div class="ds-item" data-key="30tage">Letzte 30 Tage</div>
            <div class="ds-item" data-key="90tage">Letzte 90 Tage</div>
            <div class="ds-item" data-key="monat">Dieser Monat</div>
            <div class="ds-section">Archiv</div>
            <select class="ds-select" id="dsYear">
                <option value="">Jahr auswählen…</option>
                ${yearOptions}
            </select>
            <div class="ds-section" style="cursor:pointer; margin-top:5px;" id="dsCustomToggle">Benutzerdefiniert…</div>
            <div class="ds-custom" id="dsCustom">
                <input type="date" id="dsFrom">
                <input type="date" id="dsTo">
                <button id="dsApply">Anwenden</button>
            </div>
        </div>
    `;

    container.appendChild(wrap);

    const btn = wrap.querySelector('#dsBtn');
    const drop = wrap.querySelector('#dsDrop');
    const yearSel = wrap.querySelector('#dsYear');
    const customToggle = wrap.querySelector('#dsCustomToggle');
    const customBox = wrap.querySelector('#dsCustom');
    const fromInput = wrap.querySelector('#dsFrom');
    const toInput = wrap.querySelector('#dsTo');
    const applyBtn = wrap.querySelector('#dsApply');

    btn.addEventListener('click', (e) => { e.stopPropagation(); drop.classList.toggle('hidden'); });
    document.addEventListener('click', () => drop.classList.add('hidden'));
    drop.addEventListener('click', (e) => e.stopPropagation());

    customToggle.addEventListener('click', () => customBox.classList.toggle('show'));

    function fire(label, start, end) {
        savedLabel = label;
        localStorage.setItem(STORAGE_KEY, label);
        btn.textContent = label;
        drop.classList.add('hidden');

        drop.querySelectorAll('.ds-item').forEach(el => {
            el.classList.toggle('active', el.textContent.trim() === label);
        });

        onPeriodChange(start, end);
    }

    drop.querySelectorAll('.ds-item').forEach(item => {
        item.addEventListener('click', () => {
            const key = item.getAttribute('data-key');
            const range = calcRange(key);
            fire(item.textContent.trim(), range.from, range.to);
        });
    });

    yearSel.addEventListener('change', () => {
        if (!yearSel.value) return;
        const y = yearSel.value;
        fire(`Jahr ${y}`, `${y}-01-01`, `${y}-12-31`);
    });

    applyBtn.addEventListener('click', () => {
        if (!fromInput.value || !toInput.value) return;
        fire('Individuell', fromInput.value, toInput.value);
    });

    function refreshCurrent() {
        if (RELATIVE_PERIODS[savedLabel]) {
            const range = calcRange(RELATIVE_PERIODS[savedLabel]);
            onPeriodChange(range.from, range.to);
        } else if (savedLabel.startsWith('Jahr ')) {
            const y = savedLabel.replace('Jahr ', '');
            onPeriodChange(`${y}-01-01`, `${y}-12-31`);
        } else {
            onPeriodChange(fromInput.value || fmtDate(new Date()), toInput.value || fmtDate(new Date()));
        }
    }

    return refreshCurrent;
}
