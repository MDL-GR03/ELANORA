// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  getDataGovernance,
  saveDataGovernance,
} from '@/api/service/governanceService';
import { englishI18n } from '@/testing/i18n';
import ConfigureDataGovernance from './ConfigureDataGovernance.vue';

vi.mock('@/api/service/governanceService', () => ({
  getDataGovernance: vi.fn(),
  saveDataGovernance: vi.fn(),
}));
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { projectId: '7' } }),
}));

const unclassified = {
  data_classification: null,
  legal_basis: null,
  retention_days: null,
  legal_hold: false,
  legal_hold_reason: null,
  updated_at: null,
  updated_by: null,
};

async function render(recorded = unclassified) {
  getDataGovernance.mockResolvedValue({ data: recorded });
  const wrapper = mount(ConfigureDataGovernance, {
    global: { plugins: [englishI18n()] },
  });
  await flushPromises();
  return wrapper;
}

const submit = (wrapper) => wrapper.get('button[type="submit"]');

describe('ConfigureDataGovernance', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows an unclassified project kept until someone decides', async () => {
    const wrapper = await render();

    expect(getDataGovernance).toHaveBeenCalledWith(7);
    expect(wrapper.text()).toContain('Not classified yet');
    expect(wrapper.get('.check input').element.checked).toBe(true);
    expect(wrapper.find('input[type="number"]').exists()).toBe(false);
  });

  it('requires a legal basis before sensitive personal data can be saved', async () => {
    const wrapper = await render();

    await wrapper.get('input[value="sensitive_personal"]').setValue(true);
    expect(submit(wrapper).attributes('disabled')).toBeDefined();
    expect(wrapper.get('textarea').attributes('aria-invalid')).toBe('true');

    await wrapper.get('textarea').setValue('  Consent series LSFB-2026  ');
    expect(submit(wrapper).attributes('disabled')).toBeUndefined();
  });

  it('saves a retention period and a legal hold with its reason', async () => {
    saveDataGovernance.mockImplementation((_id, payload) =>
      Promise.resolve({
        data: { ...payload, updated_at: '2026-09-16T08:30:00+00:00' },
      })
    );
    const wrapper = await render();

    await wrapper.get('input[value="internal"]').setValue(true);
    await wrapper.findAll('.check input')[0].setValue(false);
    await wrapper.get('input[type="number"]').setValue(90);
    await wrapper.findAll('.check input')[1].setValue(true);
    expect(submit(wrapper).attributes('disabled')).toBeDefined();
    await wrapper.findAll('textarea')[1].setValue('Audit 2026-17');
    await wrapper.get('form').trigger('submit');
    await flushPromises();

    expect(saveDataGovernance).toHaveBeenCalledWith(7, {
      data_classification: 'internal',
      legal_basis: null,
      retention_days: 90,
      legal_hold: true,
      legal_hold_reason: 'Audit 2026-17',
    });
    expect(wrapper.text()).toContain('Data governance saved.');
    expect(wrapper.text()).toContain('Last changed');
  });

  it('refuses a retention period shorter than thirty days', async () => {
    const wrapper = await render({ ...unclassified, retention_days: 60 });

    await wrapper.get('input[type="number"]').setValue(10);

    expect(submit(wrapper).attributes('disabled')).toBeDefined();
  });

  it('reports a failed save without losing the form', async () => {
    saveDataGovernance.mockRejectedValue(new Error('offline'));
    const wrapper = await render();

    await wrapper.get('input[value="public"]').setValue(true);
    await wrapper.get('form').trigger('submit');
    await flushPromises();

    expect(wrapper.get('.state.error').text()).toContain('could not be saved');
    expect(wrapper.get('input[value="public"]').element.checked).toBe(true);
  });
});
