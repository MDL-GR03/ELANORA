import { createI18n } from 'vue-i18n';

// Dynamically import all locale files
const modules = import.meta.glob('../locales/*.json', { eager: true });

const messages = {};
Object.entries(modules).forEach(([path, mod]) => {
  const lang = path.match(/\/([^/]+)\.json$/)?.[1];
  if (lang) {
    messages[lang] = mod.default || mod;
  }
});

// Function to set up i18n
export const setupI18n = () => {
  // Retrieve the language from localStorage or default to 'en'
  const storedLanguage = localStorage.getItem('language') || 'en';

  return createI18n({
    legacy: false,
    locale: storedLanguage,
    fallbackLocale: 'en',
    messages,
  });
};
