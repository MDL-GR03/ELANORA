<template>
  <div class="profile-settings">
    <!-- Language Settings Section -->
    <div class="settings-card">
      <div class="settings-card-header">
        <div class="settings-icon">🌐</div>
        <div class="settings-header-content">
          <h3 class="settings-section-title">
            {{ t('profile.settings.language.title') }}
          </h3>
          <p class="settings-section-description">
            {{ t('profile.settings.language.description') }}
          </p>
        </div>
      </div>

      <div class="settings-card-body">
        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">{{
              t('profile.settings.language.label')
            }}</span>
            <div class="current-selection">
              <span class="current-flag">{{ currentLanguageInfo.flag }}</span>
              <span class="current-name">{{ currentLanguageInfo.name }}</span>
            </div>
          </div>
          <div class="language-selector">
            <button
              v-for="lang in availableLanguages"
              :key="lang.code"
              class="language-option"
              :class="{ active: currentLanguage === lang.code }"
              :aria-pressed="currentLanguage === lang.code"
              :disabled="currentLanguage === lang.code"
              @click="changeLanguage(lang.code)"
            >
              <span class="language-flag">{{ lang.flag }}</span>
              <div class="language-info">
                <span class="language-name">{{ lang.name }}</span>
                <span class="language-native">{{ lang.nativeName }}</span>
              </div>
              <div v-if="currentLanguage === lang.code" class="check-icon">
                ✓
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLanguageStore } from '@/stores/language.js';
import { useEventMessageStore } from '@/stores/eventMessage.js';

const { t, availableLocales, messages } = useI18n();
const languageStore = useLanguageStore();
const eventMessageStore = useEventMessageStore();

const currentLanguage = computed(() => languageStore.language);

// Dynamic generation of available languages based on available locales
const availableLanguages = computed(() => {
  return availableLocales.map((locale) => {
    const langInfo = messages.value[locale]?.language || {};
    return {
      code: locale,
      name: langInfo.name || locale,
      nativeName: langInfo.nativeName || locale,
      flag: langInfo.flag || '🏳️',
    };
  });
});

const currentLanguageInfo = computed(() => {
  return (
    availableLanguages.value.find(
      (lang) => lang.code === currentLanguage.value
    ) ||
    (availableLanguages.value.length > 0 ? availableLanguages.value[0] : {})
  );
});

function changeLanguage(langCode) {
  if (langCode !== currentLanguage.value) {
    languageStore.setLanguage(langCode);
    const langInfo = availableLanguages.value.find((l) => l.code === langCode);
    eventMessageStore.addMessage(
      t('profile.settings.language.changed', { language: langInfo?.name }),
      'success'
    );
  }
}
</script>

<style scoped>
@import url('../../../assets/css/profile-settings.css');
</style>
