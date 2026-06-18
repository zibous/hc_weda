// static/js/card-icons.js – Ersetzt Emoji-Icons in Cards durch SVG
'use strict';

import { getAppleIcon } from './icons.js';

const ICON_MAP = {
  'card-temp': 'thermometer',
  'card-indoor': 'home',
  'card-humidity': 'droplet',
  'card-wind': 'wind',
  'card-pressure': 'gauge',
  'card-rain': 'rain',
  'card-solar': 'sun',
  'card-feels': 'snowflake',
};

export function initCardIcons() {
  for (const [cardId, iconName] of Object.entries(ICON_MAP)) {
    const card = document.getElementById(cardId);
    if (!card) continue;
    const iconEl = card.querySelector('.card-icon');
    if (iconEl) {
      iconEl.innerHTML = getAppleIcon(iconName, 20, 0.7);
    }
  }

  // Compass-Card hat keine ID-basierte Zuordnung
  const compassCard = document.querySelector('.compass-card .card-icon');
  if (compassCard) {
    compassCard.innerHTML = getAppleIcon('compass', 20, 0.7);
  }
}
