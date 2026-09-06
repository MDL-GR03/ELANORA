<template>
  <section class="protocol-workspace">
    <header class="section-intro">
      <div>
        <span class="eyebrow">Research protocol</span>
        <h3>Define rules, preview their impact, then activate them</h3>
        <p>
          Published versions are immutable. Impact scans inspect every latest
          accepted ELAN revision without changing research data.
        </p>
      </div>
      <button class="secondary" type="button" @click="toggleCreateForm">
        {{ showForm ? 'Close editor' : 'Create protocol' }}
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
        >Protocol name<input
          v-model.trim="form.name"
          required
          maxlength="150"
          :disabled="editorMode !== 'create-protocol'"
      /></label>
      <div v-if="suggesting" class="suggestion-loading wide">
        Analyzing the latest accepted ELAN files for useful starting points…
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
          {{ saving ? 'Saving…' : editorSubmitLabel }}
        </button>
      </div>
    </form>

    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <div class="protocol-list">
      <div v-if="archivedVersionCount" class="archive-toolbar">
        <span>
          {{ archivedVersionCount }} archived version{{
            archivedVersionCount === 1 ? '' : 's'
          }}
          {{ showArchived ? 'shown' : 'hidden' }}
        </span>
        <button
          class="text-button"
          type="button"
          @click="showArchived = !showArchived"
        >
          {{ showArchived ? 'Hide archived' : 'Show archived' }}
        </button>
      </div>
      <article
        v-for="protocol in visibleProtocols"
        :key="protocol.protocol_id"
        class="protocol-card"
      >
        <div class="protocol-title">
          <span class="eyebrow">Protocol</span>
          <h4>{{ protocol.name }}</h4>
          <p>{{ protocol.description || 'No description provided.' }}</p>
        </div>
        <div
          v-for="version in protocol.versions"
          :key="version.protocol_version_id"
          :class="['version-row', { archived: version.archived_at }]"
        >
          <div class="version-info">
            <span
              ><strong>Version {{ version.version_number }}</strong
              ><i
                :class="[
                  'status',
                  version.archived_at ? 'archived' : version.status,
                ]"
                >{{ version.archived_at ? 'archived' : version.status }}</i
              ></span
            ><small>{{ summarizeRules(version.rules) }}</small>
            <small v-if="version.archive_reason"
              >Reason: {{ version.archive_reason }}</small
            >
            <small v-if="version.archived_at" class="archived-copy">
              This version is withdrawn. It cannot be activated or used for a
              new scan.
            </small>
          </div>
          <div class="row-actions">
            <template v-if="version.status === 'draft'">
              <button
                class="secondary"
                type="button"
                @click="editDraft(protocol, version)"
              >
                Edit draft
              </button>
              <button
                type="button"
                @click="publish(version.protocol_version_id)"
              >
                Publish
              </button>
              <button
                class="danger"
                type="button"
                @click="removeDraft(protocol, version)"
              >
                Delete draft
              </button>
            </template>
            <template v-else>
              <button
                class="secondary"
                type="button"
                @click="createNextDraft(protocol, version)"
              >
                New draft from this version
              </button>
              <button
                v-if="!version.archived_at"
                class="secondary"
                type="button"
                :disabled="scanning"
                @click="scan(version.protocol_version_id)"
              >
                Preview impact
              </button>
              <button
                v-if="version.archived_at"
                class="danger"
                type="button"
                @click="purgeVersion(protocol, version)"
              >
                Delete permanently
              </button>
              <button
                v-if="!version.archived_at"
                type="button"
                @click="pin(version.protocol_version_id)"
              >
                Use for project
              </button>
              <button
                v-if="!version.archived_at"
                class="danger"
                type="button"
                @click="archiveVersion(protocol, version)"
              >
                Archive
              </button>
            </template>
          </div>
        </div>
      </article>
      <div v-if="!loading && !protocols.length" class="empty-state">
        <strong>No research protocol yet</strong>
        <p>
          Create a draft when the project is ready to formalize its conventions.
        </p>
      </div>
    </div>

    <section class="compliance-panel">
      <header>
        <div>
          <span class="eyebrow">Corpus compliance</span>
          <h3>Latest impact scan</h3>
        </div>
        <select
          v-if="latestScan"
          v-model="filter"
          aria-label="Filter scan files"
        >
          <option value="all">All files</option>
          <option value="failed">Needs attention</option>
          <option value="passed">Passed</option>
        </select>
      </header>
      <div v-if="scanning || loading" class="loading-state">
        Checking accepted ELAN revisions…
      </div>
      <template v-else-if="latestScan">
        <div class="summary-grid">
          <div>
            <strong>{{ latestScan.total_files }}</strong
            ><span>Files checked</span>
          </div>
          <div class="passed">
            <strong>{{ latestScan.passed_files }}</strong
            ><span>Passed</span>
          </div>
          <div class="failed">
            <strong>{{ latestScan.failed_files }}</strong
            ><span>Need attention</span>
          </div>
          <div>
            <strong>v{{ latestScan.protocol_version_number }}</strong
            ><span>{{ latestScan.protocol_name }}</span>
          </div>
        </div>
        <p class="scan-context">
          {{
            latestScan.trigger === 'preview' ? 'Impact preview' : 'Project scan'
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
                ><small>Latest accepted revision</small></span
              ><i :class="['result', file.outcome]">{{
                file.outcome === 'passed'
                  ? 'Passed'
                  : `${file.issues.length} finding(s)`
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
                  Create correction
                </button>
              </article>
            </div>
            <p v-else class="passed-copy">
              This file respects every rule in this protocol version.
            </p>
          </details>
        </div>
      </template>
      <div v-else class="empty-state compact">
        <strong>No scan has been run</strong>
        <p>
          Publish a protocol version, then preview its effect on the corpus.
        </p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useEventMessageStore } from '@/stores/eventMessage';
import reviewService from '@/api/service/reviewService';
import CorpusProtocolSuggestion from './CorpusProtocolSuggestion.vue';
import ProtocolRuleBuilder from './ProtocolRuleBuilder.vue';
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
  if (editorMode.value === 'edit-draft') return 'Edit protocol draft';
  if (editorMode.value === 'create-version') return 'New protocol version';
  return 'New protocol draft';
});
const editorHelp = computed(() =>
  editorMode.value === 'edit-draft'
    ? 'Correct this draft freely. Nothing is enforced until you publish and activate it.'
    : editorMode.value === 'create-version'
      ? 'The published version remains unchanged; your corrections become a new draft.'
      : 'Start with the conventions that are meaningful for this corpus.'
);
const editorSubmitLabel = computed(() =>
  editorMode.value === 'edit-draft' ? 'Save draft' : 'Create draft'
);
const latestScan = computed(() => scans.value[0] || null);
const visibleFiles = computed(
  () =>
    latestScan.value?.files.filter(
      (file) => filter.value === 'all' || file.outcome === filter.value
    ) || []
);
const form = reactive({
  name: '',
  rules: {
    required_tiers: [],
    tier_parents: {},
    tier_linguistic_types: {},
    required_controlled_vocabularies: [],
    media_required: false,
    allowed_media_mime_types: [],
  },
});
const emptyRules = () => ({
  required_tiers: [],
  tier_parents: {},
  tier_linguistic_types: {},
  required_controlled_vocabularies: [],
  media_required: false,
  allowed_media_mime_types: [],
});
const reasonText = (reason) =>
  reason.response?.data?.detail || reason.message || 'Unexpected error';
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
  form.rules = {
    ...emptyRules(),
    ...structuredClone(rules),
  };
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
        ? `Analyzed ${data.analyzed_files} accepted ELAN file(s). Review the suggested rules.`
        : 'No accepted ELAN revisions are available for protocol suggestions.',
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
  notify('Selected corpus suggestions added to the draft below.');
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
      notify('Draft changes saved.');
    } else if (editorMode.value === 'create-version') {
      await createProtocolVersion(projectId.value, editedProtocolId.value, {
        rules,
      });
      notify('New draft version created.');
    } else {
      await createProtocol(projectId.value, { name: form.name, rules });
      notify('Protocol draft created.');
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
    notify('Version published and locked.');
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const removeDraft = async (protocol, version) => {
  const confirmed = await userConfirm({
    title: 'Delete protocol draft?',
    message: `Version ${version.version_number} of ${protocol.name} has not been published. Deleting it is permanent.`,
    confirmText: 'Delete draft',
    cancelText: 'Keep draft',
  });
  if (!confirmed) return;
  try {
    await deleteProtocolDraft(projectId.value, version.protocol_version_id);
    if (editedVersionId.value === version.protocol_version_id) {
      showForm.value = false;
      resetForm();
    }
    notify('Draft deleted.');
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const archiveVersion = async (protocol, version) => {
  const confirmed = await userConfirm({
    title: 'Archive published version?',
    message: `Version ${version.version_number} of ${protocol.name} will remain in the audit history but cannot be activated or used for new scans.`,
    confirmText: 'Archive version',
    cancelText: 'Keep version',
  });
  if (!confirmed) return;
  try {
    await archiveProtocolVersion(
      projectId.value,
      version.protocol_version_id,
      'Configuration withdrawn by protocol manager'
    );
    notify('Published version archived.');
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const purgeVersion = async (protocol, version) => {
  const confirmed = await userConfirm({
    title: 'Permanently delete this version?',
    message: `Version ${version.version_number} of ${protocol.name} and its disposable preview results will be removed. This is allowed only if it was never activated or used for research validation.`,
    confirmText: 'Delete permanently',
    cancelText: 'Keep archived',
  });
  if (!confirmed) return;
  error.value = '';
  try {
    await purgeProtocolVersion(projectId.value, version.protocol_version_id);
    notify('Unused protocol version permanently deleted.');
    await load();
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const pin = async (id) => {
  try {
    await pinProtocolVersion(projectId.value, id);
    notify(
      'Project protocol updated. Preview its impact to review the corpus.'
    );
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
        ? 'Impact scan complete. Review the files that need attention.'
        : 'Impact scan complete. Every file passed.',
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
      title: `Protocol correction: ${file.filename}`,
      initial_comment: `${issue.message}\n\nLocation: ${issue.location}`,
    });
    notify('Correction created in Contributions.');
  } catch (reason) {
    error.value = reasonText(reason);
  }
};
const summarizeRules = (rules) => {
  const count =
    (rules.required_tiers?.length || 0) +
    Object.keys(rules.tier_parents || {}).length +
    Object.keys(rules.tier_linguistic_types || {}).length +
    (rules.required_controlled_vocabularies?.length || 0) +
    (rules.media_required ? 1 : 0) +
    (rules.allowed_media_mime_types?.length || 0);
  return `${count} configured rule${count === 1 ? '' : 's'}`;
};
const friendlyLocation = (location) =>
  location === '/ANNOTATION_DOCUMENT'
    ? 'ELAN document'
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
