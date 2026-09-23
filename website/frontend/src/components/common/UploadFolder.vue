<template>
  <div class="upload-folder-container">
    <!-- File input for browsing individual files -->
    <input
      ref="fileInput"
      type="file"
      multiple
      accept=".eaf"
      aria-hidden="true"
      tabindex="-1"
      style="display: none"
      @change="handleFileInput"
    />
    <input
      ref="folderInput"
      type="file"
      multiple
      accept=".eaf"
      aria-hidden="true"
      tabindex="-1"
      webkitdirectory
      directory
      style="display: none"
      @change="handleFileInput"
    />

    <!-- Upload Zone -->
    <!-- Dropping files has no keyboard equivalent by nature. The design system requires an equivalent control, which is the pair of browse buttons inside this zone; drag and drop is only an enhancement. -->
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
    <div
      class="upload-zone"
      :class="{
        dragover: isDragOver,
        'has-files': selectedFiles.length > 0,
        compact: compact,
        disabled: disabled,
      }"
      @drop="handleDrop"
      @dragover.prevent="!disabled && (isDragOver = true)"
      @dragleave="isDragOver = false"
    >
      <div v-if="selectedFiles.length === 0" class="upload-content">
        <div class="upload-icon" aria-hidden="true">
          <font-awesome-icon icon="fa-solid fa-cloud-arrow-up" />
        </div>
        <h3>{{ title || $t('upload.zone.title') }}</h3>
        <p>{{ subtitle || $t('upload.zone.subtitle') }}</p>
        <div class="upload-browse-actions">
          <button
            type="button"
            class="upload-browse-button"
            :disabled="disabled"
            @click="triggerBrowse"
          >
            <font-awesome-icon icon="fa-solid fa-file-circle-plus" />
            {{ $t('upload.chooseFiles') }}
          </button>
          <button
            type="button"
            class="upload-folder-button"
            :disabled="disabled"
            @click="triggerFolderBrowse"
          >
            <font-awesome-icon icon="fa-solid fa-folder-plus" />
            {{ $t('upload.chooseFolder') }}
          </button>
        </div>
      </div>

      <div v-else class="files-preview">
        <div class="preview-header">
          <h4>
            {{ $t('upload.selectedFiles', { count: selectedFiles.length }) }}
          </h4>
          <div class="preview-actions">
            <button
              type="button"
              class="action-btn add"
              :title="$t('upload.addMoreFiles')"
              :disabled="disabled"
              @click.stop="triggerBrowse"
            >
              <font-awesome-icon icon="plus" />
            </button>
            <button
              type="button"
              class="action-btn clear"
              :title="$t('upload.clearAllFiles')"
              :disabled="disabled"
              @click.stop="clearFiles"
            >
              <font-awesome-icon icon="trash" />
            </button>
          </div>
        </div>

        <div class="files-list" :class="{ 'compact-list': compact }">
          <div
            v-for="(file, index) in selectedFiles"
            :key="getFileKey(file, index)"
            class="file-item"
            :class="{
              'file-noncompliant':
                filesWithCompliance?.[index]?.isCompliant === false,
            }"
          >
            <img
              src="/images/icons/ELAN.svg"
              :alt="t('fileTree.elanFile')"
              class="file-icon"
            />
            <div class="file-details">
              <div v-if="renamingIndex !== index" class="file-info">
                <span class="file-name" :title="file.name">{{
                  file.name
                }}</span>
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
                <span
                  v-if="file.webkitRelativePath"
                  class="file-path"
                  :title="file.webkitRelativePath"
                >
                  {{ getFileDirectory(file.webkitRelativePath) }}
                </span>
              </div>
              <div v-else class="file-rename-control">
                <div class="rename-input-row">
                  <input
                    v-model="renameDraft"
                    type="text"
                    class="rename-input"
                    :placeholder="$t('upload.renamePlaceholder')"
                    :aria-label="$t('upload.renamePlaceholder')"
                    :disabled="disabled"
                    @keydown.enter="confirmRename"
                    @keydown.escape="cancelRename"
                  />
                  <button
                    type="button"
                    class="rename-confirm-btn"
                    :disabled="!isValidRename || disabled"
                    :title="$t('upload.renameConfirm')"
                    @click.stop="confirmRename"
                  >
                    <font-awesome-icon icon="fa-solid fa-check" />
                  </button>
                  <button
                    type="button"
                    class="rename-cancel-btn"
                    :disabled="disabled"
                    :title="$t('upload.renameCancel')"
                    @click.stop="cancelRename"
                  >
                    <font-awesome-icon icon="fa-solid fa-xmark" />
                  </button>
                </div>
                <button
                  v-if="renameSuggestion"
                  type="button"
                  class="rename-suggestion-btn"
                  :disabled="disabled"
                  @click="applySuggestion"
                >
                  {{
                    $t('upload.renameSuggestionAvailable', {
                      name: renameSuggestion,
                    })
                  }}
                </button>
                <div
                  v-if="
                    renameDraft.trim() &&
                    props.standard &&
                    !isRenameDraftCompliant
                  "
                  class="rename-warning"
                >
                  {{ $t('upload.renameNonCompliant') }}
                </div>
                <div v-if="isDuplicateName" class="rename-warning">
                  {{
                    $t('upload.renameDuplicate', { name: renameDraft.trim() })
                  }}
                </div>
              </div>
            </div>
            <div v-if="renamingIndex !== index" class="file-actions">
              <button
                v-if="filesWithCompliance?.[index]?.isCompliant === false"
                type="button"
                class="rename-btn"
                :aria-label="$t('upload.renameNamedFile', { name: file.name })"
                :disabled="disabled"
                @click.stop="startRename(index)"
              >
                <font-awesome-icon icon="fa-regular fa-pen-to-square" />
              </button>
              <button
                type="button"
                class="remove-btn"
                :aria-label="$t('upload.removeNamedFile', { name: file.name })"
                :disabled="disabled"
                @click.stop="removeFile(index)"
              >
                <font-awesome-icon icon="fa-solid fa-xmark" />
              </button>
            </div>
          </div>
        </div>

        <div class="files-summary">
          <span class="total-size">
            {{ $t('upload.totalSize', { size: formatFileSize(totalSize) }) }}
          </span>
          <span v-if="maxFileSize && hasOversizedFiles" class="size-warning">
            ⚠️
            {{
              $t('upload.filesExceedLimit', {
                maxSize: formatFileSize(maxFileSize),
              })
            }}
          </span>
        </div>
      </div>
    </div>
    <div class="sr-only" aria-live="polite">
      {{ $t('upload.selectedFiles', { count: selectedFiles.length }) }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import FontAwesomeIcon from '@/plugins/fontawesome';
import { useEventMessageStore } from '@stores/eventMessage';
import { useI18n } from 'vue-i18n';
import { isFilenameCompliant } from '@/utils/filenameCompliance';
import { suggestEafFilenameFromMedia } from '@/utils/filenameFromMediaFile';

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  maxFileSize: { type: Number, default: 50 * 1024 * 1024 },
  compact: { type: Boolean, default: false },
  allowDuplicates: { type: Boolean, default: false },
  filesWithCompliance: { type: Array, default: () => [] }, // New: Array of compliance statuses
  standard: { type: Object, default: null },
  mediaStandard: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue', 'error', 'files-changed']);

const { t } = useI18n();
const eventMessageStore = useEventMessageStore();
const selectedFiles = ref([]);
const isDragOver = ref(false);
const fileInput = ref(null);
const folderInput = ref(null);
const renamingIndex = ref(null);
const renameDraft = ref('');
const renameSuggestion = ref(null);

// Initialize from modelValue and sort
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue && Array.isArray(newValue)) {
      selectedFiles.value = [...newValue].sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
      );
    }
  },
  { immediate: true }
);

// Computed properties
const totalSize = computed(() =>
  selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
);

const hasOversizedFiles = computed(
  () =>
    props.maxFileSize &&
    selectedFiles.value.some((file) => file.size > props.maxFileSize)
);

function withEafExtension(name) {
  return name.toLowerCase().endsWith('.eaf') ? name : `${name}.eaf`;
}

const isRenameDraftCompliant = computed(() => {
  const trimmed = renameDraft.value.trim();
  if (!trimmed || !props.standard) return true;
  return isFilenameCompliant(props.standard, trimmed);
});

const isDuplicateName = computed(() => {
  const trimmed = renameDraft.value.trim();
  if (!trimmed || renamingIndex.value === null) return false;
  const currentFile = selectedFiles.value[renamingIndex.value];
  if (!currentFile) return false;
  const candidateName = withEafExtension(trimmed).toLowerCase();
  // Check if any other file has the same name (case-insensitive)
  return selectedFiles.value.some(
    (file, index) =>
      index !== renamingIndex.value && file.name.toLowerCase() === candidateName
  );
});

const isValidRename = computed(() => {
  const trimmed = renameDraft.value.trim();
  const currentFile =
    renamingIndex.value !== null
      ? selectedFiles.value[renamingIndex.value]
      : null;

  // Draft must not be empty
  if (!trimmed) return false;

  // Must be different from current name
  if (currentFile && currentFile.name === withEafExtension(trimmed)) {
    return false;
  }

  // Must not be a duplicate
  if (isDuplicateName.value) return false;

  // Must be compliant (if standard exists)
  if (props.standard && !isRenameDraftCompliant.value) return false;

  return true;
});

// Helper functions
function getFileKey(file, index) {
  return `${file.name}-${file.size}-${file.lastModified || index}`;
}

function getFileDirectory(relativePath) {
  const parts = relativePath.split('/');
  return parts.length > 1 ? parts.slice(0, -1).join('/') + '/' : '';
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// File input handling
function triggerBrowse() {
  if (props.disabled) return;
  fileInput.value?.click();
}

function triggerFolderBrowse() {
  if (props.disabled) return;
  folderInput.value?.click();
}

function handleFileInput(event) {
  const files = Array.from(event.target.files);
  addFiles(files);
  event.target.value = '';
}

// Drag and drop handling
async function handleDrop(event) {
  event.preventDefault();
  isDragOver.value = false;
  if (props.disabled) return;

  const files = await extractFilesFromDrop(event);
  if (files.length > 0) {
    addFiles(files);
  }
}

async function extractFilesFromDrop(event) {
  const items = event.dataTransfer.items;

  if (items && items.length > 0) {
    // Modern browsers - handle files and folders
    const promises = Array.from(items)
      .filter((item) => item.kind === 'file')
      .map((item) => {
        const entry = item.webkitGetAsEntry?.();
        if (entry) return processEntry(entry);
        const file = item.getAsFile?.();
        return file ? [file] : [];
      });

    const results = await Promise.all(promises);
    return results.flat();
  } else {
    // Fallback - handle files only
    return Array.from(event.dataTransfer.files);
  }
}

// Recursively process directory entries
async function processEntry(entry) {
  if (entry.isFile) {
    return new Promise((resolve) => {
      entry.file(
        (file) => {
          // Add relative path for folder structure
          if (entry.fullPath !== '/' + file.name) {
            Object.defineProperty(file, 'webkitRelativePath', {
              value: entry.fullPath.slice(1),
              writable: false,
            });
          }
          resolve([file]);
        },
        () => resolve([])
      );
    });
  }

  if (entry.isDirectory) {
    const dirReader = entry.createReader();
    const allFiles = [];

    // Read all entries from directory
    let entries;
    do {
      entries = await new Promise((resolve) =>
        dirReader.readEntries(resolve, () => resolve([]))
      );

      const filePromises = entries.map(processEntry);
      const fileResults = await Promise.all(filePromises);
      allFiles.push(...fileResults.flat());
    } while (entries.length > 0);

    return allFiles;
  }

  return [];
}

// File processing
function addFiles(files) {
  if (!files?.length) {
    eventMessageStore.addMessage('upload.noFilesSelected', 'error', 4000);
    emit('error', t('upload.noFilesSelected'));
    return;
  }

  // Filter for .eaf files
  const eafFiles = files.filter((file) =>
    file.name.toLowerCase().endsWith('.eaf')
  );

  // Report skipped files
  const skippedCount = files.length - eafFiles.length;
  if (skippedCount > 0) {
    eventMessageStore.addMessage('upload.filesSkipped', 'warning', 4000, {
      count: skippedCount,
    });
  }

  if (!eafFiles.length) {
    eventMessageStore.addMessage('upload.noEafFiles', 'error', 4000);
    emit('error', t('upload.noEafFiles'));
    return;
  }

  // Check file sizes
  if (props.maxFileSize) {
    const oversizedFiles = eafFiles.filter(
      (file) => file.size > props.maxFileSize
    );
    if (oversizedFiles.length > 0) {
      const fileNames = oversizedFiles.map((f) => f.name).join(', ');
      eventMessageStore.addMessage('upload.filesTooLarge', 'error', 6000, {
        files: fileNames,
        maxSize: formatFileSize(props.maxFileSize),
      });
      emit(
        'error',
        t('upload.filesTooLarge', {
          files: fileNames,
          maxSize: formatFileSize(props.maxFileSize),
        })
      );
      return;
    }
  }

  // Handle duplicates
  let filesToAdd = eafFiles;
  if (!props.allowDuplicates) {
    const existingNames = new Set(selectedFiles.value.map((f) => f.name));
    filesToAdd = eafFiles.filter((file) => !existingNames.has(file.name));

    const duplicateCount = eafFiles.length - filesToAdd.length;
    if (duplicateCount > 0) {
      eventMessageStore.addMessage(
        'upload.duplicatesSkipped',
        'warning',
        4000,
        { count: duplicateCount }
      );
    }
  }

  if (!filesToAdd.length) {
    eventMessageStore.addMessage('upload.noNewFiles', 'warning', 4000);
    emit('error', t('upload.noNewFiles'));
    return;
  }

  // Add files
  selectedFiles.value.push(...filesToAdd);

  // Sort alphabetically by file name (case-insensitive)
  selectedFiles.value.sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
  );

  updateModelValue();

  const hasFolder = filesToAdd.some((f) => f.webkitRelativePath);

  if (hasFolder) {
    eventMessageStore.addMessage(
      'upload.filesAddedFromFolder',
      'success',
      3000,
      { count: filesToAdd.length }
    );
  } else if (filesToAdd.length === 1) {
    eventMessageStore.addMessage('upload.fileAdded', 'success', 3000, {
      fileName: filesToAdd[0].name,
    });
  } else {
    eventMessageStore.addMessage('upload.filesAdded', 'success', 3000, {
      count: filesToAdd.length,
    });
  }
}

function removeFile(index) {
  if (props.disabled) return;
  selectedFiles.value.splice(index, 1);
  selectedFiles.value.sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
  );

  updateModelValue();
}

function clearFiles() {
  if (props.disabled) return;
  selectedFiles.value = [];
  if (fileInput.value) fileInput.value.value = '';
  if (folderInput.value) folderInput.value.value = '';
  updateModelValue();
}

async function startRename(index) {
  if (props.disabled) return;
  renamingIndex.value = index;
  renameDraft.value = selectedFiles.value[index].name;
  renameSuggestion.value = null;

  if (props.standard && props.mediaStandard) {
    const result = await suggestEafFilenameFromMedia(
      selectedFiles.value[index],
      props.standard,
      props.mediaStandard
    );
    if (
      renamingIndex.value === index &&
      result &&
      result !== selectedFiles.value[index].name
    ) {
      renameSuggestion.value = result;
    }
  }
}

function cancelRename() {
  renamingIndex.value = null;
  renameDraft.value = '';
  renameSuggestion.value = null;
}

function applySuggestion() {
  if (renameSuggestion.value) {
    renameDraft.value = renameSuggestion.value;
  }
}

function confirmRename() {
  if (!isValidRename.value || renamingIndex.value === null) return;

  const oldFile = selectedFiles.value[renamingIndex.value];
  const finalName = withEafExtension(renameDraft.value.trim());

  // Create a new File object with the new name
  const renamed = new File([oldFile], finalName, {
    type: oldFile.type,
    lastModified: oldFile.lastModified,
  });

  // Preserve webkitRelativePath if it exists
  if (oldFile.webkitRelativePath) {
    Object.defineProperty(renamed, 'webkitRelativePath', {
      value: oldFile.webkitRelativePath.replace(/[^/]*$/, finalName),
      writable: false,
    });
  }

  // Replace the file
  selectedFiles.value[renamingIndex.value] = renamed;

  // Sort alphabetically
  selectedFiles.value.sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
  );

  updateModelValue();

  // Show success toast
  eventMessageStore.addMessage('upload.renameSuccess', 'success', 3000, {
    name: finalName,
  });

  cancelRename();
}

function updateModelValue() {
  emit('update:modelValue', selectedFiles.value);
  emit('files-changed', selectedFiles.value);
}

// Expose methods
defineExpose({
  clearFiles,
  addFiles,
});
</script>

<style scoped>
.upload-zone.compact {
  padding: 24px 16px;
  min-height: 100px;
}

.upload-zone.has-files:hover {
  border-color: var(--color-primary);
  background: var(--color-surface-subtle);
}

.upload-zone.has-files .preview-header,
.upload-zone.has-files .files-list,
.upload-zone.has-files .files-summary {
  pointer-events: auto;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 42rem;
  gap: 0.45rem;
}

:where(.upload-content h3) {
  margin: 0;
  color: var(--color-text);
  font-weight: 600;
  font-size: 1.1rem;
}

:where(.upload-content p) {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.95rem;
}

.preview-header h4 {
  margin: 0;
  color: var(--color-text);
  font-weight: 600;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-muted);
}

.action-btn:hover {
  background: var(--color-surface-subtle);
  border-color: var(--color-primary);
  color: var(--color-primary);
  transform: translateY(-1px);
}

.action-btn.clear:hover {
  border-color: var(--color-error);
  color: var(--color-error);
}

.files-list.compact-list {
  max-height: 200px;
}

.file-item:last-child {
  border-bottom: none;
}

.file-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-size {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.file-path {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-zone {
  border: 2px dashed var(--color-primary);
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: color-mix(in srgb, var(--color-primary) 0.5%, white);
  min-height: 140px;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 2rem 1rem;
}

.upload-zone:hover {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 2.5%, white);
  cursor: default;
  transition:
    border-color 150ms ease,
    background 150ms ease,
    box-shadow 150ms ease;
}

.upload-zone.dragover {
  border-color: var(--color-secondary);
  background: var(--color-success-400-bg);
  box-shadow: inset 0 0 0 3px rgb(15 118 110 / 10%);
  transform: none;
}

.upload-zone.disabled {
  pointer-events: none;
  opacity: 0.62;
}

.upload-zone.has-files {
  cursor: default;
  text-align: left;
  width: 100%;
  display: block;
  padding: 1rem;
  border-style: solid;
  background: white;
  min-height: auto;
  pointer-events: none;
}

.upload-icon {
  width: 3.25rem;
  height: 3.25rem;
  display: grid;
  place-items: center;
  margin: 0 0 0.35rem;
  border-radius: var(--radius-md);
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 10%, white);
  font-size: 1.45rem;
  opacity: 1;
}

.upload-browse-actions {
  display: flex;
  justify-content: center;
  gap: 0.55rem;
  margin-top: 0.75rem;
}

.upload-browse-button,
.upload-folder-button {
  min-height: 2.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.5rem 0.8rem;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background-color 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.upload-browse-button {
  color: white;
  background: var(--color-primary);
}

.upload-browse-button:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px
    color-mix(in srgb, var(--color-primary) 30%, transparent);
}

.upload-browse-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-folder-button {
  color: var(--color-primary);
  background: white;
}

.upload-folder-button:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-primary) 8%, white);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px
    color-mix(in srgb, var(--color-primary) 15%, transparent);
}

.upload-folder-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-browse-button:focus-visible,
.upload-folder-button:focus-visible,
.action-btn:focus-visible,
.remove-btn:focus-visible,
.rename-btn:focus-visible,
.rename-confirm-btn:focus-visible,
.rename-cancel-btn:focus-visible,
.rename-suggestion-btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.55rem;
  padding-bottom: 0.7rem;
  border-color: var(--color-border);
}

.preview-header h4,
.file-name {
  color: var(--color-text);
}

.files-list {
  max-height: 22rem;
  display: grid;
  gap: 0.4rem;
  margin: 0 0 0.7rem;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin: 0;
  padding: 0.65rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.file-name {
  font-size: 0.88rem;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size,
.file-path,
.total-size {
  color: var(--color-text-muted);
}

.remove-btn {
  width: 2rem;
  height: 2rem;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--color-error);
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  transition: all 0.2s;
  flex-shrink: 0;
}

.remove-btn:hover {
  border-color: transparent;
  color: var(--color-error-dark);
  background: var(--color-error-bg-subtle);
  transform: translateY(-1px);
}

.remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.file-noncompliant {
  border-color: var(--color-error-bg);
  border-left: 3px solid var(--color-error);
  background: var(--color-error-bg-subtle);
}

.files-summary {
  padding-top: 0.7rem;
  border-color: var(--color-border);
}

@media (width <= 768px) {
  .preview-header {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }

  .files-summary {
    flex-direction: column;
    gap: 4px;
    align-items: flex-start;
  }
}

@media (width <= 560px) {
  .upload-browse-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .upload-zone {
    min-height: 11rem;
    padding: 1rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .upload-zone {
    transition: none;
  }
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.file-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.rename-btn {
  width: 2rem;
  height: 2rem;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.rename-btn:hover {
  color: var(--color-primary-dark);
  background: var(--color-primary-bg-subtle);
  transform: translateY(-1px);
}

.rename-btn:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.file-rename-control {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.rename-input-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.rename-input {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
  font-family: monospace;
  color: var(--color-text);
  background: var(--color-surface);
}

.rename-input:focus {
  outline: none;
  border-color: var(--color-primary-dark);
  box-shadow: 0 0 0 2px var(--color-primary-bg-subtle);
}

.rename-input:disabled {
  background: var(--color-surface-subtle);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.rename-warning {
  font-size: 0.75rem;
  color: var(--color-error);
  line-height: 1.3;
  padding: 0.25rem 0;
}

.rename-suggestion-btn {
  background: none;
  border: none;
  padding: 0.2rem 0;
  color: var(--color-primary);
  font-size: 0.8rem;
  text-decoration: underline;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: color 0.2s;
}

.rename-suggestion-btn:hover:not(:disabled) {
  color: var(--color-primary-dark);
}

.rename-suggestion-btn:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.rename-confirm-btn,
.rename-cancel-btn {
  width: 2rem;
  height: 2rem;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.rename-confirm-btn {
  color: var(--color-success);
}

.rename-confirm-btn:hover:not(:disabled) {
  background: var(--color-success-bg-subtle);
  color: var(--color-success-dark);
  transform: translateY(-1px);
}

.rename-confirm-btn:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.rename-cancel-btn {
  color: var(--color-error);
}

.rename-cancel-btn:hover:not(:disabled) {
  background: var(--color-error-bg-subtle);
  color: var(--color-error-dark);
  transform: translateY(-1px);
}

.rename-cancel-btn:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}
</style>
