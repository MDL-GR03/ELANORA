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
}) {
  function transitionConfirmation(item, state) {
    return {
      changes_requested: {
        title:
          item.state === 'resubmitted'
            ? 'Request another revision?'
            : 'Request a revision?',
        message:
          item.state === 'resubmitted'
            ? 'This corrected version will not be approved yet. The same review remains open and the researcher will be asked to submit another version.'
            : 'The researcher will be asked to revise this contribution. The same discussion will track the corrected version.',
        confirmText:
          item.state === 'resubmitted'
            ? 'Request another revision'
            : 'Request revision',
      },
      resolved: {
        title:
          item.state === 'resubmitted'
            ? 'Approve this correction?'
            : 'Close this review?',
        message:
          item.state === 'resubmitted'
            ? 'This records that the corrected version satisfies the request and closes the correction review. It does not merge the contribution; a separate merge decision is still required.'
            : 'This closes the question without requesting file changes. It can be reopened later.',
        confirmText:
          item.state === 'resubmitted'
            ? 'Approve correction and close review'
            : 'Close review',
      },
      open: {
        title: 'Reopen this review?',
        message:
          'The case will return to active review. Its previous discussion and decisions remain in the history.',
        confirmText: 'Reopen review',
      },
    }[state];
  }

  async function transition(item, state) {
    const confirmation = transitionConfirmation(item, state);
    if (
      confirmation &&
      !(await confirmAction({ ...confirmation, cancelText: 'Cancel' }))
    ) {
      return false;
    }
    busy.value = true;
    error.value = '';
    try {
      replaceCase(
        await reviewService.transition(toValue(projectId), item.case_id, state)
      );
      notify('Review status updated.', 'success');
      return true;
    } catch (requestError) {
      error.value =
        requestError?.response?.data?.detail ||
        'The review state could not be changed.';
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
          `- ${revisionTargetSummary(target)}${target.comment?.trim() ? `\n  Instruction: ${target.comment.trim()}` : ''}`
      )
      .join('\n');
    return targetDetails
      ? `${feedback ? `${feedback}\n\n` : ''}Requested annotation corrections:\n${targetDetails}`
      : feedback;
  }

  async function requestAnotherRevision(item) {
    const selectedTaskIds = selectedRevisionTaskIds(item);
    if (!hasRevisionFeedback(item) || !selectedTaskIds.length) return false;
    const recordedFeedback = buildRevisionFeedback(item);
    if (
      !(await confirmAction({
        title: 'Request another revision?',
        message: `This will return ${selectedTaskIds.length} requested edit${selectedTaskIds.length === 1 ? '' : 's'} to the researcher. Your required feedback will be added to the discussion, and another corrected upload will be required.`,
        confirmText: 'Send revision request',
        cancelText: 'Cancel',
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
      notify('Another revision was requested.', 'success');
      return true;
    } catch (requestError) {
      error.value =
        requestError?.response?.data?.detail ||
        'The new revision request could not be recorded.';
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
      error.value =
        requestError?.response?.data?.detail ||
        'The assignment could not be saved.';
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
      notify('Corrected upload linked to this review.', 'success');
      return true;
    } catch (requestError) {
      error.value =
        requestError?.response?.data?.detail ||
        'The corrected upload could not be linked.';
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
