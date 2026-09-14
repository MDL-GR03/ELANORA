// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { describe, expect, it, vi } from 'vitest';

import ProjectShareModal from './ProjectShareModal.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));
vi.mock('@stores/eventMessage', () => ({
  useEventMessageStore: () => ({ addMessage: vi.fn() }),
}));
vi.mock('@/api/service/invitationService', () => ({
  sendInvitation: vi.fn(),
}));
vi.mock('@/api/service/projectAssociationService', () => ({
  getAvailableProjectUsers: vi.fn().mockResolvedValue({ data: { users: [] } }),
}));

const global = {
  stubs: {
    'font-awesome-icon': true,
    AppSelect: { template: '<button type="button">Select</button>' },
  },
};

describe('ProjectShareModal', () => {
  it('contains focus and restores it after closing', async () => {
    const opener = document.createElement('button');
    document.body.append(opener);
    opener.focus();
    const wrapper = mount(ProjectShareModal, {
      attachTo: document.body,
      props: { show: false, projectName: 'Corpus', projectId: 1 },
      global,
    });

    await wrapper.setProps({ show: true });
    await nextTick();
    expect(document.activeElement).toBe(wrapper.get('[role="dialog"]').element);

    await wrapper.get('[role="dialog"]').trigger('keydown', { key: 'Escape' });
    expect(wrapper.emitted('close')).toHaveLength(1);
    await wrapper.setProps({ show: false });
    await nextTick();
    expect(document.activeElement).toBe(opener);

    wrapper.unmount();
    opener.remove();
  });

  it('links invitation tabs to panels and supports arrow navigation', async () => {
    const wrapper = mount(ProjectShareModal, {
      attachTo: document.body,
      props: { show: true, projectName: 'Corpus', projectId: 1 },
      global,
    });
    await nextTick();
    const emailTab = wrapper.get('#invite-by-email-tab');

    expect(emailTab.attributes('aria-controls')).toBe('invite-by-email-panel');
    expect(wrapper.get('#invite-by-email-panel').attributes('role')).toBe(
      'tabpanel'
    );
    await emailTab.trigger('keydown', { key: 'ArrowRight' });
    await nextTick();

    expect(
      wrapper.get('#invite-existing-user-tab').attributes('aria-selected')
    ).toBe('true');
    expect(wrapper.get('#invite-existing-user-panel').exists()).toBe(true);
    wrapper.unmount();
  });
});
