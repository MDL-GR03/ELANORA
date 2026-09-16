<template>
  <section class="accepted-history" aria-labelledby="accepted-history-title">
    <header class="history-heading">
      <div>
        <span class="eyebrow">{{ t('acceptedHistory.eyebrow') }}</span>
        <h2 id="accepted-history-title">{{ t('acceptedHistory.title') }}</h2>
        <p>{{ t('acceptedHistory.intro') }}</p>
      </div>
    </header>

    <aside
      v-if="health && health.status !== 'healthy'"
      class="recovery-panel"
      aria-labelledby="recovery-title"
    >
      <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
      <div class="recovery-content">
        <h3 id="recovery-title">{{ t('acceptedHistory.repairTitle') }}</h3>
        <p v-if="health.recoverable">
          {{ t('acceptedHistory.repairRecoverable') }}
        </p>
        <p v-else>{{ t('acceptedHistory.repairUnrecoverable') }}</p>
        <p v-if="health.detail" class="recovery-detail">{{ health.detail }}</p>
        <ul v-if="healthIssues.length" class="health-issues">
          <li v-for="issue in healthIssues" :key="issue.label">
            <strong>{{ issue.label }}</strong>
            <span>{{ issue.files.join(', ') }}</span>
          </li>
        </ul>
        <template v-if="health.recoverable">
          <div class="confirmation-grid">
            <label>
              {{ t('acceptedHistory.recoveryReason') }}
              <textarea
                v-model="recoveryReason"
                rows="2"
                :placeholder="t('acceptedHistory.recoveryReasonPlaceholder')"
              ></textarea>
            </label>
            <label>
              <i18n-t keypath="acceptedHistory.typeToConfirm" tag="span">
                <template #phrase>
                  <strong>RECOVER {{ projectName }}</strong>
                </template>
              </i18n-t>
              <input
                v-model="recoveryConfirmation"
                :placeholder="`RECOVER ${projectName}`"
              />
            </label>
          </div>
          <button
            type="button"
            class="danger-button"
            :disabled="!canRecover || busy"
            @click="recover"
          >
            {{ t('acceptedHistory.recover') }}
          </button>
        </template>
      </div>
    </aside>

    <div v-if="loading" class="history-state">
      {{ t('acceptedHistory.loading') }}
    </div>
    <div v-else-if="error" class="history-state error-state">{{ error }}</div>
    <ol v-else class="version-list">
      <li
        v-for="version in history.versions"
        :key="version.commit"
        class="version-row"
      >
        <div class="version-marker" aria-hidden="true"></div>
        <article :class="['version-card', { current: version.is_current }]">
          <div class="version-summary">
            <div>
              <span v-if="version.is_current" class="current-badge">{{
                t('acceptedHistory.current')
              }}</span>
              <span
                v-else-if="version.action === 'project.version.restored'"
                class="restore-badge"
                >{{ t('acceptedHistory.restoration') }}</span
              >
              <h3>{{ version.message }}</h3>
              <p>
                <code>{{ version.short_commit }}</code>
                <span>· {{ formatDate(version.committed_at) }}</span>
                <span>· {{ version.author }}</span>
                <span v-if="version.contribution_id"
                  >·
                  {{
                    t('acceptedHistory.contribution', {
                      id: version.contribution_id,
                    })
                  }}</span
                >
              </p>
              <p v-if="version.reason" class="version-reason">
                {{ t('acceptedHistory.reason', { reason: version.reason }) }}
              </p>
            </div>
            <button
              v-if="!version.is_current"
              type="button"
              class="preview-button"
              :disabled="busy"
              @click="preview(version)"
            >
              {{ t('acceptedHistory.previewRestore') }}
            </button>
          </div>

          <div
            v-if="selected?.commit === version.commit && previewData"
            class="restore-preview"
          >
            <div class="preview-title">
              <div>
                <h4>{{ t('acceptedHistory.previewTitle') }}</h4>
                <p>
                  {{
                    t('acceptedHistory.previewSummary', {
                      files: t(
                        'acceptedHistory.fileChanges',
                        previewData.files.length
                      ),
                      annotations: t(
                        'acceptedHistory.annotationChanges',
                        previewData.semantic_summary.annotations
                      ),
                    })
                  }}
                </p>
              </div>
              <button type="button" class="text-button" @click="closePreview">
                {{ t('acceptedHistory.close') }}
              </button>
            </div>

            <ul v-if="previewData.files.length" class="changed-files">
              <li
                v-for="file in previewData.files"
                :key="`${file.status}-${file.filename}`"
              >
                <span>{{ fileStatus(file.status) }}</span
                ><code>{{ file.filename }}</code>
              </li>
            </ul>

            <div class="impact-warning">
              <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
              <div>
                <strong>{{ t('acceptedHistory.openWorkTitle') }}</strong>
                <p>{{ openWorkSummary }}</p>
              </div>
            </div>

            <div class="confirmation-grid">
              <label>
                {{ t('acceptedHistory.administrativeReason') }}
                <textarea
                  v-model="reason"
                  rows="3"
                  :placeholder="
                    t('acceptedHistory.administrativeReasonPlaceholder')
                  "
                ></textarea>
              </label>
              <label>
                <i18n-t keypath="acceptedHistory.typeToConfirm" tag="span">
                  <template #phrase>
                    <strong>RESTORE {{ projectName }}</strong>
                  </template>
                </i18n-t>
                <input
                  v-model="confirmation"
                  :placeholder="`RESTORE ${projectName}`"
                />
              </label>
            </div>
            <div class="restore-actions">
              <p>{{ t('acceptedHistory.restoreNote') }}</p>
              <button
                type="button"
                class="danger-button"
                :disabled="!canRestore || busy"
                @click="restore"
              >
                {{ t('acceptedHistory.restore') }}
              </button>
            </div>
          </div>
        </article>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import gitService from '@/api/service/gitService.js';
import { useEventMessageStore } from '@/stores/eventMessage.js';

const props = defineProps({ projectName: { type: String, required: true } });
const emit = defineEmits(['restored']);
const eventMessages = useEventMessageStore();
const { t, locale } = useI18n();
const history = ref({ current_commit: '', versions: [] });
const health = ref(null);
const selected = ref(null);
const previewData = ref(null);
const reason = ref('');
const confirmation = ref('');
const recoveryReason = ref('');
const recoveryConfirmation = ref('');
const loading = ref(false);
const busy = ref(false);
const error = ref('');
const canRestore = computed(
  () =>
    reason.value.trim().length >= 10 &&
    confirmation.value === `RESTORE ${props.projectName}`
);
const canRecover = computed(
  () =>
    recoveryReason.value.trim().length >= 10 &&
    recoveryConfirmation.value === `RECOVER ${props.projectName}`
);
const healthIssues = computed(() => {
  if (!health.value) return [];
  return [
    ['missingFiles', health.value.missing_files],
    ['unexpectedFiles', health.value.unexpected_files],
    ['changedContents', health.value.checksum_mismatches],
    ['missingRecords', health.value.database_missing_files],
    ['unexpectedRecords', health.value.database_unexpected_files],
    ['recordMismatches', health.value.database_checksum_mismatches],
  ]
    .filter(([, files]) => files?.length)
    .map(([key, files]) => ({
      label: t(`acceptedHistory.issues.${key}`),
      files,
    }));
});
const openWorkSummary = computed(() => {
  const data = previewData.value;
  if (!data) return '';
  const ids = data.affected_pending_upload_ids.length
    ? ` (#${data.affected_pending_upload_ids.join(', #')})`
    : '';
  return t('acceptedHistory.openWork', {
    submissions: t(
      'acceptedHistory.openSubmissions',
      data.affected_pending_contributions
    ),
    ids,
    cases: t('acceptedHistory.activeCases', data.active_review_cases),
  });
});
// Git reports a status letter, sometimes followed by a similarity score.
function fileStatus(status) {
  const letter = String(status).charAt(0);
  return ['A', 'M', 'D', 'R', 'C'].includes(letter)
    ? t(`acceptedHistory.fileStatus.${letter}`)
    : status;
}

function apiError(value) {
  return (
    apiErrorMessage(value, t, value)?.message ||
    t('acceptedHistory.requestFailed')
  );
}
function formatDate(value) {
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
function closePreview() {
  selected.value = null;
  previewData.value = null;
  reason.value = '';
  confirmation.value = '';
}
async function loadHistory() {
  loading.value = true;
  error.value = '';
  closePreview();
  try {
    history.value = await gitService.getAcceptedProjectHistory(
      props.projectName
    );
  } catch (value) {
    error.value = apiError(value);
  } finally {
    loading.value = false;
  }
}
async function loadHealth() {
  health.value = await gitService.getCurrentProjectRevisionHealth(
    props.projectName
  );
}
async function loadAll() {
  try {
    await Promise.all([loadHistory(), loadHealth()]);
  } catch (value) {
    error.value = apiError(value);
  }
}
async function preview(version) {
  busy.value = true;
  error.value = '';
  closePreview();
  selected.value = version;
  try {
    previewData.value = await gitService.previewProjectVersionRestore(
      props.projectName,
      version.commit
    );
  } catch (value) {
    error.value = apiError(value);
    eventMessages.addMessage(error.value, 'error');
  } finally {
    busy.value = false;
  }
}
async function restore() {
  if (!canRestore.value) return;
  busy.value = true;
  try {
    await gitService.restoreProjectVersion(props.projectName, {
      target_commit: selected.value.commit,
      expected_head: previewData.value.current_commit,
      reason: reason.value.trim(),
      confirmation: confirmation.value,
    });
    eventMessages.addMessage(t('acceptedHistory.restored'), 'success');
    await loadHistory();
    emit('restored');
  } catch (value) {
    error.value = apiError(value);
    eventMessages.addMessage(error.value, 'error');
  } finally {
    busy.value = false;
  }
}

async function recover() {
  if (!canRecover.value) return;
  busy.value = true;
  try {
    await gitService.recoverCurrentProjectRevision(props.projectName, {
      revision_id: health.value.revision_id,
      reason: recoveryReason.value.trim(),
      confirmation: recoveryConfirmation.value,
    });
    recoveryReason.value = '';
    recoveryConfirmation.value = '';
    eventMessages.addMessage(t('acceptedHistory.recovered'), 'success');
    await loadAll();
    emit('restored');
  } catch (value) {
    error.value = apiError(value);
    eventMessages.addMessage(error.value, 'error');
  } finally {
    busy.value = false;
  }
}

watch(() => props.projectName, loadAll);
onMounted(loadAll);
</script>

<style scoped>
.accepted-history {
  padding: 1.25rem 0;
}

.history-heading,
.version-summary,
.preview-title,
.restore-actions {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.history-heading {
  padding: 0 0 1.25rem;
  border-bottom: 1px solid #d9e2ef;
}

.history-heading h2 {
  margin: 0.25rem 0;
}

.history-heading p,
.version-summary p,
.restore-actions p {
  margin: 0;
  color: #60718c;
}

.recovery-panel {
  display: flex;
  gap: 0.9rem;
  margin: 1.25rem 0 0;
  padding: 1rem;
  border: 1px solid #dfa93f;
  border-left: 4px solid #b86f00;
  border-radius: 0.7rem;
  background: #fff9e9;
  color: #684300;
}

.recovery-panel > svg {
  margin-top: 0.2rem;
}

.recovery-content {
  flex: 1;
  min-width: 0;
}

.recovery-content h3,
.recovery-content p {
  margin: 0 0 0.45rem;
}

.health-issues {
  margin: 0.8rem 0;
  padding: 0;
  list-style: none;
  border: 1px solid #ecd7aa;
  border-radius: 0.5rem;
  background: rgb(255 255 255 / 65%);
}

.health-issues li {
  display: grid;
  grid-template-columns: minmax(10rem, 0.35fr) 1fr;
  gap: 0.75rem;
  padding: 0.55rem 0.7rem;
  border-bottom: 1px solid #eee1c5;
}

.health-issues li:last-child {
  border-bottom: 0;
}

.health-issues span {
  overflow-wrap: anywhere;
}

.eyebrow {
  color: #1f62ea;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
}

.secondary-button,
.preview-button,
.text-button,
.danger-button {
  border-radius: 0.55rem;
  padding: 0.7rem 1rem;
  cursor: pointer;
  font: inherit;
}

.secondary-button,
.preview-button {
  background: #fff;
  border: 1px solid #9bb9ed;
  color: #174eaa;
}

.text-button {
  padding: 0.25rem;
  border: 0;
  background: transparent;
  color: #225fc8;
}

.danger-button {
  border: 1px solid #a33a2d;
  background: #a33a2d;
  color: #fff;
  font-weight: 700;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.version-list {
  margin: 0;
  padding: 1.25rem 0 0 1.25rem;
  list-style: none;
  border-left: 2px solid #d8e5fa;
}

.version-row {
  position: relative;
  margin-bottom: 1rem;
}

.version-marker {
  position: absolute;
  left: -1.65rem;
  top: 1.35rem;
  width: 0.7rem;
  height: 0.7rem;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #6f8fbf;
  box-shadow: 0 0 0 2px #b8cae6;
}

.version-card {
  border: 1px solid #d6e0ed;
  border-radius: 0.75rem;
  background: #fff;
  padding: 1rem;
}

.version-card.current {
  border-color: #61ae7d;
  background: #f6fcf8;
}

.version-card h3 {
  margin: 0.35rem 0;
  font-size: 1rem;
}

.version-summary p {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  font-size: 0.82rem;
}

.current-badge,
.restore-badge {
  display: inline-block;
  border-radius: 999px;
  padding: 0.25rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 700;
}

.current-badge {
  background: #dff5e7;
  color: #126937;
}

.restore-badge {
  background: #e8eefb;
  color: #294f92;
}

.version-reason {
  margin-top: 0.45rem !important;
}

.restore-preview {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #d9e2ef;
}

.restore-preview h4 {
  margin: 0 0 0.2rem;
}

.changed-files {
  max-height: 13rem;
  overflow: auto;
  margin: 1rem 0;
  padding: 0;
  list-style: none;
  border: 1px solid #dde5ef;
  border-radius: 0.5rem;
}

.changed-files li {
  display: grid;
  grid-template-columns: 3rem 1fr;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #edf1f6;
}

.changed-files li:last-child {
  border-bottom: 0;
}

.changed-files span {
  color: #9a5b00;
  font-weight: 800;
}

.impact-warning {
  display: flex;
  gap: 0.75rem;
  padding: 0.9rem;
  border: 1px solid #e9bd67;
  border-radius: 0.55rem;
  background: #fff9e9;
  color: #694400;
}

.impact-warning p {
  margin: 0.25rem 0 0;
}

.confirmation-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.confirmation-grid label {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  color: #34445e;
  font-weight: 650;
}

.confirmation-grid input,
.confirmation-grid textarea {
  box-sizing: border-box;
  width: 100%;
  padding: 0.7rem;
  border: 1px solid #b9c7da;
  border-radius: 0.5rem;
  font: inherit;
}

.restore-actions {
  align-items: center;
  margin-top: 1rem;
}

.history-state {
  padding: 2rem;
  text-align: center;
  color: #60718c;
}

.error-state {
  color: #a12b21;
}

@media (width <= 720px) {
  .health-issues li {
    grid-template-columns: 1fr;
    gap: 0.15rem;
  }

  .history-heading,
  .version-summary,
  .preview-title,
  .restore-actions {
    flex-direction: column;
  }

  .confirmation-grid {
    grid-template-columns: 1fr;
  }

  .secondary-button,
  .preview-button,
  .danger-button {
    width: 100%;
  }

  .version-list {
    padding-left: 0.85rem;
  }

  .version-marker {
    left: -1.28rem;
  }
}
</style>
