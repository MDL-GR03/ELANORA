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
      <dl class="details-grid">
        <div class="detail-item">
          <dt>{{ t('contributionDetails.overview.fileChanges') }}</dt>
          <dd>
            <span>{{ uploadTypeLabel }}</span>
          </dd>
        </div>
        <div class="detail-item">
          <dt>{{ t('contributionDetails.overview.reviewStatus') }}</dt>
          <dd>
            <span
              class="status-badge"
              :class="getStatusClass(upload.merge_status)"
            >
              {{ formatStatus(upload.merge_status) }}
            </span>
          </dd>
        </div>
        <div class="detail-item">
          <dt>{{ t('contributionDetails.overview.submitted') }}</dt>
          <dd>
            <span>{{ formatDate(upload.uploaded_at) }}</span>
          </dd>
        </div>
        <div class="detail-item">
          <dt>{{ t('contributionDetails.overview.researcher') }}</dt>
          <dd>
            <span>{{
              upload.uploaded_by || t('contributionDetails.unknownResearcher')
            }}</span>
          </dd>
        </div>
        <div v-if="upload.tested_at" class="detail-item">
          <dt>{{ t('contributionDetails.overview.checked') }}</dt>
          <dd>
            <span>{{ formatDate(upload.tested_at) }}</span>
          </dd>
        </div>
      </dl>
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
      <dl class="details-grid">
        <div
          class="detail-item"
          :class="{
            'detail-item--warning':
              upload.research_context.scope_status === 'outside_scope',
          }"
        >
          <dt>{{ t('contributionDetails.context.topic') }}</dt>
          <dd>
            <span>{{ researchTopicLabel }}</span>
          </dd>
        </div>
        <div class="detail-item">
          <dt>{{ t('contributionDetails.context.scopeCheck') }}</dt>
          <dd>
            <span>{{ researchScopeLabel }}</span>
          </dd>
        </div>
        <div class="detail-item detail-item--wide">
          <dt>{{ t('contributionDetails.context.summary') }}</dt>
          <dd>
            <span>{{ upload.research_context.summary }}</span>
          </dd>
        </div>
        <div class="detail-item detail-item--wide">
          <dt>{{ t('contributionDetails.context.changedTiers') }}</dt>
          <dd>
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
          </dd>
        </div>
        <p
          v-if="upload.research_context.scope_status === 'outside_scope'"
          class="scope-explanation"
        >
          <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
          <span>{{ t('contributionDetails.context.outsideExplanation') }}</span>
        </p>
      </dl>
    </div>

    <div class="details-section">
      <header class="details-section-heading">
        <span><font-awesome-icon icon="fa-solid fa-shield-halved" /></span>
        <div>
          <h3>{{ t('contributionDetails.quality.title') }}</h3>
          <p>{{ t('contributionDetails.quality.description') }}</p>
        </div>
      </header>
      <dl class="details-grid">
        <div class="detail-item">
          <dt>{{ t('contributionDetails.quality.structure') }}</dt>
          <dd>
            <span>{{ t('contributionDetails.passed') }}</span>
          </dd>
        </div>
        <div class="detail-item">
          <dt>{{ t('contributionDetails.quality.naming') }}</dt>
          <dd>
            <span>{{ t('contributionDetails.passed') }}</span>
          </dd>
        </div>
        <div class="detail-item">
          <dt>{{ t('contributionDetails.quality.protocol') }}</dt>
          <dd>
            <span>{{ protocolLabel }}</span>
          </dd>
        </div>
      </dl>
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
@import url('@/assets/css/upload-components.css');

.upload-details {
  display: grid;
  gap: 1rem;
}

/* Component-specific styles */
.message {
  padding: 0.8rem 1rem;
  border-radius: var(--radius-md);
}

.error {
  border: 1px solid var(--color-error-bg);
  background: var(--color-error-bg-subtle);
  color: var(--color-error);
}

button.danger {
  border: 1px solid var(--color-error-bg);
  background: var(--color-surface);
  color: var(--color-error);
}

button.danger:hover {
  background: var(--color-error-bg-subtle);
}

.text-button {
  padding: 0.25rem;
  background: transparent;
  color: var(--color-primary);
  white-space: nowrap;
}

.text-button:hover {
  background: transparent;
  color: var(--color-primary-dark);
  text-decoration: underline;
}

.passed-copy,
.empty-state,
.loading-state {
  padding: 1rem;
  color: var(--color-text-muted);
}

.empty-state {
  text-align: center;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.empty-state.compact {
  border: 0;
}

.status,
.result {
  width: fit-content;
  border-radius: var(--radius-full);
  padding: 0.2rem 0.55rem;
  font-size: var(--font-size-xs);
  font-style: normal;
  font-weight: 800;
  text-transform: capitalize;
}

.status.draft {
  background: var(--color-gray-200);
  color: var(--color-gray-700);
}

.status.published,
.result.passed {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.status.archived {
  background: var(--color-gray-200);
  color: var(--color-text-muted);
}

.result.failed {
  background: var(--color-error-bg);
  color: var(--color-error);
}

@media (width <= 600px) {
  .file-browser-tools {
    grid-template-columns: 1fr;
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
</style>
