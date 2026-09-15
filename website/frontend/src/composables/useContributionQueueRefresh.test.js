// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { defineComponent, nextTick, reactive, ref } from 'vue';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  QUEUE_REFRESH_INTERVAL_MS,
  useContributionQueueRefresh,
} from './useContributionQueueRefresh';

function setup({ visible = true, project = { project_id: 1 } } = {}) {
  const route = reactive({ query: {} });
  const projectStore = reactive({
    projects: [],
    setCurrentProject: vi.fn(),
    initBroadcastChannel: vi.fn(),
  });
  const currentProject = ref(project);
  const queue = {
    clear: vi.fn(),
    fetchPendingUploads: vi.fn().mockResolvedValue(),
    fetchReviewCount: vi.fn().mockResolvedValue(),
    loadResearchTopics: vi.fn().mockResolvedValue(),
  };
  const visibility = { visible };
  const Host = defineComponent({
    setup() {
      useContributionQueueRefresh({
        route,
        projectStore,
        currentProject,
        queue,
        isVisible: () => visibility.visible,
      });
      return () => null;
    },
  });
  const wrapper = mount(Host);
  return { route, projectStore, currentProject, queue, visibility, wrapper };
}

describe('useContributionQueueRefresh', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('reloads review cases along with contributions on every refresh', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const { queue, wrapper } = setup();
    queue.fetchPendingUploads.mockClear();
    queue.fetchReviewCount.mockClear();

    await vi.advanceTimersByTimeAsync(QUEUE_REFRESH_INTERVAL_MS);

    expect(queue.fetchPendingUploads).toHaveBeenCalledWith(false);
    expect(queue.fetchReviewCount).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it('does not poll while the page is hidden', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const { queue, visibility, wrapper } = setup({ visible: false });
    queue.fetchPendingUploads.mockClear();
    queue.fetchReviewCount.mockClear();

    await vi.advanceTimersByTimeAsync(QUEUE_REFRESH_INTERVAL_MS * 2);
    expect(queue.fetchPendingUploads).not.toHaveBeenCalled();

    visibility.visible = true;
    await vi.advanceTimersByTimeAsync(QUEUE_REFRESH_INTERVAL_MS);
    expect(queue.fetchReviewCount).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it('stops polling once the page is gone', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const { queue, wrapper } = setup();
    wrapper.unmount();
    queue.fetchPendingUploads.mockClear();

    await vi.advanceTimersByTimeAsync(QUEUE_REFRESH_INTERVAL_MS * 3);

    expect(queue.fetchPendingUploads).not.toHaveBeenCalled();
  });

  it('clears the previous project and loads everything for the next one', async () => {
    const { currentProject, queue, wrapper } = setup();
    queue.clear.mockClear();
    queue.loadResearchTopics.mockClear();

    currentProject.value = { project_id: 2 };
    await nextTick();

    expect(queue.clear).toHaveBeenCalledTimes(1);
    expect(queue.fetchPendingUploads).toHaveBeenLastCalledWith();
    expect(queue.loadResearchTopics).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it('selects the project named in the link once projects are known', async () => {
    const { route, projectStore, wrapper } = setup();
    route.query = { project: '9' };
    projectStore.projects = [{ project_id: 9, project_name: 'linked' }];
    await nextTick();

    expect(projectStore.setCurrentProject).toHaveBeenCalledWith({
      project_id: 9,
      project_name: 'linked',
    });
    wrapper.unmount();
  });
});
