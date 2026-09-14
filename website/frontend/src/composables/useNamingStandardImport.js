import { computed, ref, toValue } from 'vue';

export function useNamingStandardImport({
  projectId,
  standards,
  fileTypes,
  namingStandardStore,
  fileTypeStore,
  eventMessages,
  translate,
  namingApi,
  fileTypeApi,
  clearExampleCache,
}) {
  const showImportModal = ref(false);
  const importStep = ref(1);
  const importProjects = ref([]);
  const selectedImportProject = ref(null);
  const importStandards = ref([]);
  const selectedStandardIds = ref([]);
  const foldedStandardIds = ref(new Set());
  const sourceFileTypes = ref([]);

  const importProjectOptions = computed(() =>
    importProjects.value.map((project) => ({
      value: project.id,
      label: project.name,
    }))
  );
  const targetFileTypeKeys = computed(
    () =>
      new Set(
        fileTypes.value.map((fileType) =>
          [fileType.file_type_id, fileType.name].join(':')
        )
      )
  );
  const existingStandardKeys = computed(
    () =>
      new Set(
        toValue(standards).map((standard) => {
          const projectFileType = fileTypes.value.find(
            (fileType) => fileType.id === standard.project_file_type_id
          );
          return `${standard.name}::${projectFileType?.file_type_id ?? ''}`;
        })
      )
  );

  const notify = (key, type, timeout) =>
    eventMessages.addMessage(translate(key), type, timeout);

  function toggleStandardFold(standardId) {
    if (foldedStandardIds.value.has(standardId))
      foldedStandardIds.value.delete(standardId);
    else foldedStandardIds.value.add(standardId);
  }
  function isStandardFolded(standardId) {
    return foldedStandardIds.value.has(standardId);
  }
  function getSourceFileTypeDisplay(fileTypeId) {
    const fileType = sourceFileTypes.value.find(
      (candidate) => candidate.id === fileTypeId
    );
    return fileType ? `${fileType.name} (${fileType.extension})` : '';
  }
  function getSourceFileTypeNameById(fileTypeId) {
    return (
      sourceFileTypes.value.find((candidate) => candidate.id === fileTypeId)
        ?.name || ''
    );
  }

  async function fetchProjectsWithStandards() {
    const { data } = await namingApi.getProjectsWithStandards();
    importProjects.value = data.filter(
      (project) => project.id !== toValue(projectId)
    );
  }
  async function fetchStandardsForImportProject() {
    const sourceProjectId = selectedImportProject.value;
    const [{ data }, fileTypeResponse] = await Promise.all([
      namingApi.getProjectNamingStandardsFull(sourceProjectId),
      fileTypeApi.getProjectFileTypes(sourceProjectId),
    ]);
    importStandards.value = data.standards || [];
    sourceFileTypes.value = fileTypeResponse.data || [];
    selectedStandardIds.value = [];
    foldedStandardIds.value = new Set(
      importStandards.value.map((standard) => standard.id)
    );
  }
  async function startImportFlow() {
    showImportModal.value = true;
    importStep.value = 1;
    selectedImportProject.value = null;
    importStandards.value = [];
    selectedStandardIds.value = [];
    await fetchProjectsWithStandards();
  }
  async function goToImportStep2() {
    if (!selectedImportProject.value) return false;
    importStep.value = 2;
    await fetchStandardsForImportProject();
    return true;
  }

  async function importMissingFileType(standard) {
    try {
      await fileTypeApi.importSelected(
        selectedImportProject.value,
        toValue(projectId),
        [getSourceFileTypeNameById(standard.project_file_type_id)]
      );
      await fileTypeStore.fetchFileTypes(toValue(projectId));
      fileTypes.value = [...fileTypeStore.fileTypes];
      await fetchStandardsForImportProject();
      notify(
        'configureNamingStandards.eventMessages.importSuccessFileType',
        'success',
        4000
      );
      return true;
    } catch (error) {
      notify(
        error?.response?.status === 409
          ? 'configureNamingStandards.eventMessages.importFailedDuplicateFileType'
          : 'configureNamingStandards.eventMessages.importFailedFileType',
        'error',
        7000
      );
      return false;
    }
  }

  async function importSelectedStandards() {
    if (!selectedStandardIds.value.length) return false;
    try {
      await namingApi.importSelectedStandards({
        target_project_id: toValue(projectId),
        standard_ids: selectedStandardIds.value,
      });
      showImportModal.value = false;
      clearExampleCache();
      await namingStandardStore.fetchStandardsAndComponentNames(
        toValue(projectId),
        true
      );
      notify(
        'configureNamingStandards.eventMessages.importSuccessStandard',
        'success'
      );
      return true;
    } catch (error) {
      notify(
        error?.response?.status === 409
          ? 'configureNamingStandards.eventMessages.importFailedDuplicateStandard'
          : 'configureNamingStandards.eventMessages.importFailedStandard',
        'error',
        7000
      );
      return false;
    }
  }

  return {
    existingStandardKeys,
    fetchProjectsWithStandards,
    fetchStandardsForImportProject,
    foldedStandardIds,
    getSourceFileTypeDisplay,
    getSourceFileTypeNameById,
    goToImportStep2,
    importMissingFileType,
    importProjectOptions,
    importProjects,
    importSelectedStandards,
    importStandards,
    importStep,
    isStandardFolded,
    selectedImportProject,
    selectedStandardIds,
    showImportModal,
    sourceFileTypes,
    startImportFlow,
    targetFileTypeKeys,
    toggleStandardFold,
  };
}
