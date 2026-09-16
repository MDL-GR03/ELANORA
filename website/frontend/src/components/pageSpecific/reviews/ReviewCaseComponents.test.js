// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { defineComponent, h, reactive, ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

import { englishI18n } from '@/testing/i18n';
import ReviewCaseComposer from './ReviewCaseComposer.vue';
import ReviewCaseDiscussion from './ReviewCaseDiscussion.vue';
import ReviewCaseTaskList from './ReviewCaseTaskList.vue';
import { provideReviewCaseContext } from './reviewCaseContext';

const tasks = Array.from({ length: 25 }, (_, index) => ({
  task_id: `task-${index}`,
  filename: `session-${index}.eaf`,
  instruction: index === 3 ? 'Check the gloss tier' : 'Align the tiers',
  status: 'requested',
}));

function contextFor(overrides = {}) {
  const taskQuery = ref('');
  const visibleTaskLimit = ref(20);
  const filteredTasks = (item) =>
    item.tasks.filter((task) =>
      task.instruction.toLowerCase().includes(taskQuery.value.toLowerCase())
    );
  return {
    activeDiff: ref(''),
    addComment: vi.fn(),
    approveTask: vi.fn(),
    approveTaskLabel: () => 'Accept',
    busy: ref(false),
    canComment: ref(true),
    canManage: ref(false),
    filteredTasks,
    formatDate: () => '16 Sept 2026',
    formatTaskStatus: (status) => status,
    isFinished: () => false,
    isTaskSelectedForRevision: () => false,
    projectName: ref(''),
    replies: reactive({}),
    revisionFeedbackCaseId: ref(''),
    selectRevisionTarget: vi.fn(),
    selectedAnnotationIds: () => [],
    t: englishI18n().global.t,
    taskBusyLabel: (_task, _status, label) => label,
    taskQuery,
    taskStatus: ref(''),
    taskStatusOptions: ref([{ value: '', label: 'All' }]),
    toggleTaskForRevision: vi.fn(),
    unresolvedTaskCount: () => 25,
    visibleTaskLimit,
    visibleTasks: (item) =>
      filteredTasks(item).slice(0, visibleTaskLimit.value),
    ...overrides,
  };
}

function mountWithContext(component, props, context) {
  const Host = defineComponent({
    setup() {
      provideReviewCaseContext(context);
      return () => h(component, props);
    },
  });
  return mount(Host, {
    global: {
      plugins: [englishI18n()],
      stubs: {
        FontAwesomeIcon: true,
        AppSelect: true,
        ConflictMergeView: true,
      },
    },
  });
}

describe('review case components', () => {
  it('refuses to render outside a review panel', () => {
    expect(() =>
      mount(ReviewCaseDiscussion, {
        props: { item: { case_id: 'c', comments: [] } },
        global: { plugins: [englishI18n()] },
      })
    ).toThrow(/review panel/);
  });

  it('shows more tasks and filters them through the shared panel state', async () => {
    const context = contextFor();
    const item = { case_id: 'case-1', state: 'open', tasks };
    const wrapper = mountWithContext(ReviewCaseTaskList, { item }, context);

    expect(wrapper.findAll('.file-task')).toHaveLength(20);
    await wrapper.get('.load-more-tasks').trigger('click');
    expect(context.visibleTaskLimit.value).toBe(40);
    expect(wrapper.findAll('.file-task')).toHaveLength(25);

    await wrapper.get('.file-task-filters input').setValue('gloss');
    expect(context.taskQuery.value).toBe('gloss');
    expect(wrapper.findAll('.file-task')).toHaveLength(1);
  });

  it('posts a reply through the panel', async () => {
    const context = contextFor();
    const item = {
      case_id: 'case-1',
      state: 'open',
      comments: [
        { comment_id: 1, author_name: 'Ada', created_at: 'x', body: 'Hello' },
      ],
    };
    const wrapper = mountWithContext(ReviewCaseDiscussion, { item }, context);

    expect(wrapper.get('.discussion').text()).toContain('Hello');
    await wrapper.get('.reply input').setValue('Thanks');
    expect(context.replies['case-1']).toBe('Thanks');
    await wrapper.get('.reply').trigger('submit');
    expect(context.addComment).toHaveBeenCalledWith(item);
  });

  it('starts a composer from the target it was opened with', () => {
    const wrapper = mount(ReviewCaseComposer, {
      props: {
        filenames: [],
        initialTarget: { title: 'Check A1', annotation_id: 'a1' },
      },
      global: { plugins: [englishI18n()], stubs: { FontAwesomeIcon: true } },
    });

    expect(wrapper.get('input[maxlength="200"]').element.value).toBe(
      'Check A1'
    );
  });
});
