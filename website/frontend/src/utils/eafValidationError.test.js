import { describe, expect, it } from 'vitest';

import { formatEafUploadError } from './eafValidationError';

const translate = (key, params) =>
  params === undefined ? key : `${key}:${JSON.stringify(params)}`;
const failure = (data) => ({ response: { data } });

describe('formatEafUploadError', () => {
  it('lists each rejected file after the translated refusal', () => {
    const message = formatEafUploadError(
      failure({
        code: 'invalid_eaf_batch',
        detail: 'One or more EAF files failed validation.',
        params: {
          rejected_files: [
            {
              filename: 'session.eaf',
              issue_count: 3,
              issues: [
                {
                  code: 'unknown_time_slot',
                  message: "Unknown time slot 'ts1'",
                  location: '/ANNOTATION_DOCUMENT/TIER[1]',
                },
              ],
            },
          ],
        },
      }),
      translate,
      'Upload failed'
    );

    expect(message).toContain('apiErrors.invalid_eaf_batch');
    expect(message).toContain('apiErrors.unknown_time_slot:');
    expect(message).toContain('session.eaf:');
    expect(message).toContain('uploadPage.errors.moreIssues:2');
  });

  it('names the file and tiers of a reintegration conflict', () => {
    expect(
      formatEafUploadError(
        failure({
          code: 'tier_reintegration_conflict',
          params: { filename: 'session.eaf', tiers: ['gaze', 'hands'] },
        }),
        translate,
        'Upload failed'
      )
    ).toBe(
      'apiErrors.tier_reintegration_conflict:{"filename":"session.eaf","tiers":["gaze","hands"]} (session.eaf: gaze, hands)'
    );
  });

  it('falls back for a request that never reached the server', () => {
    expect(
      formatEafUploadError(new Error('offline'), translate, 'Upload failed')
    ).toBe('Upload failed');
  });
});
