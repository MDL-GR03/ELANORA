<template>
  <section class="eaf-review" aria-labelledby="eaf-review-title">
    <header class="review-heading">
      <div>
        <span class="eyebrow">ELAN annotation comparison</span>
        <h3 id="eaf-review-title">{{ filename }}</h3>
        <p>
          Review annotation meaning and timing. Corrections remain in ELAN and
          are submitted as a new revision.
        </p>
      </div>
      <span v-if="review" class="count">
        {{ review.changes.length }}
        {{ review.changes.length === 1 ? 'change' : 'changes' }}
      </span>
    </header>

    <div v-if="loading" class="state" role="status">
      <span class="spinner" aria-hidden="true"></span>
      Preparing the annotation preview…
    </div>
    <div v-else-if="error" class="state error" role="alert">
      <font-awesome-icon icon="fa-solid fa-circle-xmark" />
      <div>
        <strong>Preview unavailable</strong>
        <p>{{ error }}</p>
      </div>
    </div>

    <template v-else-if="review">
      <div v-if="mediaReferences.length" class="state info">
        <font-awesome-icon icon="fa-solid fa-circle-info" />
        <div>
          <strong>Linked media</strong>
          <p>
            {{ mediaReferences.join(', ') }}. Synchronized playback becomes
            available when this media is stored as a protected project asset.
          </p>
        </div>
      </div>

      <div v-if="review.changes.length" class="review-list">
        <article
          v-for="change in review.changes"
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
              <span class="version-label">Accepted project version</span>
              <p v-if="change.before">
                {{ displayValue(change.before.value) }}
              </p>
              <p v-else class="missing">Annotation not present</p>
              <small v-if="change.before"
                >Tier: {{ change.before.tier_id }}</small
              >
            </div>
            <font-awesome-icon class="arrow" icon="fa-solid fa-chevron-right" />
            <div class="version submitted">
              <span class="version-label">Submitted version</span>
              <p v-if="change.after">{{ displayValue(change.after.value) }}</p>
              <p v-else class="missing">Annotation removed</p>
              <small v-if="change.after"
                >Tier: {{ change.after.tier_id }}</small
              >
            </div>
          </div>
          <button
            type="button"
            class="open-case"
            @click="$emit('open-review', reviewTarget(change))"
          >
            <font-awesome-icon icon="fa-solid fa-comment-medical" />
            Open a review case for this annotation
          </button>
        </article>
      </div>
      <div v-else class="state">
        <font-awesome-icon icon="fa-solid fa-circle-check" />
        No annotation-level differences were found in these valid EAF files.
      </div>

      <footer class="state guidance">
        <div>
          <strong>What happens next?</strong>
          <p>
            Close the preview to keep reviewing. For mixed corrections, ask the
            contributor to correct the file in ELAN and upload a new revision.
          </p>
        </div>
      </footer>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import gitService from '@/api/service/gitService';

const props = defineProps({
  projectName: { type: String, required: true },
  branchName: { type: String, required: true },
  filename: { type: String, required: true },
});
defineEmits(['open-review']);
const loading = ref(true);
const error = ref('');
const review = ref(null);
const mediaReferences = computed(() => [
  ...new Set(
    [
      ...(review.value?.before_media_urls || []),
      ...(review.value?.after_media_urls || []),
    ].map((item) => item.split('/').pop())
  ),
]);

const displayValue = (value) => value || 'Empty annotation';
const formatKind = (kind) => kind.replaceAll('_', ' ');
function tierLabel(change) {
  const before = change.before?.tier_id;
  const after = change.after?.tier_id;
  return before === after || !before || !after
    ? before || after || 'Unknown tier'
    : `${before} → ${after}`;
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
    title: `Review annotation ${change.annotation_id}`,
  };
}
async function loadReview() {
  loading.value = true;
  error.value = '';
  review.value = null;
  try {
    review.value = await gitService.getEafReview(
      props.projectName,
      props.branchName,
      props.filename
    );
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The accepted and submitted files could not be compared.';
  } finally {
    loading.value = false;
  }
}
onMounted(loadReview);
watch(() => [props.projectName, props.branchName, props.filename], loadReview);
</script>

<style scoped>
.eaf-review {
  display: grid;
  gap: 1rem;
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
  margin-block: 0.2rem;
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

.state.error {
  color: #991b1b;
  border-color: #fecaca;
  background: #fef2f2;
}

.review-list {
  display: grid;
  gap: 0.75rem;
  max-height: min(60vh, 48rem);
  padding-right: 0.25rem;
  overflow: auto;
}

.annotation-change {
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.open-case {
  margin-top: 0.85rem;
  color: var(--primary-color);
  border: 0;
  background: transparent;
  font-weight: 700;
  cursor: pointer;
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

  .arrow {
    justify-self: center;
    transform: rotate(90deg);
  }
}
</style>
