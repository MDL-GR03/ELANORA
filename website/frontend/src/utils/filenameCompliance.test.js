import { describe, expect, it } from 'vitest';

import { isElanFilenameCompliant } from './elanFilenameCompliance';
import {
  extractComponentsFromFilename,
  isFilenameCompliant,
} from './filenameCompliance';

const researchStandard = {
  pattern: '{corpus}_{participant}_{session}_{language}',
  components: [
    { name: 'corpus', fixed_value: 'LSFB', regex: '[A-Z]+' },
    {
      name: 'participant',
      regex: 'S\\d{3}',
      accepted_values_str: '/^S\\d{3}$/',
    },
    {
      name: 'session',
      regex: '\\d{2}',
      numeric_range: { min: 1, max: 20, width: 2 },
    },
    { name: 'language', regex: '[a-z]{3}', accepted_values: ['fsl', 'fra'] },
  ],
};

describe('research filename conventions', () => {
  it('accepts a complete compliant EAF filename', () => {
    expect(
      isElanFilenameCompliant(researchStandard, 'LSFB_S059_03_fsl.eaf')
    ).toBe(true);
  });

  it.each([
    'LSFB_S59_03_fsl.eaf',
    'LSFB_S059_21_fsl.eaf',
    'LSFB_S059_03_eng.eaf',
    'LSFB_S059_03_fsl.xml',
  ])('rejects a convention violation: %s', (filename) => {
    expect(isElanFilenameCompliant(researchStandard, filename)).toBe(false);
  });

  it('extracts convention components for review interfaces', () => {
    expect(
      extractComponentsFromFilename(researchStandard, 'LSFB_S059_03_fsl')
    ).toEqual({
      corpus: 'LSFB',
      participant: 'S059',
      session: '03',
      language: 'fsl',
    });
  });

  it('fails closed for a malformed or incomplete standard', () => {
    expect(isFilenameCompliant(null, 'anything.eaf')).toBe(false);
    expect(
      isFilenameCompliant(
        { pattern: '{id}', components: [{ name: 'id', regex: '[' }] },
        'x.eaf'
      )
    ).toBe(false);
  });
});
