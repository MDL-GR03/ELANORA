<template>
  <div
    id="research-copy-panel"
    class="tier-export-workspace"
    role="tabpanel"
    aria-labelledby="research-copy-tab"
  >
    <div v-if="topicLoadError" class="tiers-operation-error" role="alert">
      {{ topicLoadError }}
    </div>
    <header class="tier-export-intro">
      <div>
        <span class="tier-export-eyebrow">{{
          t('researchScopes.prepare.eyebrow')
        }}</span>
        <h2>{{ t('researchScopes.prepare.title') }}</h2>
        <p>{{ t('researchScopes.prepare.description') }}</p>
      </div>
      <div class="tier-export-safety">
        <font-awesome-icon icon="fa-solid fa-shield-halved" />
        <span>
          <strong>{{ t('researchScopes.prepare.safetyTitle') }}</strong>
          <small>{{ t('researchScopes.prepare.safetyText') }}</small>
        </span>
      </div>
    </header>
    <div v-if="!tierGroups.length" class="tiers-state-panel">
      {{ t('researchScopes.prepare.noFiles') }}
    </div>
    <div v-else class="research-copy-steps">
      <ResearchCopyTopicStep />
      <ResearchCopyFileStep />
      <ResearchCopyTierStep :pending="exportPending" @download="download" />
    </div>
    <div class="tier-export-roundtrip">
      <strong>{{ t('researchScopes.roundtrip.title') }}</strong>
      <span>{{ t('researchScopes.roundtrip.text') }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { exportTierSubset } from '@/api/service/tierService';
import { useEventMessageStore } from '@/stores/eventMessage';
import ResearchCopyFileStep from './ResearchCopyFileStep.vue';
import ResearchCopyTierStep from './ResearchCopyTierStep.vue';
import ResearchCopyTopicStep from './ResearchCopyTopicStep.vue';
import { useResearchCopyContext } from './researchCopyContext';

const props = defineProps({
  projectName: { type: String, required: true },
  topicLoadError: { type: String, default: '' },
});

const { t } = useI18n();
const messages = useEventMessageStore();
const {
  tierGroups,
  selectedGroup,
  selectedTopicId,
  selectedTierNames,
  includedBaselineNames,
  editableBaselineNames,
  canDownload,
} = useResearchCopyContext();
const exportPending = ref(false);

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

async function download() {
  if (!canDownload.value || exportPending.value) return;
  const filename = selectedGroup.value.elan_file_name;
  exportPending.value = true;
  try {
    const response = await exportTierSubset(
      props.projectName,
      filename,
      [...selectedTierNames.value],
      selectedTopicId.value,
      [...includedBaselineNames.value],
      [...editableBaselineNames.value]
    );
    saveBlob(response.data, filename);
    messages.addMessage(t('researchScopes.messages.downloaded'), 'success');
  } catch {
    messages.addMessage(t('researchScopes.messages.downloadFailed'), 'error');
  } finally {
    exportPending.value = false;
  }
}
</script>
