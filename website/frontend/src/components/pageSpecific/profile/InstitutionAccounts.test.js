// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import InstitutionAccounts from './InstitutionAccounts.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, values) => (values ? `${key}:${values.name}` : key),
  }),
}));

const fetchInstitutionAccounts = vi.fn();
const setInstitutionAccountStatus = vi.fn();

vi.mock('@/api/service/userService', () => ({
  fetchInstitutionAccounts: (...args) => fetchInstitutionAccounts(...args),
  setInstitutionAccountStatus: (...args) =>
    setInstitutionAccountStatus(...args),
}));

vi.mock('@/utils/errorDiagnostics', () => ({ reportClientError: vi.fn() }));

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ user: { user_id: 1 } }),
}));

const accounts = [
  {
    user_id: 1,
    username: 'curator',
    email: 'curator@example.org',
    first_name: 'Ada',
    last_name: 'Curator',
    role: 'admin',
    is_active: true,
  },
  {
    user_id: 2,
    username: 'researcher',
    email: 'researcher@example.org',
    first_name: 'Bea',
    last_name: 'Researcher',
    role: 'public',
    is_active: true,
  },
];

function mountPanel() {
  return mount(InstitutionAccounts, {
    global: { stubs: { FontAwesomeIcon: true } },
  });
}

async function mountLoaded() {
  const wrapper = mountPanel();
  await Promise.resolve();
  await wrapper.vm.$nextTick();
  return wrapper;
}

describe('InstitutionAccounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchInstitutionAccounts.mockResolvedValue({ data: { users: accounts } });
  });

  it('lists institution accounts and marks the signed-in administrator', async () => {
    const wrapper = await mountLoaded();

    expect(wrapper.findAll('.account-row')).toHaveLength(2);
    expect(wrapper.text()).toContain('@curator');
    expect(wrapper.text()).toContain('profile.accounts.you');
    // The administrator's own row offers no status control.
    expect(wrapper.findAll('.status-action')).toHaveLength(1);
  });

  it('filters accounts by name, username, or email', async () => {
    const wrapper = await mountLoaded();

    await wrapper.get('input[type="search"]').setValue('researcher@example');

    const rows = wrapper.findAll('.account-row');
    expect(rows).toHaveLength(1);
    expect(rows[0].text()).toContain('@researcher');
  });

  it('requires a reason before a suspension can be confirmed', async () => {
    const wrapper = await mountLoaded();

    await wrapper.get('.status-action').trigger('click');
    const confirm = wrapper.get('.dialog-actions .confirm');
    expect(confirm.attributes('disabled')).toBeDefined();

    await wrapper.get('textarea').setValue('Left the institution');
    expect(
      wrapper.get('.dialog-actions .confirm').attributes('disabled')
    ).toBeUndefined();
  });

  it('suspends an account and reflects the returned status', async () => {
    setInstitutionAccountStatus.mockResolvedValue({
      data: { ...accounts[1], is_active: false },
    });
    const wrapper = await mountLoaded();

    await wrapper.get('.status-action').trigger('click');
    await wrapper.get('textarea').setValue('Left the institution');
    await wrapper.get('.status-dialog').trigger('submit');
    await wrapper.vm.$nextTick();

    expect(setInstitutionAccountStatus).toHaveBeenCalledWith(
      2,
      false,
      'Left the institution'
    );
    expect(wrapper.find('.status-dialog').exists()).toBe(false);
    expect(wrapper.text()).toContain('profile.accounts.suspended');
    expect(wrapper.emitted('show-message')[0][0]).toEqual({
      text: 'profile.accounts.suspended_message',
      type: 'success',
    });
  });

  it('shows the backend refusal inside the dialog and keeps it open', async () => {
    setInstitutionAccountStatus.mockRejectedValue({
      response: {
        data: { detail: 'The institution must retain an active administrator' },
      },
    });
    const wrapper = await mountLoaded();

    await wrapper.get('.status-action').trigger('click');
    await wrapper.get('textarea').setValue('Role handover');
    await wrapper.get('.status-dialog').trigger('submit');
    await wrapper.vm.$nextTick();

    expect(wrapper.get('.dialog-error').text()).toBe(
      'The institution must retain an active administrator'
    );
    expect(wrapper.find('.status-dialog').exists()).toBe(true);
    expect(wrapper.emitted('show-message')).toBeUndefined();
  });

  it('reports a load failure instead of rendering an empty list', async () => {
    fetchInstitutionAccounts.mockRejectedValue(new Error('network'));
    const wrapper = await mountLoaded();

    expect(wrapper.get('.state-message.error').text()).toBe(
      'profile.accounts.load_error'
    );
  });
});
