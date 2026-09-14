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
      :tabindex="activeView === 'queue' ? 0 : -1"
      aria-controls="contribution-queue-panel"
      :class="{ active: activeView === 'queue' }"
      @click="$emit('select', 'queue')"
      @keydown="onTabKeydown"
    >
      {{ t('contributionWorkspace.tabs.incoming') }}
      <span v-if="contributionCount">{{ contributionCount }}</span>
    </button>
    <button
      id="contribution-reviews-tab"
      type="button"
      role="tab"
      :aria-selected="activeView === 'reviews'"
      :tabindex="activeView === 'reviews' ? 0 : -1"
      aria-controls="contribution-reviews-panel"
      :class="{ active: activeView === 'reviews' }"
      @click="$emit('select', 'reviews')"
      @keydown="onTabKeydown"
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
      :tabindex="activeView === 'history' ? 0 : -1"
      aria-controls="contribution-history-panel"
      :class="{ active: activeView === 'history' }"
      @click="$emit('select', 'history')"
      @keydown="onTabKeydown"
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

const emit = defineEmits(['select']);

const { t } = useI18n();

function onTabKeydown(event) {
  const tabs = [
    ...event.currentTarget.parentElement.querySelectorAll('[role="tab"]'),
  ];
  const currentIndex = tabs.indexOf(event.currentTarget);
  let targetIndex;
  if (event.key === 'ArrowRight')
    targetIndex = (currentIndex + 1) % tabs.length;
  else if (event.key === 'ArrowLeft')
    targetIndex = (currentIndex - 1 + tabs.length) % tabs.length;
  else if (event.key === 'Home') targetIndex = 0;
  else if (event.key === 'End') targetIndex = tabs.length - 1;
  else return;
  event.preventDefault();
  const target = tabs[targetIndex];
  target.focus();
  emit('select', target.id.replace('contribution-', '').replace('-tab', ''));
}
</script>
