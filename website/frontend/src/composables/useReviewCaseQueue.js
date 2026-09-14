import { computed, ref, watch } from 'vue';

const PAGE_SIZE = 10;
const finishedStates = new Set(['resolved', 'closed']);

export function useReviewCaseQueue(cases) {
  const query = ref('');
  const status = ref('');
  const page = ref(1);
  const isFinished = (state) => finishedStates.has(state);
  const activeCases = computed(() =>
    cases.value.filter((item) => !isFinished(item.state))
  );
  const closedCases = computed(() =>
    cases.value.filter((item) => isFinished(item.state))
  );
  const filteredActiveCases = computed(() => {
    const needle = query.value.toLocaleLowerCase();
    return activeCases.value.filter((item) => {
      const searchable = [
        item.title,
        item.upload_id,
        item.resubmitted_upload_id,
        item.creator_name,
        ...(item.tasks || []).flatMap((task) => [
          task.filename,
          task.tier_id,
          task.annotation_id,
          task.instruction,
          task.current_text,
          task.suggested_text,
        ]),
      ]
        .filter((value) => value != null)
        .join(' ')
        .toLocaleLowerCase();
      return (
        (!status.value || item.state === status.value) &&
        (!needle || searchable.includes(needle))
      );
    });
  });
  const pageCount = computed(() =>
    Math.max(1, Math.ceil(filteredActiveCases.value.length / PAGE_SIZE))
  );
  const visibleActiveCases = computed(() => {
    const start = (page.value - 1) * PAGE_SIZE;
    return filteredActiveCases.value.slice(start, start + PAGE_SIZE);
  });
  const activeCount = computed(() => activeCases.value.length);
  const changesRequestedCount = computed(
    () =>
      cases.value.filter((item) => item.state === 'changes_requested').length
  );
  const resubmittedCount = computed(
    () => cases.value.filter((item) => item.state === 'resubmitted').length
  );

  watch([query, status], () => {
    page.value = 1;
  });
  watch(pageCount, (count) => {
    if (page.value > count) page.value = count;
  });

  return {
    query,
    status,
    page,
    pageCount,
    activeCases,
    closedCases,
    filteredActiveCases,
    visibleActiveCases,
    activeCount,
    changesRequestedCount,
    resubmittedCount,
    isFinished,
  };
}
