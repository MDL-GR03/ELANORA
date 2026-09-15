// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import ContributionDeclineDialog from './ContributionDeclineDialog.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, values) => (values ? `${key}:${JSON.stringify(values)}` : key),
  }),
}));

function mountDialog(props = {}) {
  return mount(ContributionDeclineDialog, {
    props: { upload: { upload_id: 7 }, busy: false, ...props },
    global: { stubs: { 'font-awesome-icon': true } },
    attachTo: document.body,
  });
}

describe('ContributionDeclineDialog', () => {
  it('renders nothing until a contribution is targeted', () => {
    const wrapper = mountDialog({ upload: null });
    expect(wrapper.find('form').exists()).toBe(false);
    wrapper.unmount();
  });

  it('names the contribution it will decline, in translated text', () => {
    const wrapper = mountDialog();

    expect(wrapper.text()).toContain(
      'contributionWorkspace.decline.eyebrow:{"id":7}'
    );
    expect(wrapper.text()).toContain('contributionWorkspace.decline.warning');
    wrapper.unmount();
  });

  it('requires a meaningful reason before the decision can be submitted', async () => {
    const wrapper = mountDialog();
    const submit = () => wrapper.get('button[type="submit"]');

    expect(submit().attributes('disabled')).toBeDefined();
    await wrapper.get('textarea').setValue('  no  ');
    expect(submit().attributes('disabled')).toBeDefined();
    await wrapper.get('textarea').setValue('Outside the project scope');
    expect(submit().attributes('disabled')).toBeUndefined();
    wrapper.unmount();
  });

  it('emits the trimmed reason for the targeted contribution', async () => {
    const wrapper = mountDialog();

    await wrapper.get('textarea').setValue('  Outside the project scope  ');
    await wrapper.get('form').trigger('submit');

    expect(wrapper.emitted('decline')).toEqual([['Outside the project scope']]);
    wrapper.unmount();
  });

  it('closes on Escape, but not while the decline is being recorded', async () => {
    const wrapper = mountDialog();
    await nextTick();
    const escape = () =>
      wrapper
        .get('form')
        .element.dispatchEvent(
          new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
        );

    escape();
    expect(wrapper.emitted('close')).toHaveLength(1);

    await wrapper.setProps({ busy: true });
    escape();
    await wrapper.get('.close-btn').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(1);
    expect(wrapper.get('button[type="submit"]').text()).toBe(
      'contributionWorkspace.decline.submitting'
    );
    wrapper.unmount();
  });

  it('starts with an empty reason for each contribution', async () => {
    const wrapper = mountDialog();
    await wrapper.get('textarea').setValue('Reason written for number seven');

    await wrapper.setProps({ upload: { upload_id: 8 } });

    expect(wrapper.get('textarea').element.value).toBe('');
    wrapper.unmount();
  });
});
