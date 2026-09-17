import { describe, expect, it } from 'vitest';

import { standardAt, standardIdAt } from './effectiveStandard';

describe('effective standard lookup', () => {
  it('reads a single id or the first id of a file-type mapping', () => {
    expect(standardIdAt({ 1: 7 }, 1)).toBe(7);
    expect(standardIdAt({ 1: { media: null, eaf: 8 } }, 1)).toBe(8);
    expect(standardIdAt({}, 1)).toBeUndefined();
  });

  it('finds the standard or returns null', () => {
    const standards = [{ id: 8, name: 'Main' }];
    expect(standardAt({ 4: { eaf: 8 } }, standards, 4)).toEqual(standards[0]);
    expect(standardAt({ 4: 9 }, standards, 4)).toBeNull();
  });
});
