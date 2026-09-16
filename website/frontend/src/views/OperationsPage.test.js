// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import OperationsPage from './OperationsPage.vue';

const getStatus = vi.fn();
const checkStorage = vi.fn();

vi.mock('@/api/service/operationsService', () => ({
  default: {
    getStatus: (...args) => getStatus(...args),
    checkStorage: (...args) => checkStorage(...args),
  },
}));

function mountPage() {
  return mount(OperationsPage, {
    global: {
      plugins: [
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
      stubs: { FontAwesomeIcon: true, WorkspaceHeader: true },
    },
  });
}

function baseStatus() {
  return {
    storage: {
      backend: 's3',
      location_hint: 'in...ts via objects.example.org',
      credentials_source: 'workload_identity',
      policy_verification: 'external_object_storage_controls',
    },
    integrity: {
      total_projects: 4,
      scanned_projects: 4,
      healthy_projects: 3,
      unhealthy_projects: 1,
      unscanned_projects: 0,
      latest_check_at: '2026-09-10T12:00:00Z',
    },
    publication_queue: {
      queued: 2,
      running: 1,
      review_needed: 1,
      failed: 0,
    },
    email_delivery: {
      pending: 3,
      permanently_failed: 1,
      oldest_pending_at: '2026-09-10T09:00:00Z',
      retention_days: 30,
    },
    recovery: {
      responsibility: 'installation',
      latest_backup_at: '2026-09-16T02:00:00Z',
      latest_verified_backup_at: '2026-09-15T03:00:00Z',
      latest_drill_at: null,
      state: 'healthy',
      jobs: [
        {
          job: 'backup',
          outcome: 'succeeded',
          started_at: '2026-09-16T02:00:00Z',
          finished_at: '2026-09-16T02:01:00Z',
          detail: { key: 'backups/elanora-20260916T020000Z.elanora' },
        },
        {
          job: 'storage_capacity',
          outcome: 'succeeded',
          started_at: '2026-09-16T02:05:00Z',
          finished_at: '2026-09-16T02:05:00Z',
          detail: { used_percent: 42.5 },
        },
      ],
    },
  };
}

describe('OperationsPage', () => {
  beforeEach(() => {
    getStatus.mockReset();
    checkStorage.mockReset();
    getStatus.mockResolvedValue(baseStatus());
  });

  it('shows safe status and runs an explicit storage check', async () => {
    checkStorage.mockResolvedValue({ status: 'healthy' });
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('in...ts via objects.example.org');
    expect(wrapper.text()).toContain('Needs attention');
    expect(wrapper.text()).toContain('Publication queue');
    expect(wrapper.text()).toContain('Review needed');
    expect(wrapper.text()).toContain('Backups healthy');

    await wrapper.get('button').trigger('click');
    await flushPromises();

    expect(checkStorage).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain('Read and write check passed');
  });

  it('reports email that was given up on, and the retention window', async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('Email delivery');
    expect(wrapper.text()).toContain('Awaiting delivery');
    expect(wrapper.text()).toContain('Given up on');
    // A message nobody received must read as something to act on.
    expect(wrapper.text()).toContain('removed after 30 days');
  });

  it('stays healthy and hides an age when nothing was given up on', async () => {
    getStatus.mockResolvedValue({
      ...baseStatus(),
      email_delivery: {
        pending: 0,
        permanently_failed: 0,
        oldest_pending_at: null,
        retention_days: 30,
      },
    });
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('Email delivery');
    expect(wrapper.text()).toContain('\u2014');
  });

  it('reports what the installation itself last backed up', async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('Backups healthy');
    expect(wrapper.text()).toContain('Last backup');
    expect(wrapper.text()).toContain('Last verified');
    expect(wrapper.text()).toContain('42.5% of the disk used');
    expect(wrapper.find('.recovery-alert').exists()).toBe(false);
  });

  it('warns plainly when no backup could be restored', async () => {
    const status = baseStatus();
    status.recovery = {
      responsibility: 'installation',
      latest_backup_at: null,
      latest_verified_backup_at: null,
      latest_drill_at: null,
      state: 'not_configured',
      jobs: [
        {
          job: 'backup',
          outcome: 'skipped',
          started_at: '2026-09-16T02:00:00Z',
          finished_at: '2026-09-16T02:00:00Z',
          detail: { reason: 'backup_passphrase_not_configured' },
        },
      ],
    };
    getStatus.mockResolvedValue(status);
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('Backups not configured');
    expect(wrapper.get('.recovery-alert').text()).toContain(
      'no backup it could restore from'
    );
    expect(wrapper.text()).toContain('No backup passphrase configured');
    expect(wrapper.text()).toContain('Never');
  });
});
