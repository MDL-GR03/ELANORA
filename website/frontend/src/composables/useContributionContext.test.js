import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

import {
  PROPOSED_TOPIC,
  useContributionContext,
} from './useContributionContext';

const detect = vi.hoisted(() => vi.fn());
vi.mock('@/utils/researchExtract', () => ({ detectResearchScope: detect }));

const topics = ref([{ topic_id: 3, name: 'Mouthing' }]);

describe('useContributionContext', () => {
  it('needs a topic and a summary', () => {
    const context = useContributionContext({ topics });
    context.summary.value = 'Fixed glosses';
    expect(context.ready.value).toBe(false);
    context.topicChoice.value = '3';
    expect(context.ready.value).toBe(true);
    expect(context.payload()).toEqual({
      topicId: 3,
      proposedTopicName: '',
      summary: 'Fixed glosses',
    });
  });

  it('asks to reuse an existing topic instead of proposing a near duplicate', () => {
    const context = useContributionContext({ topics });
    context.summary.value = 'New work';
    context.topicChoice.value = PROPOSED_TOPIC;
    context.proposedName.value = 'Mouthings';

    expect(context.similarTopic.value?.topic_id).toBe(3);
    expect(context.ready.value).toBe(false);

    context.acceptSimilarTopic();
    expect(context.topicChoice.value).toBe('3');
    expect(context.proposedName.value).toBe('');
    expect(context.ready.value).toBe(true);
  });

  it('takes the topic from research copies and ignores stale detections', async () => {
    let finishFirst;
    detect
      .mockReturnValueOnce(
        new Promise((resolve) => {
          finishFirst = resolve;
        })
      )
      .mockResolvedValueOnce({ topicId: 3, topicName: 'Mouthing', tiers: [] });
    const context = useContributionContext({ topics });

    const first = context.detectFrom(['old']);
    await context.detectFrom(['new']);
    finishFirst(null);
    await first;

    expect(context.detectedScope.value?.topicId).toBe(3);
    expect(context.topicChoice.value).toBe('3');
    context.summary.value = 'Copy';
    expect(context.payload().topicId).toBe(3);
  });
});
