import { computed, reactive, ref, watch } from 'vue';

const FILES_PER_PAGE = 10;

export function useReviewCaseDraft(filenames = []) {
  let taskChangeSequence = 0;
  const fileQuery = ref('');
  const filePage = ref(1);
  const activeFilename = ref('');

  function newTaskChange() {
    taskChangeSequence += 1;
    return {
      id: taskChangeSequence,
      instruction: '',
      tier_id: '',
      annotation_id: '',
      start_ms: null,
      end_ms: null,
      current_text: '',
      suggested_text: '',
    };
  }

  const taskDrafts = reactive(
    filenames.map((filename) => ({
      filename,
      selected: false,
      changes: [newTaskChange()],
    }))
  );
  const draft = reactive({
    title: '',
    filename: '',
    tier_id: null,
    annotation_id: null,
    start_ms: null,
    end_ms: null,
    initial_comment: '',
    current_text: '',
    suggested_text: '',
  });

  const selectedFileCount = computed(
    () => taskDrafts.filter((task) => task.selected).length
  );
  const filteredTaskDrafts = computed(() => {
    const needle = fileQuery.value.trim().toLocaleLowerCase();
    return taskDrafts.filter(
      (task) => !needle || task.filename.toLocaleLowerCase().includes(needle)
    );
  });
  const filePageCount = computed(() =>
    Math.max(1, Math.ceil(filteredTaskDrafts.value.length / FILES_PER_PAGE))
  );
  const visibleTaskDrafts = computed(() => {
    const start = (filePage.value - 1) * FILES_PER_PAGE;
    return filteredTaskDrafts.value.slice(start, start + FILES_PER_PAGE);
  });
  const hasSelectedTasks = computed(() => {
    const selected = taskDrafts.filter((task) => task.selected);
    return (
      selected.length > 0 &&
      selected.every(
        (task) =>
          task.changes.length > 0 &&
          task.changes.every((change) => Boolean(change.instruction.trim()))
      )
    );
  });

  function buildPayload({ uploadId = null, requestChanges = false } = {}) {
    return {
      upload_id: uploadId,
      request_changes: requestChanges,
      title: draft.title,
      filename: draft.filename || null,
      tier_id: draft.tier_id,
      annotation_id: draft.annotation_id,
      start_ms: draft.start_ms,
      end_ms: draft.end_ms,
      initial_comment: draft.initial_comment || null,
      current_text: draft.current_text || null,
      suggested_text: draft.suggested_text || null,
      tasks: taskDrafts
        .filter((task) => task.selected)
        .flatMap((task) =>
          task.changes.map((change) => ({
            filename: task.filename,
            instruction: change.instruction,
            tier_id: change.tier_id || null,
            annotation_id: change.annotation_id || null,
            start_ms: change.start_ms ?? null,
            end_ms: change.end_ms ?? null,
            current_text: change.current_text || null,
            suggested_text: change.suggested_text || null,
          }))
        ),
    };
  }

  function resetDraft() {
    Object.assign(draft, {
      title: '',
      filename: '',
      tier_id: null,
      annotation_id: null,
      start_ms: null,
      end_ms: null,
      initial_comment: '',
      current_text: '',
      suggested_text: '',
    });
    for (const task of taskDrafts) {
      task.selected = false;
      task.changes.splice(0, task.changes.length, newTaskChange());
    }
    activeFilename.value = '';
    fileQuery.value = '';
    filePage.value = 1;
  }

  function addTaskChange(task) {
    task.changes.push(newTaskChange());
  }
  function selectTask(task) {
    if (task.selected) activeFilename.value = task.filename;
    else if (activeFilename.value === task.filename) activeFilename.value = '';
  }
  function removeTaskChange(task, changeId) {
    const index = task.changes.findIndex((change) => change.id === changeId);
    if (index !== -1 && task.changes.length > 1) task.changes.splice(index, 1);
  }

  watch(fileQuery, () => {
    filePage.value = 1;
  });
  watch(filePageCount, (count) => {
    if (filePage.value > count) filePage.value = count;
  });

  return {
    activeFilename,
    addTaskChange,
    buildPayload,
    draft,
    filePage,
    filePageCount,
    fileQuery,
    filteredTaskDrafts,
    hasSelectedTasks,
    removeTaskChange,
    resetDraft,
    selectedFileCount,
    selectTask,
    taskDrafts,
    visibleTaskDrafts,
  };
}
