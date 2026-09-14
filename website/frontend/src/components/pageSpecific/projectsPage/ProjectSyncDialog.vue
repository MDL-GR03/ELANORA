<template>
  <div
    v-if="visible"
    class="sync-backdrop"
    role="presentation"
    @mousedown.self="closeDialog"
  >
    <dialog
      ref="dialogElement"
      class="sync-dialog"
      open
      aria-modal="true"
      aria-labelledby="sync-title"
    >
      <header class="sync-header">
        <div class="sync-icon" aria-hidden="true">
          <font-awesome-icon icon="fa-solid fa-arrows-rotate" />
        </div>
        <div>
          <span class="sync-eyebrow">{{
            t('projectsPage.syncDialog.eyebrow')
          }}</span>
          <h2 id="sync-title">{{ t('projectsPage.syncDialog.title') }}</h2>
          <p>
            {{
              t('projectsPage.syncDialog.description', { project: projectName })
            }}
          </p>
        </div>
        <button
          ref="closeButton"
          type="button"
          class="sync-close"
          :aria-label="t('common.close')"
          :disabled="actionLoading"
          @click="closeDialog"
        >
          <font-awesome-icon icon="fa-solid fa-xmark" />
        </button>
      </header>

      <main class="sync-body" aria-live="polite">
        <div v-if="loading" class="sync-state">
          <span class="sync-spinner"></span
          ><strong>{{ t('projectsPage.syncDialog.checkingStatus') }}</strong>
        </div>

        <div
          v-else-if="syncState === 'missing'"
          class="sync-callout danger"
          role="alert"
        >
          <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
          <div>
            <strong>{{ t('projectsPage.syncDialog.missingTitle') }}</strong>
            <p>{{ missingMessage }}</p>
          </div>
        </div>

        <template v-else-if="syncState === 'out_of_sync'">
          <div class="sync-callout warning">
            <font-awesome-icon icon="fa-solid fa-file-circle-plus" />
            <div>
              <strong>{{
                t('projectsPage.syncDialog.detectedChanges')
              }}</strong>
              <p>
                {{
                  t('projectsPage.syncDialog.changeCount', {
                    count: syncChanges.length,
                  })
                }}
              </p>
            </div>
          </div>
          <div class="sync-safety">
            <strong>{{ t('projectsPage.syncDialog.safetyTitle') }}</strong>
            <p>{{ t('projectsPage.syncDialog.safetyDescription') }}</p>
          </div>
          <div class="sync-list" role="list">
            <article
              v-for="change in sortedChanges"
              :key="`${change.status}:${change.filename}`"
              class="sync-change"
              role="listitem"
            >
              <img src="/images/icons/ELAN.svg" alt="" />
              <span class="sync-name" :title="change.filename">{{
                change.filename
              }}</span>
              <span
                class="sync-status"
                :class="`status-${normalizedStatus(change)}`"
                >{{ statusLabel(change) }}</span
              >
            </article>
          </div>
        </template>

        <div
          v-else-if="syncState === 'error'"
          class="sync-callout danger"
          role="alert"
        >
          <font-awesome-icon icon="fa-solid fa-circle-xmark" />
          <div>
            <strong>{{ t('projectsPage.syncDialog.checkFailed') }}</strong>
            <p>{{ syncError }}</p>
          </div>
        </div>

        <div
          v-else-if="syncState === 'recovery'"
          class="sync-callout warning"
          role="status"
        >
          <font-awesome-icon icon="fa-solid fa-clock-rotate-left" />
          <div>
            <strong>{{ t('projectsPage.syncDialog.recoveryTitle') }}</strong>
            <p>{{ t('projectsPage.syncDialog.recoveryDescription') }}</p>
          </div>
        </div>

        <section
          v-if="operations.length"
          class="sync-history"
          aria-labelledby="sync-history-title"
        >
          <div class="sync-history-heading">
            <h3 id="sync-history-title">
              {{ t('projectsPage.syncDialog.historyTitle') }}
            </h3>
            <span>{{ t('projectsPage.syncDialog.historyRetained') }}</span>
          </div>
          <ol>
            <li
              v-for="operation in operations.slice(0, 5)"
              :key="operation.operation_id"
            >
              <span
                class="sync-operation-state"
                :class="`operation-${operation.state}`"
                >{{
                  t(`projectsPage.syncDialog.states.${operation.state}`)
                }}</span
              >
              <span>{{ formatDate(operation.created_at) }}</span>
              <code>{{ operation.operation_id.slice(0, 8) }}</code>
              <span>{{
                t('projectsPage.syncDialog.operationChanges', {
                  count: operation.changes.length,
                })
              }}</span>
              <button
                v-if="operation.state === 'recovery_required'"
                type="button"
                class="sync-history-action"
                :disabled="actionLoading"
                @click="recoverOperation(operation)"
              >
                {{ t('projectsPage.syncDialog.recover') }}
              </button>
            </li>
          </ol>
        </section>
      </main>

      <footer v-if="!loading" class="sync-actions">
        <template v-if="syncState === 'missing'">
          <button
            type="button"
            class="sync-btn secondary"
            :disabled="actionLoading"
            @click="restoreFromBackup"
          >
            {{ t('projectsPage.syncDialog.restoreFromBackup') }}
          </button>
          <button
            type="button"
            class="sync-btn destructive"
            :disabled="actionLoading"
            @click="confirmDelete"
          >
            {{ t('projectsPage.syncDialog.deleteProject') }}
          </button>
        </template>
        <template v-else-if="syncState === 'out_of_sync'">
          <button
            type="button"
            class="sync-btn secondary"
            :disabled="actionLoading"
            @click="confirmDiscard"
          >
            {{ t('projectsPage.syncDialog.keepRepositoryVersion') }}
          </button>
          <button
            type="button"
            class="sync-btn primary"
            :disabled="actionLoading"
            @click="confirmSync"
          >
            {{ t('projectsPage.syncDialog.acceptServerChanges') }}
          </button>
        </template>
        <button
          v-if="syncState === 'error'"
          type="button"
          class="sync-btn secondary"
          :disabled="actionLoading"
          @click="checkSync"
        >
          {{ t('projectsPage.syncDialog.retry') }}
        </button>
        <button
          type="button"
          class="sync-btn quiet"
          :disabled="actionLoading"
          @click="closeDialog"
        >
          {{ t('common.cancel') }}
        </button>
      </footer>

      <UserConfirm
        v-model="showConfirm"
        :message="confirmMessage"
        :title="confirmTitle"
        @confirm="handleConfirmed"
        @cancel="showConfirm = false"
      />
    </dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import gitService from '@/api/service/gitService';
import UserConfirm from '@/components/common/UserConfirm.vue';
import { useEventMessageStore } from '@stores/eventMessage';
import { useModalDialog } from '@/composables/useModalDialog';

const { t } = useI18n();
const props = defineProps({
  projectName: { type: String, required: true },
  visible: { type: Boolean, required: true },
});
const emit = defineEmits(['close', 'sync-completed', 'update:visible']);
const eventMessageStore = useEventMessageStore();
const dialogElement = ref(null);
const closeButton = ref(null);
const loading = ref(true);
const actionLoading = ref(false);
const syncState = ref('');
const syncChanges = ref([]);
const syncError = ref('');
const missingType = ref('');
const operations = ref([]);
const showConfirm = ref(false);
const confirmMessage = ref('');
const confirmTitle = ref('');
let confirmAction = null;

const sortedChanges = computed(() =>
  [...syncChanges.value].sort((a, b) => {
    const order = {
      added: 0,
      untracked: 0,
      modified: 1,
      renamed: 2,
      deleted: 3,
    };
    return (
      (order[a.status] ?? 4) - (order[b.status] ?? 4) ||
      a.filename.localeCompare(b.filename)
    );
  })
);
const missingMessage = computed(() => {
  const keys = {
    missing_folder: 'missingFolder',
    missing_git: 'missingGit',
    missing_elan_files: 'missingElanFiles',
  };
  return t(`projectsPage.syncDialog.${keys[missingType.value] || 'illFormed'}`);
});
function normalizedStatus(change) {
  return change.status === 'untracked' ? 'added' : change.status;
}
function statusLabel(change) {
  return t(`projectsPage.syncDialog.${normalizedStatus(change)}`);
}
function closeDialog() {
  if (actionLoading.value || showConfirm.value) return;
  emit('update:visible', false);
  emit('close');
}
async function checkSync() {
  loading.value = true;
  syncState.value = '';
  syncChanges.value = [];
  syncError.value = '';
  missingType.value = '';
  try {
    const history = await gitService
      .getSynchronizationOperations(props.projectName)
      .catch(() => ({ operations: [] }));
    operations.value = history.operations || [];
    const status = await gitService.checkSyncStatus(props.projectName);
    if (
      ['missing_folder', 'missing_git', 'missing_elan_files'].includes(
        status.status
      )
    ) {
      syncState.value = 'missing';
      missingType.value = status.status;
    } else if (
      operations.value.some(
        (operation) => operation.state === 'recovery_required'
      )
    ) {
      syncState.value = 'recovery';
    } else if (status.in_sync || status.files_status?.length === 0) {
      eventMessageStore.addMessage(
        'projectsPage.syncDialog.eventMessages.alreadyUpToDate',
        'success'
      );
      closeDialog();
    } else {
      syncState.value = 'out_of_sync';
      syncChanges.value = status.files_status || [];
    }
  } catch (error) {
    syncState.value = 'error';
    syncError.value =
      error?.response?.data?.detail || t('projectsPage.syncDialog.checkFailed');
  } finally {
    loading.value = false;
  }
}
function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
function prepareConfirm(title, message, action) {
  confirmTitle.value = t(title);
  confirmMessage.value = t(message, { count: syncChanges.value.length });
  confirmAction = action;
  showConfirm.value = true;
}
function confirmDelete() {
  prepareConfirm(
    'projectsPage.syncDialog.deleteProject',
    'projectsPage.syncDialog.deleteConfirm',
    deleteProject
  );
}
function confirmDiscard() {
  prepareConfirm(
    'projectsPage.syncDialog.keepRepositoryVersion',
    'projectsPage.syncDialog.discardConfirm',
    discardLocalChanges
  );
}
function confirmSync() {
  prepareConfirm(
    'projectsPage.syncDialog.acceptServerChanges',
    'projectsPage.syncDialog.acceptConfirm',
    syncToMaster
  );
}
async function runAction(operation, successKey, failureKey) {
  actionLoading.value = true;
  syncError.value = '';
  try {
    await operation();
    emit('sync-completed');
    eventMessageStore.addMessage(successKey, 'success');
    actionLoading.value = false;
    closeDialog();
  } catch (error) {
    syncState.value = 'error';
    syncError.value = error?.response?.data?.detail || t(failureKey);
    eventMessageStore.addMessage(failureKey, 'error');
    actionLoading.value = false;
  }
}
function restoreFromBackup() {
  return runAction(
    () => gitService.restoreFromBackup(props.projectName),
    'projectsPage.syncDialog.eventMessages.succesfullyRestored',
    'projectsPage.syncDialog.restoreFailed'
  );
}
function deleteProject() {
  return runAction(
    () => gitService.declineBackup(props.projectName),
    'projectsPage.syncDialog.eventMessages.succesfullyDeleted',
    'projectsPage.syncDialog.deleteFailed'
  );
}
function discardLocalChanges() {
  return runAction(
    () => gitService.discardLocalChanges(props.projectName),
    'projectsPage.syncDialog.eventMessages.succesfullyDiscarded',
    'projectsPage.syncDialog.discardFailed'
  );
}
function syncToMaster() {
  return runAction(
    () => gitService.synchronizeProject(props.projectName),
    'projectsPage.syncDialog.eventMessages.succesfullySynced',
    'projectsPage.syncDialog.syncFailed'
  );
}

async function recoverOperation(operation) {
  actionLoading.value = true;
  try {
    await gitService.recoverSynchronizationOperation(
      props.projectName,
      operation.operation_id
    );
    eventMessageStore.addMessage(
      'projectsPage.syncDialog.eventMessages.recovered',
      'success'
    );
    await checkSync();
    emit('sync-completed');
  } catch (error) {
    syncState.value = 'error';
    syncError.value =
      error?.response?.data?.detail ||
      t('projectsPage.syncDialog.recoveryFailed');
  } finally {
    actionLoading.value = false;
  }
}
function handleConfirmed() {
  showConfirm.value = false;
  const action = confirmAction;
  confirmAction = null;
  if (action) void action();
}
useModalDialog(dialogElement, {
  onClose: closeDialog,
  isOpen: () => props.visible,
  initialFocus: closeButton,
});

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return;
    await checkSync();
  },
  { immediate: true }
);
</script>

<style scoped>
.sync-backdrop {
  position: fixed;
  z-index: 10000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgb(15 23 42 / 56%);
  backdrop-filter: blur(3px);
}

.sync-dialog {
  position: relative;
  inset: auto;
  width: min(48rem, 100%);
  max-height: calc(100dvh - 2rem);
  margin: 0;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 1rem;
  background: white;
  box-shadow: 0 24px 64px rgb(15 23 42 / 28%);
}

.sync-header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.9rem;
  padding: 1.35rem 1.4rem 1.15rem;
  border-bottom: 1px solid var(--color-border);
}

.sync-icon {
  width: 2.7rem;
  height: 2.7rem;
  display: grid;
  place-items: center;
  border-radius: 0.7rem;
  color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 10%, white);
}

.sync-eyebrow {
  display: block;
  margin-bottom: 0.2rem;
  color: var(--primary-color);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sync-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 1.3rem;
}

.sync-header p,
.sync-callout p,
.sync-safety p {
  margin: 0.25rem 0 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.sync-close {
  width: 2.35rem;
  height: 2.35rem;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 0.55rem;
  color: var(--color-text-muted);
  background: transparent;
  cursor: pointer;
}

.sync-close:hover {
  color: var(--color-text);
  background: var(--color-surface-subtle);
}

.sync-body {
  max-height: calc(100dvh - 15rem);
  padding: 1.25rem 1.4rem;
  overflow: auto;
}

.sync-state,
.sync-callout {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  color: var(--color-text);
  background: var(--color-surface-subtle);
}

.sync-state {
  min-height: 8rem;
  align-items: center;
  justify-content: center;
}

.sync-callout.warning {
  border-color: #f5d486;
  background: #fffaf0;
}

.sync-callout.danger {
  border-color: #fecaca;
  background: #fff7f7;
}

.sync-safety {
  margin: 1rem 0;
  padding: 0.9rem 1rem;
  border-left: 3px solid var(--primary-color);
  color: var(--color-text);
  background: color-mix(in srgb, var(--primary-color) 4%, white);
}

.sync-list {
  display: grid;
  gap: 0.45rem;
}

.sync-history {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.sync-history-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
}

.sync-history h3 {
  margin: 0;
  color: var(--color-text);
  font-size: 0.95rem;
}

.sync-history-heading > span {
  color: var(--color-text-muted);
  font-size: 0.75rem;
}

.sync-history ol {
  display: grid;
  gap: 0.4rem;
  margin: 0.65rem 0 0;
  padding: 0;
  list-style: none;
}

.sync-history li {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 0.6rem;
  color: var(--color-text-muted);
  font-size: 0.76rem;
}

.sync-history code {
  color: var(--color-text);
}

.sync-operation-state {
  padding: 0.18rem 0.45rem;
  border-radius: 999px;
  font-weight: 750;
}

.sync-history-action {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--primary-color);
  border-radius: 0.4rem;
  color: var(--primary-color);
  background: white;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

.operation-completed {
  color: #067647;
  background: #ecfdf3;
}

.operation-discarded {
  color: #475467;
  background: #f2f4f7;
}

.operation-failed,
.operation-recovery_required {
  color: #b42318;
  background: #fff1f0;
}

.operation-preparing,
.operation-prepared,
.operation-committing {
  color: #9a6700;
  background: #fff8c5;
}

.sync-change {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.7rem;
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: 0.65rem;
  background: white;
}

.sync-change img {
  width: 1.25rem;
  height: 1.25rem;
}

.sync-name {
  overflow: hidden;
  color: var(--color-text);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 0.82rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sync-status {
  padding: 0.25rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 750;
}

.status-added {
  color: #067647;
  background: #ecfdf3;
}

.status-modified {
  color: #9a6700;
  background: #fff8c5;
}

.status-deleted {
  color: #b42318;
  background: #fff1f0;
}

.status-renamed {
  color: #175cd3;
  background: #eff8ff;
}

.sync-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  padding: 1rem 1.4rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.sync-btn {
  min-height: 2.55rem;
  padding: 0.55rem 0.85rem;
  border: 1px solid transparent;
  border-radius: 0.55rem;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 750;
  cursor: pointer;
}

.sync-btn.primary {
  color: white;
  background: var(--primary-color);
}

.sync-btn.secondary {
  color: var(--color-text);
  border-color: var(--color-border);
  background: white;
}

.sync-btn.destructive {
  color: #b42318;
  border-color: #fecaca;
  background: #fff7f7;
}

.sync-btn.quiet {
  color: var(--color-text-muted);
  background: transparent;
}

.sync-btn:disabled {
  cursor: wait;
  opacity: 0.6;
}

.sync-btn:focus-visible,
.sync-close:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.sync-spinner {
  width: 1.3rem;
  height: 1.3rem;
  border: 2px solid #dbeafe;
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 700ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (width <= 640px) {
  .sync-backdrop {
    place-items: end center;
    padding: 0;
  }

  .sync-dialog {
    width: 100%;
    max-height: 92dvh;
    border-radius: 1rem 1rem 0 0;
  }

  .sync-header,
  .sync-body {
    padding: 1rem;
  }

  .sync-icon {
    display: none;
  }

  .sync-actions {
    flex-direction: column;
    padding: 0.85rem 1rem max(0.85rem, env(safe-area-inset-bottom));
  }

  .sync-btn {
    width: 100%;
  }

  .sync-change {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .sync-status {
    grid-column: 2;
    justify-self: start;
  }

  .sync-history li {
    grid-template-columns: auto 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sync-spinner {
    animation-duration: 1.5s;
  }
}
</style>
