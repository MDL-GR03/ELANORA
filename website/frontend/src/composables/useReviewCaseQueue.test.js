import { nextTick, ref } from 'vue';
import { describe, expect, it } from 'vitest';

import { useReviewCaseQueue } from './useReviewCaseQueue';

function reviewCase(id, state = 'open', overrides = {}) {
  return {
    case_id: `case-${id}`,
    title: `Review ${id}`,
    state,
    upload_id: id,
    tasks: [],
    ...overrides,
  };
}

describe('useReviewCaseQueue', () => {
  it('separates active and archived states and reports workflow counts', () => {
    const queue = useReviewCaseQueue(
      ref([
        reviewCase(1),
        reviewCase(2, 'changes_requested'),
        reviewCase(3, 'resubmitted'),
        reviewCase(4, 'resolved'),
        reviewCase(5, 'closed'),
      ])
    );

    expect(queue.activeCount.value).toBe(3);
    expect(queue.closedCases.value).toHaveLength(2);
    expect(queue.changesRequestedCount.value).toBe(1);
    expect(queue.resubmittedCount.value).toBe(1);
  });

  it('searches case identity and nested correction evidence', () => {
    const queue = useReviewCaseQueue(
      ref([
        reviewCase(1, 'open', {
          tasks: [
            {
              filename: 'elan_files/session.eaf',
              tier_id: 'translation',
              annotation_id: 'A17',
              instruction: 'Correct the gloss',
            },
          ],
        }),
        reviewCase(2),
      ])
    );

    queue.query.value = 'a17';
    expect(queue.filteredActiveCases.value.map((item) => item.case_id)).toEqual(
      ['case-1']
    );
    queue.query.value = '';
    queue.status.value = 'open';
    expect(queue.filteredActiveCases.value).toHaveLength(2);
  });

  it('paginates ten cases and returns to page one when filters change', async () => {
    const queue = useReviewCaseQueue(
      ref(Array.from({ length: 12 }, (_, index) => reviewCase(index + 1)))
    );

    expect(queue.pageCount.value).toBe(2);
    queue.page.value = 2;
    expect(queue.visibleActiveCases.value).toHaveLength(2);
    queue.query.value = 'Review 1';
    await nextTick();
    expect(queue.page.value).toBe(1);
  });
});
