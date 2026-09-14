// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import ContributionCardBody from './ContributionCardBody.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));

const global = {
  stubs: { 'font-awesome-icon': { template: '<span />' } },
};

describe('ContributionCardBody', () => {
  it('summarizes collisions once and links the competing contribution', async () => {
    const wrapper = mount(ContributionCardBody, {
      props: {
        upload: {
          annotation_collisions: [
            {
              contribution_id: 15,
              annotations: { 'elan_files/session.eaf': ['a1', 'a2'] },
            },
            {
              contribution_id: 16,
              annotations: { 'elan_files/session.eaf': ['a1'] },
            },
          ],
        },
      },
      global,
    });

    expect(wrapper.get('.annotation-collision-notice').text()).toContain(
      '2 annotations'
    );
    await wrapper
      .findAll('.annotation-collision-notice button')[1]
      .trigger('click');
    expect(wrapper.emitted('show-contribution')).toEqual([[16]]);
  });

  it('renders revision history, quality evidence, and semantic counts', async () => {
    const previous = {
      upload_id: 20,
      uploaded_at: '2026-09-09T22:40:00Z',
    };
    const wrapper = mount(ContributionCardBody, {
      props: {
        upload: {
          upload_id: 21,
          uploaded_at: '2026-09-09T22:48:00Z',
          version_number: 2,
          version_history: [previous],
          review_case: { title: 'Correct the gloss' },
          quality_checks: { protocol: 'recheck_required' },
          file_counts: { modified: 1 },
          semantic_summary: {
            files: 1,
            annotations: 2,
            value_changed: 2,
          },
        },
      },
      global,
    });

    expect(wrapper.get('.quality-check.recheck-required').text()).toContain(
      'acceptance will recheck'
    );
    expect(wrapper.get('.semantic-recap').text()).toContain(
      '2 annotation changes'
    );
    await wrapper.get('.version-history ol button').trigger('click');
    expect(wrapper.emitted('view-version')[0][0]).toEqual(previous);
  });

  it('shows duplicate, superseded, and conflicted-file evidence', () => {
    const wrapper = mount(ContributionCardBody, {
      props: {
        upload: {
          duplicate_of_upload_id: 4,
          superseded_by_upload_id: 7,
          conflicted_files: ['elan_files/session.eaf'],
          quality_checks: { protocol: 'passed' },
        },
      },
      global,
    });

    expect(wrapper.findAll('.duplicate-notice')).toHaveLength(2);
    expect(wrapper.get('.conflict-file').text()).toBe('elan_files/session.eaf');
    expect(wrapper.get('.quality-check.passed').exists()).toBe(true);
  });
});
