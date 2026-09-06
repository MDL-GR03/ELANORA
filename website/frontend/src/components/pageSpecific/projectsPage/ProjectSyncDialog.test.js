// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import en from '@/locales/en.json';
import gitService from '@/api/service/gitService';
import ProjectSyncDialog from './ProjectSyncDialog.vue';

vi.mock('@/api/service/gitService', () => ({
  default: {
    checkSyncStatus: vi.fn(),
    getSynchronizationOperations: vi.fn(),
    recoverSynchronizationOperation: vi.fn(),
    synchronizeProject: vi.fn(),
  },
}));

function mountDialog() {
  return mount(ProjectSyncDialog, {
    props: { projectName: 'LSFB', visible: true },
    global: {
      plugins: [
        createPinia(),
        createI18n({ legacy: false, locale: 'en', messages: { en } }),
      ],
      stubs: {
        FontAwesomeIcon: true,
        UserConfirm: {
          props: ['modelValue'],
          emits: ['confirm'],
          template:
            '<button v-if="modelValue" class="confirm-stub" @click="$emit(\'confirm\')">confirm</button>',
        },
      },
    },
  });
}

describe('ProjectSyncDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    gitService.getSynchronizationOperations.mockResolvedValue({
      operations: [],
    });
    gitService.checkSyncStatus.mockResolvedValue({
      in_sync: false,
      files_status: [
        { filename: 'elan_files/session.eaf', status: 'modified' },
      ],
    });
    gitService.synchronizeProject.mockResolvedValue({ status: 'completed' });
  });

  it('presents server changes without claiming they are already accepted', async () => {
    const wrapper = mountDialog();
    await flushPromises();

    expect(wrapper.get('dialog').attributes('aria-modal')).toBe('true');
    expect(wrapper.text()).toContain('Nothing has been accepted yet');
    expect(wrapper.text()).toContain('elan_files/session.eaf');
    expect(
      wrapper.findAll('button').some((button) => button.text() === 'Inspect')
    ).toBe(false);
  });

  it('requires confirmation before starting synchronization', async () => {
    const wrapper = mountDialog();
    await flushPromises();

    await wrapper.get('.sync-btn.primary').trigger('click');
    expect(gitService.synchronizeProject).not.toHaveBeenCalled();
    await wrapper.get('.confirm-stub').trigger('click');
    await flushPromises();

    expect(gitService.synchronizeProject).toHaveBeenCalledWith('LSFB');
  });

  it('keeps the dialog open when a clean worktree needs database recovery', async () => {
    gitService.getSynchronizationOperations.mockResolvedValue({
      operations: [
        {
          operation_id: '00000000-0000-0000-0000-000000000001',
          state: 'recovery_required',
          changes: [{ filename: 'elan_files/session.eaf' }],
          created_at: '2026-09-05T12:00:00Z',
        },
      ],
    });
    gitService.checkSyncStatus.mockResolvedValue({
      in_sync: true,
      files_status: [],
    });

    const wrapper = mountDialog();
    await flushPromises();

    expect(wrapper.text()).toContain('needs recovery');
    expect(wrapper.get('.sync-history-action').text()).toBe('Recover');
    expect(wrapper.emitted('close')).toBeUndefined();
  });
});
