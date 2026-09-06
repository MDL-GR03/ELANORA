import { describe, expect, it } from 'vitest';

import { formatEafUploadError } from './eafValidationError';

describe('formatEafUploadError', () => {
  it('renders a quarantined EAF response without exposing raw content', () => {
    const message = formatEafUploadError(
      {
        code: 'invalid_eaf_batch',
        message: 'The original was preserved.',
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
      'Upload failed'
    );

    expect(message).toContain('The original was preserved.');
    expect(message).toContain("session.eaf: Unknown time slot 'ts1'");
    expect(message).toContain('2 more issue(s)');
  });

  it('keeps legacy string errors and falls back for unknown responses', () => {
    expect(formatEafUploadError('Legacy error', 'Upload failed')).toBe(
      'Legacy error'
    );
    expect(formatEafUploadError(null, 'Upload failed')).toBe('Upload failed');
  });

  it('shows an actionable tier reintegration conflict', () => {
    expect(
      formatEafUploadError(
        {
          code: 'tier_reintegration_conflict',
          message: 'session.eaf has newer accepted changes in: gaze.',
          tiers: ['gaze'],
        },
        'Upload failed'
      )
    ).toBe('session.eaf has newer accepted changes in: gaze.');
  });
});
