import { ref } from 'vue';

import {
  fetchProjectBaselineTiers,
  fetchResearchTopics,
  fetchSectionsAndGroups,
} from '@/api/service/tierService';

/**
 * Load a project's files, research topics and protected baseline tiers.
 *
 * Files are required; topics and baseline tiers degrade to empty lists so a
 * researcher can still prepare a custom copy. A response for a project the
 * page has since left is discarded.
 */
export function useResearchScopes({ translate }) {
  const tierGroups = ref([]);
  const topics = ref([]);
  const baselineTiers = ref([]);
  const loading = ref(true);
  const error = ref('');
  const topicLoadError = ref('');
  let latestRequest = 0;

  function clear() {
    tierGroups.value = [];
    topics.value = [];
    baselineTiers.value = [];
    topicLoadError.value = '';
  }

  async function load(projectId) {
    const request = ++latestRequest;
    error.value = '';
    if (!projectId) {
      error.value = translate('researchScopes.messages.selectProject');
      loading.value = false;
      return false;
    }
    loading.value = true;
    const [tree, topicList, baseline] = await Promise.allSettled([
      fetchSectionsAndGroups(projectId),
      fetchResearchTopics(projectId),
      fetchProjectBaselineTiers(projectId),
    ]);
    if (request !== latestRequest) return false;
    loading.value = false;
    if (tree.status === 'rejected') {
      error.value = translate('researchScopes.messages.loadFailed');
      return false;
    }
    tierGroups.value = tree.value.tier_groups;
    topics.value = topicList.status === 'fulfilled' ? topicList.value : [];
    baselineTiers.value =
      baseline.status === 'fulfilled' ? baseline.value.tier_names : [];
    topicLoadError.value =
      topicList.status === 'rejected'
        ? translate('researchScopes.messages.topicsUnavailable')
        : '';
    return true;
  }

  return {
    tierGroups,
    topics,
    baselineTiers,
    loading,
    error,
    topicLoadError,
    clear,
    load,
  };
}
