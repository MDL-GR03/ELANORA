import { computed, ref } from 'vue';

import gitService from '@/api/service/gitService';
import { apiErrorMessage } from '@/utils/apiError';

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
    error.value = apiErrorMessage(requestError, translate, fallback);
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
      notify(
        translate('contributionWorkspace.mutations.topicAssigned'),
        'success'
      );
      return true;
    } catch (requestError) {
      fail(
        requestError,
        translate('contributionWorkspace.mutations.topicAssignFailed')
      );
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
          ? translate('contributionWorkspace.mutations.topicCreated')
          : translate('contributionWorkspace.mutations.topicMatched', {
              name: context.declared_topic_name,
            }),
        'success'
      );
      return true;
    } catch (requestError) {
      fail(
        requestError,
        translate('contributionWorkspace.mutations.topicCreateFailed')
      );
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
      notify(
        translate('contributionWorkspace.mutations.testCompleted'),
        'success'
      );
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
      tone: 'success',
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
      notify(translate('contributionWorkspace.mutations.merged'), 'success');
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
      title: translate('contributionWorkspace.mutations.dismissTitle', {
        id: upload.upload_id,
      }),
      message: translate('contributionWorkspace.mutations.dismissMessage', {
        id: upload.duplicate_of_upload_id,
      }),
      confirmText: translate('contributionWorkspace.mutations.dismissConfirm'),
      tone: 'danger',
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
      notify(translate('contributionWorkspace.mutations.dismissed'), 'success');
      return true;
    } catch (requestError) {
      fail(
        requestError,
        translate('contributionWorkspace.mutations.dismissFailed')
      );
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
      notify(translate('contributionWorkspace.mutations.declined'), 'success');
      return true;
    } catch (requestError) {
      fail(
        requestError,
        translate('contributionWorkspace.mutations.declineFailed')
      );
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
