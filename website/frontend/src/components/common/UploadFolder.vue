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
              <span class="file-name" :title="file.name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <span
                v-if="file.webkitRelativePath"
                class="file-path"
                :title="file.webkitRelativePath"
              >
                {{ getFileDirectory(file.webkitRelativePath) }}
              </span>
            </div>
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

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  maxFileSize: { type: Number, default: 50 * 1024 * 1024 },
  compact: { type: Boolean, default: false },
  allowDuplicates: { type: Boolean, default: false },
  filesWithCompliance: { type: Array, default: () => [] }, // New: Array of compliance statuses
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue', 'error', 'files-changed']);

const { t } = useI18n();
const eventMessageStore = useEventMessageStore();
const selectedFiles = ref([]);
const isDragOver = ref(false);
const fileInput = ref(null);
const folderInput = ref(null);

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
:where(.upload-zone) {
  border: 2px dashed var(--color-primary);
  border-radius: var(--radius-lg);
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--color-surface-subtle);
  min-height: 140px;
  position: relative;
}

:where(.upload-zone:hover) {
  border-color: var(--color-primary-dark);
  background: color-mix(in srgb, var(--color-primary) 4%, white);
}

.upload-zone.compact {
  padding: 24px 16px;
  min-height: 100px;
}

:where(.upload-zone.dragover) {
  border-color: var(--color-secondary);
  background: var(--color-secondary-bg);
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgb(15 118 110 / 20%);
}

:where(.upload-zone.has-files) {
  cursor: default;
  text-align: left;
  padding: 16px;
  min-height: auto;
  pointer-events: none;
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

:where(.upload-content) {
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

:where(.upload-icon) {
  font-size: 3.5rem;
  opacity: 0.7;
  margin-bottom: 4px;
}

:where(.preview-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
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
}

.action-btn.clear:hover {
  border-color: var(--color-error);
  color: var(--color-error);
}

:where(.files-list) {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.files-list.compact-list {
  max-height: 200px;
}

:where(.file-item) {
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-subtle);
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

:where(.file-name) {
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

:where(.remove-btn) {
  width: 24px;
  height: 24px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  transition: all 0.2s;
  flex-shrink: 0;
  border: 1px solid var(--color-border);
}

:where(.remove-btn:hover) {
  background: var(--color-error);
  color: white;
  border-color: var(--color-error);
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
  width: 100%;
  display: block;
  padding: 1rem;
  border-style: solid;
  background: white;
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
}

.upload-browse-button {
  color: white;
  background: var(--color-primary);
}

.upload-folder-button {
  color: var(--color-primary);
  background: white;
}

.upload-browse-button:focus-visible,
.upload-folder-button:focus-visible,
.action-btn:focus-visible,
.remove-btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.preview-header {
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
}

.file-item {
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
}

.remove-btn:hover {
  border-color: transparent;
  color: var(--color-error-dark);
  background: var(--color-error-bg-subtle);
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
</style>
