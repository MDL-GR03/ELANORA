// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AcceptedProjectHistory from './AcceptedProjectHistory.vue';
import gitService from '@/api/service/gitService.js';

const addMessage = vi.fn();

vi.mock('@/api/service/gitService.js', () => ({
  default: {
    getAcceptedProjectHistory: vi.fn(),
    getCurrentProjectRevisionHealth: vi.fn(),
    recoverCurrentProjectRevision: vi.fn(),
  },
}));
vi.mock('@/stores/eventMessage.js', () => ({
  useEventMessageStore: () => ({ addMessage }),
}));

describe('AcceptedProjectHistory recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    gitService.getAcceptedProjectHistory.mockResolvedValue({
      current_commit: 'a'.repeat(40),
      versions: [],
    });
  });

  it('only offers confirmed recovery when accepted data is unhealthy', async () => {
    gitService.getCurrentProjectRevisionHealth
      .mockResolvedValueOnce({
        status: 'recovery_required',
        recoverable: true,
        revision_id: '11111111-1111-1111-1111-111111111111',
        missing_files: ['session.eaf'],
        unexpected_files: [],
        checksum_mismatches: [],
        database_missing_files: ['session.eaf'],
        database_unexpected_files: [],
        database_checksum_mismatches: [],
      })
      .mockResolvedValueOnce({ status: 'healthy', recoverable: true });
    gitService.recoverCurrentProjectRevision.mockResolvedValue({
      status: 'recovered',
    });
    const wrapper = mount(AcceptedProjectHistory, {
      props: { projectName: 'Corpus' },
      global: { stubs: { FontAwesomeIcon: true } },
    });
    await flushPromises();

    expect(wrapper.text()).toContain('Accepted project data needs repair');
    expect(wrapper.text()).toContain('session.eaf');
    const button = wrapper.get('.recovery-panel .danger-button');
    expect(button.attributes('disabled')).toBeDefined();

    await wrapper
      .get('.recovery-panel textarea')
      .setValue('Repair damaged files');
    await wrapper.get('.recovery-panel input').setValue('RECOVER Corpus');
    expect(button.attributes('disabled')).toBeUndefined();
    await button.trigger('click');
    await flushPromises();

    expect(gitService.recoverCurrentProjectRevision).toHaveBeenCalledWith(
      'Corpus',
      {
        revision_id: '11111111-1111-1111-1111-111111111111',
        reason: 'Repair damaged files',
        confirmation: 'RECOVER Corpus',
      }
    );
    expect(wrapper.find('.recovery-panel').exists()).toBe(false);
  });

  it('does not clutter a healthy history with recovery controls', async () => {
    gitService.getCurrentProjectRevisionHealth.mockResolvedValue({
      status: 'healthy',
      recoverable: true,
    });
    const wrapper = mount(AcceptedProjectHistory, {
      props: { projectName: 'Corpus' },
      global: { stubs: { FontAwesomeIcon: true } },
    });
    await flushPromises();

    expect(wrapper.find('.recovery-panel').exists()).toBe(false);
  });
});
