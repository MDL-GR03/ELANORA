<template>
  <div
    v-if="casesCount"
    class="review-summary"
    :aria-label="t('reviewCases.queue.summary')"
  >
    <div>
      <strong>{{ activeCount }}</strong>
      <span>{{ t('reviewCases.queue.active') }}</span>
    </div>
    <div>
      <strong>{{ changesRequestedCount }}</strong>
      <span>{{ t('reviewCases.queue.awaiting') }}</span>
    </div>
    <div>
      <strong>{{ resubmittedCount }}</strong>
      <span>{{ t('reviewCases.queue.ready') }}</span>
    </div>
  </div>

  <div v-if="loading" class="panel-state">
    {{ t('reviewCases.queue.loading') }}
  </div>
  <div v-else-if="error" class="panel-state error" role="alert">
    {{ error }}
  </div>
  <div v-else-if="!activeCasesCount" class="panel-state">
    {{ emptyMessage }}
  </div>

  <div
    v-if="!loading && !error && activeCasesCount > 5"
    class="review-list-filters"
  >
    <input
      :value="query"
      type="search"
      :placeholder="t('reviewCases.queue.searchPlaceholder')"
      :aria-label="t('reviewCases.queue.search')"
      @input="$emit('update:query', $event.target.value.trim())"
    />
    <AppSelect
      id="review-status-filter"
      :model-value="status"
      size="small"
      :aria-label="t('reviewCases.queue.statusFilter')"
      :options="statusOptions"
      @update:model-value="$emit('update:status', $event)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import AppSelect from '@/components/common/AppSelect.vue';

const props = defineProps({
  casesCount: { type: Number, default: 0 },
  activeCount: { type: Number, default: 0 },
  changesRequestedCount: { type: Number, default: 0 },
  resubmittedCount: { type: Number, default: 0 },
  activeCasesCount: { type: Number, default: 0 },
  closedCasesCount: { type: Number, default: 0 },
  uploadId: { type: Number, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  query: { type: String, default: '' },
  status: { type: String, default: '' },
});

defineEmits(['update:query', 'update:status']);
const { t } = useI18n();

const statusOptions = computed(() => [
  { value: '', label: t('reviewCases.queue.statuses.all') },
  { value: 'open', label: t('reviewCases.queue.statuses.open') },
  {
    value: 'changes_requested',
    label: t('reviewCases.queue.statuses.changes_requested'),
  },
  { value: 'resubmitted', label: t('reviewCases.queue.statuses.resubmitted') },
]);
const emptyMessage = computed(() => {
  if (props.uploadId) {
    return t('reviewCases.queue.emptyContribution');
  }
  if (props.closedCasesCount) {
    return t('reviewCases.queue.emptyActive');
  }
  return t('reviewCases.queue.emptyProject');
});
</script>

<style scoped>
.review-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
}

.review-summary > div {
  display: grid;
  gap: 0.15rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: white;
}

.review-summary strong {
  color: var(--primary-color);
  font-size: 1.25rem;
}

.review-summary span {
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.review-list-filters {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 0.35fr);
  gap: 0.65rem;
  margin-bottom: 0.8rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-subtle);
}

.panel-state {
  padding: 1rem;
  color: var(--color-text-muted);
  text-align: center;
}

.panel-state.error {
  color: var(--color-error-darkest);
}

@media (width <= 700px) {
  .review-summary,
  .review-list-filters {
    grid-template-columns: 1fr;
  }
}
</style>
