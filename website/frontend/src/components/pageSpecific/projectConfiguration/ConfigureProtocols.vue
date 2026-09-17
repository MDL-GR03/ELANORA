<template>
  <section class="protocol-workspace">
    <header class="section-intro">
      <div>
        <span class="eyebrow">{{ t('protocols.eyebrow') }}</span>
        <h3>{{ t('protocols.title') }}</h3>
        <p>{{ t('protocols.introduction') }}</p>
      </div>
      <button class="secondary" type="button" @click="toggleEditor">
        {{
          editor.open.value
            ? t('protocols.close_editor')
            : t('protocols.create')
        }}
      </button>
    </header>

    <ProtocolEditorForm
      v-if="editor.open.value"
      v-model:name="editor.form.name"
      v-model:rules="editor.form.rules"
      :mode="editor.mode.value"
      :saving="editor.saving.value"
      :suggesting="editor.suggesting.value"
      :suggestion="editor.suggestion.value"
      @submit="editor.submit"
      @apply-suggestion="editor.applySuggestion"
      @dismiss-suggestion="editor.suggestion.value = null"
    />

    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <ProtocolVersionList
      :protocols="protocols"
      :loading="loading"
      :scanning="scanning"
      @edit-draft="
        (protocol, version) => editor.start('edit-draft', protocol, version)
      "
      @create-version="
        (protocol, version) => editor.start('create-version', protocol, version)
      "
      @publish="(_, version) => publish(version)"
      @remove-draft="removeDraft"
      @scan="(_, version) => scan(version)"
      @pin="(_, version) => pin(version)"
      @archive="archive"
      @purge="purge"
    />

    <ComplianceScanPanel
      :scan="latestScan"
      :busy="scanning || loading"
      @create-correction="createCorrection"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import { useProtocolEditor } from '@/composables/useProtocolEditor';
import { useProtocolLibrary } from '@/composables/useProtocolLibrary';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useEventMessageStore } from '@/stores/eventMessage';
import ComplianceScanPanel from './ComplianceScanPanel.vue';
import ProtocolEditorForm from './ProtocolEditorForm.vue';
import ProtocolVersionList from './ProtocolVersionList.vue';

const { t } = useI18n();
const route = useRoute();
const messages = useEventMessageStore();
const projectId = computed(() => Number(route.params.projectId));
const notify = (message, type = 'success') =>
  messages.addMessage(message, type, 5000);

const library = useProtocolLibrary({
  projectId,
  translate: t,
  notify,
  confirm: useUserConfirm(),
});
const {
  protocols,
  latestScan,
  loading,
  scanning,
  error,
  load,
  publish,
  archive,
  purge,
  pin,
  scan,
  createCorrection,
} = library;
const editor = useProtocolEditor({
  projectId,
  translate: t,
  notify,
  fail: library.fail,
  onSaved: load,
});

function toggleEditor() {
  if (editor.open.value) editor.close();
  else editor.start('create-protocol');
}

async function removeDraft(protocol, version) {
  const removed = await library.removeDraft(protocol, version);
  if (removed && editor.versionId.value === version.protocol_version_id) {
    editor.close();
  }
}

watch(projectId, load);
onMounted(load);
</script>

<style scoped src="@/assets/css/protocol-workspace.css"></style>

<style scoped>
.protocol-workspace {
  display: grid;
  gap: 1.25rem;
  color: var(--color-slate-900);
}
</style>
