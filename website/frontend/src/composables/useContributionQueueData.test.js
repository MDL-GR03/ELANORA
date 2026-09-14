import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

import { useContributionQueueData } from './useContributionQueueData';

function setup(overrides = {}) {
  const currentProject = ref({ project_id: 7 });
  const currentProjectName = ref('corpus');
  const gitClient = {
    getPendingUploadsWithStatus: vi.fn().mockResolvedValue({
      pending_uploads: [
        {
          upload_id: 12,
          research_context: { proposed_topic_name: 'Interactional rhythm' },
        },
      ],
    }),
  };
  const reviewClient = {
    list: vi.fn().mockResolvedValue([
      { case_id: 'open', state: 'changes_requested' },
      { case_id: 'done', state: 'resolved' },
    ]),
  };
  const topicClient = vi
    .fn()
    .mockResolvedValue([{ topic_id: 3, name: 'Prosody' }]);
  return {
    currentProject,
    currentProjectName,
    gitClient,
    reviewClient,
    topicClient,
    queue: useContributionQueueData({
      currentProject,
      currentProjectName,
      translate: (key) => key,
      gitClient,
      reviewClient,
      topicClient,
      ...overrides,
    }),
  };
}

describe('useContributionQueueData', () => {
  it('loads contributions, proposed names, reviews, and topics together', async () => {
    const { queue, gitClient, reviewClient, topicClient } = setup();

    await Promise.all([
      queue.fetchPendingUploads(),
      queue.fetchReviewCount(),
      queue.loadResearchTopics(),
    ]);

    expect(gitClient.getPendingUploadsWithStatus).toHaveBeenCalledWith(
      'corpus'
    );
    expect(reviewClient.list).toHaveBeenCalledWith(7);
    expect(topicClient).toHaveBeenCalledWith(7);
    expect(queue.pendingUploads.value).toHaveLength(1);
    expect(queue.topicSuggestionNames.value).toEqual({
      12: 'Interactional rhythm',
    });
    expect(queue.activeReviewCount.value).toBe(1);
    expect(queue.researchTopics.value[0].name).toBe('Prosody');
  });

  it('reports a visible queue error without leaking a request failure', async () => {
    const { queue } = setup({
      gitClient: {
        getPendingUploadsWithStatus: vi
          .fn()
          .mockRejectedValue(new Error('boom')),
      },
    });

    await queue.fetchPendingUploads();

    expect(queue.error.value).toBe('pendingUploads.errors.loadFailed');
    expect(queue.pendingUploads.value).toEqual([]);
    expect(queue.uploadsLoading.value).toBe(false);
  });

  it('clears project-scoped data when no project is selected', async () => {
    const { queue, currentProject, currentProjectName } = setup();
    queue.pendingUploads.value = [{ upload_id: 1 }];
    queue.researchTopics.value = [{ topic_id: 2 }];
    currentProject.value = null;
    currentProjectName.value = '';

    await Promise.all([
      queue.fetchPendingUploads(),
      queue.fetchReviewCount(),
      queue.loadResearchTopics(),
    ]);

    expect(queue.pendingUploads.value).toEqual([]);
    expect(queue.reviewCases.value).toEqual([]);
    expect(queue.researchTopics.value).toEqual([]);
  });
});
