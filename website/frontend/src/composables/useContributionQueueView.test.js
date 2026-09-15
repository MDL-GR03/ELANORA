import { ref } from 'vue';
import { describe, expect, it } from 'vitest';

import {
  QUEUE_FILTERS,
  useContributionQueueView,
} from './useContributionQueueView';

function contribution(id, mergeStatus, extra = {}) {
  return {
    upload_id: id,
    merge_status: mergeStatus,
    uploaded_by: `researcher-${id}`,
    uploaded_at: `2026-09-${String(id).padStart(2, '0')}T10:00:00Z`,
    files: { modified: [`elan_files/session-${id}.eaf`] },
    ...extra,
  };
}

function setup(uploads, reviewCases = []) {
  return useContributionQueueView({
    pendingUploads: ref(uploads),
    reviewCases: ref(reviewCases),
  });
}

describe('useContributionQueueView', () => {
  it('shows exactly as many contributions as each summary card counts', () => {
    const queue = setup(
      [
        contribution(1, 'ready_to_merge'),
        contribution(2, 'needs_resolution'),
        contribution(3, 'pending_admin_approval'),
        contribution(4, 'ready_to_merge'),
        contribution(5, 'ready_to_merge'),
        contribution(6, 'ready_to_merge'),
      ],
      [
        { case_id: 'a', upload_id: 4, state: 'open' },
        { case_id: 'b', upload_id: 5, state: 'changes_requested' },
        { case_id: 'c', upload_id: 6, state: 'resubmitted' },
      ]
    );
    const counts = {
      all: queue.totalPending,
      ready: queue.readyCount,
      corrections: queue.awaitingCorrectionsCount,
      resolution: queue.conflictsCount,
    };

    for (const name of Object.keys(QUEUE_FILTERS)) {
      queue.queueFilter.value = name;
      expect(
        queue.filteredContributionThreads.value.length,
        `the "${name}" card`
      ).toBe(counts[name].value);
    }
    // Previously this card counted only changes_requested while showing all three.
    expect(queue.awaitingCorrectionsCount.value).toBe(3);
  });

  it('finds a contribution by number, contributor or filename, ignoring case', () => {
    const queue = setup([
      contribution(6, 'ready_to_merge', { uploaded_by: 'External.Researcher' }),
      contribution(7, 'ready_to_merge', {
        files: { new: ['elan_files/CLSFB2912_S060.eaf'] },
      }),
    ]);
    const ids = () =>
      queue.filteredContributionThreads.value.map((item) => item.upload_id);

    queue.queueQuery.value = '#6';
    expect(ids()).toEqual([6]);
    queue.queueQuery.value = 'external.researcher';
    expect(ids()).toEqual([6]);
    queue.queueQuery.value = '  clsfb2912_s060 ';
    expect(ids()).toEqual([7]);
  });

  it('searches within the selected filter only', () => {
    const queue = setup([
      contribution(1, 'ready_to_merge'),
      contribution(2, 'needs_resolution'),
    ]);
    queue.queueFilter.value = 'ready';
    queue.queueQuery.value = 'session-2';
    expect(queue.filteredContributionThreads.value).toEqual([]);
  });

  it('counts a superseded version inside its thread, not as another contribution', () => {
    const queue = setup([
      contribution(1, 'superseded', { superseded_by_upload_id: 2 }),
      contribution(2, 'ready_to_merge'),
    ]);
    expect(queue.totalPending.value).toBe(1);
    expect(queue.contributionThreads.value[0].version_number).toBe(2);
  });

  it('orders oldest or newest first', () => {
    const queue = setup([
      contribution(3, 'ready_to_merge'),
      contribution(1, 'ready_to_merge'),
      contribution(2, 'ready_to_merge'),
    ]);
    const ids = () =>
      queue.filteredContributionThreads.value.map((item) => item.upload_id);
    expect(ids()).toEqual([1, 2, 3]);
    queue.queueSort.value = 'newest';
    expect(ids()).toEqual([3, 2, 1]);
  });

  it('treats an unknown filter as showing everything', () => {
    const queue = setup([contribution(1, 'ready_to_merge')]);
    queue.queueFilter.value = 'not-a-filter';
    expect(queue.filteredContributionThreads.value).toHaveLength(1);
  });
});
