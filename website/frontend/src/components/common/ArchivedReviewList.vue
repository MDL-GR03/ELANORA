<template>
  <section id="review-archive" class="archive" aria-labelledby="archive-title">
    <div class="archive-heading">
      <div>
        <span>{{ t('reviewArchive.eyebrow') }}</span>
        <h5 id="archive-title">{{ t('reviewArchive.title') }}</h5>
      </div>
      <strong>{{
        t('reviewArchive.archivedCount', { count: cases.length })
      }}</strong>
    </div>

    <div class="archive-tools">
      <label>
        <span>{{ t('reviewArchive.search') }}</span>
        <input
          v-model.trim="query"
          type="search"
          :placeholder="t('reviewArchive.searchPlaceholder')"
        />
      </label>
      <label for="archive-outcome-filter">
        <span>{{ t('reviewArchive.outcome') }}</span>
        <AppSelect
          id="archive-outcome-filter"
          v-model="stateFilter"
          size="small"
          :options="outcomeOptions"
          :aria-label="t('reviewArchive.outcomeFilter')"
        />
      </label>
    </div>

    <p v-if="!filteredCases.length" class="archive-empty">
      {{ t('reviewArchive.empty') }}
    </p>

    <div v-else class="archive-list">
      <details
        v-for="item in pageCases"
        :id="`archived-review-${item.case_id}`"
        :key="item.case_id"
        class="archive-item"
        :class="{ highlighted: item.case_id === highlightedCaseId }"
        :open="item.case_id === highlightedCaseId"
      >
        <summary>
          <span class="archive-summary-main">
            <strong>{{ item.title }}</strong>
            <small>
              {{ item.filename || t('reviewArchive.generalReview') }}
            </small>
          </span>
          <span class="archive-summary-meta">
            <span class="archive-state">{{ formatState(item) }}</span>
            <time :datetime="item.updated_at">{{
              formatDate(item.updated_at)
            }}</time>
            <font-awesome-icon icon="fa-solid fa-chevron-down" />
          </span>
        </summary>

        <div class="archive-details">
          <dl>
            <div>
              <dt>{{ t('reviewArchive.openedBy') }}</dt>
              <dd>
                {{ item.creator_name || t('reviewArchive.formerMember') }}
              </dd>
            </div>
            <div>
              <dt>{{ t('reviewArchive.contribution') }}</dt>
              <dd>
                #{{ item.upload_id }}
                <template v-if="item.resubmitted_upload_id">
                  → #{{ item.resubmitted_upload_id }}
                </template>
              </dd>
            </div>
            <div>
              <dt>{{ t('reviewArchive.reviewLead') }}</dt>
              <dd>
                {{ item.assignee_name || t('reviewArchive.notAssigned') }}
              </dd>
            </div>
            <div>
              <dt>{{ t('reviewArchive.closedAt') }}</dt>
              <dd>{{ formatDate(item.resolved_at || item.updated_at) }}</dd>
            </div>
            <div>
              <dt>{{ t('reviewArchive.openedAt') }}</dt>
              <dd>{{ formatDate(item.created_at) }}</dd>
            </div>
          </dl>

          <section
            v-if="
              item.tier_id ||
              item.annotation_id ||
              item.start_ms != null ||
              item.end_ms != null
            "
            class="archive-subsection"
          >
            <h6>{{ t('reviewArchive.target') }}</h6>
            <div class="archive-target">
              <span v-if="item.tier_id"
                ><strong>{{ t('reviewArchive.tier') }}</strong
                >{{ item.tier_id }}</span
              >
              <span v-if="item.annotation_id">
                <strong>{{ t('reviewArchive.annotation') }}</strong
                >{{ item.annotation_id }}
              </span>
              <span v-if="item.start_ms != null || item.end_ms != null">
                <strong>{{ t('reviewArchive.time') }}</strong
                >{{ formatTimeRange(item) }}
              </span>
            </div>
          </section>

          <section
            v-if="item.current_text || item.suggested_text"
            class="archive-subsection"
          >
            <h6>{{ t('reviewArchive.suggestion') }}</h6>
            <div class="archive-suggestion">
              <div>
                <span>{{ t('reviewArchive.original') }}</span>
                <p>{{ item.current_text || t('reviewArchive.notRecorded') }}</p>
              </div>
              <font-awesome-icon icon="fa-solid fa-arrow-right" />
              <div>
                <span>{{ t('reviewArchive.suggested') }}</span>
                <p>
                  {{ item.suggested_text || t('reviewArchive.notRecorded') }}
                </p>
              </div>
            </div>
          </section>

          <section v-if="item.tasks?.length" class="archive-subsection">
            <h6>
              {{
                t('reviewArchive.requestedFiles', { count: item.tasks.length })
              }}
            </h6>
            <ul class="archive-tasks">
              <li v-for="task in item.tasks" :key="task.task_id">
                <div>
                  <strong>{{ task.filename }}</strong>
                  <span>{{ formatTaskStatus(task.status) }}</span>
                </div>
                <p>{{ task.instruction }}</p>
                <small v-if="task.tier_id || task.annotation_id">
                  {{ task.tier_id || t('reviewArchive.anyTier') }} ·
                  {{ task.annotation_id || t('reviewArchive.anyAnnotation') }}
                </small>
                <div
                  v-if="task.current_text || task.suggested_text"
                  class="archive-task-suggestion"
                >
                  <span>{{
                    task.current_text || t('reviewArchive.notRecorded')
                  }}</span>
                  <font-awesome-icon icon="fa-solid fa-arrow-right" />
                  <span>{{
                    task.suggested_text || t('reviewArchive.notRecorded')
                  }}</span>
                </div>
              </li>
            </ul>
          </section>

          <section v-if="item.comments?.length" class="archive-subsection">
            <h6>
              {{
                t('reviewArchive.discussion', { count: item.comments.length })
              }}
            </h6>
            <ol class="archive-comments">
              <li v-for="comment in item.comments" :key="comment.comment_id">
                <div>
                  <strong>{{ comment.author_name }}</strong>
                  <time :datetime="comment.created_at">
                    {{ formatDate(comment.created_at) }}
                  </time>
                </div>
                <p>{{ comment.body }}</p>
              </li>
            </ol>
          </section>
        </div>
      </details>
    </div>

    <nav
      v-if="pageCount > 1"
      class="archive-pagination"
      :aria-label="t('reviewArchive.pages')"
    >
      <button type="button" :disabled="page === 1" @click="page -= 1">
        {{ t('reviewArchive.previous') }}
      </button>
      <span>{{ t('reviewArchive.pageOf', { page, count: pageCount }) }}</span>
      <button type="button" :disabled="page === pageCount" @click="page += 1">
        {{ t('reviewArchive.next') }}
      </button>
    </nav>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import AppSelect from '@/components/common/AppSelect.vue';

const { t, locale } = useI18n();
const outcomeOptions = computed(() => [
  { value: '', label: t('reviewArchive.outcomes.all') },
  { value: 'closed', label: t('reviewArchive.outcomes.closed') },
  { value: 'resolved', label: t('reviewArchive.outcomes.resolved') },
]);

const props = defineProps({
  cases: { type: Array, default: () => [] },
  highlightedCaseId: { type: String, default: '' },
});

const PAGE_SIZE = 8;
const query = ref('');
const stateFilter = ref('');
const page = ref(1);

const filteredCases = computed(() => {
  const needle = query.value.toLocaleLowerCase();
  return props.cases.filter((item) => {
    const searchable = [
      item.title,
      item.filename,
      item.upload_id,
      item.resubmitted_upload_id,
      item.assignee_name,
      ...(item.tasks || []).flatMap((task) => [
        task.filename,
        task.instruction,
      ]),
      ...(item.comments || []).flatMap((comment) => [
        comment.author_name,
        comment.body,
      ]),
    ]
      .filter((value) => value !== null && value !== undefined)
      .join(' ')
      .toLocaleLowerCase();
    return (
      (!stateFilter.value || item.state === stateFilter.value) &&
      (!needle || searchable.includes(needle))
    );
  });
});
const pageCount = computed(() =>
  Math.max(1, Math.ceil(filteredCases.value.length / PAGE_SIZE))
);
const pageCases = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE;
  return filteredCases.value.slice(start, start + PAGE_SIZE);
});

watch([query, stateFilter], () => {
  page.value = 1;
});
watch(pageCount, (count) => {
  if (page.value > count) page.value = count;
});
watch(
  [() => props.highlightedCaseId, filteredCases],
  async ([highlightedCaseId, cases]) => {
    if (!highlightedCaseId) return;
    const index = cases.findIndex((item) => item.case_id === highlightedCaseId);
    if (index === -1) return;
    query.value = '';
    stateFilter.value = '';
    page.value = Math.floor(index / PAGE_SIZE) + 1;
    await nextTick();
    document
      .getElementById(`archived-review-${highlightedCaseId}`)
      ?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
  },
  { immediate: true, flush: 'post' }
);

const formatState = (item) => {
  if (item.resubmitted_upload_status === 'no_changes') {
    return t('reviewArchive.states.approvedNoChanges');
  }
  return item.state === 'resolved'
    ? t('reviewArchive.states.approved')
    : t('reviewArchive.states.closed');
};
const TASK_STATUSES = ['requested', 'reopened', 'addressed', 'accepted'];
const formatTaskStatus = (status) =>
  TASK_STATUSES.includes(status)
    ? t(`reviewArchive.taskStatus.${status}`)
    : status;
const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat(locale.value, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(value))
    : t('reviewArchive.notRecorded');
const formatTimeRange = (item) => {
  const start =
    item.start_ms == null
      ? t('reviewArchive.startNotSet')
      : t('reviewArchive.milliseconds', { value: item.start_ms });
  const end =
    item.end_ms == null
      ? t('reviewArchive.endNotSet')
      : t('reviewArchive.milliseconds', { value: item.end_ms });
  return t('reviewArchive.timeRange', { start, end });
};
</script>

<style scoped>
.archive {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: white;
}

.archive-heading,
.archive-tools,
.archive-item summary,
.archive-summary-meta,
.archive-comments li > div,
.archive-tasks li > div,
.archive-pagination {
  display: flex;
  align-items: center;
}

.archive-heading,
.archive-item summary,
.archive-comments li > div,
.archive-tasks li > div {
  justify-content: space-between;
}

.archive-heading > div {
  min-width: 0;
}

.archive-heading span {
  color: var(--primary-color);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.archive-heading h5 {
  margin: 0.15rem 0 0;
  font-size: 1rem;
}

.archive-heading > strong,
.archive-state {
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  color: #475569;
  background: #eef2f7;
  font-size: 0.75rem;
}

.archive-tools {
  align-items: end;
  gap: 0.65rem;
}

.archive-tools label {
  flex: 1;
  display: grid;
  gap: 0.25rem;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 700;
}

.archive-tools label:last-child {
  max-width: 12rem;
}

.archive-tools input,
.archive-tools select {
  width: 100%;
  min-height: 2.5rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: white;
}

.archive-list {
  display: grid;
  gap: 0.5rem;
}

.archive-item {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.archive-item.highlighted {
  border-color: #60a5fa;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 12%);
}

.archive-item summary {
  gap: 1rem;
  padding: 0.75rem;
  list-style: none;
  cursor: pointer;
}

.archive-item summary::-webkit-details-marker {
  display: none;
}

.archive-item summary:hover {
  background: var(--color-surface-subtle);
}

.archive-summary-main {
  min-width: 0;
  display: grid;
  gap: 0.15rem;
}

.archive-summary-main strong,
.archive-summary-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.archive-summary-main small,
.archive-summary-meta time {
  color: var(--color-text-muted);
}

.archive-summary-meta {
  flex: none;
  gap: 0.65rem;
  font-size: 0.75rem;
}

.archive-item[open] .archive-summary-meta svg {
  transform: rotate(180deg);
}

.archive-details {
  display: grid;
  gap: 1rem;
  padding: 0.85rem;
  border-top: 1px solid var(--color-border);
  background: white;
}

.archive-details dl {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.6rem;
  margin: 0;
}

.archive-details dl > div {
  min-width: 0;
}

.archive-details dt {
  color: var(--color-text-muted);
  font-size: 0.7rem;
  font-weight: 700;
}

.archive-details dd {
  margin: 0.15rem 0 0;
  overflow-wrap: anywhere;
}

.archive-subsection h6 {
  margin: 0 0 0.5rem;
  font-size: 0.82rem;
}

.archive-target {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.archive-target span {
  display: inline-flex;
  gap: 0.35rem;
  padding: 0.4rem 0.55rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface-subtle);
  font-size: 0.78rem;
}

.archive-suggestion {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 0.65rem;
}

.archive-suggestion > div {
  min-width: 0;
  height: 100%;
  padding: 0.65rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface-subtle);
}

.archive-suggestion span {
  color: var(--primary-color);
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
}

.archive-tasks,
.archive-comments {
  display: grid;
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.archive-tasks li,
.archive-comments li {
  padding: 0.65rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface-subtle);
}

.archive-tasks li > div,
.archive-comments li > div {
  gap: 0.75rem;
}

.archive-tasks li span,
.archive-comments time {
  flex: none;
  color: var(--color-text-muted);
  font-size: 0.72rem;
}

.archive-tasks p,
.archive-comments p {
  margin: 0.3rem 0 0;
  overflow-wrap: anywhere;
}

.archive-tasks small {
  display: block;
  margin-top: 0.3rem;
  color: var(--color-text-muted);
}

.archive-task-suggestion {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: white;
  font-size: 0.78rem;
}

.archive-pagination {
  justify-content: center;
  gap: 0.75rem;
}

.archive-pagination button {
  padding: 0.45rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: white;
}

.archive-pagination button:disabled {
  opacity: 0.5;
}

.archive-pagination span,
.archive-empty {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  text-align: center;
}

@media (width <= 700px) {
  .archive-tools,
  .archive-item summary {
    align-items: stretch;
    flex-direction: column;
  }

  .archive-tools label:last-child {
    max-width: none;
  }

  .archive-summary-meta {
    justify-content: space-between;
  }

  .archive-details dl {
    grid-template-columns: 1fr;
  }

  .archive-suggestion,
  .archive-task-suggestion {
    grid-template-columns: 1fr;
  }

  .archive-suggestion > svg,
  .archive-task-suggestion > svg {
    transform: rotate(90deg);
  }
}
</style>
