// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { describe, expect, it } from 'vitest';

import messages from '@/locales/en.json';
import ProfileCardHeader from './ProfileCardHeader.vue';

function mountHeader(props) {
  return mount(ProfileCardHeader, {
    props: { title: 'Address Information', ...props },
    slots: { icon: '<svg data-test="icon"></svg>' },
    global: {
      plugins: [
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
    },
  });
}

describe('ProfileCardHeader', () => {
  it('shows the card title and its icon', () => {
    const wrapper = mountHeader();
    expect(wrapper.find('h3').text()).toBe('Address Information');
    expect(wrapper.find('.card-icon [data-test="icon"]').exists()).toBe(true);
  });

  it('offers editing only when the card can be edited', async () => {
    expect(mountHeader().find('button').exists()).toBe(false);

    const wrapper = mountHeader({ editable: true });
    const button = wrapper.find('button.edit-button');
    expect(button.text()).toContain(messages.profile.overview.edit);
    await button.trigger('click');
    expect(wrapper.emitted('edit')).toHaveLength(1);
  });
});
