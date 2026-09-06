<template>
  <div
    :class="[
      'file-rename-suggestion-popover',
      `file-rename-suggestion-popover--${placement}`,
    ]"
    tabindex="-1"
    @mouseenter="clearCloseTimer"
    @mouseleave="startCloseTimer"
    @focusin="clearCloseTimer"
    @focusout="startCloseTimer"
  >
    <div class="suggestion-title">{{ t('fileRenameSuggestion.title') }}</div>

    <div v-if="mediaFiles && mediaFiles.length > 0" class="media-files-info">
      <small
        >{{ t('fileRenameSuggestion.basedOnMediaFiles') }}:
        {{ mediaFiles.join(', ') }}</small
      >
    </div>

    <div class="suggestion-input-container">
      <input
        v-model="renameValue"
        class="suggestion-input"
        :class="{ 'non-compliant': renameValue.trim() && !isCompliant }"
        :placeholder="t('fileRenameSuggestion.enterNewName')"
        @keydown.enter="confirmRename"
        @focus="clearCloseTimer"
        @blur="startCloseTimer"
      />
      <div v-if="renameValue.trim() && !isCompliant" class="compliance-warning">
        <i class="fas fa-exclamation-triangle"></i>
        <small>{{ t('fileRenameSuggestion.notCompliant') }}</small>
      </div>
      <button
        class="suggestion-confirm-btn"
        :disabled="!isValidRename || isRenaming"
        @click="confirmRename"
        @focus="clearCloseTimer"
        @blur="startCloseTimer"
      >
        <i v-if="isRenaming" class="fas fa-spinner fa-spin"></i>
        {{
          isRenaming
            ? t('fileRenameSuggestion.renaming')
            : t('fileRenameSuggestion.confirm')
        }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { isElanFilenameCompliant } from '@/utils/elanFilenameCompliance';
import gitService from '@/api/service/gitService.js';

const { t } = useI18n();
const props = defineProps({
  suggestion: { type: String, required: true },
  currentFilename: { type: String, required: true },
  projectName: { type: String, required: true },
  elanId: { type: Number, required: true },
  standard: { type: Object, default: null },
  mediaFiles: { type: Array, default: () => [] },
  placement: {
    type: String,
    default: 'right',
    validator: (value) => ['right', 'left', 'top', 'bottom'].includes(value),
  },
});
const emit = defineEmits(['accept', 'close', 'error', 'conflict']);

const renameValue = ref('');
const isRenaming = ref(false);

const isValidRename = computed(() => {
  const trimmedValue = renameValue.value.trim();
  if (!trimmedValue || trimmedValue === props.currentFilename) return false;
  if (!props.standard) return false;

  console.log(
    'FileRenameSuggestion - Checking compliance for:',
    trimmedValue,
    'with standard:',
    props.standard
  );
  const result = isElanFilenameCompliant(props.standard, trimmedValue);
  console.log('FileRenameSuggestion - Compliance result:', result);
  return result;
});

const isCompliant = computed(() => {
  const trimmedValue = renameValue.value.trim();
  if (!trimmedValue || !props.standard) return false;
  return isElanFilenameCompliant(props.standard, trimmedValue);
});

let closeTimer = null;
function startCloseTimer() {
  clearCloseTimer();
  closeTimer = setTimeout(() => emit('close'), 1500);
}
function clearCloseTimer() {
  if (closeTimer) {
    clearTimeout(closeTimer);
    closeTimer = null;
  }
}

async function confirmRename() {
  if (!isValidRename.value || isRenaming.value) return;

  isRenaming.value = true;
  try {
    const result = await gitService.renameFile(
      props.projectName,
      props.elanId,
      renameValue.value.trim()
    );

    // Check if the operation was successful or if there was a conflict
    if (result.success) {
      emit('accept', renameValue.value.trim());
      emit('close');
    } else if (result.conflict_elan_id) {
      // Handle conflict case - log the conflicting files for future merge tool
      console.log('Rename conflict detected:', {
        currentElanId: props.elanId,
        conflictElanId: result.conflict_elan_id,
        targetFilename: renameValue.value.trim(),
        currentFilename: props.currentFilename,
      });

      // Emit conflict event with conflict information
      emit('conflict', {
        currentElanId: props.elanId,
        conflictElanId: result.conflict_elan_id,
        targetFilename: renameValue.value.trim(),
        currentFilename: props.currentFilename,
        messageKey: result.message_key || 'rename.conflict',
      });

      emit('close');
    } else {
      // Other error case
      emit('error', new Error(result.message || 'Failed to rename file'));
    }
  } catch (error) {
    console.error('Error renaming file:', error);
    emit('error', error);
  } finally {
    isRenaming.value = false;
  }
}

onMounted(() => {
  // Pre-fill with the suggestion
  renameValue.value = props.suggestion;
});

// Watch for changes in suggestion prop and update the input
watch(
  () => props.suggestion,
  (newSuggestion) => {
    renameValue.value = newSuggestion;
  },
  { immediate: true }
);

// Watch for changes in currentFilename to ensure we're showing the right file
watch(
  () => props.currentFilename,
  () => {
    renameValue.value = props.suggestion;
  },
  { immediate: true }
);
</script>

<style scoped>
.file-rename-suggestion-popover {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  box-shadow: 0 18px 45px rgb(15 23 42 / 18%);
  padding: 1rem;
  width: min(20rem, calc(100vw - 1.5rem));
  max-height: calc(100vh - 1.5rem);
  overflow: visible;
  z-index: 1000;
  font-size: 0.98rem;
  position: fixed;

  /* Smooth appearance animation */
  animation: popover-fade-in 0.2s ease-out;
  transform-origin: center;
}

@keyframes popover-fade-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Create arrow/pointer based on placement */
.file-rename-suggestion-popover::before,
.file-rename-suggestion-popover::after {
  content: '';
  position: absolute;
  border: solid transparent;
}

/* Arrow pointing to the filename - right placement (default) */
.file-rename-suggestion-popover::before {
  border-width: 8px;
  border-right-color: #94a3b8;
  top: var(--arrow-offset, 50%);
  left: -16px;
  transform: translateY(-50%);
}

.file-rename-suggestion-popover::after {
  border-width: 7px;
  border-right-color: #fff;
  top: var(--arrow-offset, 50%);
  left: -14px;
  transform: translateY(-50%);
}

/* Left placement - arrow points right */
.file-rename-suggestion-popover--left::before {
  border-left-color: #94a3b8;
  border-right-color: transparent;
  left: auto;
  right: -16px;
  top: var(--arrow-offset, 50%);
  transform: translateY(-50%);
}

.file-rename-suggestion-popover--left::after {
  border-left-color: #fff;
  border-right-color: transparent;
  left: auto;
  right: -14px;
  top: var(--arrow-offset, 50%);
  transform: translateY(-50%);
}

/* Top placement - arrow points down */
.file-rename-suggestion-popover--top::before {
  border-top-color: #94a3b8;
  border-right-color: transparent;
  top: auto;
  bottom: -16px;
  left: var(--arrow-offset, 50%);
  transform: translateX(-50%);
}

.file-rename-suggestion-popover--top::after {
  border-top-color: #fff;
  border-right-color: transparent;
  top: auto;
  bottom: -14px;
  left: var(--arrow-offset, 50%);
  transform: translateX(-50%);
}

/* Bottom placement - arrow points up */
.file-rename-suggestion-popover--bottom::before {
  border-bottom-color: #94a3b8;
  border-right-color: transparent;
  bottom: auto;
  top: -16px;
  left: var(--arrow-offset, 50%);
  transform: translateX(-50%);
}

.file-rename-suggestion-popover--bottom::after {
  border-bottom-color: #fff;
  border-right-color: transparent;
  bottom: auto;
  top: -14px;
  left: var(--arrow-offset, 50%);
  transform: translateX(-50%);
}

.suggestion-title {
  font-weight: 600;
  color: #d32f2f;
  margin-bottom: 8px;
}

.media-files-info {
  color: #666;
  font-size: 0.85rem;
  margin-bottom: 8px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
  border-left: 3px solid #1565c0;
}

.suggestion-input-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestion-input {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 0.95rem;
  font-family: monospace;
  width: 100%;
}

.suggestion-input:focus {
  outline: none;
  border-color: #2196f3;
}

.suggestion-input.non-compliant {
  border-color: #f44336;
  background-color: #fff8f8;
}

.compliance-warning {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #f44336;
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.compliance-warning i {
  color: #f44336;
}

.suggestion-confirm-btn {
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 0.95rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.suggestion-confirm-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.suggestion-confirm-btn:hover:not(:disabled) {
  background: #1565c0;
}
</style>
