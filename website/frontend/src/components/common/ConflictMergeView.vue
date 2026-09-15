<template>
  <section class="eaf-review" aria-labelledby="eaf-review-title">
    <header v-if="!compact" class="review-heading">
      <div>
        <span class="eyebrow">{{ t('annotationComparison.eyebrow') }}</span>
        <h3 id="eaf-review-title">{{ filename }}</h3>
        <p>{{ t('annotationComparison.intro') }}</p>
      </div>
      <span v-if="review" class="count">
        {{ t('annotationComparison.changeCount', review.changes.length) }}
      </span>
    </header>

    <div v-if="loading" class="state" role="status">
      <span class="spinner" aria-hidden="true"></span>
      {{ t('annotationComparison.loading') }}
    </div>
    <div v-else-if="error" class="state error" role="alert">
      <font-awesome-icon icon="fa-solid fa-circle-xmark" />
      <div>
        <strong>{{ t('annotationComparison.unavailable') }}</strong>
        <p>{{ error }}</p>
      </div>
    </div>

    <template v-else-if="review">
      <div v-if="comparisonContext" class="state comparison-context">
        <font-awesome-icon :icon="comparisonContext.icon" />
        <div>
          <strong>{{ comparisonContext.title }}</strong>
          <p>{{ comparisonContext.description }}</p>
        </div>
      </div>
      <div v-if="mediaReferences.length" class="state info">
        <font-awesome-icon icon="fa-solid fa-circle-info" />
        <div>
          <strong>{{ t('annotationComparison.linkedMedia') }}</strong>
          <ul v-if="!mediaChanged" class="media-filenames">
            <li v-for="mediaName in mediaReferences" :key="mediaName">
              {{ mediaName }}
            </li>
          </ul>
          <div v-else class="media-reference-changes">
            <div
              v-if="addedMedia.length"
              class="media-change-group media-added"
            >
              <span>{{ t('annotationComparison.mediaAdded') }}</span>
              <ul class="media-filenames">
                <li v-for="mediaName in addedMedia" :key="mediaName">
                  {{ mediaName }}
                </li>
              </ul>
            </div>
            <div
              v-if="removedMedia.length"
              class="media-change-group media-removed"
            >
              <span>{{ t('annotationComparison.mediaRemoved') }}</span>
              <ul class="media-filenames">
                <li v-for="mediaName in removedMedia" :key="mediaName">
                  {{ mediaName }}
                </li>
              </ul>
            </div>
            <div
              v-if="unchangedMedia.length"
              class="media-change-group media-unchanged"
            >
              <span>{{ t('annotationComparison.mediaUnchanged') }}</span>
              <ul class="media-filenames">
                <li v-for="mediaName in unchangedMedia" :key="mediaName">
                  {{ mediaName }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div v-if="review.changes.length" class="review-tools">
        <label class="change-search">
          <span>{{ t('annotationComparison.search') }}</span>
          <input
            v-model.trim="query"
            type="search"
            :placeholder="t('annotationComparison.searchPlaceholder')"
          />
        </label>
        <label :for="tierFilterId">
          <span>{{ t('annotationComparison.tier') }}</span>
          <AppSelect
            :id="tierFilterId"
            v-model="selectedTier"
            size="small"
            :options="tierOptions"
            :aria-label="t('annotationComparison.tierFilter')"
          />
        </label>
        <label :for="kindFilterId">
          <span>{{ t('annotationComparison.change') }}</span>
          <AppSelect
            :id="kindFilterId"
            v-model="selectedKind"
            size="small"
            :options="kindOptions"
            :aria-label="t('annotationComparison.kindFilter')"
          />
        </label>
      </div>
      <div v-if="filteredChanges.length" class="result-summary">
        {{
          t('annotationComparison.showing', {
            start: rangeStart,
            end: rangeEnd,
            count: filteredChanges.length,
          })
        }}
      </div>
      <div v-if="filteredChanges.length" class="review-list">
        <article
          v-for="change in visibleChanges"
          :key="change.annotation_id"
          class="annotation-change"
        >
          <div class="annotation-meta">
            <div>
              <span class="annotation-id">{{ change.annotation_id }}</span>
              <strong>{{ tierLabel(change) }}</strong>
            </div>
            <div class="badges">
              <span
                v-for="kind in change.kinds"
                :key="kind"
                class="badge"
                :class="`kind-${kind}`"
                >{{ formatKind(kind) }}</span
              >
              <span v-if="timeLabel(change)" class="time">
                {{ timeLabel(change) }}
              </span>
            </div>
          </div>

          <div class="comparison">
            <div class="version accepted">
              <span class="version-label">{{
                t('annotationComparison.currentVersion')
              }}</span>
              <p v-if="change.before">
                {{ displayValue(change.before.value) }}
              </p>
              <p v-else class="missing">
                {{ t('annotationComparison.notPresent') }}
              </p>
              <small v-if="change.before">{{
                t('annotationComparison.tierOf', {
                  tier: change.before.tier_id,
                })
              }}</small>
            </div>
            <font-awesome-icon class="arrow" icon="fa-solid fa-chevron-right" />
            <div class="version submitted">
              <span class="version-label">{{
                t('annotationComparison.submittedVersion')
              }}</span>
              <p v-if="change.after">{{ displayValue(change.after.value) }}</p>
              <p v-else class="missing">
                {{ t('annotationComparison.removedAnnotation') }}
              </p>
              <small v-if="change.after">{{
                t('annotationComparison.tierOf', { tier: change.after.tier_id })
              }}</small>
            </div>
          </div>
          <button
            v-if="allowOpenReview"
            type="button"
            class="open-case"
            :class="{ selected: isTargetSelected(change) }"
            :aria-pressed="isTargetSelected(change)"
            @click="$emit('open-review', reviewTarget(change))"
          >
            <font-awesome-icon
              :icon="
                isTargetSelected(change)
                  ? 'fa-solid fa-circle-check'
                  : 'fa-solid fa-plus'
              "
            />
            {{
              isTargetSelected(change)
                ? t('annotationComparison.addedToRequest')
                : reviewActionLabel || t('annotationComparison.openReview')
            }}
          </button>
        </article>
      </div>
      <nav
        v-if="pageCount > 1"
        class="change-pagination"
        :aria-label="t('annotationComparison.pages')"
      >
        <button type="button" :disabled="page === 1" @click="page--">
          {{ t('annotationComparison.previous') }}
        </button>
        <span>{{
          t('annotationComparison.pageOf', { page, count: pageCount })
        }}</span>
        <button type="button" :disabled="page === pageCount" @click="page++">
          {{ t('annotationComparison.next') }}
        </button>
      </nav>
      <div
        v-else-if="review.changes.length && !filteredChanges.length"
        class="state"
      >
        <font-awesome-icon icon="fa-solid fa-filter-circle-xmark" />
        {{ t('annotationComparison.noMatches') }}
      </div>
      <div v-else-if="!review.changes.length" class="state">
        <font-awesome-icon icon="fa-solid fa-circle-check" />
        <div>
          <strong>{{ t('annotationComparison.identicalTitle') }}</strong>
          <p>{{ t('annotationComparison.identicalDescription') }}</p>
        </div>
      </div>

      <footer class="state guidance">
        <div>
          <strong>{{ t('annotationComparison.nextTitle') }}</strong>
          <p v-if="review.changes.length">
            {{ t('annotationComparison.nextWithChanges') }}
          </p>
          <p v-else>{{ t('annotationComparison.nextWithoutChanges') }}</p>
        </div>
      </footer>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, useId, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import gitService from '@/api/service/gitService';
import AppSelect from '@/components/common/AppSelect.vue';

const props = defineProps({
  projectName: { type: String, required: true },
  branchName: { type: String, required: true },
  filename: { type: String, required: true },
  allowOpenReview: { type: Boolean, default: false },
  // Empty uses the translated default action.
  reviewActionLabel: { type: String, default: '' },
  selectedAnnotationIds: { type: Array, default: () => [] },
  compact: { type: Boolean, default: false },
  fileChangeKind: { type: String, default: '' },
});
const emit = defineEmits(['open-review', 'loaded']);
const { t } = useI18n();
const loading = ref(true);
const error = ref('');
const review = ref(null);
const query = ref('');
const selectedTier = ref('');
const selectedKind = ref('');
const page = ref(1);
const PAGE_SIZE = 25;
// Per instance: several comparisons can be on one page at once.
const instanceId = useId();
const tierFilterId = `conflict-tier-filter-${instanceId}`;
const kindFilterId = `conflict-kind-filter-${instanceId}`;
const mediaFilename = (value) => value.replaceAll('\\', '/').split('/').pop();
const beforeMedia = computed(() => [
  ...new Set((review.value?.before_media_urls || []).map(mediaFilename)),
]);
const afterMedia = computed(() => [
  ...new Set((review.value?.after_media_urls || []).map(mediaFilename)),
]);
const mediaReferences = computed(() => [
  ...new Set([...beforeMedia.value, ...afterMedia.value]),
]);
const addedMedia = computed(() =>
  afterMedia.value.filter((item) => !beforeMedia.value.includes(item))
);
const removedMedia = computed(() =>
  beforeMedia.value.filter((item) => !afterMedia.value.includes(item))
);
const unchangedMedia = computed(() =>
  afterMedia.value.filter((item) => beforeMedia.value.includes(item))
);
const mediaChanged = computed(
  () => addedMedia.value.length > 0 || removedMedia.value.length > 0
);
const comparisonContext = computed(() => {
  const changes = review.value?.changes || [];
  if (
    props.fileChangeKind === 'new' &&
    changes.length &&
    changes.every((change) => change.before === null)
  ) {
    return {
      icon: 'fa-solid fa-file-circle-plus',
      title: t('annotationComparison.newFile.title'),
      description: t('annotationComparison.newFile.description'),
    };
  }
  if (
    props.fileChangeKind === 'deleted' &&
    changes.length &&
    changes.every((change) => change.after === null)
  ) {
    return {
      icon: 'fa-solid fa-file-circle-minus',
      title: t('annotationComparison.removedFile.title'),
      description: t('annotationComparison.removedFile.description'),
    };
  }
  return null;
});
const tiers = computed(() =>
  [...new Set((review.value?.changes || []).flatMap(changeTiers))].sort()
);
const kinds = computed(() =>
  [
    ...new Set((review.value?.changes || []).flatMap((change) => change.kinds)),
  ].sort()
);
const tierOptions = computed(() => [
  { value: '', label: t('annotationComparison.allTiers') },
  ...tiers.value.map((tier) => ({ value: tier, label: tier })),
]);
const kindOptions = computed(() => [
  { value: '', label: t('annotationComparison.allChanges') },
  ...kinds.value.map((kind) => ({ value: kind, label: formatKind(kind) })),
]);
const filteredChanges = computed(() => {
  const needle = query.value.toLocaleLowerCase();
  return (review.value?.changes || []).filter((change) => {
    const searchable = [
      change.annotation_id,
      ...changeTiers(change),
      change.before?.value,
      change.after?.value,
    ]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase();
    return (
      (!needle || searchable.includes(needle)) &&
      (!selectedTier.value ||
        changeTiers(change).includes(selectedTier.value)) &&
      (!selectedKind.value || change.kinds.includes(selectedKind.value))
    );
  });
});
const pageCount = computed(() =>
  Math.max(1, Math.ceil(filteredChanges.value.length / PAGE_SIZE))
);
const visibleChanges = computed(() =>
  filteredChanges.value.slice(
    (page.value - 1) * PAGE_SIZE,
    page.value * PAGE_SIZE
  )
);
const rangeStart = computed(() => (page.value - 1) * PAGE_SIZE + 1);
const rangeEnd = computed(() =>
  Math.min(page.value * PAGE_SIZE, filteredChanges.value.length)
);

const displayValue = (value) =>
  value || t('annotationComparison.emptyAnnotation');
const isTargetSelected = (change) =>
  props.selectedAnnotationIds.includes(change.annotation_id);
const KINDS = [
  'added',
  'removed',
  'value_changed',
  'timing_changed',
  'tier_changed',
  'reference_changed',
];
const formatKind = (kind) =>
  KINDS.includes(kind)
    ? t(`annotationComparison.kinds.${kind}`)
    : kind.replaceAll('_', ' ');
function tierLabel(change) {
  const before = change.before?.tier_id;
  const after = change.after?.tier_id;
  return before === after || !before || !after
    ? before || after || t('annotationComparison.unknownTier')
    : `${before} → ${after}`;
}
function changeTiers(change) {
  return [
    ...new Set([change.before?.tier_id, change.after?.tier_id].filter(Boolean)),
  ];
}
function formatTime(milliseconds) {
  const seconds = milliseconds / 1000;
  return `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(3).padStart(6, '0')}`;
}
function timeLabel(change) {
  const starts = [change.before?.start_ms, change.after?.start_ms].filter(
    Number.isFinite
  );
  const ends = [change.before?.end_ms, change.after?.end_ms].filter(
    Number.isFinite
  );
  return starts.length && ends.length
    ? `${formatTime(Math.min(...starts))}–${formatTime(Math.max(...ends))}`
    : '';
}
function reviewTarget(change) {
  const starts = [change.before?.start_ms, change.after?.start_ms].filter(
    Number.isFinite
  );
  const ends = [change.before?.end_ms, change.after?.end_ms].filter(
    Number.isFinite
  );
  return {
    filename: props.filename,
    tier_id: change.after?.tier_id || change.before?.tier_id || null,
    annotation_id: change.annotation_id,
    start_ms: starts.length ? Math.min(...starts) : null,
    end_ms: ends.length ? Math.max(...ends) : null,
    title: t('annotationComparison.reviewTitle', { id: change.annotation_id }),
    current_text: change.before?.value || null,
    suggested_text: change.after?.value || null,
    change_kinds: change.kinds,
  };
}
// Each load is numbered. A response is applied only if no newer load has
// started, and is reported under the file it was requested for. Otherwise a
// slow response for one file could be shown, and recorded by a resolution
// decision, as the comparison of another.
let loadSequence = 0;

async function loadReview() {
  const request = ++loadSequence;
  const requested = {
    projectName: props.projectName,
    branchName: props.branchName,
    filename: props.filename,
  };
  loading.value = true;
  error.value = '';
  review.value = null;
  try {
    const result = await gitService.getEafReview(
      requested.projectName,
      requested.branchName,
      requested.filename
    );
    if (request !== loadSequence) return;
    review.value = result;
    emit('loaded', { filename: requested.filename, review: result });
  } catch (requestError) {
    if (request !== loadSequence) return;
    error.value =
      requestError?.response?.data?.detail ||
      t('annotationComparison.loadFailed');
  } finally {
    if (request === loadSequence) loading.value = false;
  }
}

// Page and filters describe one file. Tier identifiers differ between files,
// and a page number from a longer file could point past the end of this one.
function resetNavigation() {
  query.value = '';
  selectedTier.value = '';
  selectedKind.value = '';
  page.value = 1;
}

onMounted(loadReview);
watch(
  () => [props.projectName, props.branchName, props.filename],
  () => {
    resetNavigation();
    void loadReview();
  }
);
watch([query, selectedTier, selectedKind], () => {
  page.value = 1;
});
watch(pageCount, (count) => {
  if (page.value > count) page.value = count;
});
</script>

<style scoped>
.eaf-review {
  display: grid;
  gap: 1.1rem;
  margin-top: 0.35rem;
  padding: 1rem 0.1rem 0.15rem;
  border-top: 1px solid #dbeafe;
  color: var(--color-text);
}

.review-heading,
.annotation-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.review-heading h3,
.review-heading p,
.state p {
  margin: 0;
}

.review-heading h3 {
  margin-block: 0.3rem 0.4rem;
  overflow-wrap: anywhere;
}

.review-heading p,
.state p,
.version small {
  color: var(--color-text-muted);
}

.eyebrow,
.version-label,
.annotation-id {
  color: var(--primary-color);
  font-size: 0.75rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.count,
.badge,
.time {
  flex: none;
  padding: 0.3rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}

.count,
.time {
  color: #1e40af;
  background: #dbeafe;
}

.state {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.state > div {
  min-width: 0;
}

.state.error {
  color: #991b1b;
  border-color: #fecaca;
  background: #fef2f2;
}

.state.comparison-context {
  color: #1e40af;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.media-reference-changes {
  display: grid;
  gap: 0.65rem;
  margin-top: 0.55rem;
}

.media-change-group {
  display: grid;
  grid-template-columns: 5.5rem minmax(0, 1fr);
  align-items: start;
  gap: 0.55rem;
}

.media-change-group > span {
  padding: 0.15rem 0.4rem;
  border-radius: 999px;
  text-align: center;
  font-size: 0.72rem;
  font-weight: 750;
}

.media-filenames {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.55rem 0 0;
  padding: 0;
  list-style: none;
}

.media-change-group .media-filenames {
  margin-top: 0;
}

.media-filenames li {
  min-width: 0;
  max-width: 100%;
  padding: 0.28rem 0.5rem;
  border: 1px solid #d7e0ec;
  border-radius: 0.4rem;
  color: #40536d;
  background: white;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.76rem;
  overflow-wrap: anywhere;
}

.media-added span {
  color: #166534;
  background: #dcfce7;
}

.media-removed span {
  color: #991b1b;
  background: #fee2e2;
}

.media-unchanged span {
  color: #475569;
  background: #e2e8f0;
}

.review-list {
  display: grid;
  gap: 0.75rem;
  max-height: min(60vh, 48rem);
  padding-right: 0.25rem;
  overflow: auto;
}

.review-tools {
  display: grid;
  grid-template-columns: minmax(12rem, 2fr) repeat(2, minmax(8rem, 1fr));
  gap: 0.65rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.review-tools label {
  display: grid;
  gap: 0.3rem;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 700;
}

.review-tools input,
.review-tools select {
  min-width: 0;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: 0.45rem;
  color: var(--color-text);
  background: white;
  font: inherit;
}

.result-summary {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 650;
}

.change-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.change-pagination button {
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: 0.45rem;
  color: var(--primary-color);
  background: white;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.change-pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.annotation-change {
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.open-case {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: 0.85rem;
  padding: 0.55rem 0.75rem;
  color: var(--primary-color);
  border: 1px solid #93c5fd;
  border-radius: var(--radius-sm);
  background: white;
  font-weight: 700;
  cursor: pointer;
}

.open-case.selected {
  color: #166534;
  border-color: #86efac;
  background: #f0fdf4;
}

.annotation-meta > div:first-child {
  display: grid;
  gap: 0.15rem;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.35rem;
}

.badge {
  color: #92400e;
  background: #fef3c7;
}

.kind-added {
  color: #166534;
  background: #dcfce7;
}

.kind-removed {
  color: #991b1b;
  background: #fee2e2;
}

.comparison {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: stretch;
  gap: 0.75rem;
  margin-top: 0.9rem;
}

.version {
  min-width: 0;
  padding: 0.85rem;
  border-radius: var(--radius-sm);
}

.version.accepted {
  background: #f1f5f9;
}

.version.submitted {
  background: #eff6ff;
}

.version p {
  margin: 0.35rem 0;
  font-size: 1rem;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.missing {
  color: var(--color-text-muted);
  font-style: italic;
}

.arrow {
  align-self: center;
  color: var(--color-text-muted);
}

.spinner {
  width: 1.1rem;
  height: 1.1rem;
  border: 2px solid var(--color-border);
  border-radius: 50%;
  animation: spin 700ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (width <= 700px) {
  .review-heading,
  .annotation-meta {
    align-items: stretch;
    flex-direction: column;
  }

  .badges {
    justify-content: flex-start;
  }

  .comparison {
    grid-template-columns: 1fr;
  }

  .review-tools {
    grid-template-columns: 1fr;
  }

  .eaf-review {
    gap: 0.85rem;
    padding-top: 0.85rem;
  }

  .state {
    padding: 0.8rem;
  }

  .media-change-group {
    grid-template-columns: 1fr;
  }

  .media-change-group > span {
    width: fit-content;
  }

  .arrow {
    justify-self: center;
    transform: rotate(90deg);
  }
}
</style>
