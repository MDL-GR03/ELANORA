import { computed, ref } from 'vue';

import { useEffectiveStandardStore } from '@/stores/effectiveStandard';
import { useNamingStandardStore } from '@/stores/namingStandard';
import { standardAt } from '@/utils/effectiveStandard';
import { isFilenameCompliant } from '@/utils/filenameCompliance';

const UPLOAD_LOCATION_ID = 4;

/**
 * The naming standard uploads to a project must follow. When it cannot be
 * loaded, uploading pauses rather than letting files through unchecked.
 */
export function useUploadStandard() {
  const standard = ref(null);
  const loading = ref(false);
  const failed = ref(false);
  let latestRequest = 0;

  const hasStandard = computed(() => Boolean(standard.value));

  function clear() {
    latestRequest += 1;
    standard.value = null;
    loading.value = false;
    failed.value = false;
  }

  async function load(projectId) {
    const request = ++latestRequest;
    if (!projectId) {
      clear();
      return true;
    }
    const effectiveStandards = useEffectiveStandardStore();
    const namingStandards = useNamingStandardStore();
    loading.value = true;
    failed.value = false;
    try {
      await Promise.all([
        effectiveStandards.fetchEffectiveStandards(
          projectId,
          UPLOAD_LOCATION_ID
        ),
        namingStandards.fetchStandardsAndComponentNames(projectId),
      ]);
      if (request !== latestRequest) return true;
      standard.value = standardAt(
        effectiveStandards.effectiveStandards,
        namingStandards.standards,
        UPLOAD_LOCATION_ID
      );
      return true;
    } catch {
      if (request !== latestRequest) return true;
      standard.value = null;
      failed.value = true;
      return false;
    } finally {
      if (request === latestRequest) loading.value = false;
    }
  }

  function isCompliant(filename) {
    return !standard.value || isFilenameCompliant(standard.value, filename);
  }

  return { standard, hasStandard, loading, failed, clear, load, isCompliant };
}
