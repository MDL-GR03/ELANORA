import { computed, ref } from 'vue';

import { detectResearchScope } from '@/utils/researchExtract';
import { findSimilarResearchTopic } from '@/utils/researchTopics';

export const GENERAL_TOPIC = '__general__';
export const PROPOSED_TOPIC = '__propose__';

/**
 * What a contribution is about: its research topic and a summary for
 * reviewers. Files downloaded as research copies carry their topic, so the
 * researcher is not asked again. A proposed topic too close to an existing
 * one must be replaced by that topic before submitting.
 */
export function useContributionContext({ topics }) {
  const topicChoice = ref('');
  const proposedName = ref('');
  const summary = ref('');
  const detectedScope = ref(null);
  let latestDetection = 0;

  const proposing = computed(
    () => !detectedScope.value && topicChoice.value === PROPOSED_TOPIC
  );
  const similarTopic = computed(() =>
    proposing.value && proposedName.value.trim().length >= 2
      ? findSimilarResearchTopic(proposedName.value, topics.value)
      : null
  );
  const topicReady = computed(() => {
    if (detectedScope.value) return true;
    if (!topicChoice.value) return false;
    if (topicChoice.value !== PROPOSED_TOPIC) return true;
    return proposedName.value.trim().length >= 2 && !similarTopic.value;
  });
  const ready = computed(
    () => summary.value.trim().length >= 3 && topicReady.value
  );

  async function detectFrom(files) {
    const request = ++latestDetection;
    const scope = await detectResearchScope(files);
    if (request !== latestDetection) return;
    detectedScope.value = scope;
    const topicId = Number(scope?.topicId);
    if (topics.value.some((topic) => topic.topic_id === topicId)) {
      topicChoice.value = String(topicId);
    }
  }

  function acceptSimilarTopic() {
    if (!similarTopic.value) return;
    topicChoice.value = String(similarTopic.value.topic_id);
    proposedName.value = '';
  }

  function reset() {
    latestDetection += 1;
    topicChoice.value = '';
    proposedName.value = '';
    summary.value = '';
    detectedScope.value = null;
  }

  /** The contribution fields the upload API expects. */
  function payload() {
    const chosenTopicId = /^\d+$/.test(topicChoice.value)
      ? Number(topicChoice.value)
      : null;
    return {
      topicId: detectedScope.value
        ? detectedScope.value.topicId || null
        : chosenTopicId,
      proposedTopicName: proposing.value ? proposedName.value.trim() : '',
      summary: summary.value.trim(),
    };
  }

  return {
    topicChoice,
    proposedName,
    summary,
    detectedScope,
    proposing,
    similarTopic,
    ready,
    detectFrom,
    acceptSimilarTopic,
    reset,
    payload,
  };
}
