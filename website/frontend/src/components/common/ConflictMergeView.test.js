// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { defineComponent } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ConflictMergeView from './ConflictMergeView.vue';

const getEafReview = vi.fn();

vi.mock('@/api/service/gitService', () => ({
  default: { getEafReview: (...args) => getEafReview(...args) },
}));

function deferred() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function reviewWith(count, prefix, tier = `${prefix}-tier`) {
  return {
    changes: Array.from({ length: count }, (_, index) => ({
      annotation_id: `${prefix}${index + 1}`,
      kinds: ['value_changed'],
      before: { tier_id: tier, value: `${prefix} before ${index}` },
      after: { tier_id: tier, value: `${prefix} after ${index}` },
    })),
    before_media_urls: [],
    after_media_urls: [],
  };
}

function mountView(filename = 'a.eaf') {
  return mount(ConflictMergeView, {
    props: { projectName: 'corpus', branchName: 'contribution', filename },
    global: { stubs: { 'font-awesome-icon': true } },
    attachTo: document.body,
  });
}

describe('ConflictMergeView', () => {
  beforeEach(() => {
    getEafReview.mockReset();
    document.body.innerHTML = '';
  });

  it('never shows or reports a slow response under a later file', async () => {
    const first = deferred();
    const second = deferred();
    getEafReview
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const wrapper = mountView('a.eaf');
    await flushPromises();

    await wrapper.setProps({ filename: 'b.eaf' });
    second.resolve(reviewWith(1, 'B'));
    await flushPromises();
    // The comparison requested first, for a.eaf, arrives last.
    first.resolve(reviewWith(1, 'A'));
    await flushPromises();

    expect(wrapper.text()).toContain('B1');
    expect(wrapper.text()).not.toContain('A1');
    const loaded = wrapper.emitted('loaded') || [];
    expect(loaded).toHaveLength(1);
    expect(loaded[0][0].filename).toBe('b.eaf');
    expect(loaded[0][0].review.changes[0].annotation_id).toBe('B1');
  });

  it('starts a newly opened file at its first page', async () => {
    getEafReview
      .mockResolvedValueOnce(reviewWith(60, 'A'))
      .mockResolvedValueOnce(reviewWith(10, 'B'));
    const wrapper = mountView('a.eaf');
    await flushPromises();
    const next = () =>
      wrapper
        .findAll('.change-pagination button')
        .find((button) => button.text() === 'Next');
    await next().trigger('click');
    await next().trigger('click');
    expect(wrapper.get('.result-summary').text()).toContain('51–60 of 60');

    await wrapper.setProps({ filename: 'b.eaf' });
    await flushPromises();

    expect(wrapper.get('.result-summary').text()).toContain('1–10 of 10');
    expect(wrapper.findAll('.annotation-change')).toHaveLength(10);
  });

  it('does not carry a search from one file into the next', async () => {
    getEafReview
      .mockResolvedValueOnce(reviewWith(3, 'A'))
      .mockResolvedValueOnce(reviewWith(3, 'B'));
    const wrapper = mountView('a.eaf');
    await flushPromises();
    await wrapper.get('input[type="search"]').setValue('A2');
    expect(wrapper.findAll('.annotation-change')).toHaveLength(1);

    await wrapper.setProps({ filename: 'b.eaf' });
    await flushPromises();

    expect(wrapper.get('input[type="search"]').element.value).toBe('');
    expect(wrapper.findAll('.annotation-change')).toHaveLength(3);
  });

  it('gives each comparison its own filter control identifiers', async () => {
    getEafReview.mockResolvedValue(reviewWith(2, 'A'));
    // Two comparisons in one application, as the review panel can render.
    const Page = defineComponent({
      components: { ConflictMergeView },
      template: `<div>
          <ConflictMergeView project-name="corpus" branch-name="c" filename="a.eaf" />
          <ConflictMergeView project-name="corpus" branch-name="c" filename="b.eaf" />
        </div>`,
    });
    const wrapper = mount(Page, {
      global: { stubs: { 'font-awesome-icon': true } },
      attachTo: document.body,
    });
    await flushPromises();

    const labels = [...document.querySelectorAll('label[for^="conflict-"]')];
    const ids = labels.map((label) => label.htmlFor);
    expect(ids).toHaveLength(4);
    expect(new Set(ids).size).toBe(4);
    for (const id of ids) {
      expect(document.querySelectorAll(`[id="${id}"]`)).toHaveLength(1);
    }
    wrapper.unmount();
  });
});
