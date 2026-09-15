import { nextTick, ref } from 'vue';
import { describe, expect, it } from 'vitest';

import {
  RESOLUTION_STRATEGIES,
  useResolutionDecision,
} from './useResolutionDecision';

function contribution(id, overrides = {}) {
  return {
    upload_id: id,
    conflicted_files: ['elan_files/a.eaf', 'elan_files/b.eaf'],
    files: {
      new: ['elan_files/new.eaf'],
      modified: ['elan_files/a.eaf', 'elan_files/b.eaf', 'elan_files/c.eaf'],
      deleted: ['elan_files/old.eaf'],
    },
    ...overrides,
  };
}

describe('useResolutionDecision', () => {
  it('never carries a decision over to a different contribution', async () => {
    const upload = ref(contribution(5));
    const decision = useResolutionDecision(upload);
    decision.choose(RESOLUTION_STRATEGIES.incoming);
    await nextTick();
    decision.acknowledged.value = true;
    decision.recordComparison({ filename: 'elan_files/a.eaf', review: {} });
    decision.toggleFile('elan_files/a.eaf');
    expect(decision.canApply.value).toBe(true);

    upload.value = contribution(7);
    await nextTick();

    expect(decision.strategy.value).toBe('');
    expect(decision.acknowledged.value).toBe(false);
    expect(decision.comparedCount.value).toBe(0);
    expect(decision.selectedFile.value).toBeNull();
    expect(decision.canApply.value).toBe(false);
  });

  it('requires a fresh acknowledgement whenever the outcome changes', async () => {
    const decision = useResolutionDecision(ref(contribution(5)));
    decision.choose(RESOLUTION_STRATEGIES.incoming);
    await nextTick();
    decision.acknowledged.value = true;

    decision.choose(RESOLUTION_STRATEGIES.current);
    await nextTick();

    expect(decision.acknowledged.value).toBe(false);
    expect(decision.canApply.value).toBe(false);
  });

  it('lists the files applied whichever outcome is chosen, deletions included', () => {
    const decision = useResolutionDecision(ref(contribution(5)));

    expect(decision.otherFiles.value).toEqual({
      new: ['elan_files/new.eaf'],
      modified: ['elan_files/c.eaf'],
      deleted: ['elan_files/old.eaf'],
    });
    expect(decision.otherFileCount.value).toBe(3);
  });

  it('states the annotation impact only once every overlapping file is compared', () => {
    const decision = useResolutionDecision(ref(contribution(5)));
    decision.recordComparison({
      filename: 'elan_files/a.eaf',
      review: { changes: [{ kinds: ['value_changed'] }] },
    });

    expect(decision.comparedCount.value).toBe(1);
    expect(decision.allCompared.value).toBe(false);
    expect(decision.impact.value).toEqual([]);

    decision.recordComparison({
      filename: 'elan_files/b.eaf',
      review: {
        changes: [
          { kinds: ['value_changed', 'timing_changed'] },
          { kinds: ['added'] },
        ],
      },
    });

    expect(decision.allCompared.value).toBe(true);
    expect(decision.impact.value).toEqual([
      { kind: 'value_changed', count: 2 },
      { kind: 'timing_changed', count: 1 },
      { kind: 'added', count: 1 },
    ]);
  });

  it('clearing the choice leaves nothing that can be applied', async () => {
    const decision = useResolutionDecision(ref(contribution(5)));
    decision.choose(RESOLUTION_STRATEGIES.current);
    await nextTick();
    decision.acknowledged.value = true;

    decision.clear();
    await nextTick();

    expect(decision.canApply.value).toBe(false);
  });
});
