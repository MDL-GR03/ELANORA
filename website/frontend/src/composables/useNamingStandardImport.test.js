import { computed, ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useNamingStandardImport } from './useNamingStandardImport';

describe('useNamingStandardImport', () => {
  let namingApi;
  let fileTypeApi;
  let namingStandardStore;
  let fileTypeStore;
  let eventMessages;
  let clearExampleCache;
  let fileTypes;
  let standards;
  let workflow;

  beforeEach(() => {
    namingApi = {
      getProjectsWithStandards: vi.fn(),
      getProjectNamingStandardsFull: vi.fn(),
      importSelectedStandards: vi.fn(),
    };
    fileTypeApi = {
      getProjectFileTypes: vi.fn(),
      importSelected: vi.fn(),
    };
    namingStandardStore = {
      fetchStandardsAndComponentNames: vi.fn(),
    };
    fileTypeStore = {
      fileTypes: [],
      fetchFileTypes: vi.fn(),
    };
    eventMessages = { addMessage: vi.fn() };
    clearExampleCache = vi.fn();
    fileTypes = ref([
      { id: 101, file_type_id: 5, name: 'ELAN', extension: '.eaf' },
    ]);
    standards = computed(() => [
      { name: 'Corpus name', project_file_type_id: 101 },
    ]);
    workflow = useNamingStandardImport({
      projectId: computed(() => 12),
      standards,
      fileTypes,
      namingStandardStore,
      fileTypeStore,
      eventMessages,
      translate: (key) => `translated:${key}`,
      namingApi,
      fileTypeApi,
      clearExampleCache,
    });
  });

  it('loads source projects while excluding the current project', async () => {
    namingApi.getProjectsWithStandards.mockResolvedValue({
      data: [
        { id: 12, name: 'Current' },
        { id: 20, name: 'Reusable source' },
      ],
    });

    await workflow.startImportFlow();

    expect(workflow.showImportModal.value).toBe(true);
    expect(workflow.importProjectOptions.value).toEqual([
      { value: 20, label: 'Reusable source' },
    ]);
  });

  it('loads standards and file types together for the selected source', async () => {
    workflow.selectedImportProject.value = 20;
    namingApi.getProjectNamingStandardsFull.mockResolvedValue({
      data: { standards: [{ id: 3, name: 'Session naming' }] },
    });
    fileTypeApi.getProjectFileTypes.mockResolvedValue({
      data: [{ id: 201, name: 'ELAN', extension: '.eaf' }],
    });

    await expect(workflow.goToImportStep2()).resolves.toBe(true);

    expect(workflow.importStep.value).toBe(2);
    expect(workflow.importStandards.value).toHaveLength(1);
    expect(workflow.sourceFileTypes.value).toHaveLength(1);
    expect(workflow.isStandardFolded(3)).toBe(true);
  });

  it('detects duplicate standards by stable file type rather than project-local ids', () => {
    expect(workflow.existingStandardKeys.value).toEqual(
      new Set(['Corpus name::5'])
    );
    expect(workflow.existingStandardKeys.value.has('Corpus name::999')).toBe(
      false
    );
  });

  it('imports selected standards then refreshes the target project', async () => {
    workflow.showImportModal.value = true;
    workflow.selectedStandardIds.value = [3, 4];
    namingApi.importSelectedStandards.mockResolvedValue({ data: {} });

    await expect(workflow.importSelectedStandards()).resolves.toBe(true);

    expect(namingApi.importSelectedStandards).toHaveBeenCalledWith({
      target_project_id: 12,
      standard_ids: [3, 4],
    });
    expect(clearExampleCache).toHaveBeenCalledOnce();
    expect(
      namingStandardStore.fetchStandardsAndComponentNames
    ).toHaveBeenCalledWith(12, true);
    expect(workflow.showImportModal.value).toBe(false);
    expect(eventMessages.addMessage).toHaveBeenCalledWith(
      'translated:configureNamingStandards.eventMessages.importSuccessStandard',
      'success',
      undefined
    );
  });

  it('imports a missing file type and reports duplicate conflicts cleanly', async () => {
    workflow.selectedImportProject.value = 20;
    workflow.sourceFileTypes.value = [
      { id: 201, name: 'ELAN', extension: '.eaf' },
    ];
    fileTypeApi.importSelected.mockRejectedValue({ response: { status: 409 } });

    await expect(
      workflow.importMissingFileType({ project_file_type_id: 201 })
    ).resolves.toBe(false);

    expect(fileTypeApi.importSelected).toHaveBeenCalledWith(20, 12, ['ELAN']);
    expect(eventMessages.addMessage).toHaveBeenCalledWith(
      'translated:configureNamingStandards.eventMessages.importFailedDuplicateFileType',
      'error',
      7000
    );
  });
});
