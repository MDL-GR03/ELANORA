// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { describe, expect, it } from 'vitest';

import messages from '@/locales/en.json';
import ProjectCard from './ProjectCard.vue';
import ProjectComplianceBanner from './ProjectComplianceBanner.vue';
import SelectedProjectOverview from './SelectedProjectOverview.vue';

const global = {
  plugins: [
    createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
  ],
  stubs: { FontAwesomeIcon: true },
};

describe('ProjectCard', () => {
  it('shows only permitted actions and does not select through them', async () => {
    const wrapper = mount(ProjectCard, {
      props: { project: { project_name: 'Corpus' }, canShare: true },
      global,
    });
    expect(wrapper.findAll('.project-card-action-btn')).toHaveLength(1);
    await wrapper.get('.share').trigger('click');
    expect(wrapper.emitted('share')).toHaveLength(1);
    expect(wrapper.emitted('select')).toBeUndefined();
    await wrapper.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('select')).toHaveLength(1);
  });
});

describe('ProjectComplianceBanner', () => {
  it('offers bulk renaming only when files break the standard', async () => {
    const wrapper = mount(ProjectComplianceBanner, {
      props: { hasStandard: true, nonCompliantCount: 2 },
      global,
    });
    expect(wrapper.classes()).toContain('info-banner-noncompliant');
    await wrapper.get('.info-banner-bulk-rename-link').trigger('click');
    expect(wrapper.emitted('bulk-rename')).toHaveLength(1);

    await wrapper.setProps({ hasStandard: false });
    expect(wrapper.find('.info-banner-bulk-rename-link').exists()).toBe(false);
    await wrapper.get('.info-banner-link').trigger('click');
    expect(wrapper.emitted('configure')).toHaveLength(1);
  });
});

describe('SelectedProjectOverview', () => {
  it('collapses a long description until expanded', async () => {
    const wrapper = mount(SelectedProjectOverview, {
      props: {
        project: {
          project_id: 1,
          project_name: 'Corpus',
          project_description: 'x'.repeat(200),
        },
      },
      global,
    });
    const description = wrapper.get('.project-selected-description');
    expect(description.classes()).toContain(
      'project-selected-description--collapsed'
    );
    await wrapper.get('.project-description-toggle').trigger('click');
    expect(description.classes()).not.toContain(
      'project-selected-description--collapsed'
    );
  });
});
