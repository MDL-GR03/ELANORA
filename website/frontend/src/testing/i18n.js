import { createI18n } from 'vue-i18n';

import en from '@/locales/en.json';

/** The application's English messages, for mounting translated components. */
export const englishI18n = () =>
  createI18n({
    legacy: false,
    locale: 'en',
    fallbackLocale: 'en',
    messages: { en },
  });
