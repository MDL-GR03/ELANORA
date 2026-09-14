// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import HelpTooltip from './HelpTooltip.vue';

describe('HelpTooltip', () => {
  it('connects a keyboard-focusable help control to accessible content', () => {
    const wrapper = mount(HelpTooltip, {
      props: {
        label: 'Explain consistency',
        title: 'Consistency',
        text: 'Files containing the tier agree on its relationship.',
      },
    });

    const trigger = wrapper.get('button');
    const tooltip = wrapper.get('[role="tooltip"]');
    expect(trigger.attributes('aria-label')).toBe('Explain consistency');
    expect(trigger.attributes('aria-describedby')).toBe(
      tooltip.attributes('id')
    );
    expect(tooltip.text()).toContain('Files containing the tier agree');
  });

  it('supports touch-style toggling and Escape dismissal', async () => {
    const wrapper = mount(HelpTooltip, {
      props: {
        label: 'Explain consistency',
        text: 'Files containing the tier agree on its relationship.',
      },
    });
    const trigger = wrapper.get('button');

    await trigger.trigger('click');
    expect(wrapper.classes()).toContain('open');
    await trigger.trigger('keydown', { key: 'Escape' });
    expect(wrapper.classes()).not.toContain('open');
  });
});
