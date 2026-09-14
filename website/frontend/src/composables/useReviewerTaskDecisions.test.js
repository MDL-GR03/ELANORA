import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useReviewerTaskDecisions } from './useReviewerTaskDecisions';

const resubmittedCase = () => ({
  case_id: 'case-1',
  state: 'resubmitted',
  tasks: [
    { task_id: 'task-1', status: 'addressed' },
    { task_id: 'task-2', status: 'addressed' },
  ],
});

describe('useReviewerTaskDecisions', () => {
  let reviewService;
  let replaceCase;
  let notify;
  let busy;
  let error;
  let decisions;

  beforeEach(() => {
    reviewService = { updateTask: vi.fn() };
    replaceCase = vi.fn();
    notify = vi.fn();
    busy = ref(false);
    error = ref('');
    decisions = useReviewerTaskDecisions({
      projectId: () => 12,
      reviewService,
      busy,
      error,
      replaceCase,
      notify,
    });
  });

  it('stages and cancels a correction request without a server mutation', () => {
    const item = resubmittedCase();
    const task = item.tasks[0];

    decisions.toggleTaskForRevision(item, task);
    expect(decisions.selectedRevisionTaskIds(item)).toEqual(['task-1']);
    expect(decisions.revisionFeedbackCaseId.value).toBe('case-1');

    decisions.toggleTaskForRevision(item, task);
    expect(decisions.selectedRevisionTaskIds(item)).toEqual([]);
    expect(decisions.revisionFeedbackCaseId.value).toBe('');
    expect(reviewService.updateTask).not.toHaveBeenCalled();
  });

  it('restores selections from legacy reopened task state', () => {
    const item = resubmittedCase();
    item.tasks[0].status = 'reopened';

    expect(decisions.selectedRevisionTaskIds(item)).toEqual(['task-1']);
    expect(decisions.isTaskSelectedForRevision(item, item.tasks[0])).toBe(true);
  });

  it('deduplicates annotation targets and keeps their file task selected', () => {
    const item = resubmittedCase();
    const task = item.tasks[0];
    const target = {
      annotation_id: 'A1',
      tier_id: 'translation',
      start_ms: 100,
      end_ms: 250,
    };

    decisions.selectRevisionTarget(item, task, target);
    expect(decisions.selectedRevisionTaskIds(item)).toEqual(['task-1']);
    expect(decisions.selectedAnnotationIds(item, task)).toEqual(['A1']);
    expect(decisions.revisionTargets['case-1'][0]).toMatchObject({
      ...target,
      task_id: 'task-1',
      comment: '',
    });
    expect(decisions.revisionTargetSummary(target)).toBe(
      'Target: A1 · Tier: translation · 100–250 ms'
    );

    decisions.selectRevisionTarget(item, task, target);
    expect(decisions.selectedAnnotationIds(item, task)).toEqual([]);
    expect(decisions.selectedRevisionTaskIds(item)).toEqual([]);
  });

  it('approves one task while leaving the remaining review open', async () => {
    const item = resubmittedCase();
    const updated = {
      ...item,
      tasks: [{ ...item.tasks[0], status: 'accepted' }, item.tasks[1]],
    };
    reviewService.updateTask.mockResolvedValue(updated);

    await decisions.approveTask(item, item.tasks[0]);

    expect(reviewService.updateTask).toHaveBeenCalledWith(
      12,
      'case-1',
      'task-1',
      'accepted'
    );
    expect(replaceCase).toHaveBeenCalledWith(updated);
    expect(notify).toHaveBeenCalledWith('Requested edit approved.', 'success');
    expect(busy.value).toBe(false);
    expect(decisions.updatingTask.value).toEqual({ id: '', status: '' });
  });

  it('reports final approval with no project-content changes accurately', async () => {
    const item = resubmittedCase();
    item.tasks = [item.tasks[0]];
    const updated = {
      ...item,
      state: 'resolved',
      resubmitted_upload_status: 'no_changes',
      tasks: [{ ...item.tasks[0], status: 'accepted' }],
    };
    reviewService.updateTask.mockResolvedValue(updated);

    await decisions.approveTask(item, item.tasks[0]);

    expect(notify).toHaveBeenCalledWith(
      'Correction approved. No project content changed.',
      'success'
    );
  });

  it('surfaces backend rejection and always releases the busy state', async () => {
    const item = resubmittedCase();
    reviewService.updateTask.mockRejectedValue({
      response: { data: { detail: 'Task decision is stale.' } },
    });

    await decisions.approveTask(item, item.tasks[0]);

    expect(error.value).toBe('Task decision is stale.');
    expect(notify).toHaveBeenCalledWith('Task decision is stale.', 'error');
    expect(replaceCase).not.toHaveBeenCalled();
    expect(busy.value).toBe(false);
  });
});
