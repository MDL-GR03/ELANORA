<template>
  <div class="bulk-rename-dialog-overlay" @click="closeDialog">
    <div class="bulk-rename-dialog" @click.stop>
      <div class="dialog-header">
        <h2>{{ t('bulkRenameDialog.title') }}</h2>
        <button class="close-btn" @click="closeDialog">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <div class="dialog-content">
        <div v-if="loading" class="loading">
          {{ t('bulkRenameDialog.loading') }}
        </div>

        <div v-else-if="filesSuggestions.length === 0" class="no-suggestions">
          {{ t('bulkRenameDialog.noSuggestions') }}
        </div>

        <div v-else class="files-list">
          <div
            v-for="file in filesSuggestions"
            :key="file.name"
            class="file-rename-item"
            :class="{
              'non-compliant':
                file.newName &&
                file.newName.trim() &&
                !isFileCompliant(file.newName),
              'has-rename':
                file.newName &&
                file.newName.trim() &&
                file.newName !== file.name,
            }"
          >
            <div class="file-current">
              <strong>{{ t('bulkRenameDialog.current') }}:</strong>
              {{ file.name }}
            </div>

            <div class="file-suggestion">
              <strong>{{ t('bulkRenameDialog.suggested') }}:</strong>
              <input
                v-model="file.newName"
                class="suggestion-input"
                :placeholder="
                  file.suggestedName || t('bulkRenameDialog.enterNewName')
                "
              />
            </div>

            <div
              v-if="file.extractedComponents && file.mediaFiles"
              class="extracted-info"
            >
              <small
                >{{ t('bulkRenameDialog.extractedFrom') }}:
                {{ file.mediaFiles?.join(', ') }}</small
              >
            </div>

            <div
              v-if="
                file.newName &&
                file.newName.trim() &&
                !isFileCompliant(file.newName)
              "
              class="compliance-warning"
            >
              <i class="fas fa-exclamation-triangle"></i>
              <small>{{ t('bulkRenameDialog.notCompliant') }}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="dialog-footer">
        <button class="cancel-btn" @click="closeDialog">
          {{ t('common.cancel') }}
        </button>
        <button
          class="apply-btn"
          :disabled="!canApplyRenames"
          @click="applyRenames"
        >
          <i v-if="isRenaming" class="fas fa-spinner fa-spin"></i>
          {{
            isRenaming
              ? t('bulkRenameDialog.renaming')
              : t('bulkRenameDialog.renameAll')
          }}
        </button>

        <div v-if="!allRenamesCompliant" class="compliance-error">
          <small>{{ t('bulkRenameDialog.complianceRequired') }}</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { generateMediaBasedSuggestions } from '@/utils/filenameFromMediaFile';
import { isElanFilenameCompliant } from '@/utils/elanFilenameCompliance';
import gitService from '@/api/service/gitService';

const { t } = useI18n();

const props = defineProps({
  files: {
    type: Array,
    required: true,
  },
  allFiles: {
    type: Array,
    required: true,
  },
  projectId: {
    type: Number,
    required: true,
  },
  projectName: {
    type: String,
    required: true,
  },
  projectStandard: {
    type: Object,
    default: null,
  },
  mediaStandard: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['close', 'rename', 'conflict']);

const loading = ref(false);
const loadingSuggestions = ref(false);
const filesSuggestions = ref([]);
const isRenaming = ref(false);

// Initialize files with empty new names
const initializeFiles = () => {
  filesSuggestions.value = props.files.map((file) => ({
    ...file,
    newName: '',
    suggestedName: null,
    extractedComponents: null,
    mediaFiles: null,
  }));
};

// Helper function to check compliance, handling .eaf extension properly
const isFileCompliant = (filename) => {
  if (!props.projectStandard || !filename || !filename.trim()) return false;
  return isElanFilenameCompliant(props.projectStandard, filename.trim());
};

const hasValidRenames = computed(() => {
  return filesSuggestions.value.some(
    (file) => file.newName && file.newName.trim() && file.newName !== file.name
  );
});

const allRenamesCompliant = computed(() => {
  if (!props.projectStandard) return false; // Changed: require standard for compliance

  return filesSuggestions.value.every((file) => {
    if (!file.newName || !file.newName.trim() || file.newName === file.name) {
      return true; // Skip files with no rename
    }

    return isFileCompliant(file.newName);
  });
});

const canApplyRenames = computed(() => {
  return (
    hasValidRenames.value && allRenamesCompliant.value && !isRenaming.value
  );
});

async function generateSuggestions() {
  loadingSuggestions.value = true;
  try {
    // Check if we have the required standards
    if (!props.mediaStandard || !props.projectStandard) {
      console.warn('Missing required standards for suggestion generation');
      return;
    }

    // Use the already-fetched files with media (passed as prop)
    const filesWithMedia = { files: props.allFiles };

    // Generate suggestions using the passed standards
    const suggestions = generateMediaBasedSuggestions(
      filesWithMedia.files,
      props.mediaStandard,
      props.projectStandard
    );

    // Update files with suggestions
    filesSuggestions.value = filesSuggestions.value.map((file) => {
      const suggestion = suggestions.find((s) => s.currentName === file.name);
      if (suggestion) {
        return {
          ...file,
          suggestedName: suggestion.suggestedName,
          extractedComponents: suggestion.extractedComponents,
          mediaFiles: suggestion.mediaFiles,
          newName: suggestion.suggestedName, // Pre-fill with suggestion
        };
      }
      return file;
    });
  } catch (error) {
    console.error('Error generating suggestions:', error);
  } finally {
    loadingSuggestions.value = false;
  }
}

function closeDialog() {
  emit('close');
}

async function applyRenames() {
  if (!canApplyRenames.value) return;

  isRenaming.value = true;
  try {
    const renames = filesSuggestions.value
      .filter(
        (file) =>
          file.newName && file.newName.trim() && file.newName !== file.name
      )
      .map((file) => ({
        elan_id: file.elan_id,
        new_filename: file.newName.trim(),
      }));

    if (renames.length > 0) {
      const result = await gitService.renameFiles(props.projectName, renames);

      // Handle conflicts and other results
      if (result.conflicts_count > 0) {
        // Collect conflict files for future merge tool
        const conflictFiles = result.results.filter((r) => r.conflict_elan_id);
        console.log('Bulk rename conflicts detected:', conflictFiles);

        // Emit conflict event with conflict information
        emit('conflict', {
          conflictFiles: conflictFiles,
          conflictsCount: result.conflicts_count,
          messageKey: result.message_key || 'rename.conflictMultiple',
          totalFiles: result.total_files,
          successfulRenames: result.successful_renames,
        });
      }

      emit('rename', {
        renames: renames,
        result: result,
      });
    }
    closeDialog();
  } catch (error) {
    console.error('Error applying renames:', error);
    // Could emit an error event or show a notification here
  } finally {
    isRenaming.value = false;
  }
}

onMounted(async () => {
  initializeFiles();
  // Auto-generate suggestions on mount
  await generateSuggestions();
});
</script>

<style scoped>
.bulk-rename-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgb(0 0 0 / 50%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.bulk-rename-dialog {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgb(0 0 0 / 10%);
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
}

.dialog-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #666;
}

.close-btn:hover {
  color: #333;
}

.dialog-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.loading,
.no-suggestions {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.suggestions-header {
  margin-bottom: 1rem;
}

.generate-suggestions-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.generate-suggestions-btn:hover {
  background: #45a049;
}

.generate-suggestions-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.file-rename-item {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 0.5rem;
  transition: border-color 0.2s;
}

.file-rename-item.has-rename {
  border-color: #4caf50;
  background-color: #f8fff8;
}

.file-rename-item.non-compliant {
  border-color: #f44336;
  background-color: #fff8f8;
}

.file-current {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.file-suggestion {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.suggestion-input {
  flex: 1;
  padding: 0.25rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: monospace;
}

.extracted-info {
  color: #666;
  font-size: 0.8rem;
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
  flex-wrap: wrap;
}

.compliance-error {
  flex-basis: 100%;
  text-align: center;
  color: #f44336;
  margin-top: 0.5rem;
}

.cancel-btn,
.apply-btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.cancel-btn {
  background: #f5f5f5;
  border: 1px solid #ccc;
  color: #333;
}

.cancel-btn:hover {
  background: #e0e0e0;
}

.apply-btn {
  background: #1976d2;
  border: none;
  color: white;
}

.apply-btn:hover {
  background: #1565c0;
}

.apply-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
