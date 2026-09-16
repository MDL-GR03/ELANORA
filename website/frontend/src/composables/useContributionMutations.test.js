import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useContributionMutations } from './useContributionMutations';

function setup(overrides = {}) {
  const currentProjectName = ref('corpus');
  const pendingUploads = ref([
    {
      upload_id: 12,
      branch_name: 'contribution-12',
      merge_status: 'ready_to_merge',
    },
  ]);
  const error = ref('');
  const fetchPendingUploads = vi.fn().mockResolvedValue(undefined);
  const fetchReviewCount = vi.fn().mockResolvedValue(undefined);
  const loadResearchTopics = vi.fn().mockResolvedValue(undefined);
  const confirmAction = vi.fn().mockResolvedValue(true);
  const eventMessages = { addMessage: vi.fn() };
  const gitClient = {
    setContributionResearchTopic: vi.fn().mockResolvedValue({
      declared_topic_name: 'Prosody',
    }),
    adminTestMerge: vi.fn().mockResolvedValue({
      status: 'needs_resolution',
      conflicted_files: ['elan_files/session.eaf'],
      conflicts_count: 1,
      can_auto_merge: false,
      tested_at: '2026-09-14T12:00:00Z',
    }),
    adminCompleteMerge: vi.fn().mockResolvedValue({}),
    dismissDuplicateUpload: vi.fn().mockResolvedValue({}),
    declinePendingUpload: vi.fn().mockResolvedValue({}),
  };
  const dependencies = {
    currentProjectName,
    pendingUploads,
    error,
    fetchPendingUploads,
    fetchReviewCount,
    loadResearchTopics,
    translate: (key, params) =>
      params ? `${key}:${JSON.stringify(params)}` : key,
    confirmAction,
    eventMessages,
    gitClient,
    ...overrides,
  };
  return {
    ...dependencies,
    mutations: useContributionMutations(dependencies),
  };
}

describe('useContributionMutations', () => {
  beforeEach(() => vi.clearAllMocks());

  it('assigns an explicit existing topic and refreshes the queue', async () => {
    const { mutations, gitClient, fetchPendingUploads, eventMessages } =
      setup();

    expect(await mutations.assignResearchTopic({ upload_id: 12 }, '4')).toBe(
      true
    );
    expect(gitClient.setContributionResearchTopic).toHaveBeenCalledWith(
      'corpus',
      12,
      { topic_id: 4, new_topic_name: null }
    );
    expect(fetchPendingUploads).toHaveBeenCalledWith(false);
    expect(eventMessages.addMessage).toHaveBeenCalledWith(
      'contributionWorkspace.mutations.topicAssigned',
      'success'
    );
  });

  it('reports when a proposed spelling matched an existing topic', async () => {
    const { mutations, loadResearchTopics, eventMessages } = setup();

    expect(
      await mutations.createResearchTopic({ upload_id: 12 }, '  Prozody  ')
    ).toBe(true);
    expect(loadResearchTopics).toHaveBeenCalledOnce();
    expect(eventMessages.addMessage).toHaveBeenCalledWith(
      'contributionWorkspace.mutations.topicMatched:{"name":"Prosody"}',
      'success'
    );
  });

  it('updates only the tested contribution with compatibility evidence', async () => {
    const { mutations, pendingUploads } = setup();

    expect(await mutations.testMerge(pendingUploads.value[0])).toBe(true);
    expect(pendingUploads.value[0]).toEqual(
      expect.objectContaining({
        merge_status: 'needs_resolution',
        conflicted_files: ['elan_files/session.eaf'],
        can_auto_merge: false,
      })
    );
    expect(mutations.testing.value).toBeNull();
  });

  it('requires confirmation and removes successfully merged work', async () => {
    const { mutations, pendingUploads, gitClient, confirmAction } = setup();
    const upload = pendingUploads.value[0];

    expect(await mutations.mergeUpload(upload)).toBe(true);
    expect(confirmAction).toHaveBeenCalledOnce();
    expect(gitClient.adminCompleteMerge).toHaveBeenCalledWith(
      'corpus',
      'contribution-12',
      'auto'
    );
    expect(pendingUploads.value).toEqual([]);
    expect(mutations.merging.value).toBeNull();
  });

  it('keeps a contribution when dismissal is cancelled', async () => {
    const confirmAction = vi.fn().mockResolvedValue(false);
    const { mutations, pendingUploads, gitClient } = setup({ confirmAction });
    const upload = {
      ...pendingUploads.value[0],
      duplicate_of_upload_id: 8,
    };

    expect(await mutations.dismissDuplicate(upload)).toBe(false);
    expect(gitClient.dismissDuplicateUpload).not.toHaveBeenCalled();
    expect(pendingUploads.value).toHaveLength(1);
  });

  it('declines valid work and refreshes both queue and review state', async () => {
    const { mutations, pendingUploads, gitClient, fetchReviewCount } = setup();
    const upload = pendingUploads.value[0];

    expect(
      await mutations.declineUpload(upload, '  Outside project scope  ')
    ).toBe(true);
    expect(gitClient.declinePendingUpload).toHaveBeenCalledWith(
      'corpus',
      12,
      'Outside project scope'
    );
    expect(fetchReviewCount).toHaveBeenCalledOnce();
    expect(pendingUploads.value).toEqual([]);
  });

  it('uses the backend detail and resets busy state after a failure', async () => {
    const gitClient = {
      adminTestMerge: vi.fn().mockRejectedValue({
        response: { data: { detail: 'Branch no longer exists' } },
      }),
    };
    const { mutations, pendingUploads, error, eventMessages } = setup({
      gitClient,
    });

    expect(await mutations.testMerge(pendingUploads.value[0])).toBe(false);
    expect(error.value).toBe('Branch no longer exists');
    expect(mutations.testing.value).toBeNull();
    expect(eventMessages.addMessage).toHaveBeenCalledWith(
      'Branch no longer exists',
      'error'
    );
  });
});
