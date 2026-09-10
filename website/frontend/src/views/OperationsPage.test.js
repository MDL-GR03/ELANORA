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

describe('OperationsPage', () => {
  beforeEach(() => {
    getStatus.mockReset();
    checkStorage.mockReset();
    getStatus.mockResolvedValue({
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
      recovery: {
        responsibility: 'deployment_operator',
        latest_drill_at: null,
        state: 'not_reported',
      },
    });
  });

  it('shows safe status and runs an explicit storage check', async () => {
    checkStorage.mockResolvedValue({ status: 'healthy' });
    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.text()).toContain('in...ts via objects.example.org');
    expect(wrapper.text()).toContain('Needs attention');
    expect(wrapper.text()).toContain('Publication queue');
    expect(wrapper.text()).toContain('Review needed');
    expect(wrapper.text()).toContain('Not reported to ELANORA');

    await wrapper.get('button').trigger('click');
    await flushPromises();

    expect(checkStorage).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain('Read and write check passed');
  });
});
