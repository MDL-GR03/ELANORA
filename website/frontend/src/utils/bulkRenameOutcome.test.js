import { describe, expect, it } from 'vitest';

import { bulkRenameMessage, successfulRenames } from './bulkRenameOutcome';

describe('successfulRenames', () => {
  const files = [
    { elan_id: 1, name: 'a.eaf' },
    { elan_id: 2, name: 'b.eaf' },
    { elan_id: 3, name: 'c.eaf' },
  ];
  const renames = [1, 2, 3, 4].map((elan_id) => ({
    elan_id,
    new_filename: `${elan_id}.eaf`,
  }));

  it('keeps only renames that succeeded without a conflict', () => {
    const result = {
      results: [
        { old_filename: 'a.eaf', success: true },
        { old_filename: 'b.eaf', success: true, conflict_elan_id: 9 },
        { old_filename: 'c.eaf', success: false },
      ],
    };
    expect(
      successfulRenames(renames, result, files).map((r) => r.elan_id)
    ).toEqual([1]);
  });

  it('trusts the request when the server sent no per-file results', () => {
    expect(successfulRenames(renames, undefined, files)).toBe(renames);
  });
});

describe('bulkRenameMessage', () => {
  it.each([
    [
      { requested: 3, successful: 3, conflicts: 0 },
      'rename.bulkSuccess',
      undefined,
    ],
    [
      { requested: 2, successful: 1, conflicts: 1 },
      'rename.bulkMixedSingular',
      undefined,
    ],
    [
      { requested: 4, successful: 1, conflicts: 3 },
      'rename.bulkMixedOneSuccess',
      { failed: 3 },
    ],
    [
      { requested: 4, successful: 3, conflicts: 1 },
      'rename.bulkMixedOneConflict',
      { successful: 3 },
    ],
    [
      { requested: 5, successful: 2, conflicts: 3 },
      'rename.bulkMixed',
      { successful: 2, failed: 3 },
    ],
    [
      { requested: 1, successful: 0, conflicts: 1 },
      'rename.bulkAllConflictsSingular',
      undefined,
    ],
    [
      { requested: 2, successful: 0, conflicts: 2 },
      'rename.bulkAllConflicts',
      { count: 2 },
    ],
    [
      { requested: 2, successful: 1, conflicts: 0 },
      'rename.bulkPartialSingular',
      undefined,
    ],
    [
      { requested: 3, successful: 1, conflicts: 0 },
      'rename.bulkPartialOneSuccess',
      { failed: 2 },
    ],
    [
      { requested: 3, successful: 2, conflicts: 0 },
      'rename.bulkPartialOneFailed',
      { successful: 2 },
    ],
    [
      { requested: 5, successful: 3, conflicts: 0 },
      'rename.bulkPartial',
      { successful: 3, failed: 2 },
    ],
  ])('summarizes %o as %s', (counts, key, params) => {
    const message = bulkRenameMessage(counts);
    expect(message.key).toBe(key);
    expect(message.params).toEqual(params);
  });

  it('says nothing when nothing was renamed or conflicted', () => {
    expect(
      bulkRenameMessage({ requested: 2, successful: 0, conflicts: 0 })
    ).toBeNull();
  });
});
