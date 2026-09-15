// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { createI18n } from 'vue-i18n';

import fr from '@/locales/fr.json';
import { englishI18n } from '@/testing/i18n';
import AcceptedProjectHistory from './AcceptedProjectHistory.vue';
import gitService from '@/api/service/gitService.js';

const addMessage = vi.fn();

vi.mock('@/api/service/gitService.js', () => ({
  default: {
    getAcceptedProjectHistory: vi.fn(),
    getCurrentProjectRevisionHealth: vi.fn(),
    recoverCurrentProjectRevision: vi.fn(),
    previewProjectVersionRestore: vi.fn(),
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
      global: { plugins: [englishI18n()], stubs: { FontAwesomeIcon: true } },
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
      global: { plugins: [englishI18n()], stubs: { FontAwesomeIcon: true } },
    });
    await flushPromises();

    expect(wrapper.find('.recovery-panel').exists()).toBe(false);
  });

  describe('restore preview', () => {
    const openPreview = async (i18n) => {
      gitService.getCurrentProjectRevisionHealth.mockResolvedValue({
        status: 'healthy',
      });
      gitService.getAcceptedProjectHistory.mockResolvedValue({
        current_commit: 'b'.repeat(40),
        versions: [
          {
            commit: 'a'.repeat(40),
            short_commit: 'aaaaaaa',
            message: 'Accepted contribution',
            author: 'Ada',
            committed_at: '2026-09-10T10:00:00Z',
            is_current: false,
          },
        ],
      });
      gitService.previewProjectVersionRestore.mockResolvedValue({
        current_commit: 'b'.repeat(40),
        files: [
          { status: 'M', filename: 'elan_files/a.eaf' },
          { status: 'R087', filename: 'elan_files/b.eaf' },
        ],
        semantic_summary: { annotations: 1 },
        affected_pending_contributions: 2,
        affected_pending_upload_ids: [4, 7],
        active_review_cases: 1,
      });
      const wrapper = mount(AcceptedProjectHistory, {
        props: { projectName: 'Corpus' },
        global: { plugins: [i18n], stubs: { FontAwesomeIcon: true } },
      });
      await flushPromises();
      await wrapper.get('.preview-button').trigger('click');
      await flushPromises();
      return wrapper.get('.restore-preview');
    };

    it('counts changes and names Git statuses in words', async () => {
      const preview = await openPreview(englishI18n());

      expect(preview.text()).toContain('2 file changes, 1 annotation change.');
      expect(
        preview.findAll('.changed-files span').map((s) => s.text())
      ).toEqual(['Modified', 'Renamed']);
      expect(preview.get('.impact-warning p').text()).toBe(
        '2 open submission versions (#4, #7) and 1 active correction case ' +
          'may change compatibility. Their branches, discussions, and base ' +
          'versions remain intact.'
      );
      expect(preview.text()).toContain('Type RESTORE Corpus');
    });

    it('reads naturally in French while keeping the confirmation word', async () => {
      const preview = await openPreview(
        createI18n({
          legacy: false,
          locale: 'fr',
          fallbackLocale: 'en',
          messages: { fr },
        })
      );

      expect(preview.text()).toContain(
        '2 modifications de fichiers, 1 modification d’annotation.'
      );
      expect(preview.text()).toContain('Saisissez RESTORE Corpus');
      expect(preview.text()).not.toContain('acceptedHistory.');
    });
  });
});
