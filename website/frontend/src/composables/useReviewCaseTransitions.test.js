import { reactive, ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useReviewCaseTransitions } from './useReviewCaseTransitions';
import { englishI18n } from '@/testing/i18n';

describe('useReviewCaseTransitions', () => {
  let reviewService;
  let busy;
  let error;
  let replies;
  let revisionFeedbackCaseId;
  let revisionTargets;
  let selectedRevisionTaskIds;
  let clearRevisionDraft;
  let replaceCase;
  let confirmAction;
  let notify;
  let transitions;

  const item = { case_id: 'case-1', state: 'resubmitted' };

  beforeEach(() => {
    reviewService = {
      transition: vi.fn(),
      requestRevision: vi.fn(),
      resubmit: vi.fn(),
    };
    busy = ref(false);
    error = ref('');
    replies = reactive({});
    revisionFeedbackCaseId = ref('');
    revisionTargets = reactive({});
    selectedRevisionTaskIds = vi.fn(() => ['task-1']);
    clearRevisionDraft = vi.fn();
    replaceCase = vi.fn();
    confirmAction = vi.fn().mockResolvedValue(true);
    notify = vi.fn();
    transitions = useReviewCaseTransitions({
      projectId: () => 12,
      resubmissionUploadId: () => 19,
      reviewService,
      busy,
      error,
      replies,
      revisionFeedbackCaseId,
      revisionTargets,
      selectedRevisionTaskIds,
      revisionTargetSummary: (target) =>
        `Target: ${target.annotation_id} · Tier: ${target.tier_id}`,
      clearRevisionDraft,
      replaceCase,
      confirmAction,
      notify,
      t: englishI18n().global.t,
    });
  });

  it('uses correction-specific confirmation before resolving a resubmission', async () => {
    const updated = { ...item, state: 'resolved' };
    reviewService.transition.mockResolvedValue(updated);

    await expect(transitions.transition(item, 'resolved')).resolves.toBe(true);

    expect(confirmAction).toHaveBeenCalledWith({
      title: 'Approve this correction?',
      message: expect.stringContaining('does not merge the contribution'),
      confirmText: 'Approve correction and close review',
      cancelText: 'Cancel',
      tone: 'success',
    });
    expect(reviewService.transition).toHaveBeenCalledWith(
      12,
      'case-1',
      'resolved'
    );
    expect(replaceCase).toHaveBeenCalledWith(updated);
  });

  it('does not mutate review state when confirmation is cancelled', async () => {
    confirmAction.mockResolvedValue(false);

    await expect(
      transitions.transition(item, 'changes_requested')
    ).resolves.toBe(false);

    expect(reviewService.transition).not.toHaveBeenCalled();
    expect(busy.value).toBe(false);
  });

  it('builds structured annotation feedback and clears it after sending', async () => {
    replies['case-1'] = 'Please address these details.';
    revisionTargets['case-1'] = [
      {
        task_id: 'task-1',
        annotation_id: 'A1',
        tier_id: 'translation',
        comment: 'Use the verified wording.',
      },
    ];
    const updated = { ...item, state: 'changes_requested' };
    reviewService.requestRevision.mockResolvedValue(updated);

    await expect(transitions.requestAnotherRevision(item)).resolves.toBe(true);

    expect(reviewService.requestRevision).toHaveBeenCalledWith(
      12,
      'case-1',
      ['task-1'],
      'Please address these details.\n\nRequested annotation corrections:\n- Target: A1 · Tier: translation\n  Instruction: Use the verified wording.'
    );
    expect(replies['case-1']).toBe('');
    expect(clearRevisionDraft).toHaveBeenCalledWith('case-1');
    expect(replaceCase).toHaveBeenCalledWith(updated);
  });

  it('requires both selected tasks and reviewer feedback', async () => {
    expect(transitions.hasRevisionFeedback(item)).toBe(false);
    await expect(transitions.requestAnotherRevision(item)).resolves.toBe(false);
    expect(confirmAction).not.toHaveBeenCalled();

    replies['case-1'] = 'Try again.';
    selectedRevisionTaskIds.mockReturnValue([]);
    await expect(transitions.requestAnotherRevision(item)).resolves.toBe(false);
    expect(reviewService.requestRevision).not.toHaveBeenCalled();
  });

  it('opens feedback before a second click sends the revision request', async () => {
    const requestSpy = vi
      .spyOn(transitions, 'requestAnotherRevision')
      .mockResolvedValue(true);

    transitions.beginOrRequestAnotherRevision(item);
    expect(revisionFeedbackCaseId.value).toBe('case-1');
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it('normalizes reviewer assignment identifiers and permits unassignment', async () => {
    reviewService.transition
      .mockResolvedValueOnce({ ...item, assigned_to: 7 })
      .mockResolvedValueOnce({ ...item, assigned_to: null });

    await transitions.assign(item, '7');
    await transitions.assign(item, '');

    expect(reviewService.transition).toHaveBeenNthCalledWith(
      1,
      12,
      'case-1',
      'resubmitted',
      { assigned_to: 7 }
    );
    expect(reviewService.transition).toHaveBeenNthCalledWith(
      2,
      12,
      'case-1',
      'resubmitted',
      { assigned_to: null }
    );
  });

  it('links the configured corrected upload and reports backend failures', async () => {
    reviewService.resubmit.mockRejectedValue({
      response: { data: { detail: 'Upload does not belong to this review.' } },
    });

    await expect(transitions.linkResubmission(item)).resolves.toBe(false);

    expect(reviewService.resubmit).toHaveBeenCalledWith(12, 'case-1', 19);
    expect(error.value).toBe('Upload does not belong to this review.');
    expect(notify).toHaveBeenCalledWith(
      'Upload does not belong to this review.',
      'error'
    );
    expect(busy.value).toBe(false);
  });
});
