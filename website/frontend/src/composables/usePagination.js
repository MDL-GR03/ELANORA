import { computed, ref, watch } from 'vue';

/** Pages over a reactive list; the page stays within range as the list changes. */
export function usePagination(items, pageSize) {
  const page = ref(1);
  const pageCount = computed(() =>
    Math.max(1, Math.ceil(items.value.length / pageSize))
  );
  const pageItems = computed(() => {
    const start = (page.value - 1) * pageSize;
    return items.value.slice(start, start + pageSize);
  });

  function goTo(value) {
    const number = Math.trunc(Number(value));
    page.value = Number.isFinite(number)
      ? Math.min(Math.max(number, 1), pageCount.value)
      : 1;
  }

  watch(pageCount, (count) => {
    if (page.value > count) page.value = count;
  });

  return {
    page,
    pageCount,
    pageItems,
    goTo,
    next: () => goTo(page.value + 1),
    previous: () => goTo(page.value - 1),
  };
}
