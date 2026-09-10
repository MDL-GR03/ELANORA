import { beforeEach, describe, expect, it, vi } from 'vitest';

import axiosInstance from '@/api/apiClient';
import { exportTierSubset } from './tierService';

vi.mock('@/api/apiClient', () => ({
  default: { post: vi.fn() },
}));

describe('tierService research-copy export', () => {
  beforeEach(() => axiosInstance.post.mockReset());

  it('sends optional context and declared baseline corrections separately', async () => {
    axiosInstance.post.mockResolvedValue({ data: new Blob() });

    await exportTierSubset(
      'LSFB project',
      'session.eaf',
      ['Prosody'],
      7,
      ['Sign left', 'Sign right'],
      ['Sign left']
    );

    expect(axiosInstance.post).toHaveBeenCalledWith(
      '/tier/LSFB%20project/export',
      {
        filename: 'session.eaf',
        tier_names: ['Prosody'],
        topic_id: 7,
        context_tier_names: ['Sign left', 'Sign right'],
        editable_baseline_tier_names: ['Sign left'],
      },
      { responseType: 'blob' }
    );
  });
});
