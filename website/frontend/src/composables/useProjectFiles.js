import { computed, ref } from 'vue';

import gitService from '@/api/service/gitService';
import { useEffectiveStandardStore } from '@/stores/effectiveStandard';
import { useNamingStandardStore } from '@/stores/namingStandard';
import { isFilenameCompliant } from '@/utils/filenameCompliance';
import { getMediaStandardForProject } from '@/utils/filenameFromMediaFile';

const PROJECT_FILES_LOCATION_ID = 1;
const MEDIA_FILES_LOCATION_ID = 3;

function firstStandardId(assignment) {
  if (typeof assignment === 'string' || typeof assignment === 'number') {
    return assignment;
  }
  if (assignment && typeof assignment === 'object') {
    return Object.values(assignment).find(Boolean);
  }
  return undefined;
}

/**
 * The selected project's files and their naming compliance. Compliance is
 * checked only for institution administrators, who are the ones able to
 * rename files; everyone else sees every file as compliant.
 */
export function useProjectFiles({ isAdmin }) {
  const files = ref([]);
  const loaded = ref(false);
  const loading = ref(false);
  const projectStandard = ref(null);
  const mediaStandard = ref(null);
  let latestRequest = 0;

  const hasEffectiveStandard = computed(() => Boolean(projectStandard.value));
  const checksCompliance = computed(
    () => isAdmin.value && hasEffectiveStandard.value
  );
  const nonCompliantFiles = computed(() =>
    checksCompliance.value
      ? files.value.filter((file) => file.isCompliant === false)
      : []
  );

  function complianceOf(name) {
    return checksCompliance.value
      ? isFilenameCompliant(projectStandard.value, name)
      : true;
  }

  function clear() {
    latestRequest += 1;
    files.value = [];
    loaded.value = false;
    loading.value = false;
    projectStandard.value = null;
    mediaStandard.value = null;
  }

  async function load(project) {
    const request = ++latestRequest;
    if (!project?.project_id) {
      clear();
      return;
    }
    const effectiveStandards = useEffectiveStandardStore();
    const namingStandards = useNamingStandardStore();
    loading.value = true;
    try {
      const [listing] = await Promise.all([
        gitService.listProjectFiles(project.project_name, true),
        effectiveStandards.fetchEffectiveStandards(
          project.project_id,
          PROJECT_FILES_LOCATION_ID
        ),
        namingStandards.fetchStandardsAndComponentNames(project.project_id),
        effectiveStandards.fetchEffectiveStandards(
          project.project_id,
          MEDIA_FILES_LOCATION_ID
        ),
      ]);
      const media = await getMediaStandardForProject(
        project.project_id,
        effectiveStandards,
        namingStandards,
        false
      );
      if (request !== latestRequest) return;

      const standardId = firstStandardId(
        effectiveStandards.effectiveStandards[PROJECT_FILES_LOCATION_ID]
      );
      projectStandard.value =
        namingStandards.standards.find((item) => item.id === standardId) ??
        null;
      mediaStandard.value = media;
      files.value = listing.files.map((file) => ({
        ...file,
        isCompliant: complianceOf(file.name),
      }));
      loaded.value = true;
    } finally {
      if (request === latestRequest) loading.value = false;
    }
  }

  /** Apply renames the server accepted without reloading the project. */
  function applyRenames(renames) {
    for (const { elan_id, new_filename } of renames) {
      const file = files.value.find((item) => item.elan_id === elan_id);
      if (!file) continue;
      file.name = new_filename;
      file.isCompliant = complianceOf(new_filename);
    }
  }

  return {
    files,
    loaded,
    loading,
    projectStandard,
    mediaStandard,
    hasEffectiveStandard,
    checksCompliance,
    nonCompliantFiles,
    clear,
    load,
    applyRenames,
  };
}
