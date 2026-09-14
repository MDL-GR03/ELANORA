import { describe, expect, it } from 'vitest';

import {
  acceptedValuesPlaceholder,
  extractPatternComponents,
  normalizeNumericAcceptedValues,
  splitPatternBlocks,
  splitTypeGroups,
} from './namingStandardPattern';

describe('naming standard pattern utilities', () => {
  it('normalizes numeric values and ranges to the configured width', () => {
    expect(normalizeNumericAcceptedValues('1, 7; 12-98', 3)).toEqual({
      values: ['001', '007', '012-098'],
      error: null,
    });
  });

  it('rejects descending, oversized, and non-numeric accepted values', () => {
    expect(normalizeNumericAcceptedValues('9-2', 2)).toEqual({
      error: 'Invalid range "9-2".',
    });
    expect(normalizeNumericAcceptedValues('100', 2)).toEqual({
      error: 'Value "100" exceeds 2 digits.',
    });
    expect(normalizeNumericAcceptedValues('A1', 2)).toEqual({
      error: 'Invalid value "A1".',
    });
  });

  it('extracts ordered components without sharing mutable arrays', () => {
    const components = extractPatternComponents(
      '{prefix_video}_{participant}-{session}'
    );

    expect(components.map(({ name, order }) => ({ name, order }))).toEqual([
      { name: 'prefix_video', order: 1 },
      { name: 'participant', order: 2 },
      { name: 'session', order: 3 },
    ]);
    components[0].accepted_values.push('VIDEO');
    expect(components[1].accepted_values).toEqual([]);
  });

  it('splits example values when character classes change', () => {
    expect(splitTypeGroups('ABcd012-XY')).toEqual([
      'AB',
      'cd',
      '012',
      '-',
      'XY',
    ]);
    expect(splitTypeGroups('')).toEqual([]);
  });

  it('splits separators only outside component braces', () => {
    expect(
      splitPatternBlocks('{prefix_video}_{participant}_{session}', '_')
    ).toEqual(['{prefix_video}', '{participant}', '{session}']);
  });

  it('provides examples appropriate to letter and numeric regex widths', () => {
    expect(acceptedValuesPlaceholder('\\p{L}{2}')).toBe('e.g. AB, ÉZ, ZA');
    expect(acceptedValuesPlaceholder('\\p{N}{3}')).toBe('e.g. 001, 999');
    expect(acceptedValuesPlaceholder('.+')).toBe('Accepted Values');
  });
});
