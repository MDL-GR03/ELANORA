// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest';

import { setupI18n } from './i18n';

describe('setupI18n', () => {
  beforeEach(() => localStorage.clear());

  it('falls back to English for a key a translation lacks', () => {
    localStorage.setItem('language', 'fr');
    const i18n = setupI18n();
    i18n.global.mergeLocaleMessage('en', {
      probe: { onlyInEnglish: 'English' },
    });

    expect(i18n.global.t('probe.onlyInEnglish')).toBe('English');
  });

  it('starts in the stored language', () => {
    localStorage.setItem('language', 'fr');

    expect(setupI18n().global.locale.value).toBe('fr');
  });
});
