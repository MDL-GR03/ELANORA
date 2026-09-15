import { onMounted, onUnmounted, watch } from 'vue';

export const QUEUE_REFRESH_INTERVAL_MS = 30000;

/**
 * Keep the contribution queue current for the selected project.
 *
 * A contribution's displayed status is derived from its review case, so the
 * periodic refresh reloads review cases together with contributions. Otherwise
 * a researcher's resubmission would arrive without the case that links it to
 * its correction thread, and show as an ordinary contribution.
 */
export function useContributionQueueRefresh({
  route,
  projectStore,
  currentProject,
  queue,
  intervalMs = QUEUE_REFRESH_INTERVAL_MS,
  isVisible = () => document.visibilityState === 'visible',
}) {
  let refreshInterval = null;

  watch(
    () => [route.query.project, projectStore.projects.length],
    ([projectId]) => {
      if (!projectId) return;
      const requested = projectStore.projects.find(
        (project) => project.project_id === Number(projectId)
      );
      if (requested) projectStore.setCurrentProject(requested);
    },
    { immediate: true }
  );

  watch(
    () => currentProject.value?.project_id,
    async (newProjectId, oldProjectId) => {
      if (newProjectId === oldProjectId) return;
      queue.clear();
      if (newProjectId) {
        await Promise.all([
          queue.fetchPendingUploads(),
          queue.fetchReviewCount(),
          queue.loadResearchTopics(),
        ]);
      }
    },
    { immediate: true }
  );

  function refreshQuietly() {
    if (!currentProject.value || !isVisible()) return Promise.resolve();
    return Promise.all([
      queue.fetchPendingUploads(false),
      queue.fetchReviewCount(),
    ]);
  }

  onMounted(() => {
    refreshInterval = setInterval(refreshQuietly, intervalMs);
    projectStore.initBroadcastChannel();
  });

  onUnmounted(() => {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = null;
  });

  return { refreshQuietly };
}
