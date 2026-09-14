<template>
  <div
    v-if="casesCount"
    class="review-summary"
    aria-label="Review status summary"
  >
    <div>
      <strong>{{ activeCount }}</strong>
      <span>Active</span>
    </div>
    <div>
      <strong>{{ changesRequestedCount }}</strong>
      <span>Awaiting corrections</span>
    </div>
    <div>
      <strong>{{ resubmittedCount }}</strong>
      <span>Ready for another review</span>
    </div>
  </div>

  <div v-if="loading" class="panel-state">Loading correction requests…</div>
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
      placeholder="Find by title, contribution, file, tier, annotation, or instruction"
      aria-label="Search correction requests"
      @input="$emit('update:query', $event.target.value.trim())"
    />
    <AppSelect
      id="review-status-filter"
      :model-value="status"
      size="small"
      aria-label="Filter correction requests by status"
      :options="statusOptions"
      @update:model-value="$emit('update:status', $event)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue';

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

const statusOptions = [
  { value: '', label: 'All active statuses' },
  { value: 'open', label: 'Open questions' },
  { value: 'changes_requested', label: 'Awaiting corrections' },
  { value: 'resubmitted', label: 'Ready for review' },
];
const emptyMessage = computed(() => {
  if (props.uploadId) {
    return 'No correction requests have been opened for this contribution.';
  }
  if (props.closedCasesCount) {
    return 'There are no active correction requests for this project.';
  }
  return 'No correction requests have been opened for this project.';
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
  color: #991b1b;
}

@media (width <= 700px) {
  .review-summary,
  .review-list-filters {
    grid-template-columns: 1fr;
  }
}
</style>
