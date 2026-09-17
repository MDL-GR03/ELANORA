<template>
  <section class="compliance-panel">
    <header>
      <div>
        <span class="eyebrow">{{ t('protocols.scan.eyebrow') }}</span>
        <h3>{{ t('protocols.scan.title') }}</h3>
      </div>
      <AppSelect
        v-if="scan"
        id="protocol-scan-filter"
        v-model="filter"
        size="small"
        :aria-label="t('protocols.scan.filter')"
        :options="filterOptions"
      />
    </header>
    <div v-if="busy" class="loading-state">
      {{ t('protocols.scan.checking') }}
    </div>
    <template v-else-if="scan">
      <div class="summary-grid">
        <div>
          <strong>{{ scan.total_files }}</strong>
          <span>{{ t('protocols.scan.files_checked') }}</span>
        </div>
        <div class="passed">
          <strong>{{ scan.passed_files }}</strong>
          <span>{{ t('protocols.scan.passed') }}</span>
        </div>
        <div class="failed">
          <strong>{{ scan.failed_files }}</strong>
          <span>{{ t('protocols.scan.need_attention') }}</span>
        </div>
        <div>
          <strong>v{{ scan.protocol_version_number }}</strong>
          <span>{{ scan.protocol_name }}</span>
        </div>
      </div>
      <p class="scan-context">
        {{
          scan.trigger === 'preview'
            ? t('protocols.scan.impact_preview')
            : t('protocols.scan.project_scan')
        }}
        · {{ formatDate(scan.completed_at || scan.started_at) }}
      </p>
      <div class="file-results">
        <details
          v-for="file in visibleFiles"
          :key="file.scan_file_id"
          class="file-result"
        >
          <summary>
            <span>
              <strong>{{ file.filename }}</strong>
              <small>{{ t('protocols.scan.latest_revision') }}</small>
            </span>
            <i :class="['result', file.outcome]">{{
              file.outcome === 'passed'
                ? t('protocols.scan.passed')
                : t('protocols.scan.findings', file.issues.length)
            }}</i>
          </summary>
          <div v-if="file.issues.length" class="findings">
            <article v-for="issue in file.issues" :key="issue.issue_number">
              <div>
                <strong>{{ issue.message }}</strong>
                <small>{{ friendlyLocation(issue.location) }}</small>
              </div>
              <button
                class="text-button"
                type="button"
                @click="emit('create-correction', file, issue)"
              >
                {{ t('protocols.scan.create_correction') }}
              </button>
            </article>
          </div>
          <p v-else class="passed-copy">
            {{ t('protocols.scan.file_passed') }}
          </p>
        </details>
      </div>
    </template>
    <div v-else class="empty-state compact">
      <strong>{{ t('protocols.scan.empty.title') }}</strong>
      <p>{{ t('protocols.scan.empty.description') }}</p>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import AppSelect from '@/components/common/AppSelect.vue';

const props = defineProps({
  scan: { type: Object, default: null },
  busy: { type: Boolean, default: false },
});
const emit = defineEmits(['create-correction']);

const { t } = useI18n();
const filter = ref('all');
const filterOptions = computed(() => [
  { value: 'all', label: t('protocols.scan.all_files') },
  { value: 'failed', label: t('protocols.scan.need_attention') },
  { value: 'passed', label: t('protocols.scan.passed') },
]);
const visibleFiles = computed(
  () =>
    props.scan?.files.filter(
      (file) => filter.value === 'all' || file.outcome === filter.value
    ) ?? []
);

function friendlyLocation(location) {
  return location === '/ANNOTATION_DOCUMENT'
    ? t('protocols.scan.document')
    : location.replace('/ANNOTATION_DOCUMENT/', '');
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
</script>

<style scoped src="@/assets/css/protocol-workspace.css"></style>

<style scoped>
.compliance-panel {
  overflow: hidden;
  border: 1px solid var(--color-blue-100-alt);
  border-radius: 0.9rem;
  background: var(--color-surface);
  padding: 1.1rem;
  display: grid;
  gap: 1rem;
}

.compliance-panel select {
  width: auto;
  min-width: 10rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.7rem;
}

.summary-grid div {
  display: grid;
  gap: 0.15rem;
  padding: 0.9rem;
  border-radius: 0.7rem;
  background: var(--color-surface-subtle);
}

.summary-grid strong {
  font-size: 1.35rem;
}

.summary-grid span {
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.summary-grid .passed strong {
  color: var(--color-success-800);
}

.summary-grid .failed strong {
  color: var(--color-error);
}

.file-results {
  display: grid;
  gap: 0.55rem;
}

.file-result {
  border: 1px solid var(--color-blue-100-alt);
  border-radius: 0.7rem;
  overflow: hidden;
}

.file-result summary {
  padding: 0.8rem 1rem;
  cursor: pointer;
  background: var(--color-gray-50-alt);
}

.file-result summary > span {
  display: grid;
  gap: 0.15rem;
}

.findings {
  display: grid;
}

.findings article {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border-top: 1px solid var(--color-gray-200);
}

.findings article > div {
  display: grid;
  gap: 0.25rem;
}

@media (width <= 760px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .findings article {
    flex-direction: column;
  }
}
</style>
