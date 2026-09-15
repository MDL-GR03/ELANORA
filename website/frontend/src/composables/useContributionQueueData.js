import { ref } from 'vue';

import gitService from '@/api/service/gitService';
import reviewService from '@/api/service/reviewService';
import { fetchResearchTopics } from '@/api/service/tierService';

export function useContributionQueueData({
  currentProject,
  currentProjectName,
  translate,
  gitClient = gitService,
  reviewClient = reviewService,
  topicClient = fetchResearchTopics,
}) {
  const pendingUploads = ref([]);
  const uploadsLoading = ref(false);
  // True once the current project's contributions have actually been read,
  // so an empty list can be told apart from one that has not loaded yet.
  const uploadsLoaded = ref(false);
  const error = ref('');
  const activeReviewCount = ref(0);
  const reviewCases = ref([]);
  const researchTopics = ref([]);
  const topicSuggestionNames = ref({});
  let fetchSequence = 0;
  let fetchInFlight = false;

  async function fetchPendingUploads(showLoading = true) {
    if (!currentProjectName.value) {
      pendingUploads.value = [];
      uploadsLoaded.value = false;
      return;
    }
    if (fetchInFlight) return;

    const requestedProject = currentProjectName.value;
    const request = ++fetchSequence;
    fetchInFlight = true;
    try {
      if (showLoading) uploadsLoading.value = true;
      error.value = '';
      const response =
        await gitClient.getPendingUploadsWithStatus(requestedProject);
      if (
        request === fetchSequence &&
        requestedProject === currentProjectName.value
      ) {
        pendingUploads.value = response.pending_uploads || [];
        uploadsLoaded.value = true;
        topicSuggestionNames.value = Object.fromEntries(
          pendingUploads.value
            .filter((upload) => upload.research_context?.proposed_topic_name)
            .map((upload) => [
              upload.upload_id,
              upload.research_context.proposed_topic_name,
            ])
        );
      }
    } catch {
      if (
        showLoading &&
        request === fetchSequence &&
        requestedProject === currentProjectName.value
      ) {
        error.value = translate('pendingUploads.errors.loadFailed');
        pendingUploads.value = [];
        uploadsLoaded.value = false;
      }
    } finally {
      fetchInFlight = false;
      if (showLoading && request === fetchSequence)
        uploadsLoading.value = false;
      if (
        requestedProject !== currentProjectName.value &&
        currentProjectName.value
      ) {
        void fetchPendingUploads(showLoading);
      }
    }
  }

  async function loadResearchTopics() {
    if (!currentProject.value?.project_id) {
      researchTopics.value = [];
      return;
    }
    try {
      researchTopics.value = await topicClient(currentProject.value.project_id);
    } catch {
      researchTopics.value = [];
    }
  }

  async function fetchReviewCount() {
    if (!currentProject.value?.project_id) {
      activeReviewCount.value = 0;
      reviewCases.value = [];
      return;
    }
    try {
      const cases = await reviewClient.list(currentProject.value.project_id);
      reviewCases.value = cases;
      activeReviewCount.value = cases.filter(
        (item) => !['resolved', 'closed'].includes(item.state)
      ).length;
    } catch {
      activeReviewCount.value = 0;
      reviewCases.value = [];
    }
  }

  function clear() {
    pendingUploads.value = [];
    uploadsLoaded.value = false;
    error.value = '';
  }

  return {
    pendingUploads,
    uploadsLoading,
    uploadsLoaded,
    error,
    activeReviewCount,
    reviewCases,
    researchTopics,
    topicSuggestionNames,
    fetchPendingUploads,
    loadResearchTopics,
    fetchReviewCount,
    clear,
  };
}
