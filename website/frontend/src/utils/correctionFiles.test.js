import { describe, expect, it } from 'vitest';
import {
  activeCorrectionTasks,
  findMissingCorrectionFiles,
} from './correctionFiles';

const reviewCase = {
  tasks: [
    {
      task_id: 'one',
      filename: 'elan_files/session-a.eaf',
      status: 'requested',
    },
    {
      task_id: 'two',
      filename: 'elan_files/session-b.eaf',
      status: 'reopened',
    },
    {
      task_id: 'done',
      filename: 'elan_files/already-fixed.eaf',
      status: 'accepted',
    },
  ],
};

describe('correction file scope', () => {
  it('requires every unresolved file but never an accepted one', () => {
    expect(
      activeCorrectionTasks(reviewCase).map((task) => task.task_id)
    ).toEqual(['one', 'two']);
    expect(findMissingCorrectionFiles(reviewCase, [])).toEqual([
      'elan_files/session-a.eaf',
      'elan_files/session-b.eaf',
    ]);
  });

  it('reports only the requested file missing from a partial correction', () => {
    expect(
      findMissingCorrectionFiles(reviewCase, [{ name: 'session-a.eaf' }])
    ).toEqual(['elan_files/session-b.eaf']);
  });

  it('matches folder uploads to their project-relative requested paths', () => {
    const selected = [
      { name: 'session-a.eaf', webkitRelativePath: 'elan_files/session-a.eaf' },
      { name: 'session-b.eaf', webkitRelativePath: 'elan_files/session-b.eaf' },
    ];
    expect(findMissingCorrectionFiles(reviewCase, selected)).toEqual([]);
  });
});
