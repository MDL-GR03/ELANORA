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
});
