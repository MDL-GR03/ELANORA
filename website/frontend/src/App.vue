<template>
  <router-view v-slot="{ Component }"
    ><Suspense
      ><component :is="Component" /><template #fallback
        ><PageLoader /></template></Suspense
  ></router-view>
  <EventMessageContainer />
</template>

<script setup>
import { onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLanguageStore } from '@stores/language';
import { useAppInfoStore } from '@/stores/appInfo';
import { useProjectStore } from '@/stores/project';
import instanceService from '@/api/service/instanceService';

import EventMessageContainer from '@components/eventComponent/eventMessageContainer.vue';
import PageLoader from '@components/common/PageLoader.vue';

const languageStore = useLanguageStore();
const { locale } = useI18n();
const appInfoStore = useAppInfoStore();
const projectStore = useProjectStore();

// Hydrate synchronously so authenticated pages can paint cached workspace data
// while the router refreshes it in the background.
projectStore.initializeFromStorage();

onMounted(async () => {
  languageStore.initializeFromStorage();

  const cached = localStorage.getItem('instance');
  if (cached) {
    try {
      appInfoStore.setInstance(JSON.parse(cached));
    } catch {
      localStorage.removeItem('instance');
    }
  }

  try {
    const response = await instanceService.getInstanceInfo();
    if (response) {
      appInfoStore.setInstance(response);
      localStorage.setItem('instance', JSON.stringify(response));
    }
  } catch {
    /* Keep the last known identity while offline. */
  }

  locale.value = languageStore.language;
});

watch(
  () => languageStore.language,
  (newLang) => {
    locale.value = newLang;
  }
);
</script>
