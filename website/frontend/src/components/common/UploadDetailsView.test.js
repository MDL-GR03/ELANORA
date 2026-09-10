// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { describe, expect, it } from 'vitest';

import messages from '@/locales/en.json';
import UploadDetailsView from './UploadDetailsView.vue';

describe('UploadDetailsView', () => {
  it('labels modified files correctly and exposes their semantic comparison', async () => {
    const wrapper = mount(UploadDetailsView, {
      props: {
        projectName: 'test',
        upload: {
          upload_id: 6,
          branch_name: 'researcher-contribution',
          merge_status: 'ready_to_merge',
          uploaded_by: 'external.researcher',
          files: {
            new: [],
            modified: ['elan_files/subject-11.eaf'],
            deleted: [],
          },
          quality_checks: { protocol: 'not_configured' },
          research_context: {
            declared_topic_name: 'Prosody',
            summary: 'Reviewed prominence and rhythm.',
            changed_tiers: ['CA:summary1', 'Role1'],
            baseline_changed_tiers: ['Role1'],
            declared_baseline_correction_tiers: ['Role1'],
            outside_scope_tiers: ['CA:summary1'],
            scope_status: 'outside_scope',
          },
        },
      },
      global: {
        plugins: [
          createI18n({
            legacy: false,
            locale: 'en',
            messages: { en: messages },
          }),
        ],
        stubs: {
          FontAwesomeIcon: true,
          ConflictMergeView: {
            props: ['projectName', 'branchName', 'filename', 'fileChangeKind'],
            template:
              '<div class="comparison-stub">{{ projectName }} {{ branchName }} {{ filename }} {{ fileChangeKind }}</div>',
          },
        },
      },
    });

    expect(wrapper.text()).toContain('Modified files');
    expect(wrapper.text()).not.toContain('New Files Only');
    expect(wrapper.text()).toContain('Review annotation changes');
    expect(wrapper.text()).toContain('Prosody');
    expect(wrapper.text()).toContain('Reviewed prominence and rhythm.');
    expect(wrapper.text()).toContain('CA:summary1');
    expect(wrapper.text()).toContain(
      'Some changed tiers are outside the declared topic'
    );
    expect(wrapper.get('.changed-tier-chips .is-outside-scope').text()).toBe(
      'CA:summary1'
    );
    expect(wrapper.get('.changed-tier-chips .is-baseline').text()).toBe(
      'Role1'
    );
    expect(
      wrapper.get('.changed-tier-chips .is-baseline-correction').text()
    ).toBe('Role1');
    expect(wrapper.get('.scope-explanation').text()).toContain(
      'Orange tiers were changed in the uploaded file'
    );

    await wrapper.get('.review-file-button').trigger('click');

    expect(wrapper.get('.comparison-stub').text()).toContain(
      'test researcher-contribution elan_files/subject-11.eaf modified'
    );
  });
});
