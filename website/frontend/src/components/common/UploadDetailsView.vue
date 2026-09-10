<template>
  <div class="upload-details">
    <div class="details-section">
      <header class="details-section-heading">
        <span><font-awesome-icon icon="fa-solid fa-circle-info" /></span>
        <div>
          <h3>{{ t('contributionDetails.overview.title') }}</h3>
          <p>{{ t('contributionDetails.overview.description') }}</p>
        </div>
      </header>
      <div class="details-grid">
        <div class="detail-item">
          <label>{{ t('contributionDetails.overview.fileChanges') }}</label>
          <span>{{ uploadTypeLabel }}</span>
        </div>
        <div class="detail-item">
          <label>{{ t('contributionDetails.overview.reviewStatus') }}</label>
          <span
            class="status-badge"
            :class="getStatusClass(upload.merge_status)"
          >
            {{ formatStatus(upload.merge_status) }}
          </span>
        </div>
        <div class="detail-item">
          <label>{{ t('contributionDetails.overview.submitted') }}</label>
          <span>{{ formatDate(upload.uploaded_at) }}</span>
        </div>
        <div class="detail-item">
          <label>{{ t('contributionDetails.overview.researcher') }}</label>
          <span>{{
            upload.uploaded_by || t('contributionDetails.unknownResearcher')
          }}</span>
        </div>
        <div v-if="upload.tested_at" class="detail-item">
          <label>{{ t('contributionDetails.overview.checked') }}</label>
          <span>{{ formatDate(upload.tested_at) }}</span>
        </div>
      </div>
    </div>

    <div
      v-if="upload.research_context"
      class="details-section"
      :class="{
        'details-section--warning':
          upload.research_context.scope_status === 'outside_scope',
      }"
    >
      <header class="details-section-heading">
        <span><font-awesome-icon icon="fa-solid fa-layer-group" /></span>
        <div>
          <h3>{{ t('contributionDetails.context.title') }}</h3>
          <p>{{ t('contributionDetails.context.description') }}</p>
        </div>
      </header>
      <div class="details-grid">
        <div
          class="detail-item"
          :class="{
            'detail-item--warning':
              upload.research_context.scope_status === 'outside_scope',
          }"
        >
          <label>{{ t('contributionDetails.context.topic') }}</label>
          <span>{{ researchTopicLabel }}</span>
        </div>
        <div class="detail-item">
          <label>{{ t('contributionDetails.context.scopeCheck') }}</label>
          <span>{{ researchScopeLabel }}</span>
        </div>
        <div class="detail-item detail-item--wide">
          <label>{{ t('contributionDetails.context.summary') }}</label>
          <span>{{ upload.research_context.summary }}</span>
        </div>
        <div class="detail-item detail-item--wide">
          <label>{{ t('contributionDetails.context.changedTiers') }}</label>
          <div v-if="changedTiers.length" class="changed-tier-chips">
            <span
              v-for="tier in changedTiers"
              :key="tier"
              :class="{
                'is-baseline': isBaselineTier(tier),
                'is-baseline-correction': isBaselineCorrectionTier(tier),
                'is-outside-scope': isOutsideScopeTier(tier),
              }"
              :title="tierKindLabel(tier)"
            >
              {{ tier }}
            </span>
          </div>
          <span v-else>{{
            t('contributionDetails.context.noTierChanges')
          }}</span>
          <div v-if="changedTiers.length" class="changed-tier-legend">
            <span
              ><i class="topic" />
              {{ t('contributionDetails.tiers.topic') }}</span
            >
            <span v-if="baselineChangedTiers.length"
              ><i class="baseline" />
              {{ t('contributionDetails.tiers.baseline') }}</span
            >
            <span v-if="declaredBaselineCorrectionTiers.length"
              ><i class="correction" />
              {{ t('contributionDetails.tiers.correction') }}</span
            >
            <span v-if="outsideScopeTiers.length"
              ><i class="outside" />
              {{ t('contributionDetails.tiers.outside') }}</span
            >
          </div>
        </div>
        <p
          v-if="upload.research_context.scope_status === 'outside_scope'"
          class="scope-explanation"
        >
          <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
          <span>{{ t('contributionDetails.context.outsideExplanation') }}</span>
        </p>
      </div>
    </div>

    <div class="details-section">
      <header class="details-section-heading">
        <span><font-awesome-icon icon="fa-solid fa-shield-halved" /></span>
        <div>
          <h3>{{ t('contributionDetails.quality.title') }}</h3>
          <p>{{ t('contributionDetails.quality.description') }}</p>
        </div>
      </header>
      <div class="details-grid">
        <div class="detail-item">
          <label>{{ t('contributionDetails.quality.structure') }}</label>
          <span>{{ t('contributionDetails.passed') }}</span>
        </div>
        <div class="detail-item">
          <label>{{ t('contributionDetails.quality.naming') }}</label>
          <span>{{ t('contributionDetails.passed') }}</span>
        </div>
        <div class="detail-item">
          <label>{{ t('contributionDetails.quality.protocol') }}</label>
          <span>{{ protocolLabel }}</span>
        </div>
      </div>
    </div>

    <div class="details-section">
      <header class="details-section-heading">
        <span><font-awesome-icon icon="fa-solid fa-file" /></span>
        <div>
          <h3>{{ t('contributionDetails.files.title') }}</h3>
          <p>{{ t('contributionDetails.files.description') }}</p>
        </div>
      </header>
      <div v-if="allFiles.length > 10" class="file-browser-tools">
        <input
          v-model.trim="fileQuery"
          type="search"
          :placeholder="t('contributionDetails.files.filterPlaceholder')"
          :aria-label="t('contributionDetails.files.filterLabel')"
        />
        <AppSelect
          id="upload-file-kind-filter"
          v-model="fileKind"
          size="small"
          :aria-label="t('contributionDetails.files.kindFilterLabel')"
          :options="fileKindOptions"
        />
      </div>
      <div class="file-changes">
        <p v-if="filteredFiles.length" class="file-result-count">
          {{
            t('contributionDetails.files.range', {
              first: fileRangeStart,
              last: fileRangeEnd,
              total: filteredFiles.length,
            })
          }}
        </p>
        <ul v-if="filteredFiles.length" class="file-list">
          <li
            v-for="entry in visibleFiles"
            :key="`${entry.kind}:${entry.path}`"
            class="file-item"
            :class="entry.kind"
          >
            <div class="file-row">
              <span class="file-change-kind" :class="entry.kind">
                {{ fileKindLabel(entry.kind) }}
              </span>
              <span class="file-name" :title="entry.path">{{
                entry.path
              }}</span>
              <button
                v-if="isEaf(entry.path)"
                type="button"
                class="review-file-button"
                :aria-expanded="activeSemanticFile === entry.path"
                @click="toggleSemanticFile(entry.path)"
              >
                <font-awesome-icon icon="fa-solid fa-eye" />
                <span>{{
                  activeSemanticFile === entry.path
                    ? t('contributionDetails.files.hideAnnotations')
                    : t('contributionDetails.files.reviewAnnotations')
                }}</span>
                <font-awesome-icon
                  :icon="
                    activeSemanticFile === entry.path
                      ? 'fa-solid fa-chevron-up'
                      : 'fa-solid fa-chevron-down'
                  "
                />
              </button>
            </div>
            <div
              v-if="activeSemanticFile === entry.path"
              class="inline-semantic-review"
            >
              <ConflictMergeView
                :project-name="projectName"
                :branch-name="upload.branch_name"
                :filename="entry.path"
                :allow-open-review="false"
                :file-change-kind="entry.kind"
                compact
              />
            </div>
          </li>
        </ul>
        <p v-else>{{ t('contributionDetails.files.empty') }}</p>
        <nav
          v-if="filePageCount > 1"
          class="file-pagination"
          :aria-label="t('contributionDetails.files.pages')"
        >
          <button type="button" :disabled="filePage === 1" @click="filePage--">
            {{ t('contributionDetails.previous') }}
          </button>
          <span>{{
            t('contributionDetails.page', {
              page: filePage,
              total: filePageCount,
            })
          }}</span>
          <button
            type="button"
            :disabled="filePage === filePageCount"
            @click="filePage++"
          >
            {{ t('contributionDetails.next') }}
          </button>
        </nav>
      </div>
    </div>

    <div v-if="upload.conflicted_files?.length > 0" class="details-section">
      <header class="details-section-heading">
        <span
          ><font-awesome-icon icon="fa-solid fa-triangle-exclamation"
        /></span>
        <div>
          <h3>{{ t('contributionDetails.conflicts.title') }}</h3>
          <p>{{ t('contributionDetails.conflicts.description') }}</p>
        </div>
      </header>
      <div class="conflicts-info">
        <p class="conflict-summary">
          {{
            t('contributionDetails.conflicts.count', {
              count: upload.conflicted_files.length,
            })
          }}
        </p>
        <ul class="conflict-files">
          <li
            v-for="file in upload.conflicted_files"
            :key="file"
            class="conflict-file"
          >
            <span class="conflict-icon">⚠️</span>
            <span class="file-name" :title="file">{{ file }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import ConflictMergeView from '@/components/common/ConflictMergeView.vue';
import AppSelect from '@/components/common/AppSelect.vue';

const { t } = useI18n();
const fileKindOptions = computed(() => [
  { value: '', label: t('contributionDetails.files.all') },
  { value: 'new', label: t('contributionDetails.files.new') },
  { value: 'modified', label: t('contributionDetails.files.modified') },
  { value: 'deleted', label: t('contributionDetails.files.deleted') },
]);
const props = defineProps({
  upload: {
    type: Object,
    required: true,
  },
  projectName: {
    type: String,
    required: true,
  },
});
const researchTopicLabel = computed(
  () =>
    props.upload.research_context?.declared_topic_name ||
    props.upload.research_context?.proposed_topic_name ||
    t('contributionDetails.context.general')
);
const researchScopeLabel = computed(
  () =>
    ({
      aligned: t('contributionDetails.scope.aligned'),
      outside_scope: t('contributionDetails.scope.outside'),
      topic_review_needed: t('contributionDetails.scope.review'),
      declared_general: t('contributionDetails.scope.general'),
      missing_context: t('contributionDetails.scope.missing'),
    })[props.upload.research_context?.scope_status] ||
    t('contributionDetails.scope.unknown')
);
const changedTiers = computed(
  () => props.upload.research_context?.changed_tiers || []
);
const outsideScopeTiers = computed(
  () => props.upload.research_context?.outside_scope_tiers || []
);
const baselineChangedTiers = computed(
  () => props.upload.research_context?.baseline_changed_tiers || []
);
const declaredBaselineCorrectionTiers = computed(
  () => props.upload.research_context?.declared_baseline_correction_tiers || []
);
const isOutsideScopeTier = (tier) => outsideScopeTiers.value.includes(tier);
const isBaselineTier = (tier) => baselineChangedTiers.value.includes(tier);
const isBaselineCorrectionTier = (tier) =>
  declaredBaselineCorrectionTiers.value.includes(tier);
const tierKindLabel = (tier) =>
  isOutsideScopeTier(tier)
    ? t('contributionDetails.tiers.outside')
    : isBaselineCorrectionTier(tier)
      ? t('contributionDetails.tiers.correction')
      : isBaselineTier(tier)
        ? t('contributionDetails.tiers.baseline')
        : t('contributionDetails.tiers.topic');

const fileQuery = ref('');
const fileKind = ref('');
const filePage = ref(1);
const activeSemanticFile = ref('');
const FILE_PAGE_SIZE = 50;
const allFiles = computed(() =>
  ['new', 'modified', 'deleted'].flatMap((kind) =>
    (props.upload.files?.[kind] || []).map((path) => ({ kind, path }))
  )
);
const isEaf = (path) => path.toLocaleLowerCase().endsWith('.eaf');
const filteredFiles = computed(() => {
  const needle = fileQuery.value.toLocaleLowerCase();
  return allFiles.value.filter(
    (entry) =>
      (!fileKind.value || entry.kind === fileKind.value) &&
      (!needle || entry.path.toLocaleLowerCase().includes(needle))
  );
});
const filePageCount = computed(() =>
  Math.max(1, Math.ceil(filteredFiles.value.length / FILE_PAGE_SIZE))
);
const visibleFiles = computed(() =>
  filteredFiles.value.slice(
    (filePage.value - 1) * FILE_PAGE_SIZE,
    filePage.value * FILE_PAGE_SIZE
  )
);
const fileRangeStart = computed(
  () => (filePage.value - 1) * FILE_PAGE_SIZE + 1
);
const fileRangeEnd = computed(() =>
  Math.min(filePage.value * FILE_PAGE_SIZE, filteredFiles.value.length)
);
watch([fileQuery, fileKind], () => {
  filePage.value = 1;
});

function toggleSemanticFile(path) {
  activeSemanticFile.value = activeSemanticFile.value === path ? '' : path;
}

const fileKindLabel = (kind) =>
  ({
    new: t('contributionDetails.files.new'),
    modified: t('contributionDetails.files.modified'),
    deleted: t('contributionDetails.files.deleted'),
  })[kind] || kind;

const protocolLabel = computed(() => {
  const outcome = props.upload.quality_checks?.protocol;
  if (outcome === 'passed') return t('contributionDetails.passed');
  if (outcome === 'recheck_required')
    return t('contributionDetails.protocol.changed');
  if (outcome === 'not_configured')
    return t('contributionDetails.protocol.missing');
  return t('contributionDetails.protocol.unrecorded');
});

const uploadTypeLabel = computed(() => {
  const kinds = ['new', 'modified', 'deleted'].filter(
    (kind) => props.upload.files?.[kind]?.length
  );
  if (kinds.length > 1) return t('contributionDetails.uploadType.mixed');
  return (
    {
      new: t('contributionDetails.uploadType.new'),
      modified: t('contributionDetails.uploadType.modified'),
      deleted: t('contributionDetails.uploadType.deleted'),
    }[kinds[0]] || t('contributionDetails.uploadType.none')
  );
});

function formatStatus(status) {
  const statuses = {
    ready_to_merge: t('contributionDetails.status.ready'),
    needs_resolution: t('contributionDetails.status.resolution'),
    error: t('contributionDetails.status.error'),
    pending_admin_approval: t('contributionDetails.status.pending'),
    superseded: t('contributionDetails.status.superseded'),
  };
  return statuses[status] || status;
}

function getStatusClass(status) {
  const classes = {
    ready_to_merge: 'ready',
    needs_resolution: 'conflicts',
    error: 'error',
    pending_admin_approval: 'pending',
    superseded: 'pending',
  };
  return classes[status] || 'pending';
}

function formatDate(dateString) {
  if (!dateString) return t('contributionDetails.unknown');
  return new Date(dateString).toLocaleString();
}
</script>

<style scoped>
.upload-details {
  display: grid;
  gap: 1rem;
}

.details-section {
  min-width: 0;
  padding: 1.1rem;
  border: 1px solid var(--color-border, #dbe3ee);
  border-radius: 0.75rem;
  background: #fff;
}

.details-section--warning {
  border-color: #efc56f;
}

.details-section-heading {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--color-border, #dbe3ee);
}

.details-section-heading > span {
  display: inline-flex;
  width: 2.35rem;
  height: 2.35rem;
  align-items: center;
  justify-content: center;
  flex: none;
  border-radius: 0.65rem;
  color: #2563eb;
  background: #eaf2ff;
}

.details-section-heading h3 {
  margin: 0 0 0.15rem;
  color: var(--color-text, #172033);
  font-size: 1.05rem;
  line-height: 1.3;
}

.details-section-heading p {
  margin: 0;
  color: var(--color-text-muted, #64748b);
  font-size: 0.84rem;
  line-height: 1.45;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.file-row .file-name {
  min-width: 0;
  flex: 1;
  overflow-wrap: anywhere;
}

.review-file-button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  flex: none;
  padding: 0.45rem 0.65rem;
  border: 1px solid #93c5fd;
  border-radius: 0.45rem;
  color: #1d4ed8;
  background: #fff;
  font-family: 'Nunito Sans Variable', system-ui, sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
}

.review-file-button:hover,
.review-file-button:focus-visible {
  border-color: #2563eb;
  background: #eff6ff;
}

.inline-semantic-review {
  margin-top: 0.75rem;
  padding: 0.9rem;
  border: 1px solid #bfdbfe;
  border-radius: 0.55rem;
  background: #fff;
  font-family: 'Nunito Sans Variable', system-ui, sans-serif;
}

.file-browser-tools {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) minmax(8rem, auto);
  gap: 0.6rem;
  margin-bottom: 0.75rem;
}

.file-browser-tools input,
.file-browser-tools select {
  min-width: 0;
  padding: 0.55rem 0.65rem;
  border: 1px solid #d4dce7;
  border-radius: 0.45rem;
  font: inherit;
}

.file-result-count {
  color: #64748b;
  font-size: 0.82rem;
}

.file-change-kind {
  flex: none;
  min-width: 4.5rem;
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  text-align: center;
  font-size: 0.72rem;
  font-weight: 700;
}

.file-change-kind.new {
  color: #166534;
  background: #dcfce7;
}

.file-change-kind.modified {
  color: #92400e;
  background: #fef3c7;
}

.file-change-kind.deleted {
  color: #991b1b;
  background: #fee2e2;
}

.file-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  margin-top: 0.75rem;
}

.file-pagination button {
  padding: 0.4rem 0.65rem;
  border: 1px solid #d4dce7;
  border-radius: 0.4rem;
  color: #1d4ed8;
  background: white;
  font: inherit;
}

@media (width <= 600px) {
  .file-browser-tools {
    grid-template-columns: 1fr;
  }

  .semantic-action {
    display: none;
  }

  .file-row {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .review-file-button {
    width: 100%;
    justify-content: center;
  }
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
  gap: 0.7rem;
}

.detail-item--wide {
  grid-column: 1 / -1;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
  padding: 0.75rem 0.8rem;
  border: 1px solid #e7edf5;
  border-radius: 0.55rem;
  background: #f8fafc;
}

.detail-item label {
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.045em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.detail-item span {
  min-width: 0;
  color: var(--color-text, #172033);
  line-height: 1.45;
}

.detail-item--warning {
  border-color: #f3d49b;
  background: #fffbeb;
}

.changed-tier-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.changed-tier-chips span {
  max-width: 100%;
  padding: 0.28rem 0.55rem;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  overflow-wrap: anywhere;
  color: #1e40af;
  background: #eff6ff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.78rem;
  font-weight: 700;
}

.changed-tier-chips span.is-outside-scope {
  border-color: #fed7aa;
  color: #9a3412;
  background: #ffedd5;
}

.changed-tier-chips span.is-baseline:not(.is-outside-scope) {
  border-color: #c4b5fd;
  color: #6d28d9;
  background: #f5f3ff;
}

.changed-tier-chips span.is-baseline-correction:not(.is-outside-scope) {
  border-color: #a78bfa;
  color: #5b21b6;
  background: #ede9fe;
  box-shadow: inset 0 0 0 1px #c4b5fd;
}

.changed-tier-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.25rem;
  color: #64748b;
  font-size: 0.72rem;
}

.changed-tier-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.changed-tier-legend i {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  background: #bfdbfe;
}

.changed-tier-legend i.baseline {
  background: #c4b5fd;
}

.changed-tier-legend i.correction {
  background: #8b5cf6;
}

.changed-tier-legend i.outside {
  background: #fdba74;
}

.scope-explanation {
  grid-column: 1 / -1;
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  margin: 0;
  padding: 0.7rem 0.8rem;
  border: 1px solid #f3d49b;
  border-radius: 0.55rem;
  color: #7a4b00;
  background: #fffbeb;
  font-size: 0.82rem;
  line-height: 1.45;
}

.scope-explanation > svg {
  flex: none;
  margin-top: 0.18rem;
}

/* Branch name specific styling with truncation */
.branch-name {
  font-family: monospace;
  font-size: 0.9rem;
  word-break: break-all;
  overflow-wrap: break-word;
  max-width: 100%;
  display: block;
}

/* Alternative: use ellipsis truncation for very long names */
.branch-name-ellipsis {
  font-family: monospace;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
  display: block;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
  width: fit-content;
}

.status-badge.ready {
  background: #e8f5e8;
  color: #2e7d32;
}

.status-badge.conflicts {
  background: #fff3e0;
  color: #f57c00;
}

.status-badge.error {
  background: #ffebee;
  color: #d32f2f;
}

.status-badge.pending {
  background: #e3f2fd;
  color: #1976d2;
}

.file-group {
  margin-bottom: 20px;
}

.file-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  font-size: 1rem;
  font-weight: 600;
}

.file-icon {
  font-weight: bold;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.file-group-title.new {
  color: #2e7d32;
}

.file-group-title.modified {
  color: #f57c00;
}

.file-group-title.deleted {
  color: #d32f2f;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.file-item {
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 4px;
  font-size: 0.9rem;
  min-width: 0;
}

.file-item > .file-row > .file-name {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.file-item.new {
  background: #e8f5e8;
  border-left: 3px solid #2e7d32;
}

.file-item.modified {
  background: #fff3e0;
  border-left: 3px solid #f57c00;
}

.file-item.deleted {
  background: #ffebee;
  border-left: 3px solid #d32f2f;
}

/* File name styling with proper wrapping */
.file-name {
  word-break: break-all;
  overflow-wrap: break-word;
  display: block;
  max-width: 100%;
}

.conflicts-info {
  background: #fff3e0;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #f57c00;
}

.conflict-summary {
  margin: 0 0 15px;
  font-weight: 500;
  color: #f57c00;
}

.conflict-files {
  list-style: none;
  padding: 0;
  margin: 0;
}

.conflict-file {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  margin-bottom: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  min-width: 0;
}

.conflict-icon {
  font-size: 1rem;
  flex-shrink: 0;
  margin-top: 1px; /* Align with text baseline */
}

.tech-details {
  background: #f8f9fa;
  border-radius: 8px;
  overflow-x: auto;
}

.tech-details pre {
  padding: 15px;
  margin: 0;
  font-size: 0.8rem;
  color: #666;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: break-word;
}

/* Responsive design improvements */
@media (width <= 768px) {
  .details-section {
    padding: 0.9rem;
  }

  .details-grid {
    grid-template-columns: 1fr;
  }

  .detail-item {
    padding: 0.7rem;
  }

  .branch-name {
    font-size: 0.8rem;
  }
}

/* Alternative styles if you prefer ellipsis truncation */

/* Uncomment these and change .branch-name to .branch-name-ellipsis in template */

/*
@media (min-width: 769px) {
  .branch-name-ellipsis {
    max-width: 250px;
  }
}

@media (max-width: 768px) {
  .branch-name-ellipsis {
    max-width: 200px;
  }
}
*/
</style>
