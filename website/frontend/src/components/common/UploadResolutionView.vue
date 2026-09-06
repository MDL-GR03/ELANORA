<template>
  <div class="upload-resolution">
    <div class="resolution-header">
      <h3>Reviewing submitted differences</h3>
      <p class="resolution-summary">
        {{ upload.conflicted_files?.length || 0 }} file(s) overlap with accepted
        project work and need a decision.
      </p>
    </div>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>Loading conflict details...</p>
    </div>

    <div v-else class="resolution-content">
      <ReviewCasePanel
        ref="reviewPanel"
        :project-id="projectId"
        :upload-id="upload.upload_id"
        :filenames="upload.conflicted_files || []"
      />
      <!-- Strategy Selection -->
      <div class="strategy-section">
        <h4>Decision for overlapping files</h4>
        <div class="strategy-options">
          <label class="strategy-option">
            <input
              v-model="resolutionStrategy"
              type="radio"
              value="accept_incoming"
            />
            <div class="strategy-content">
              <strong>Use the submitted versions</strong>
              <p>
                Accept the contributor's version wherever the same file changed
              </p>
            </div>
          </label>

          <label class="strategy-option">
            <input
              v-model="resolutionStrategy"
              type="radio"
              value="accept_current"
            />
            <div class="strategy-content">
              <strong>Keep the accepted versions</strong>
              <p>
                Keep the shared version for overlapping files and accept only
                the submission's non-overlapping work
              </p>
            </div>
          </label>

          <div class="strategy-option guidance-option">
            <div class="strategy-content">
              <strong>Need a mixed or corrected version?</strong>
              <p>
                Inspect each EAF comparison, then ask the contributor to make
                corrections in ELAN and upload a new revision.
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Conflicted Files -->
      <div v-if="upload.conflicted_files?.length > 0" class="conflicted-files">
        <h4>Conflicted Files</h4>
        <div class="files-list">
          <div
            v-for="file in upload.conflicted_files"
            :key="file"
            class="conflict-file-item"
          >
            <div class="file-info">
              <span class="file-name">{{ file }}</span>
              <span class="file-status">Merge conflict</span>
            </div>
            <div class="file-actions">
              <button
                class="action-btn view-btn"
                @click="viewFileConflict(file)"
              >
                Preview annotations
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- File Changes Preview -->
      <div class="changes-preview">
        <h4>Changes in this Upload</h4>
        <div class="changes-grid">
          <div v-if="upload.files?.new?.length > 0" class="change-group">
            <h5>New Files ({{ upload.files.new.length }})</h5>
            <ul class="change-list">
              <li v-for="file in upload.files.new.slice(0, 5)" :key="file">
                {{ file }}
              </li>
              <li v-if="upload.files.new.length > 5" class="more-files">
                ... and {{ upload.files.new.length - 5 }} more
              </li>
            </ul>
          </div>

          <div v-if="upload.files?.modified?.length > 0" class="change-group">
            <h5>Modified Files ({{ upload.files.modified.length }})</h5>
            <ul class="change-list">
              <li v-for="file in upload.files.modified.slice(0, 5)" :key="file">
                {{ file }}
              </li>
              <li v-if="upload.files.modified.length > 5" class="more-files">
                ... and {{ upload.files.modified.length - 5 }} more
              </li>
            </ul>
          </div>

          <div v-if="upload.files?.deleted?.length > 0" class="change-group">
            <h5>Deleted Files ({{ upload.files.deleted.length }})</h5>
            <ul class="change-list">
              <li v-for="file in upload.files.deleted.slice(0, 5)" :key="file">
                {{ file }}
              </li>
              <li v-if="upload.files.deleted.length > 5" class="more-files">
                ... and {{ upload.files.deleted.length - 5 }} more
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Resolution Actions -->
      <div class="resolution-actions">
        <button
          class="action-btn resolve-btn"
          :disabled="!resolutionStrategy || resolving"
          @click="applyResolution"
        >
          {{ resolving ? 'Accepting...' : 'Accept with this decision' }}
        </button>

        <button class="action-btn cancel-btn" @click="$emit('cancelled')">
          Cancel
        </button>
      </div>

      <!-- Progress -->
      <div v-if="resolving" class="resolution-progress">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="`width: ${resolutionProgress}%`"
          ></div>
        </div>
        <p class="progress-text">{{ resolutionMessage }}</p>
      </div>
    </div>

    <!-- File Conflict Modal -->
    <div
      v-if="showFileConflict"
      class="modal-overlay"
      @click="closeFileConflict"
    >
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>Conflict in: {{ selectedConflictFile }}</h3>
          <button class="close-btn" @click="closeFileConflict">×</button>
        </div>

        <div class="modal-body">
          <ConflictMergeView
            v-if="selectedConflictFile"
            :project-name="projectName"
            :branch-name="upload.branch_name"
            :filename="selectedConflictFile"
            @open-review="openTargetedReview"
            @resolved="onFileResolved"
          />
        </div>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import gitService from '@/api/service/gitService';
import ConflictMergeView from '@/components/common/ConflictMergeView.vue';
import ReviewCasePanel from '@/components/common/ReviewCasePanel.vue';

const props = defineProps({
  projectId: {
    type: Number,
    required: true,
  },
  projectName: {
    type: String,
    required: true,
  },
  upload: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(['resolved', 'cancelled']);

// State
const loading = ref(false);
const resolving = ref(false);
const resolutionProgress = ref(0);
const resolutionMessage = ref('');
const resolutionStrategy = ref('');
const error = ref('');

// File conflict modal
const showFileConflict = ref(false);
const selectedConflictFile = ref(null);
const reviewPanel = ref(null);

onMounted(() => {
  // Load any additional conflict details if needed
});

async function applyResolution() {
  if (!resolutionStrategy.value) {
    error.value = 'Please select a resolution strategy';
    return;
  }

  try {
    resolving.value = true;
    resolutionProgress.value = 10;
    resolutionMessage.value = 'Starting resolution...';
    error.value = '';

    resolutionProgress.value = 30;
    resolutionMessage.value = 'Applying resolution strategy...';

    const result = await gitService.adminCompleteMerge(
      props.projectName,
      props.upload.branch_name,
      resolutionStrategy.value
    );

    resolutionProgress.value = 80;
    resolutionMessage.value = 'Creating the accepted revision...';

    // Simulate final progress
    await new Promise((resolve) => setTimeout(resolve, 1000));

    resolutionProgress.value = 100;
    resolutionMessage.value = 'Resolution complete!';

    // Emit success after a brief delay
    setTimeout(() => {
      emit('resolved', result);
    }, 500);
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to resolve upload';
    console.error('Resolution error:', e);
  } finally {
    resolving.value = false;
    resolutionProgress.value = 0;
    resolutionMessage.value = '';
  }
}

function viewFileConflict(filename) {
  selectedConflictFile.value = filename;
  showFileConflict.value = true;
}

function closeFileConflict() {
  showFileConflict.value = false;
  selectedConflictFile.value = null;
}

function openTargetedReview(target) {
  closeFileConflict();
  reviewPanel.value?.openComposer(target);
}

function onFileResolved() {
  closeFileConflict();
  // Could refresh the upload status here
}
</script>

<style scoped>
.upload-resolution {
  padding: 20px 0;
}

.resolution-header {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.resolution-header h3 {
  margin: 0 0 10px;
  color: #2c3e50;
}

.resolution-summary {
  margin: 0;
  color: #666;
}

.loading {
  text-align: center;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e0e0e0;
  border-top: 4px solid #1976d2;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.strategy-section {
  margin-bottom: 30px;
}

.strategy-section h4 {
  margin: 0 0 15px;
  color: #2c3e50;
}

.strategy-options {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.strategy-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.3s;
}

.strategy-option:hover {
  border-color: #1976d2;
}

.strategy-option input[type='radio']:checked + .strategy-content {
  color: #1976d2;
}

.strategy-content strong {
  display: block;
  margin-bottom: 4px;
}

.strategy-content p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.conflicted-files {
  margin-bottom: 30px;
  padding: 20px;
  background: #fff3e0;
  border-radius: 8px;
  border-left: 4px solid #f57c00;
}

.conflicted-files h4 {
  margin: 0 0 15px;
  color: #f57c00;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.conflict-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-family: monospace;
  font-weight: 500;
}

.file-status {
  font-size: 0.8rem;
  color: #f57c00;
}

.changes-preview {
  margin-bottom: 30px;
}

.changes-preview h4 {
  margin: 0 0 15px;
  color: #2c3e50;
}

.changes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.change-group h5 {
  margin: 0 0 10px;
  color: #666;
  font-size: 0.9rem;
}

.change-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.change-list li {
  padding: 4px 0;
  font-family: monospace;
  font-size: 0.8rem;
  color: #555;
}

.more-files {
  color: #999;
  font-style: italic;
}

.resolution-actions {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.action-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.3s;
}

.resolve-btn {
  background: #4caf50;
  color: white;
}

.resolve-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.cancel-btn {
  background: #666;
  color: white;
}

.view-btn {
  background: #2196f3;
  color: white;
  padding: 8px 16px;
  font-size: 0.8rem;
}

.resolution-progress {
  margin-top: 20px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: #4caf50;
  transition: width 0.3s ease;
}

.progress-text {
  margin: 0;
  text-align: center;
  color: #666;
  font-size: 0.9rem;
}

.error-message {
  background: #ffebee;
  border: 1px solid #f44336;
  color: #d32f2f;
  padding: 16px;
  border-radius: 8px;
  margin-top: 20px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgb(0 0 0 / 50%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-overlay.large {
  align-items: flex-start;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content.large {
  width: 95%;
  max-width: 1400px;
  max-height: 90vh;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-body {
  padding: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}
</style>
