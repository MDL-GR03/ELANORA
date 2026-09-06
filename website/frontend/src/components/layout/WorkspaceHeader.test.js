// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import WorkspaceHeader from './WorkspaceHeader.vue';

describe('WorkspaceHeader', () => {
  it('renders the page hierarchy and optional actions semantically', () => {
    const wrapper = mount(WorkspaceHeader, {
      props: {
        context: 'LSFB',
        title: 'Projects',
        description: 'Manage linguistic research projects.',
      },
      slots: {
        actions: '<button type="button">Create project</button>',
      },
    });

    expect(wrapper.element.tagName).toBe('HEADER');
    expect(wrapper.findAll('h1')).toHaveLength(1);
    expect(wrapper.get('h1').text()).toBe('Projects');
    expect(wrapper.text()).toContain('LSFB');
    expect(wrapper.get('button').text()).toBe('Create project');
  });
});
