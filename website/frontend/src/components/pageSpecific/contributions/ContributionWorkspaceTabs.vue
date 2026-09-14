<template>
  <nav
    class="contribution-tabs"
    role="tablist"
    :aria-label="t('contributionWorkspace.tabs.label')"
  >
    <button
      id="contribution-queue-tab"
      type="button"
      role="tab"
      :aria-selected="activeView === 'queue'"
      aria-controls="contribution-queue-panel"
      :class="{ active: activeView === 'queue' }"
      @click="$emit('select', 'queue')"
    >
      {{ t('contributionWorkspace.tabs.incoming') }}
      <span v-if="contributionCount">{{ contributionCount }}</span>
    </button>
    <button
      id="contribution-reviews-tab"
      type="button"
      role="tab"
      :aria-selected="activeView === 'reviews'"
      aria-controls="contribution-reviews-panel"
      :class="{ active: activeView === 'reviews' }"
      @click="$emit('select', 'reviews')"
    >
      {{ t('contributionWorkspace.tabs.corrections') }}
      <span v-if="activeReviewCount">{{ activeReviewCount }}</span>
    </button>
    <button
      v-if="canAdminister"
      id="contribution-history-tab"
      type="button"
      role="tab"
      :aria-selected="activeView === 'history'"
      aria-controls="contribution-history-panel"
      :class="{ active: activeView === 'history' }"
      @click="$emit('select', 'history')"
    >
      {{ t('contributionWorkspace.tabs.history') }}
    </button>
  </nav>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

defineProps({
  activeView: { type: String, required: true },
  contributionCount: { type: Number, default: 0 },
  activeReviewCount: { type: Number, default: 0 },
  canAdminister: { type: Boolean, default: false },
});

defineEmits(['select']);

const { t } = useI18n();
</script>
