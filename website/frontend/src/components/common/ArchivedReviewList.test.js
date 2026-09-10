// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import ArchivedReviewList from './ArchivedReviewList.vue';

const archivedCase = (index) => ({
  case_id: 'case-' + index,
  title: 'Correction ' + index,
  state: index % 2 ? 'closed' : 'resolved',
  filename: 'elan_files/session-' + index + '.eaf',
  upload_id: index,
  resubmitted_upload_id: index + 100,
  assignee_name: 'Review Lead',
  updated_at: '2026-09-08T10:00:00Z',
  resolved_at: '2026-09-08T10:00:00Z',
  tasks: [
    {
      task_id: 'task-' + index,
      filename: 'elan_files/session-' + index + '.eaf',
      instruction: 'Check topic ' + index,
      status: 'accepted',
    },
  ],
  comments: [],
});

describe('ArchivedReviewList', () => {
  it('keeps large histories compact, searchable, and paginated', async () => {
    const wrapper = mount(ArchivedReviewList, {
      props: {
        cases: Array.from({ length: 10 }, (_, index) =>
          archivedCase(index + 1)
        ),
      },
      global: {
        stubs: { FontAwesomeIcon: true },
      },
    });

    expect(wrapper.findAll('.archive-item')).toHaveLength(8);
    expect(wrapper.text()).toContain('Page 1 of 2');

    await wrapper.get('input[type="search"]').setValue('topic 10');

    expect(wrapper.findAll('.archive-item')).toHaveLength(1);
    expect(wrapper.text()).toContain('Correction 10');
    expect(wrapper.text()).not.toContain('Page 1 of 2');
  });

  it('opens a deep-linked archived review on its correct page', async () => {
    const wrapper = mount(ArchivedReviewList, {
      props: {
        cases: Array.from({ length: 10 }, (_, index) =>
          archivedCase(index + 1)
        ),
        highlightedCaseId: 'case-10',
      },
      global: {
        stubs: { FontAwesomeIcon: true },
      },
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Page 2 of 2');
    expect(
      wrapper.get('#archived-review-case-10').attributes('open')
    ).toBeDefined();
    expect(wrapper.get('#archived-review-case-10').classes()).toContain(
      'highlighted'
    );
  });

  it('names a successful content-identical correction explicitly', () => {
    const item = archivedCase(2);
    item.resubmitted_upload_status = 'no_changes';
    const wrapper = mount(ArchivedReviewList, {
      props: { cases: [item] },
      global: { stubs: { FontAwesomeIcon: true } },
    });

    expect(wrapper.get('.archive-state').text()).toBe(
      'Approved · no project changes'
    );
  });
});
