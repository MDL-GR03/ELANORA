import { toValue } from 'vue';

export function buildNamingStandardPayload(draft, projectId) {
  return {
    name: draft.name.trim(),
    project_id: projectId,
    project_file_type_id: draft.project_file_type_id,
    pattern: draft.pattern,
    description: draft.description.trim(),
    components: draft.components.map((component) => ({
      name: component.name,
      regex: component.regex,
      description: component.description,
      order: component.order,
      accepted_values: component.accepted_values,
      project_file_type_id: draft.project_file_type_id,
    })),
  };
}

export function useNamingStandardMutations({
  projectId,
  draft,
  standards,
  extractionError,
  store,
  confirmAction,
  eventMessages,
  translate,
  clearExampleCache,
  resetDraft,
}) {
  const notify = (key, type, timeout) =>
    eventMessages.addMessage(translate(key), type, timeout);

  async function addStandard() {
    const currentDraft = draft.value;
    const duplicate = toValue(standards).some(
      (standard) =>
        standard.name.trim().toLocaleLowerCase() ===
          currentDraft.name.trim().toLocaleLowerCase() &&
        standard.project_file_type_id === currentDraft.project_file_type_id
    );
    if (duplicate) {
      notify(
        'configureNamingStandards.eventMessages.addFailedDuplicate',
        'error',
        7000
      );
      return false;
    }
    if (
      currentDraft.components.some(
        (component) => !component.regex || !component.regex.trim()
      )
    ) {
      notify(
        'configureNamingStandards.eventMessages.addFailedEmptyRegex',
        'error',
        7000
      );
      return false;
    }
    if (extractionError.value) return false;

    try {
      clearExampleCache();
      await store.addNamingStandard(
        buildNamingStandardPayload(currentDraft, toValue(projectId)),
        toValue(projectId)
      );
      resetDraft();
      notify(
        'configureNamingStandards.eventMessages.addSuccess',
        'success',
        4000
      );
      return true;
    } catch (error) {
      notify(
        error?.response?.status === 409
          ? 'configureNamingStandards.eventMessages.addFailedDuplicate'
          : 'configureNamingStandards.eventMessages.addFailed',
        'error',
        7000
      );
      return false;
    }
  }

  async function deleteStandard(id) {
    const confirmed = await confirmAction({
      message: translate('configureNamingStandards.deleteConfirm'),
      confirmText: translate('common.confirm'),
      tone: 'danger',
      cancelText: translate('common.cancel'),
    });
    if (!confirmed) return false;
    try {
      clearExampleCache();
      await store.deleteNamingStandard(id, toValue(projectId));
      notify(
        'configureNamingStandards.eventMessages.deleteSuccess',
        'success',
        4000
      );
      return true;
    } catch {
      notify(
        'configureNamingStandards.eventMessages.deleteFailed',
        'error',
        7000
      );
      return false;
    }
  }

  return { addStandard, deleteStandard };
}
