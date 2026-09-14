// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import AppSelect from './AppSelect.vue';

const global = {
  stubs: { 'font-awesome-icon': { template: '<span />' } },
};

const options = [
  { value: 'oldest', label: 'Oldest first' },
  { value: 'newest', label: 'Newest first' },
];

describe('AppSelect', () => {
  it('selects a styled option and closes the listbox', async () => {
    const wrapper = mount(AppSelect, {
      props: { modelValue: 'oldest', options, id: 'order' },
      global,
    });

    await wrapper.get('.app-select-trigger').trigger('click');
    expect(wrapper.get('[role="listbox"]').isVisible()).toBe(true);
    await wrapper.findAll('[role="option"]')[1].trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([['newest']]);
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false);
  });

  it('supports keyboard navigation and selection', async () => {
    const wrapper = mount(AppSelect, {
      props: { modelValue: 'oldest', options, id: 'order' },
      global,
    });
    const button = wrapper.get('.app-select-trigger');

    await button.trigger('keydown', { key: 'ArrowDown' });
    await button.trigger('keydown', { key: 'ArrowDown' });
    expect(button.attributes('aria-activedescendant')).toBe('order-option-1');
    expect(wrapper.findAll('[role="option"]')[1].classes()).toContain('active');
    await button.trigger('keydown', { key: 'Enter' });

    expect(wrapper.emitted('update:modelValue')).toEqual([['newest']]);
  });

  it('exposes listbox relationships without putting options in the tab order', async () => {
    const wrapper = mount(AppSelect, {
      props: {
        modelValue: 'oldest',
        options,
        id: 'accessible-order',
        ariaLabel: 'Contribution order',
      },
      global,
    });

    const trigger = wrapper.get('.app-select-trigger');
    expect(trigger.attributes('role')).toBe('combobox');
    expect(trigger.attributes('aria-label')).toBe('Contribution order');
    await trigger.trigger('click');

    expect(trigger.attributes('aria-controls')).toBe(
      'accessible-order-options'
    );
    expect(trigger.attributes('aria-activedescendant')).toBe(
      'accessible-order-option-0'
    );
    expect(wrapper.get('[role="listbox"]').attributes('id')).toBe(
      'accessible-order-options'
    );
    expect(
      wrapper
        .findAll('[role="option"]')
        .every((item) => item.attributes('tabindex') === '-1')
    ).toBe(true);
  });

  it('shows a placeholder and does not open while disabled', async () => {
    const wrapper = mount(AppSelect, {
      props: {
        modelValue: '',
        options,
        id: 'disabled-select',
        placeholder: 'Choose one',
        disabled: true,
      },
      global,
    });

    expect(wrapper.get('.app-select-placeholder').text()).toBe('Choose one');
    await wrapper.get('.app-select-trigger').trigger('click');
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false);
  });

  it('skips disabled options during keyboard navigation', async () => {
    const wrapper = mount(AppSelect, {
      props: {
        modelValue: 'oldest',
        options: [
          options[0],
          { ...options[1], disabled: true },
          { value: 'name', label: 'Name' },
        ],
        id: 'disabled-option-select',
      },
      global,
    });
    const button = wrapper.get('.app-select-trigger');

    await button.trigger('keydown', { key: 'ArrowDown' });
    await button.trigger('keydown', { key: 'ArrowDown' });
    await button.trigger('keydown', { key: 'Enter' });

    expect(wrapper.emitted('update:modelValue')).toEqual([['name']]);
  });
});
