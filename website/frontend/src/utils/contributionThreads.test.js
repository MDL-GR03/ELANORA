import { describe, expect, it } from 'vitest';
import {
  countAnnotationCollisions,
  groupContributionThreads,
  sortContributionThreads,
} from './contributionThreads';

describe('groupContributionThreads', () => {
  it('shows a correction chain as one current contribution with history', () => {
    const uploads = [
      { upload_id: 2, superseded_by_upload_id: 5 },
      { upload_id: 5, superseded_by_upload_id: 8 },
      { upload_id: 8, superseded_by_upload_id: null },
    ];
    const cases = [
      { case_id: 'case-1', upload_id: 2, resubmitted_upload_id: 8 },
    ];

    expect(groupContributionThreads(uploads, cases)).toEqual([
      expect.objectContaining({
        upload_id: 8,
        version_number: 3,
        version_history: [uploads[0], uploads[1]],
        review_case: cases[0],
      }),
    ]);
  });

  it('keeps unrelated contributions as separate threads', () => {
    const uploads = [{ upload_id: 1 }, { upload_id: 4 }];
    expect(groupContributionThreads(uploads)).toHaveLength(2);
  });

  it('lets active human review override technical merge readiness', () => {
    const uploads = [{ upload_id: 5, merge_status: 'ready_to_merge' }];
    const cases = [
      {
        case_id: 'case-1',
        upload_id: 2,
        resubmitted_upload_id: 5,
        state: 'changes_requested',
      },
    ];

    expect(groupContributionThreads(uploads, cases)[0]).toEqual(
      expect.objectContaining({
        merge_status: 'changes_requested',
        technical_merge_status: 'ready_to_merge',
      })
    );
  });
});

describe('sortContributionThreads', () => {
  const threads = [
    { upload_id: 15, uploaded_at: '2026-09-09T12:42:00Z' },
    { upload_id: 14, uploaded_at: '2026-09-09T12:41:00Z' },
  ];

  it('orders the queue oldest first by default', () => {
    expect(
      sortContributionThreads(threads).map((item) => item.upload_id)
    ).toEqual([14, 15]);
  });

  it('supports newest first without mutating the source list', () => {
    expect(
      sortContributionThreads(threads, 'newest').map((item) => item.upload_id)
    ).toEqual([15, 14]);
    expect(threads.map((item) => item.upload_id)).toEqual([15, 14]);
  });
});

describe('countAnnotationCollisions', () => {
  it('counts unique annotation targets instead of ordinary same-file work', () => {
    expect(
      countAnnotationCollisions({
        annotation_collisions: [
          {
            contribution_id: 15,
            annotations: { 'elan_files/session.eaf': ['a1', 'a2'] },
          },
          {
            contribution_id: 16,
            annotations: { 'elan_files/session.eaf': ['a1'] },
          },
        ],
      })
    ).toBe(2);
    expect(
      countAnnotationCollisions({
        files: { modified: ['elan_files/session.eaf'] },
      })
    ).toBe(0);
  });
});
