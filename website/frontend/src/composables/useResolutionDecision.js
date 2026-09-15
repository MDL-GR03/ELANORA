import { computed, ref, watch } from 'vue';

export const RESOLUTION_STRATEGIES = Object.freeze({
  incoming: 'accept_incoming',
  current: 'accept_current',
});

const EMPTY_FILES = Object.freeze({ new: [], modified: [], deleted: [] });

/**
 * The administrator's decision on a contribution whose files overlap the
 * accepted project.
 *
 * Every piece of state belongs to one contribution and is cleared when a
 * different one is shown, so a choice acknowledged for one contribution can
 * never be carried over and applied to another.
 */
export function useResolutionDecision(upload) {
  const strategy = ref('');
  const acknowledged = ref(false);
  const comparisons = ref({});
  const selectedFile = ref(null);

  const conflictedFiles = computed(() => upload.value?.conflicted_files || []);

  // Files outside the overlap are applied whichever outcome is chosen.
  const otherFiles = computed(() => {
    const overlapping = new Set(conflictedFiles.value);
    const files = upload.value?.files || EMPTY_FILES;
    const keep = (list) =>
      (list || []).filter((file) => !overlapping.has(file));
    return {
      new: keep(files.new),
      modified: keep(files.modified),
      deleted: keep(files.deleted),
    };
  });
  const otherFileCount = computed(
    () =>
      otherFiles.value.new.length +
      otherFiles.value.modified.length +
      otherFiles.value.deleted.length
  );

  const comparedCount = computed(
    () =>
      conflictedFiles.value.filter((file) => file in comparisons.value).length
  );
  const allCompared = computed(
    () =>
      conflictedFiles.value.length > 0 &&
      comparedCount.value === conflictedFiles.value.length
  );

  // The annotation impact is only stated once every overlapping file has been
  // compared. A count from some of them would understate the decision.
  const impact = computed(() => {
    if (!allCompared.value) return [];
    const counts = new Map();
    for (const file of conflictedFiles.value) {
      for (const change of comparisons.value[file]?.changes || []) {
        for (const kind of change.kinds || []) {
          counts.set(kind, (counts.get(kind) || 0) + 1);
        }
      }
    }
    return [...counts].map(([kind, count]) => ({ kind, count }));
  });

  const canApply = computed(
    () => Boolean(strategy.value) && acknowledged.value
  );

  function choose(nextStrategy) {
    strategy.value = strategy.value === nextStrategy ? '' : nextStrategy;
  }

  function clear() {
    strategy.value = '';
  }

  function recordComparison({ filename, review }) {
    comparisons.value = { ...comparisons.value, [filename]: review };
  }

  function toggleFile(filename) {
    selectedFile.value = selectedFile.value === filename ? null : filename;
  }

  function reset() {
    strategy.value = '';
    acknowledged.value = false;
    comparisons.value = {};
    selectedFile.value = null;
  }

  watch(strategy, () => {
    acknowledged.value = false;
  });
  watch(() => upload.value?.upload_id, reset);

  return {
    strategy,
    acknowledged,
    selectedFile,
    conflictedFiles,
    otherFiles,
    otherFileCount,
    comparedCount,
    allCompared,
    impact,
    canApply,
    choose,
    clear,
    recordComparison,
    toggleFile,
    reset,
  };
}
