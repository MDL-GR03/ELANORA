import { nextTick, ref } from 'vue';
import { describe, expect, it } from 'vitest';

import { usePagination } from './usePagination';

describe('usePagination', () => {
  it('pages through items and keeps the page in range', async () => {
    const items = ref([1, 2, 3, 4, 5, 6, 7]);
    const pages = usePagination(items, 3);

    expect(pages.pageCount.value).toBe(3);
    pages.next();
    expect(pages.pageItems.value).toEqual([4, 5, 6]);
    pages.goTo('99');
    expect(pages.page.value).toBe(3);
    pages.goTo('not a number');
    expect(pages.page.value).toBe(1);
    pages.previous();
    expect(pages.page.value).toBe(1);

    pages.goTo(3);
    items.value = [1, 2];
    await nextTick();
    expect(pages.page.value).toBe(1);
  });
});
