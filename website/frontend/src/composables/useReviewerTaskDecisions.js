import { reactive, ref, toValue } from 'vue';

export function useReviewerTaskDecisions({
  projectId,
  reviewService,
  busy,
  error,
  replaceCase,
  notify,
}) {
  const updatingTask = ref({ id: '', status: '' });
  const revisionFeedbackCaseId = ref('');
  const revisionTaskSelections = reactive({});
  const revisionTargets = reactive({});

  const unresolvedTaskCount = (item) =>
    item.tasks.filter((task) => task.status !== 'accepted').length;
  const approveTaskLabel = (item) =>
    unresolvedTaskCount(item) === 1 ? 'Approve correction' : 'Approve edit';

  function selectedRevisionTaskIds(item) {
    if (revisionTaskSelections[item.case_id]) {
      return revisionTaskSelections[item.case_id];
    }
    // Recover reviews left in the former non-atomic intermediate state.
    return item.state === 'resubmitted'
      ? item.tasks
          .filter((task) => task.status === 'reopened')
          .map((task) => task.task_id)
      : [];
  }
  function isTaskSelectedForRevision(item, task) {
    return selectedRevisionTaskIds(item).includes(task.task_id);
  }
  function toggleTaskForRevision(item, task) {
    const selected = [...selectedRevisionTaskIds(item)];
    const index = selected.indexOf(task.task_id);
    if (index === -1) selected.push(task.task_id);
    else selected.splice(index, 1);
    revisionTaskSelections[item.case_id] = selected;
    revisionFeedbackCaseId.value = selected.length ? item.case_id : '';
    if (!selected.length) delete revisionTargets[item.case_id];
  }
  function selectRevisionTarget(item, task, target) {
    const targets = [...(revisionTargets[item.case_id] || [])];
    const key = `${task.task_id}:${target.annotation_id}`;
    const index = targets.findIndex(
      (entry) => `${entry.task_id}:${entry.annotation_id}` === key
    );
    if (index === -1)
      targets.push({ ...target, task_id: task.task_id, comment: '' });
    else targets.splice(index, 1);
    revisionTargets[item.case_id] = targets;
    revisionTaskSelections[item.case_id] = [
      ...new Set(targets.map((entry) => entry.task_id)),
    ];
    revisionFeedbackCaseId.value = targets.length ? item.case_id : '';
  }
  function removeRevisionTarget(item, target) {
    selectRevisionTarget(item, { task_id: target.task_id }, target);
  }
  function selectedAnnotationIds(item, task) {
    return (revisionTargets[item.case_id] || [])
      .filter((target) => target.task_id === task.task_id)
      .map((target) => target.annotation_id);
  }
  function revisionTargetSummary(target) {
    const time =
      target.start_ms != null || target.end_ms != null
        ? ` · ${target.start_ms ?? 'start'}–${target.end_ms ?? 'end'} ms`
        : '';
    return `Target: ${target.annotation_id} · Tier: ${target.tier_id || 'unknown'}${time}`;
  }
  function taskBusyLabel(task, status, label) {
    return updatingTask.value.id === task.task_id &&
      updatingTask.value.status === status
      ? 'Saving…'
      : label;
  }

  async function approveTask(item, task) {
    if (isTaskSelectedForRevision(item, task)) {
      toggleTaskForRevision(item, task);
    }
    const completesReview = unresolvedTaskCount(item) === 1;
    updatingTask.value = { id: task.task_id, status: 'accepted' };
    busy.value = true;
    error.value = '';
    try {
      const updated = await reviewService.updateTask(
        toValue(projectId),
        item.case_id,
        task.task_id,
        'accepted'
      );
      replaceCase(updated);
      notify(
        completesReview
          ? updated.resubmitted_upload_status === 'no_changes'
            ? 'Correction approved. No project content changed.'
            : 'Correction approved and review completed.'
          : 'Requested edit approved.',
        'success'
      );
    } catch (requestError) {
      error.value =
        requestError?.response?.data?.detail ||
        'The requested edit could not be approved.';
      notify(error.value, 'error');
    } finally {
      busy.value = false;
      updatingTask.value = { id: '', status: '' };
    }
  }

  function clearRevisionDraft(caseId) {
    revisionFeedbackCaseId.value = '';
    revisionTaskSelections[caseId] = [];
    delete revisionTargets[caseId];
  }

  return {
    approveTask,
    approveTaskLabel,
    clearRevisionDraft,
    isTaskSelectedForRevision,
    removeRevisionTarget,
    revisionFeedbackCaseId,
    revisionTargets,
    revisionTargetSummary,
    selectedAnnotationIds,
    selectedRevisionTaskIds,
    selectRevisionTarget,
    taskBusyLabel,
    toggleTaskForRevision,
    unresolvedTaskCount,
    updatingTask,
  };
}
