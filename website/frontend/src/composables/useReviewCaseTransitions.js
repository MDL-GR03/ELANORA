import { apiErrorMessage } from '@/utils/apiError';
import { toValue } from 'vue';

export function useReviewCaseTransitions({
  projectId,
  resubmissionUploadId,
  reviewService,
  busy,
  error,
  replies,
  revisionFeedbackCaseId,
  revisionTargets,
  selectedRevisionTaskIds,
  revisionTargetSummary,
  clearRevisionDraft,
  replaceCase,
  confirmAction,
  notify,
  t,
}) {
  function transitionConfirmation(item, state) {
    return {
      changes_requested: {
        title:
          item.state === 'resubmitted'
            ? t('reviewCases.confirm.requestAnotherTitle')
            : t('reviewCases.confirm.requestTitle'),
        message:
          item.state === 'resubmitted'
            ? t('reviewCases.confirm.requestAnotherMessage')
            : t('reviewCases.confirm.requestMessage'),
        confirmText:
          item.state === 'resubmitted'
            ? t('reviewCases.confirm.requestAnotherConfirm')
            : t('reviewCases.confirm.requestConfirm'),
      },
      resolved: {
        title:
          item.state === 'resubmitted'
            ? t('reviewCases.confirm.approveTitle')
            : t('reviewCases.confirm.closeTitle'),
        message:
          item.state === 'resubmitted'
            ? t('reviewCases.confirm.approveMessage')
            : t('reviewCases.confirm.closeMessage'),
        confirmText:
          item.state === 'resubmitted'
            ? t('reviewCases.confirm.approveConfirm')
            : t('reviewCases.confirm.closeConfirm'),
        tone: 'success',
      },
      open: {
        title: t('reviewCases.confirm.reopenTitle'),
        message: t('reviewCases.confirm.reopenMessage'),
        confirmText: t('reviewCases.confirm.reopenConfirm'),
        tone: 'success',
      },
    }[state];
  }

  async function transition(item, state) {
    const confirmation = transitionConfirmation(item, state);
    if (
      confirmation &&
      !(await confirmAction({
        ...confirmation,
        cancelText: t('reviewCases.confirm.cancel'),
      }))
    ) {
      return false;
    }
    busy.value = true;
    error.value = '';
    try {
      replaceCase(
        await reviewService.transition(toValue(projectId), item.case_id, state)
      );
      notify(t('reviewCases.notify.statusUpdated'), 'success');
      return true;
    } catch (requestError) {
      error.value = apiErrorMessage(
        requestError,
        t,
        t('reviewCases.errors.transition')
      );
      notify(error.value, 'error');
      return false;
    } finally {
      busy.value = false;
    }
  }

  function hasRevisionFeedback(item) {
    return Boolean(
      replies[item.case_id]?.trim() || revisionTargets[item.case_id]?.length
    );
  }
  function revisionRequestCount(item) {
    return (
      revisionTargets[item.case_id]?.length ||
      selectedRevisionTaskIds(item).length
    );
  }
  function buildRevisionFeedback(item) {
    const feedback = replies[item.case_id]?.trim();
    const targetDetails = (revisionTargets[item.case_id] || [])
      .map(
        (target) =>
          `- ${revisionTargetSummary(target)}${
            target.comment?.trim()
              ? `\n  ${t('reviewCases.revision.recordedInstruction', { text: target.comment.trim() })}`
              : ''
          }`
      )
      .join('\n');
    return targetDetails
      ? `${feedback ? `${feedback}\n\n` : ''}${t('reviewCases.revision.recordedHeading')}\n${targetDetails}`
      : feedback;
  }

  async function requestAnotherRevision(item) {
    const selectedTaskIds = selectedRevisionTaskIds(item);
    if (!hasRevisionFeedback(item) || !selectedTaskIds.length) return false;
    const recordedFeedback = buildRevisionFeedback(item);
    if (
      !(await confirmAction({
        title: t('reviewCases.confirm.requestAnotherTitle'),
        message: t('reviewCases.confirm.sendRevisionMessage', {
          edits: t(
            'reviewCases.confirm.requestedEdits',
            selectedTaskIds.length
          ),
        }),
        confirmText: t('reviewCases.confirm.sendRevisionConfirm'),
        cancelText: t('reviewCases.confirm.cancel'),
      }))
    ) {
      return false;
    }
    busy.value = true;
    error.value = '';
    try {
      replaceCase(
        await reviewService.requestRevision(
          toValue(projectId),
          item.case_id,
          selectedTaskIds,
          recordedFeedback
        )
      );
      replies[item.case_id] = '';
      clearRevisionDraft(item.case_id);
      notify(t('reviewCases.notify.revisionRequested'), 'success');
      return true;
    } catch (requestError) {
      error.value = apiErrorMessage(
        requestError,
        t,
        t('reviewCases.errors.revision')
      );
      notify(error.value, 'error');
      return false;
    } finally {
      busy.value = false;
    }
  }

  function beginOrRequestAnotherRevision(item) {
    if (revisionFeedbackCaseId.value !== item.case_id) {
      revisionFeedbackCaseId.value = item.case_id;
      return;
    }
    void requestAnotherRevision(item);
  }

  async function assign(item, value) {
    busy.value = true;
    error.value = '';
    try {
      replaceCase(
        await reviewService.transition(
          toValue(projectId),
          item.case_id,
          item.state,
          { assigned_to: value ? Number(value) : null }
        )
      );
      return true;
    } catch (requestError) {
      error.value = apiErrorMessage(
        requestError,
        t,
        t('reviewCases.errors.assign')
      );
      return false;
    } finally {
      busy.value = false;
    }
  }

  async function linkResubmission(item) {
    busy.value = true;
    error.value = '';
    try {
      replaceCase(
        await reviewService.resubmit(
          toValue(projectId),
          item.case_id,
          toValue(resubmissionUploadId)
        )
      );
      notify(t('reviewCases.notify.linked'), 'success');
      return true;
    } catch (requestError) {
      error.value = apiErrorMessage(
        requestError,
        t,
        t('reviewCases.errors.link')
      );
      notify(error.value, 'error');
      return false;
    } finally {
      busy.value = false;
    }
  }

  return {
    assign,
    beginOrRequestAnotherRevision,
    buildRevisionFeedback,
    hasRevisionFeedback,
    linkResubmission,
    requestAnotherRevision,
    revisionRequestCount,
    transition,
    transitionConfirmation,
  };
}
