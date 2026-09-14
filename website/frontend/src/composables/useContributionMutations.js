import { computed, ref } from 'vue';

import gitService from '@/api/service/gitService';

function requestMessage(error, fallback) {
  return error?.response?.data?.detail || fallback;
}

export function useContributionMutations({
  currentProjectName,
  pendingUploads,
  error,
  fetchPendingUploads,
  fetchReviewCount,
  loadResearchTopics,
  translate,
  confirmAction,
  eventMessages,
  gitClient = gitService,
}) {
  const merging = ref(null);
  const testing = ref(null);
  const dismissing = ref(null);
  const topicDecisionBusy = ref(false);
  const actionBusy = computed(
    () =>
      merging.value !== null ||
      testing.value !== null ||
      dismissing.value !== null
  );

  function notify(message, type) {
    eventMessages.addMessage(message, type);
  }

  function fail(requestError, fallback) {
    error.value = requestMessage(requestError, fallback);
    notify(error.value, 'error');
  }

  async function assignResearchTopic(upload, topicId) {
    const selectedId = Number(topicId);
    if (!selectedId) return false;
    topicDecisionBusy.value = true;
    error.value = '';
    try {
      await gitClient.setContributionResearchTopic(
        currentProjectName.value,
        upload.upload_id,
        { topic_id: selectedId, new_topic_name: null }
      );
      await fetchPendingUploads(false);
      notify('Research topic assigned.', 'success');
      return true;
    } catch (requestError) {
      fail(requestError, 'The research topic could not be assigned.');
      return false;
    } finally {
      topicDecisionBusy.value = false;
    }
  }

  async function createResearchTopic(upload, proposedName) {
    const topicName = String(proposedName || '').trim();
    if (!topicName) return false;
    topicDecisionBusy.value = true;
    error.value = '';
    try {
      const context = await gitClient.setContributionResearchTopic(
        currentProjectName.value,
        upload.upload_id,
        { topic_id: null, new_topic_name: topicName }
      );
      await Promise.all([fetchPendingUploads(false), loadResearchTopics()]);
      notify(
        context.declared_topic_name === topicName
          ? 'Research topic created and assigned.'
          : `Matched and assigned the existing topic “${context.declared_topic_name}”.`,
        'success'
      );
      return true;
    } catch (requestError) {
      fail(requestError, 'The research topic could not be created.');
      return false;
    } finally {
      topicDecisionBusy.value = false;
    }
  }

  async function testMerge(upload) {
    testing.value = upload.upload_id;
    error.value = '';
    try {
      const response = await gitClient.adminTestMerge(
        currentProjectName.value,
        upload.branch_name
      );
      const index = pendingUploads.value.findIndex(
        (item) => item.upload_id === upload.upload_id
      );
      if (index !== -1) {
        pendingUploads.value[index] = {
          ...pendingUploads.value[index],
          merge_status: response.status,
          conflicted_files: response.conflicted_files || [],
          conflicts_count: response.conflicts_count || 0,
          can_auto_merge: response.can_auto_merge,
          tested_at: response.tested_at,
        };
      }
      notify('Compatibility check completed.', 'success');
      return true;
    } catch (requestError) {
      fail(requestError, translate('pendingUploads.errors.testMergeFailed'));
      return false;
    } finally {
      testing.value = null;
    }
  }

  async function mergeUpload(upload) {
    if (upload.merge_status !== 'ready_to_merge') {
      error.value = translate('pendingUploads.errors.notReadyToMerge');
      return false;
    }
    const confirmed = await confirmAction({
      title: translate('pendingUploads.mergeConfirmation.title'),
      message: translate('pendingUploads.mergeConfirmation.message', {
        branch: `contribution #${upload.upload_id}`,
      }),
      confirmText: translate('pendingUploads.actions.mergeNow'),
      cancelText: translate('common.cancel'),
    });
    if (!confirmed) return false;

    merging.value = upload.upload_id;
    error.value = '';
    try {
      await gitClient.adminCompleteMerge(
        currentProjectName.value,
        upload.branch_name,
        'auto'
      );
      pendingUploads.value = pendingUploads.value.filter(
        (item) => item.upload_id !== upload.upload_id
      );
      await fetchPendingUploads(false);
      notify('Contribution merged into the project.', 'success');
      return true;
    } catch (requestError) {
      fail(requestError, translate('pendingUploads.errors.mergeFailed'));
      return false;
    } finally {
      merging.value = null;
    }
  }

  async function dismissDuplicate(upload) {
    const confirmed = await confirmAction({
      title: `Dismiss contribution #${upload.upload_id}?`,
      message: `It contains exactly the same project content as contribution #${upload.duplicate_of_upload_id}. Its redundant Git branch will be removed, while the dismissal remains in the audit history.`,
      confirmText: 'Dismiss duplicate',
      cancelText: translate('common.cancel'),
    });
    if (!confirmed) return false;

    dismissing.value = upload.upload_id;
    error.value = '';
    try {
      await gitClient.dismissDuplicateUpload(
        currentProjectName.value,
        upload.upload_id
      );
      pendingUploads.value = pendingUploads.value.filter(
        (item) => item.upload_id !== upload.upload_id
      );
      await fetchPendingUploads(false);
      notify('Duplicate contribution dismissed.', 'success');
      return true;
    } catch (requestError) {
      fail(requestError, 'The duplicate contribution could not be dismissed.');
      return false;
    } finally {
      dismissing.value = null;
    }
  }

  async function declineUpload(upload, reason) {
    const cleanedReason = String(reason || '').trim();
    if (!upload || cleanedReason.length < 3) return false;
    dismissing.value = upload.upload_id;
    error.value = '';
    try {
      await gitClient.declinePendingUpload(
        currentProjectName.value,
        upload.upload_id,
        cleanedReason
      );
      pendingUploads.value = pendingUploads.value.filter(
        (item) => item.upload_id !== upload.upload_id
      );
      await Promise.all([fetchPendingUploads(false), fetchReviewCount()]);
      notify('Contribution declined and archived.', 'success');
      return true;
    } catch (requestError) {
      fail(requestError, 'The contribution could not be declined.');
      return false;
    } finally {
      dismissing.value = null;
    }
  }

  return {
    merging,
    testing,
    dismissing,
    topicDecisionBusy,
    actionBusy,
    assignResearchTopic,
    createResearchTopic,
    testMerge,
    mergeUpload,
    dismissDuplicate,
    declineUpload,
  };
}
