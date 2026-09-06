import { defineStore } from 'pinia';

const DEFAULT_THEME = {
  primary_color: '#2563eb',
  secondary_color: '#0f766e',
  accent_color: '#d97706',
};

function shade(hex, amount) {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)
    .map((value) => parseInt(value, 16));
  return `#${channels
    .map((value) =>
      Math.max(0, Math.min(255, value + amount))
        .toString(16)
        .padStart(2, '0')
    )
    .join('')}`;
}

function applyTheme(instance = DEFAULT_THEME) {
  const primary = instance.primary_color || DEFAULT_THEME.primary_color;
  const root = document.documentElement;
  root.style.setProperty('--primary-color', primary);
  root.style.setProperty('--primary-color-dark', shade(primary, -28));
  root.style.setProperty(
    '--secondary-color',
    instance.secondary_color || DEFAULT_THEME.secondary_color
  );
  root.style.setProperty(
    '--accent-color',
    instance.accent_color || DEFAULT_THEME.accent_color
  );
}

export const useAppInfoStore = defineStore('appInfo', {
  state: () => ({
    instance: null,
    version: '1.0.0',
  }),

  actions: {
    setInstance(instance) {
      this.instance = instance;
      applyTheme(instance);
      localStorage.setItem('instance', JSON.stringify(instance));
    },
    setVersion(version) {
      this.version = version;
      localStorage.setItem('version', version);
    },
  },

  getters: {
    getInstance() {
      return this.instance;
    },
    getVersion() {
      return this.version;
    },
  },
});
