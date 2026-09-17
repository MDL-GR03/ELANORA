<template>
  <div class="configure-filetypes-page">
    <div class="configure-filetypes-header">
      <h2 class="configure-filetypes-title">
        {{ t('configureFileTypes.title') }}
      </h2>
    </div>
    <div v-if="isLoading" class="configure-filetypes-loading">
      {{ t('configureFileTypes.loading') }}
    </div>
    <div v-else>
      <!-- File Types Table -->
      <div v-if="fileTypes.length">
        <h3>{{ t('configureFileTypes.FileTypes') }}</h3>
        <table class="configure-filetypes-table">
          <thead>
            <tr>
              <th>{{ t('configureFileTypes.name') }}</th>
              <th>{{ t('configureFileTypes.extension') }}</th>
              <th>{{ t('configureFileTypes.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ft in fileTypes" :key="ft.id">
              <td>
                <template v-if="editId === ft.id">
                  <input
                    v-model="editFileType.name"
                    class="configure-file-types-edit-highlight"
                    @keydown.enter="saveEdit(ft.id)"
                    @keydown.esc="cancelEdit"
                  />
                </template>
                <template v-else>
                  {{ ft.name }}
                </template>
              </td>
              <td>
                <template v-if="editId === ft.id">
                  <input
                    v-model="editFileType.extension"
                    class="configure-file-types-edit-highlight"
                    @keydown.enter="saveEdit(ft.id)"
                    @keydown.esc="cancelEdit"
                  />
                </template>
                <template v-else>
                  {{ ft.extension }}
                </template>
              </td>
              <td>
                <div class="configure-file-types-actions">
                  <template v-if="editId === ft.id">
                    <button
                      class="configure-file-types-action-btn configure-file-types-edit-btn"
                      :title="t('configureFileTypes.edit')"
                      @click="saveEdit(ft.id)"
                    >
                      <font-awesome-icon icon="fa-regular fa-pen-to-square" />
                    </button>
                    <button
                      class="configure-file-types-action-btn configure-file-types-edit-btn"
                      :title="t('configureFileTypes.delete')"
                      @click="cancelEdit"
                    >
                      <span style="font-size: 1.1em">✖</span>
                    </button>
                  </template>
                  <template v-else>
                    <button
                      class="configure-file-types-action-btn configure-file-types-edit-btn"
                      :title="t('configureFileTypes.edit')"
                      @click="startEdit(ft)"
                    >
                      <font-awesome-icon icon="fa-regular fa-pen-to-square" />
                    </button>
                    <button
                      class="configure-file-types-action-btn configure-file-types-delete-btn"
                      :title="t('configureFileTypes.delete')"
                      @click="deleteFileType(ft.id)"
                    >
                      <font-awesome-icon icon="trash" />
                    </button>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Add Custom File Type Form -->
      <div class="configure-filetypes-add-form">
        <div class="add-form-col">
          <input
            v-model="newFileType.name"
            :placeholder="t('configureFileTypes.name')"
          />
          <span v-if="addNameError" class="configure-file-types-input-error">{{
            addNameError
          }}</span>
        </div>
        <div class="add-form-col">
          <input
            v-model="newFileType.extension"
            :placeholder="t('configureFileTypes.extension')"
          />
          <span
            v-if="addExtensionError"
            class="configure-file-types-input-error"
            >{{ addExtensionError }}</span
          >
        </div>
        <button @click="addFileType">
          {{ t('configureFileTypes.createFileType') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { apiErrorCode } from '@/utils/apiError';
import { ref, nextTick, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useFileTypeStore } from '@/stores/fileType.js';
import { useEventMessageStore } from '@/stores/eventMessage.js';
import FontAwesomeIcon from '@/plugins/fontawesome';
import { useI18n } from 'vue-i18n';
import { useUserConfirm } from '@/composables/useUserConfirm';

const { t } = useI18n();
const route = useRoute();

const fileTypeStore = useFileTypeStore();
const eventMessageStore = useEventMessageStore();

const userConfirm = useUserConfirm();

const projectId = computed(() => Number(route.params.projectId));

const fileTypes = computed(() => fileTypeStore.fileTypes);

const newFileType = ref({ name: '', extension: '' });
const editId = ref(null);
const editFileType = ref({ name: '', extension: '' });

const addNameError = ref('');
const addExtensionError = ref('');

const isLoading = computed(() => fileTypeStore.isLoading);

// Refetch file types when projectId changes
watch(
  projectId,
  () => {
    fetchFileTypes();
  },
  { immediate: true }
);

async function fetchFileTypes() {
  await fileTypeStore.fetchFileTypes(projectId.value);
}

function startEdit(ft) {
  editId.value = ft.id;
  editFileType.value = { name: ft.name, extension: ft.extension };
  nextTick(() => {
    const input = document.querySelector(
      '.configure-file-types-edit-highlight'
    );
    if (input) input.focus();
  });
}
function cancelEdit() {
  editId.value = null;
  editFileType.value = { name: '', extension: '' };
}
function isValidExtension(ext) {
  return /^\.[a-z0-9]{1,10}$/.test(ext);
}
function isValidName(name) {
  const trimmed = name.trim();
  return (
    trimmed.length >= 2 &&
    trimmed.length <= 40 &&
    /^[\w\s-]+$/.test(trimmed) &&
    /[a-zA-Z]/.test(trimmed)
  );
}
async function saveEdit(id) {
  editFileType.value.name = editFileType.value.name.trim();
  editFileType.value.extension = editFileType.value.extension.trim();
  if (
    editFileType.value.extension &&
    !editFileType.value.extension.startsWith('.')
  ) {
    editFileType.value.extension = '.' + editFileType.value.extension;
  }
  if (!isValidName(editFileType.value.name)) {
    eventMessageStore.addMessage(
      'configureFileTypes.invalidName',
      'error',
      5000
    );
    return;
  }
  if (!isValidExtension(editFileType.value.extension)) {
    eventMessageStore.addMessage(
      'configureFileTypes.invalidExtension',
      'error',
      5000
    );
    return;
  }
  try {
    await fileTypeStore.updateFileType(
      id,
      { ...editFileType.value },
      projectId.value
    );
    eventMessageStore.addMessage(
      'configureFileTypes.eventMessages.updateSuccess',
      'success',
      4000
    );
  } catch {
    eventMessageStore.addMessage(
      'configureFileTypes.eventMessages.updateFailed',
      'error',
      7000
    );
  }
  cancelEdit();
}

async function deleteFileType(id) {
  const ok = await userConfirm({
    message:
      t('configureFileTypes.delete') +
      '?\n' +
      t('configureFileTypes.deleteMessage'),
    title: t('configureFileTypes.deleteTitle'),
    confirmText: t('common.confirm'),
    tone: 'danger',
    cancelText: t('common.cancel'),
  });
  if (!ok) return;
  try {
    await fileTypeStore.deleteFileType(id, projectId.value);
    eventMessageStore.addMessage(
      'configureFileTypes.eventMessages.deleteSuccess',
      'success',
      4000
    );
  } catch (e) {
    if (apiErrorCode(e) === 'file_type_in_use') {
      eventMessageStore.addMessage(
        'configureNamingStandards.eventMessages.cannotDeleteUsedFileType',
        'error',
        7000
      );
    } else {
      eventMessageStore.addMessage(
        'configureFileTypes.eventMessages.deleteFailed',
        'error',
        7000
      );
    }
  }
}

async function addFileType() {
  addNameError.value = '';
  addExtensionError.value = '';
  newFileType.value.name = newFileType.value.name.trim();
  newFileType.value.extension = newFileType.value.extension.trim();
  if (
    newFileType.value.extension &&
    !newFileType.value.extension.startsWith('.')
  ) {
    newFileType.value.extension = '.' + newFileType.value.extension;
  }
  let valid = true;
  if (!isValidName(newFileType.value.name)) {
    addNameError.value = t('configureFileTypes.invalidName');
    valid = false;
  }
  if (!isValidExtension(newFileType.value.extension)) {
    addExtensionError.value = t('configureFileTypes.invalidExtension');
    valid = false;
  }
  if (!valid) return;
  const duplicate = fileTypes.value.some(
    (ft) =>
      ft.name.trim().toLowerCase() === newFileType.value.name.toLowerCase()
  );
  if (duplicate) {
    eventMessageStore.addMessage(
      'configureFileTypes.eventMessages.duplicateName',
      'error',
      5000
    );
    return;
  }
  try {
    await fileTypeStore.addFileType(
      { ...newFileType.value, project_id: projectId.value },
      projectId.value
    );
    eventMessageStore.addMessage(
      'configureFileTypes.eventMessages.addSuccess',
      'success',
      4000
    );
    newFileType.value = { name: '', extension: '' };
  } catch {
    eventMessageStore.addMessage(
      'configureFileTypes.eventMessages.addFailed',
      'error',
      7000
    );
  }
}
</script>

<style scoped>
.configure-filetypes-page {
  width: 100%;
  min-width: 0;
  min-height: 200px;
  overflow: hidden;
}

.configure-filetypes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--color-border-strong);
}

.configure-filetypes-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
  color: var(--color-text);
}

.configure-filetypes-loading {
  color: var(--color-gray-800);
  font-size: 1.1rem;
  margin-bottom: 18px;
}

.configure-filetypes-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 18px;
  table-layout: fixed;
}

.configure-filetypes-table th,
.configure-filetypes-table td {
  border: 1px solid var(--color-border-strong);
  padding: 6px 10px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.configure-filetypes-table th:nth-child(1),
.configure-filetypes-table td:nth-child(1) {
  width: 40%;
}

.configure-filetypes-table th:nth-child(2),
.configure-filetypes-table td:nth-child(2) {
  width: 30%;
}

.configure-filetypes-table th:nth-child(3),
.configure-filetypes-table td:nth-child(3) {
  width: 30%;
}

.configure-filetypes-add-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
  gap: 10px;
  margin-top: 12px;
  align-items: flex-start;
}

.add-form-col {
  display: flex;
  flex-direction: column;
  width: auto;
  min-width: 0;
}

.configure-filetypes-add-form input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 1rem;
}

.configure-filetypes-add-form button {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  padding: 6.5px 18px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.18s;
  white-space: nowrap;
}

.configure-filetypes-add-form button:hover {
  background: var(--color-primary-dark);
}

.configure-file-types-actions {
  display: flex;
  gap: 8px;
}

.configure-file-types-action-btn {
  background: none;
  border: 2px solid;
  font-size: 1.2rem;
  cursor: pointer;
  margin-left: 0;
  border-radius: 6px;
  padding: 0;
  min-width: 38px;
  min-height: 38px;
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition:
    color 0.2s,
    border-color 0.2s,
    background 0.2s;
}

.configure-file-types-edit-btn {
  border-color: var(--color-gray-750);
  color: var(--color-gray-750);
}

.configure-file-types-edit-btn:hover {
  background: var(--color-gray-750);
  color: var(--color-text-inverse);
  border-color: var(--color-gray-850);
}

.configure-file-types-delete-btn {
  border-color: var(--color-error-medium);
  color: var(--color-error-medium);
}

.configure-file-types-delete-btn:hover {
  background: var(--color-error-medium);
  color: var(--color-text-inverse);
  border-color: var(--color-error-darker);
}

/* Highlight editable fields */
.configure-file-types-edit-highlight {
  border: 2px solid var(--color-primary) !important;
  background: var(--color-primary-bg-lighter) !important;
  border-radius: var(--radius-sm);
  outline: none;
  box-shadow: 0 0 0 2px rgb(37 99 235 / 20%);
  transition:
    border 0.18s,
    box-shadow 0.18s;
  width: 100%;
  box-sizing: border-box;
}

.configure-file-types-input-error {
  color: var(--color-error-medium);
  font-size: 0.92em;
  margin-top: 2px;
  display: block;
  width: 100%;
  box-sizing: border-box;
  overflow-wrap: break-word;
  white-space: normal;
}

@media (width <= 760px) {
  .configure-filetypes-add-form {
    grid-template-columns: 1fr;
  }

  .configure-filetypes-add-form button {
    width: 100%;
    min-height: 2.75rem;
  }

  .configure-filetypes-table th,
  .configure-filetypes-table td {
    padding-inline: 0.45rem;
  }
}
</style>
