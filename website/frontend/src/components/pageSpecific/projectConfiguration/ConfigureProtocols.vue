<template>
  <section class="protocol-workspace">
    <header class="section-intro">
      <div>
        <span class="eyebrow">{{ t('protocols.eyebrow') }}</span>
        <h3>{{ t('protocols.title') }}</h3>
        <p>{{ t('protocols.introduction') }}</p>
      </div>
      <button class="secondary" type="button" @click="toggleCreateForm">
        {{ showForm ? t('protocols.close_editor') : t('protocols.create') }}
      </button>
    </header>

    <form
      v-if="showForm"
      class="protocol-form"
      @submit.prevent="submitProtocol"
    >
      <div class="wide">
        <h4>{{ editorTitle }}</h4>
        <p>{{ editorHelp }}</p>
      </div>
      <label class="wide"
        >{{ t('protocols.name')
        }}<input
          v-model.trim="form.name"
          required
          maxlength="150"
          :disabled="editorMode !== 'create-protocol'"
      /></label>
      <div v-if="suggesting" class="suggestion-loading wide">
        {{ t('protocols.analyzing') }}
      </div>
      <CorpusProtocolSuggestion
        v-else-if="corpusSuggestion"
        :suggestion="corpusSuggestion"
        class="wide"
        @apply="applyCorpusSuggestion"
        @close="corpusSuggestion = null"
      />
      <ProtocolRuleBuilder v-model="form.rules" class="wide" />
      <div class="form-actions wide">
        <button :disabled="saving">
          {{ saving ? t('protocols.saving') : editorSubmitLabel }}
        </button>
      </div>
    </form>

    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <div class="protocol-list">
      <div v-if="archivedVersionCount" class="archive-toolbar">
        <span>
          {{
            showArchived
              ? t('protocols.archived_shown', archivedVersionCount)
              : t('protocols.archived_hidden', archivedVersionCount)
          }}
        </span>
        <button
          class="text-button"
          type="button"
          @click="showArchived = !showArchived"
        >
          {{
            showArchived
              ? t('protocols.hide_archived')
              : t('protocols.show_archived')
          }}
        </button>
      </div>
      <article
        v-for="protocol in visibleProtocols"
        :key="protocol.protocol_id"
        class="protocol-card"
      >
        <div class="protocol-title">
          <span class="eyebrow">{{ t('protocols.protocol') }}</span>
          <h4>{{ protocol.name }}</h4>
          <p>{{ protocol.description || t('protocols.no_description') }}</p>
        </div>
        <div
          v-for="version in protocol.versions"
          :key="version.protocol_version_id"
          :class="['version-row', { archived: version.archived_at }]"
        >
          <div class="version-info">
            <span
              ><strong>{{
                t('protocols.version', { number: version.version_number })
              }}</strong
              ><i
                :class="[
                  'status',
                  version.archived_at ? 'archived' : version.status,
                ]"
                >{{
                  t(
                    `protocols.status.${version.archived_at ? 'archived' : version.status}`
                  )
                }}</i
              ></span
            ><small>{{ summarizeRules(version.rules) }}</small>
            <small v-if="version.archive_reason">{{
              t('protocols.archive_reason', { reason: version.archive_reason })
            }}</small>
            <small v-if="version.archived_at" class="archived-copy">
              {{ t('protocols.withdrawn') }}
            </small>
          </div>
          <div class="row-actions">
            <template v-if="version.status === 'draft'">
              <button
                class="secondary"
                type="button"
                @click="editDraft(protocol, version)"
              >
                {{ t('protocols.edit_draft') }}
              </button>
              <button
                type="button"
                @click="publish(version.protocol_version_id)"
              >
                {{ t('protocols.publish') }}
              </button>
              <button
                class="danger"
                type="button"
                @click="removeDraft(protocol, version)"
              >
                {{ t('protocols.delete_draft') }}
              </button>
            </template>
            <template v-else>
              <button
                class="secondary"
                type="button"
                @click="createNextDraft(protocol, version)"
              >
                {{ t('protocols.new_draft_from_version') }}
              </button>
              <button
                v-if="!version.archived_at"
                class="secondary"
                type="button"
                :disabled="scanning"
                @click="scan(version.protocol_version_id)"
              >
                {{ t('protocols.preview_impact') }}
              </button>
              <button
                v-if="version.archived_at"
                class="danger"
                type="button"
                @click="purgeVersion(protocol, version)"
              >
                {{ t('protocols.delete_permanently') }}
              </button>
              <button
                v-if="!version.archived_at"
                type="button"
                @click="pin(version.protocol_version_id)"
              >
                {{ t('protocols.use_for_project') }}
              </button>
              <button
                v-if="!version.archived_at"
                class="danger"
                type="button"
                @click="archiveVersion(protocol, version)"
              >
                {{ t('protocols.archive') }}
              </button>
            </template>
          </div>
        </div>
      </article>
      <div v-if="!loading && !protocols.length" class="empty-state">
        <strong>{{ t('protocols.empty.title') }}</strong>
        <p>{{ t('protocols.empty.description') }}</p>
      </div>
    </div>

    <section class="compliance-panel">
      <header>
        <div>
          <span class="eyebrow">{{ t('protocols.scan.eyebrow') }}</span>
          <h3>{{ t('protocols.scan.title') }}</h3>
        </div>
        <AppSelect
          v-if="latestScan"
          id="protocol-scan-filter"
          v-model="filter"
          size="small"
          :aria-label="t('protocols.scan.filter')"
          :options="scanFilterOptions"
        />
      </header>
      <div v-if="scanning || loading" class="loading-state">
        {{ t('protocols.scan.checking') }}
      </div>
      <template v-else-if="latestScan">
        <div class="summary-grid">
          <div>
            <strong>{{ latestScan.total_files }}</strong
            ><span>{{ t('protocols.scan.files_checked') }}</span>
          </div>
          <div class="passed">
            <strong>{{ latestScan.passed_files }}</strong
            ><span>{{ t('protocols.scan.passed') }}</span>
          </div>
          <div class="failed">
            <strong>{{ latestScan.failed_files }}</strong
            ><span>{{ t('protocols.scan.need_attention') }}</span>
          </div>
          <div>
            <strong>v{{ latestScan.protocol_version_number }}</strong
            ><span>{{ latestScan.protocol_name }}</span>
          </div>
        </div>
        <p class="scan-context">
          {{
            latestScan.trigger === 'preview'
              ? t('protocols.scan.impact_preview')
              : t('protocols.scan.project_scan')
          }}
          · {{ formatDate(latestScan.completed_at || latestScan.started_at) }}
        </p>
        <div class="file-results">
          <details
            v-for="file in visibleFiles"
            :key="file.scan_file_id"
            class="file-result"
          >
            <summary>
              <span
                ><strong>{{ file.filename }}</strong
                ><small>{{ t('protocols.scan.latest_revision') }}</small></span
              ><i :class="['result', file.outcome]">{{
                file.outcome === 'passed'
                  ? t('protocols.scan.passed')
                  : t('protocols.scan.findings', file.issues.length)
              }}</i>
            </summary>
            <div v-if="file.issues.length" class="findings">
              <article v-for="issue in file.issues" :key="issue.issue_number">
                <div>
                  <strong>{{ issue.message }}</strong
                  ><small>{{ friendlyLocation(issue.location) }}</small>
                </div>
                <button
                  class="text-button"
                  type="button"
                  @click="openCorrection(file, issue)"
                >
                  {{ t('protocols.scan.create_correction') }}
                </button>
              </article>
            </div>
            <p v-else class="passed-copy">
              {{ t('protocols.scan.file_passed') }}
            </p>
          </details>
        </div>
      </template>
      <div v-else class="empty-state compact">
        <strong>{{ t('protocols.scan.empty.title') }}</strong>
        <p>{{ t('protocols.scan.empty.description') }}</p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useEventMessageStore } from '@/stores/eventMessage';
import reviewService from '@/api/service/reviewService';
import AppSelect from '@/components/common/AppSelect.vue';
import CorpusProtocolSuggestion from './CorpusProtocolSuggestion.vue';
import ProtocolRuleBuilder from './ProtocolRuleBuilder.vue';
import { countRules, emptyRules, normalizeRules } from '@/utils/protocolRules';

const { t } = useI18n();
const scanFilterOptions = computed(() => [
  { value: 'all', label: t('protocols.scan.all_files') },
  { value: 'failed', label: t('protocols.scan.need_attention') },
  { value: 'passed', label: t('protocols.scan.passed') },
]);
import {
  archiveProtocolVersion,
  createProtocol,
  createProtocolVersion,
  deleteProtocolDraft,
  listComplianceScans,
  listProtocols,
  pinProtocolVersion,
  publishProtocolVersion,
  purgeProtocolVersion,
  runComplianceScan,
  suggestProtocolFromCorpus,
  updateProtocolDraft,
} from '@/api/service/protocolService';

const route = useRoute();
const userConfirm = useUserConfirm();
const eventMessageStore = useEventMessageStore();
const protocols = ref([]);
const scans = ref([]);
const error = ref('');
const loading = ref(true);
const saving = ref(false);
const scanning = ref(false);
const suggesting = ref(false);
const corpusSuggestion = ref(null);
const showForm = ref(false);
const showArchived = ref(false);
const editorMode = ref('create-protocol');
const editedProtocolId = ref(null);
const editedVersionId = ref(null);
const filter = ref('all');
const projectId = computed(() => Number(route.params.projectId));
const archivedVersionCount = computed(() =>
  protocols.value.reduce(
    (total, protocol) =>
      total + protocol.versions.filter((version) => version.archived_at).length,
    0
  )
);
const visibleProtocols = computed(() =>
  protocols.value
    .map((protocol) => ({
      ...protocol,
      versions: showArchived.value
        ? protocol.versions
        : protocol.versions.filter((version) => !version.archived_at),
    }))
    .filter((protocol) => protocol.versions.length)
);
const editorTitle = computed(() => {
  if (editorMode.value === 'edit-draft')
    return t('protocols.editor.edit_title');
  if (editorMode.value === 'create-version')
    return t('protocols.editor.version_title');
  return t('protocols.editor.new_title');
});
const editorHelp = computed(() =>
  editorMode.value === 'edit-draft'
    ? t('protocols.editor.edit_help')
    : editorMode.value === 'create-version'
      ? t('protocols.editor.version_help')
      : t('protocols.editor.new_help')
);
const editorSubmitLabel = computed(() =>
  editorMode.value === 'edit-draft'
    ? t('protocols.editor.save_draft')
    : t('protocols.editor.create_draft')
);
const latestScan = computed(() => scans.value[0] || null);
const visibleFiles = computed(
  () =>
    latestScan.value?.files.filter(
      (file) => filter.value === 'all' || file.outcome === filter.value
    ) || []
);
const form = reactive({ name: '', rules: emptyRules() });
const reasonText = (reason) =>
  reason.response?.data?.detail ||
  reason.message ||
  t('protocols.errors.unexpected');
const notify = (message, type = 'success') =>
  eventMessageStore.addMessage(message, type, 5000);
const resetForm = () => {
  Object.assign(form, {
    name: '',
    rules: emptyRules(),
  });
  editorMode.value = 'create-protocol';
  editedProtocolId.value = null;
  editedVersionId.value = null;
};
const fillRules = (rules) => {
  form.rules = normalizeRules(rules);
};
const toggleCreateForm = () => {
  if (showForm.value) {
    showForm.value = false;
    resetForm();
    return;
  }
  resetForm();
  showForm.value = true;
  if (!corpusSuggestion.value) analyzeCorpus();
};
const analyzeCorpus = async () => {
  suggesting.value = true;
  error.value = '';
  try {
    const { data } = await suggestProtocolFromCorpus(projectId.value);
    corpusSuggestion.value = data;
    notify(
      data.analyzed_files
        ? t('protocols.messages.analyzed', data.analyzed_files)
        : t('protocols.messages.nothing_to_analyze'),
      data.analyzed_files ? 'success' : 'warning'
    );
  } catch (reason) {
    error.value = reasonText(reason);
  } finally {
    suggesting.value = false;
  }
};
const applyCorpusSuggestion = (rules) => {
  form.rules = {
    ...form.rules,
    required_tiers: [
      ...new Set([...form.rules.required_tiers, ...rules.required_tiers]),
    ],
    tier_parents: { ...form.rules.tier_parents, ...rules.tier_parents },
    tier_linguistic_types: {
      ...form.rules.tier_linguistic_types,
      ...rules.tier_linguistic_types,
    },
    required_controlled_vocabularies: [
      ...new Set([
        ...form.rules.required_controlled_vocabularies,
        ...rules.required_controlled_vocabularies,
      ]),
    ],
    media_required: form.rules.media_required || rules.media_required,
    allowed_media_mime_types: [
      ...new Set([
        ...form.rules.allowed_media_mime_types,
        ...rules.allowed_media_mime_types,
      ]),
    ],
  };
  notify(t('protocols.messages.suggestions_added'));
};
const editDraft = (protocol, version) => {
  resetForm();
  editorMode.value = 'edit-draft';
  editedProtocolId.value = protocol.protocol_id;
  editedVersionId.value = version.protocol_version_id;
  form.name = protocol.name;
  fillRules(version.rules);
  showForm.value = true;
  if (!corpusSuggestion.value) analyzeCorpus();
};
const createNextDraft = (protocol, version) => {
  resetForm();
  editorMode.value = 'create-version';
  editedProtocolId.value = protocol.protocol_id;
  form.name = protocol.name;
  fillRules(version.rules);
  showForm.value = true;
  if (!corpusSuggestion.value) analyzeCorpus();
};
const protocolRules = () => structuredClone(form.rules);
const load = async () => {
  loading.value = true;
  error.value = '';
  try {
    const [p, s] = await Promise.all([
      listProtocols(projectId.value),
      listComplianceScans(projectId.value),
    ]);
    protocols.value = p.data;
    scans.value = s.data;
  } catch (reason) {
    error.value = reasonText(reason);
  } finally {
    loading.value = false;
  }
};
const submitProtocol = async () => {
  saving.value = true;
  error.value = '';
  try {
    const rules = protocolRules();
    if (editorMode.value === 'edit-draft') {
      await updateProtocolDraft(projectId.value, editedVersionId.value, {
        rules,
      });
      notify(t('protocols.messages.draft_saved'));
    } else if (editorMode.value === 'create-version') {
      await createProtocolVersion(projectId.value, editedProtocolId.value, {
        rules,
      });
      notify(t('protocols.messages.version_created'));
    } else {
      await createProtocol(projectId.value, { name: form.name, rules });
      notify(t('protocols.messages.draft_created'));
    }
    showForm.value = false;
    resetForm();
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  } finally {
    saving.value = false;
  }
};
const publish = async (id) => {
  try {
    await publishProtocolVersion(projectId.value, id);
    notify(t('protocols.messages.published'));
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const removeDraft = async (protocol, version) => {
  const confirmed = await userConfirm({
    title: t('protocols.confirm.delete_draft.title'),
    message: t('protocols.confirm.delete_draft.message', {
      number: version.version_number,
      name: protocol.name,
    }),
    confirmText: t('protocols.delete_draft'),
    tone: 'danger',
    cancelText: t('protocols.confirm.delete_draft.cancel'),
  });
  if (!confirmed) return;
  try {
    await deleteProtocolDraft(projectId.value, version.protocol_version_id);
    if (editedVersionId.value === version.protocol_version_id) {
      showForm.value = false;
      resetForm();
    }
    notify(t('protocols.messages.draft_deleted'));
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const archiveVersion = async (protocol, version) => {
  const confirmed = await userConfirm({
    title: t('protocols.confirm.archive.title'),
    message: t('protocols.confirm.archive.message', {
      number: version.version_number,
      name: protocol.name,
    }),
    confirmText: t('protocols.confirm.archive.confirm'),
    tone: 'danger',
    cancelText: t('protocols.confirm.archive.cancel'),
  });
  if (!confirmed) return;
  try {
    await archiveProtocolVersion(
      projectId.value,
      version.protocol_version_id,
      'Configuration withdrawn by protocol manager'
    );
    notify(t('protocols.messages.archived'));
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const purgeVersion = async (protocol, version) => {
  const confirmed = await userConfirm({
    title: t('protocols.confirm.purge.title'),
    message: t('protocols.confirm.purge.message', {
      number: version.version_number,
      name: protocol.name,
    }),
    confirmText: t('protocols.delete_permanently'),
    tone: 'danger',
    cancelText: t('protocols.confirm.purge.cancel'),
  });
  if (!confirmed) return;
  error.value = '';
  try {
    await purgeProtocolVersion(projectId.value, version.protocol_version_id);
    notify(t('protocols.messages.purged'));
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const pin = async (id) => {
  try {
    await pinProtocolVersion(projectId.value, id);
    notify(t('protocols.messages.pinned'));
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const scan = async (id) => {
  scanning.value = true;
  error.value = '';
  try {
    const { data } = await runComplianceScan(projectId.value, id, true);
    scans.value = [
      data,
      ...scans.value.filter((item) => item.scan_id !== data.scan_id),
    ];
    notify(
      data.failed_files
        ? t('protocols.messages.scan_attention')
        : t('protocols.messages.scan_passed'),
      data.failed_files ? 'warning' : 'success'
    );
  } catch (reason) {
    error.value = reasonText(reason);
  } finally {
    scanning.value = false;
  }
};
const openCorrection = async (file, issue) => {
  try {
    await reviewService.create(projectId.value, {
      upload_id: null,
      validation_issue_id: issue.validation_issue_id,
      filename: file.filename,
      title: t('protocols.correction.title', { filename: file.filename }),
      initial_comment: t('protocols.correction.comment', {
        message: issue.message,
        location: issue.location,
      }),
    });
    notify(t('protocols.messages.correction_created'));
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const summarizeRules = (rules) => {
  const count = countRules(rules);
  const warnings = Object.keys(rules.severities || {}).length;
  const summary = t('protocols.rule_count', count);
  return warnings
    ? `${summary}, ${t('protocols.warning_count', warnings)}`
    : summary;
};
const friendlyLocation = (location) =>
  location === '/ANNOTATION_DOCUMENT'
    ? t('protocols.scan.document')
    : location.replace('/ANNOTATION_DOCUMENT/', '');
const formatDate = (value) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
watch(projectId, load);
onMounted(load);
</script>

<style scoped>
.protocol-workspace {
  display: grid;
  gap: 1.25rem;
  color: #14213d;
}

.section-intro,
.compliance-panel > header,
.version-row,
.file-result summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

h3,
h4,
p {
  margin: 0;
}

h3 {
  margin-top: 0.25rem;
  font-size: 1.25rem;
}

h4 {
  font-size: 1.05rem;
}

.section-intro p,
.protocol-title p,
small,
.scan-context {
  color: #64748b;
}

.suggestion-loading {
  padding: 1rem;
  border: 1px solid #bfdbfe;
  border-radius: 0.75rem;
  background: #eff6ff;
  color: #1e3a8a;
  text-align: center;
}

.eyebrow {
  color: #2563eb;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

button {
  border: 0;
  border-radius: 0.65rem;
  padding: 0.7rem 1rem;
  background: #2563eb;
  color: #fff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

button:hover {
  background: #1d4ed8;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

button.secondary {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #1e3a8a;
}

button.secondary:hover {
  background: #eff6ff;
}

.protocol-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid #bfdbfe;
  border-radius: 0.9rem;
  background: #f8fbff;
}

.protocol-form label {
  display: grid;
  gap: 0.4rem;
  font-weight: 700;
}

.protocol-form .wide {
  grid-column: 1/-1;
}

input,
textarea,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 0.55rem;
  padding: 0.7rem 0.8rem;
  background: #fff;
  color: inherit;
  font: inherit;
}

textarea {
  min-height: 5rem;
  resize: vertical;
}

.checkbox {
  display: flex !important;
  align-items: center;
}

.checkbox input {
  width: auto;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.message {
  padding: 0.8rem 1rem;
  border-radius: 0.65rem;
}

.error {
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #b91c1c;
}

.protocol-list {
  display: grid;
  gap: 0.8rem;
}

.archive-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.35rem;
  min-height: 2rem;
  color: #64748b;
  font-size: 0.85rem;
}

.archived-copy {
  max-width: 42rem;
  margin-top: 0.2rem;
  color: #475569;
  font-size: 0.82rem;
  line-height: 1.4;
}

.protocol-card,
.compliance-panel {
  border: 1px solid #dbe3ef;
  border-radius: 0.9rem;
  background: #fff;
  overflow: hidden;
}

.protocol-title {
  padding: 1rem 1.1rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.version-row {
  display: grid;
  grid-template-columns: minmax(16rem, 1fr) auto;
  align-items: center;
  padding: 0.9rem 1.1rem;
  border-bottom: 1px solid #edf2f7;
}

.version-row.archived {
  background: #fafbfc;
  box-shadow: inset 3px 0 #cbd5e1;
}

.version-row:last-child {
  border-bottom: 0;
}

.version-info {
  display: grid;
  gap: 0.25rem;
}

.version-info > span {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.status,
.result {
  width: fit-content;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 0.75rem;
  font-style: normal;
  font-weight: 800;
  text-transform: capitalize;
}

.status.draft {
  background: #f1f5f9;
  color: #475569;
}

.status.published,
.result.passed {
  background: #dcfce7;
  color: #166534;
}

.status.archived {
  background: #f1f5f9;
  color: #64748b;
}

.result.failed {
  background: #fee2e2;
  color: #b91c1c;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

button.danger {
  border: 1px solid #fecaca;
  background: #fff;
  color: #b91c1c;
}

button.danger:hover {
  background: #fff1f2;
}

.compliance-panel {
  padding: 1.1rem;
  display: grid;
  gap: 1rem;
}

.compliance-panel select {
  width: auto;
  min-width: 10rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.7rem;
}

.summary-grid div {
  display: grid;
  gap: 0.15rem;
  padding: 0.9rem;
  border-radius: 0.7rem;
  background: #f8fafc;
}

.summary-grid strong {
  font-size: 1.35rem;
}

.summary-grid span {
  color: #64748b;
  font-size: 0.82rem;
}

.summary-grid .passed strong {
  color: #15803d;
}

.summary-grid .failed strong {
  color: #b91c1c;
}

.file-results {
  display: grid;
  gap: 0.55rem;
}

.file-result {
  border: 1px solid #dbe3ef;
  border-radius: 0.7rem;
  overflow: hidden;
}

.file-result summary {
  padding: 0.8rem 1rem;
  cursor: pointer;
  background: #fbfdff;
}

.file-result summary > span {
  display: grid;
  gap: 0.15rem;
}

.findings {
  display: grid;
}

.findings article {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border-top: 1px solid #e2e8f0;
}

.findings article > div {
  display: grid;
  gap: 0.25rem;
}

.text-button {
  padding: 0.25rem;
  background: transparent;
  color: #2563eb;
  white-space: nowrap;
}

.text-button:hover {
  background: transparent;
  color: #1d4ed8;
  text-decoration: underline;
}

.passed-copy,
.empty-state,
.loading-state {
  padding: 1rem;
  color: #64748b;
}

.empty-state {
  text-align: center;
  border: 1px dashed #cbd5e1;
  border-radius: 0.8rem;
}

.empty-state.compact {
  border: 0;
}

@media (width <= 760px) {
  .section-intro,
  .version-row,
  .compliance-panel > header {
    align-items: stretch;
    flex-direction: column;
  }

  .version-row {
    display: flex;
  }

  .protocol-form {
    grid-template-columns: 1fr;
  }

  .protocol-form .wide {
    grid-column: auto;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .row-actions button {
    flex: 1;
  }

  .findings article {
    flex-direction: column;
  }
}
</style>
