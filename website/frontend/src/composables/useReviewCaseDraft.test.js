import { nextTick } from 'vue';
import { describe, expect, it } from 'vitest';

import { useReviewCaseDraft } from './useReviewCaseDraft';

describe('useReviewCaseDraft', () => {
  it('serializes independently targeted changes for selected files', () => {
    const composer = useReviewCaseDraft(['first.eaf', 'second.eaf']);
    const first = composer.taskDrafts[0];
    first.selected = true;
    composer.selectTask(first);
    Object.assign(first.changes[0], {
      instruction: 'Correct A1',
      tier_id: 'translation',
      annotation_id: 'A1',
      start_ms: 100,
      end_ms: 250,
    });
    composer.addTaskChange(first);
    Object.assign(first.changes[1], {
      instruction: 'Correct A2',
      annotation_id: 'A2',
    });
    composer.draft.title = 'Precise review';

    expect(composer.hasSelectedTasks.value).toBe(true);
    expect(
      composer.buildPayload({ uploadId: 9, requestChanges: true })
    ).toMatchObject({
      upload_id: 9,
      request_changes: true,
      title: 'Precise review',
      initial_comment: null,
      tasks: [
        {
          filename: 'first.eaf',
          instruction: 'Correct A1',
          tier_id: 'translation',
          annotation_id: 'A1',
          start_ms: 100,
          end_ms: 250,
        },
        {
          filename: 'first.eaf',
          instruction: 'Correct A2',
          annotation_id: 'A2',
        },
      ],
    });
  });

  it('requires a non-empty instruction for every selected change', () => {
    const composer = useReviewCaseDraft(['subject.eaf']);
    const task = composer.taskDrafts[0];

    expect(composer.hasSelectedTasks.value).toBe(false);
    task.selected = true;
    composer.selectTask(task);
    expect(composer.hasSelectedTasks.value).toBe(false);
    task.changes[0].instruction = '   ';
    expect(composer.hasSelectedTasks.value).toBe(false);
    task.changes[0].instruction = 'Correct the gloss';
    expect(composer.hasSelectedTasks.value).toBe(true);
  });

  it('filters and paginates large file lists predictably', async () => {
    const filenames = Array.from(
      { length: 24 },
      (_, index) => `session-${index + 1}.eaf`
    );
    const composer = useReviewCaseDraft(filenames);

    expect(composer.filePageCount.value).toBe(3);
    expect(composer.visibleTaskDrafts.value).toHaveLength(10);
    composer.filePage.value = 3;
    expect(composer.visibleTaskDrafts.value).toHaveLength(4);

    composer.fileQuery.value = 'session-2';
    await nextTick();
    expect(composer.filePage.value).toBe(1);
    expect(
      composer.filteredTaskDrafts.value.map((task) => task.filename)
    ).toEqual([
      'session-2.eaf',
      'session-20.eaf',
      'session-21.eaf',
      'session-22.eaf',
      'session-23.eaf',
      'session-24.eaf',
    ]);
  });

  it('resets all composer state without retaining stale corrections', () => {
    const composer = useReviewCaseDraft(['subject.eaf']);
    const task = composer.taskDrafts[0];
    composer.draft.title = 'Old request';
    composer.fileQuery.value = 'subject';
    task.selected = true;
    composer.selectTask(task);
    task.changes[0].instruction = 'Old instruction';
    composer.addTaskChange(task);

    composer.resetDraft();

    expect(composer.draft.title).toBe('');
    expect(composer.fileQuery.value).toBe('');
    expect(composer.filePage.value).toBe(1);
    expect(composer.activeFilename.value).toBe('');
    expect(task.selected).toBe(false);
    expect(task.changes).toHaveLength(1);
    expect(task.changes[0].instruction).toBe('');
  });

  it('preserves the legacy single-question fields', () => {
    const composer = useReviewCaseDraft([]);
    Object.assign(composer.draft, {
      title: 'Question about A4',
      filename: 'subject.eaf',
      tier_id: 'gloss',
      annotation_id: 'A4',
      initial_comment: 'Could you explain this choice?',
    });

    expect(composer.buildPayload({ uploadId: 3 })).toMatchObject({
      upload_id: 3,
      request_changes: false,
      title: 'Question about A4',
      filename: 'subject.eaf',
      tier_id: 'gloss',
      annotation_id: 'A4',
      initial_comment: 'Could you explain this choice?',
      tasks: [],
    });
  });
});
