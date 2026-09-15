import { computed, ref } from 'vue';

import {
  groupContributionThreads,
  sortContributionThreads,
} from '@/utils/contributionThreads';

// Every stage of a correction review: open discussion, changes requested of
// the researcher, and a resubmission awaiting the administrator's re-review.
const CORRECTION_REVIEW_STATUSES = new Set([
  'under_review',
  'changes_requested',
  'review_required',
]);

/**
 * One predicate per summary card. The card's number and the list it filters
 * to are both derived from it, so a card never promises a count its filter
 * does not show.
 */
export const QUEUE_FILTERS = Object.freeze({
  all: () => true,
  ready: (thread) => thread.merge_status === 'ready_to_merge',
  corrections: (thread) => CORRECTION_REVIEW_STATUSES.has(thread.merge_status),
  resolution: (thread) => thread.merge_status === 'needs_resolution',
});

function searchableText(thread) {
  return [
    thread.upload_id,
    `#${thread.upload_id}`,
    `contribution ${thread.upload_id}`,
    thread.uploaded_by,
    thread.review_case?.title,
    ...Object.values(thread.files || {}).flat(),
    ...Object.entries(thread.semantic_summary || {}).flat(),
  ]
    .filter((value) => value != null)
    .join(' ')
    .toLocaleLowerCase();
}

/** Group, count, search, filter and sort the contribution queue. */
export function useContributionQueueView({ pendingUploads, reviewCases }) {
  const queueFilter = ref('all');
  const queueQuery = ref('');
  const queueSort = ref('oldest');

  const contributionThreads = computed(() =>
    groupContributionThreads(pendingUploads.value, reviewCases.value)
  );

  const countFor = (name) =>
    computed(
      () => contributionThreads.value.filter(QUEUE_FILTERS[name]).length
    );
  const totalPending = countFor('all');
  const readyCount = countFor('ready');
  const awaitingCorrectionsCount = countFor('corrections');
  const conflictsCount = countFor('resolution');

  const filteredContributionThreads = computed(() => {
    const matchesFilter = QUEUE_FILTERS[queueFilter.value] || QUEUE_FILTERS.all;
    const needle = queueQuery.value.trim().toLocaleLowerCase();
    const matching = contributionThreads.value.filter(
      (thread) =>
        matchesFilter(thread) &&
        (!needle || searchableText(thread).includes(needle))
    );
    return sortContributionThreads(matching, queueSort.value);
  });

  return {
    queueFilter,
    queueQuery,
    queueSort,
    contributionThreads,
    totalPending,
    readyCount,
    awaitingCorrectionsCount,
    conflictsCount,
    filteredContributionThreads,
  };
}
