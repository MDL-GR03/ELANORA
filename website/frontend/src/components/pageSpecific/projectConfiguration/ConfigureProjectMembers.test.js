// @vitest-environment jsdom

import { mount, flushPromises } from '@vue/test-utils';
import { defineComponent, nextTick } from 'vue';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { addUserToProject } from '@/api/service/projectAssociationService';
import ConfigureProjectMembers from './ConfigureProjectMembers.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { projectId: '42' } }),
}));
vi.mock('@/stores/project', () => ({
  useProjectStore: () => ({ initBroadcastChannel: vi.fn() }),
}));
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ user: { user_id: 1, role: 'admin' } }),
}));
vi.mock('@/stores/eventMessage', () => ({
  useEventMessageStore: () => ({ addMessage: vi.fn() }),
}));
vi.mock('@/composables/useUserConfirm', () => ({
  useUserConfirm: () => vi.fn().mockResolvedValue(true),
}));
vi.mock('@/api/service/projectAssociationService', () => ({
  getProjectUsers: vi.fn().mockResolvedValue({ data: { users: [] } }),
  getAvailableProjectUsers: vi.fn().mockResolvedValue({
    data: {
      users: [
        {
          user_id: 7,
          first_name: 'Ada',
          last_name: 'Lovelace',
          username: 'ada',
          email: 'ada@example.test',
        },
      ],
    },
  }),
  addUserToProject: vi.fn().mockResolvedValue({ data: { user_id: 7 } }),
  updateUserPermission: vi.fn(),
  removeUserFromProject: vi.fn(),
  grantProtocolManager: vi.fn(),
  revokeProtocolManager: vi.fn(),
}));

const AppSelectStub = defineComponent({
  inheritAttrs: false,
  props: { modelValue: { type: [String, Number], default: '' } },
  emits: ['update:modelValue', 'change'],
  template: `
    <button
      type="button"
      v-bind="$attrs"
      @click="$emit('update:modelValue', $attrs.id === 'userId' ? 7 : 'write')"
    >Select</button>
  `,
});

const global = {
  stubs: {
    AppSelect: AppSelectStub,
    'font-awesome-icon': true,
  },
};

afterEach(() => {
  document.body.innerHTML = '';
  vi.clearAllMocks();
});

describe('ConfigureProjectMembers', () => {
  it('opens an accessible modal, contains focus, and returns it on Escape', async () => {
    const wrapper = mount(ConfigureProjectMembers, {
      attachTo: document.body,
      global,
    });
    await flushPromises();

    const opener = wrapper.get('.btn-add-member');
    opener.element.focus();
    await opener.trigger('click');
    await nextTick();

    const dialog = wrapper.get('[role="dialog"]');
    expect(dialog.attributes('aria-labelledby')).toBe('add-member-title');
    expect(dialog.attributes('aria-describedby')).toBe(
      'add-member-description'
    );
    expect(document.activeElement).toBe(dialog.element);

    await dialog.trigger('keydown', { key: 'Escape' });
    await nextTick();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(document.activeElement).toBe(opener.element);
    wrapper.unmount();
  });

  it('requires a researcher and submits the selected access level', async () => {
    const wrapper = mount(ConfigureProjectMembers, { global });
    await flushPromises();
    await wrapper.get('.btn-add-member').trigger('click');
    await flushPromises();

    const submit = wrapper.get('button[type="submit"]');
    expect(submit.attributes()).toHaveProperty('disabled');
    await wrapper.get('#userId').trigger('click');
    await nextTick();
    expect(submit.attributes()).not.toHaveProperty('disabled');

    await wrapper.get('form').trigger('submit');
    await flushPromises();
    expect(addUserToProject).toHaveBeenCalledWith(42, {
      user_id: 7,
      permission: 'read',
    });
  });
});
