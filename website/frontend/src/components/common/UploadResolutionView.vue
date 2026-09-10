<template>
  <div class="upload-resolution">
    <div class="resolution-header">
      <h3>Reviewing submitted differences</h3>
      <p class="resolution-summary">
        {{ upload.conflicted_files?.length || 0 }} file(s) overlap with accepted
        the current project version and need a decision.
      </p>
    </div>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>Loading conflict details...</p>
    </div>

    <div v-else class="resolution-content">
      <ReviewCasePanel
        v-if="showCorrectionWorkflow"
        ref="reviewPanel"
        :project-id="projectId"
        :project-name="projectName"
        :upload-id="upload.upload_id"
        :filenames="upload.conflicted_files || []"
      />
      <section
        v-if="upload.conflicted_files?.length > 0"
        class="conflicted-files"
        aria-labelledby="conflicted-files-title"
      >
        <div class="section-heading">
          <div>
            <span class="step-label">Step 1</span>
            <h4 id="conflicted-files-title">Inspect overlapping files</h4>
            <p>
              Compare the current project and submitted annotations before
              choosing an outcome.
            </p>
          </div>
        </div>
        <div class="files-list">
          <div
            v-for="file in upload.conflicted_files"
            :key="file"
            class="conflict-file-item"
          >
            <div class="file-info">
              <span class="file-name">{{ file }}</span>
              <span class="file-status">Both versions changed this file</span>
            </div>
            <button
              type="button"
              class="action-btn view-btn"
              :aria-expanded="selectedConflictFile === file"
              @click="toggleFileComparison(file)"
            >
              {{
                selectedConflictFile === file
                  ? 'Hide comparison'
                  : 'Compare annotations'
              }}
            </button>
          </div>
        </div>

        <section
          v-if="selectedConflictFile"
          class="inline-comparison"
          aria-live="polite"
        >
          <header>
            <div>
              <span class="step-label">Annotation comparison</span>
              <h4>{{ selectedConflictFile }}</h4>
            </div>
            <button
              type="button"
              class="close-inline"
              @click="closeFileConflict"
            >
              Close comparison
            </button>
          </header>
          <ConflictMergeView
            :project-name="projectName"
            :branch-name="upload.branch_name"
            :filename="selectedConflictFile"
            allow-open-review
            @open-review="openTargetedReview"
            @loaded="recordComparison"
          />
        </section>
      </section>

      <!-- Strategy Selection -->
      <div class="strategy-section">
        <span class="step-label">Step 2</span>
        <h4>Choose what contribution #{{ upload.upload_id }} should do</h4>
        <div class="strategy-options">
          <button
            type="button"
            class="strategy-option"
            role="radio"
            :aria-checked="resolutionStrategy === 'accept_incoming'"
            @click="toggleStrategy('accept_incoming')"
          >
            <span class="decision-indicator" aria-hidden="true">
              <font-awesome-icon
                v-if="resolutionStrategy === 'accept_incoming'"
                icon="fa-solid fa-check"
              />
            </span>
            <div class="strategy-content">
              <strong
                >Replace current project files with the submitted
                versions</strong
              >
              <p>
                The submitted file replaces the file in the current project,
                including annotations not changed intentionally by the
                contributor.
              </p>
            </div>
          </button>

          <button
            type="button"
            class="strategy-option"
            role="radio"
            :aria-checked="resolutionStrategy === 'accept_current'"
            @click="toggleStrategy('accept_current')"
          >
            <span class="decision-indicator" aria-hidden="true">
              <font-awesome-icon
                v-if="resolutionStrategy === 'accept_current'"
                icon="fa-solid fa-check"
              />
            </span>
            <div class="strategy-content">
              <strong
                >Keep current project files and discard overlapping
                changes</strong
              >
              <p>
                The current project file remains. Only additional,
                non-overlapping files from this contribution are merged.
              </p>
            </div>
          </button>

          <aside class="correction-path">
            <div class="strategy-content">
              <strong>Need a mixed or corrected version?</strong>
              <p>
                Neither whole-file outcome is suitable. Ask the contributor to
                combine the intended annotations in ELAN and submit a new
                revision.
              </p>
            </div>
            <button
              type="button"
              class="correction-button"
              @click="openCorrectionComposer"
            >
              Request a corrected version
            </button>
          </aside>
        </div>
      </div>

      <!-- File Changes Preview -->
      <div v-if="nonOverlappingCount" class="changes-preview">
        <h4>Additional files included</h4>
        <div class="changes-grid">
          <div v-if="otherFiles.new.length" class="change-group">
            <h5>New files ({{ otherFiles.new.length }})</h5>
            <ul class="change-list">
              <li v-for="file in otherFiles.new.slice(0, 5)" :key="file">
                {{ file }}
              </li>
              <li v-if="otherFiles.new.length > 5" class="more-files">
                ... and {{ otherFiles.new.length - 5 }} more
              </li>
            </ul>
          </div>

          <div v-if="otherFiles.modified.length" class="change-group">
            <h5>Modified files ({{ otherFiles.modified.length }})</h5>
            <ul class="change-list">
              <li v-for="file in otherFiles.modified.slice(0, 5)" :key="file">
                {{ file }}
              </li>
              <li v-if="otherFiles.modified.length > 5" class="more-files">
                ... and {{ otherFiles.modified.length - 5 }} more
              </li>
            </ul>
          </div>

          <div v-if="otherFiles.deleted.length" class="change-group">
            <h5>Deleted files ({{ otherFiles.deleted.length }})</h5>
            <ul class="change-list">
              <li v-for="file in otherFiles.deleted.slice(0, 5)" :key="file">
                {{ file }}
              </li>
              <li v-if="otherFiles.deleted.length > 5" class="more-files">
                ... and {{ otherFiles.deleted.length - 5 }} more
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Resolution Actions -->
      <div class="resolution-actions">
        <div v-if="resolutionStrategy" class="decision-confirmation">
          <header>
            <div>
              <span class="step-label">Step 3 · Confirm</span>
              <h4>{{ decisionTitle }}</h4>
            </div>
            <button
              type="button"
              class="clear-decision"
              @click="toggleStrategy(resolutionStrategy)"
            >
              Clear choice
            </button>
          </header>
          <p class="decision-consequence">{{ decisionConsequence }}</p>
          <p v-if="semanticEffect" class="decision-impact">
            <strong>Annotation impact:</strong> {{ semanticEffect }}.
          </p>
          <p class="completion-note">
            After this action, contribution #{{ upload.upload_id }} is closed
            and removed from
            <router-link :to="incomingWorkRoute">Incoming work</router-link>.
          </p>
          <label>
            <input v-model="decisionAcknowledged" type="checkbox" />
            {{ decisionAcknowledgement }}
          </label>
        </div>
        <button
          class="action-btn resolve-btn"
          :disabled="!resolutionStrategy || !decisionAcknowledged || resolving"
          @click="applyResolution"
        >
          {{ resolving ? 'Completing contribution…' : finalActionLabel }}
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

    <!-- Error Display -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
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

const selectedConflictFile = ref(null);
const decisionAcknowledged = ref(false);
const showCorrectionWorkflow = ref(false);
const reviewPanel = ref(null);
const comparisons = ref({});

const otherFiles = computed(() => {
  const conflicts = new Set(props.upload.conflicted_files || []);
  return {
    new: (props.upload.files?.new || []).filter((file) => !conflicts.has(file)),
    modified: (props.upload.files?.modified || []).filter(
      (file) => !conflicts.has(file)
    ),
    deleted: (props.upload.files?.deleted || []).filter(
      (file) => !conflicts.has(file)
    ),
  };
});
const nonOverlappingCount = computed(() => {
  return Object.values(otherFiles.value).reduce(
    (total, files) => total + files.length,
    0
  );
});
const incomingWorkRoute = computed(() => ({
  path: '/contribution',
  query: { project: props.projectId, view: 'queue' },
}));
const decisionTitle = computed(() =>
  resolutionStrategy.value === 'accept_incoming'
    ? 'Merge the submitted file into the project'
    : 'Close without merging the overlapping file'
);
const decisionConsequence = computed(() =>
  resolutionStrategy.value === 'accept_incoming'
    ? "The contributor's complete file will replace the current project file."
    : 'The current project file stays unchanged. Its submitted replacement is discarded.'
);
const finalActionLabel = computed(() =>
  resolutionStrategy.value === 'accept_incoming'
    ? 'Merge #' + props.upload.upload_id + ' into project'
    : 'Close #' + props.upload.upload_id + ' without merging file'
);
const decisionAcknowledgement = computed(() =>
  resolutionStrategy.value === 'accept_incoming'
    ? 'I reviewed the comparison and want to replace the current project file.'
    : 'I reviewed the comparison and want to discard the overlapping submitted file.'
);
const semanticEffect = computed(() => {
  const changes = Object.values(comparisons.value).flatMap(
    (review) => review?.changes || []
  );
  if (!changes.length) return '';
  const counts = {};
  for (const change of changes) {
    for (const kind of change.kinds) counts[kind] = (counts[kind] || 0) + 1;
  }
  const labels = {
    added: ['addition', 'additions'],
    removed: ['removal', 'removals'],
    value_changed: ['value change', 'value changes'],
    tier_changed: ['tier change', 'tier changes'],
    timing_changed: ['timing change', 'timing changes'],
  };
  const parts = Object.entries(counts).map(([kind, count]) => {
    const forms = labels[kind] || [
      kind.replaceAll('_', ' '),
      kind.replaceAll('_', ' '),
    ];
    return `${count} ${forms[count === 1 ? 0 : 1]}`;
  });
  const summary =
    parts.length > 1
      ? `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}`
      : parts[0];
  return resolutionStrategy.value === 'accept_incoming'
    ? 'Apply ' + summary
    : 'Discard ' + summary;
});

watch(resolutionStrategy, () => {
  decisionAcknowledged.value = false;
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

    resolutionProgress.value = 100;
    resolutionMessage.value = 'Resolution complete!';
    emit('resolved', result);
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to resolve upload';
    console.error('Resolution error:', e);
  } finally {
    resolving.value = false;
    resolutionProgress.value = 0;
    resolutionMessage.value = '';
  }
}

function toggleFileComparison(filename) {
  selectedConflictFile.value =
    selectedConflictFile.value === filename ? null : filename;
}

function closeFileConflict() {
  selectedConflictFile.value = null;
}

function openTargetedReview(target) {
  reviewPanel.value?.openComposer(target);
}

function recordComparison({ filename, review }) {
  comparisons.value = { ...comparisons.value, [filename]: review };
}

async function openCorrectionComposer() {
  resolutionStrategy.value = '';
  showCorrectionWorkflow.value = true;
  await nextTick();
  reviewPanel.value?.openComposer();
}

function toggleStrategy(strategy) {
  resolutionStrategy.value =
    resolutionStrategy.value === strategy ? '' : strategy;
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
  position: relative;
  align-items: flex-start;
  width: 100%;
  gap: 12px;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  color: inherit;
  background: white;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    box-shadow 0.18s ease;
}

.strategy-option[aria-checked='true'] {
  border-color: #2563eb;
  background: #f5f9ff;
  box-shadow: 0 0 0 1px #2563eb;
}

.decision-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 1.15rem;
  height: 1.15rem;
  margin-top: 0.15rem;
  border: 1.5px solid #94a3b8;
  border-radius: 50%;
  color: white;
  background: white;
  font-size: 0.72rem;
  font-weight: 800;
}

.strategy-option:hover {
  border-color: #1976d2;
}

.strategy-option[aria-checked='true'] .decision-indicator {
  border-color: #2563eb;
  background: #2563eb;
}

.strategy-option[aria-checked='true'] .strategy-content {
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

.correction-path {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 16px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
}

.correction-button,
.close-inline {
  flex: none;
  padding: 0.65rem 0.85rem;
  border: 1px solid #8b5cf6;
  border-radius: 0.5rem;
  color: #6d28d9;
  background: white;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.step-label {
  display: inline-block;
  margin-bottom: 0.35rem;
  color: #1d4ed8;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.section-heading h4,
.section-heading p {
  margin: 0;
}

.section-heading p {
  margin-top: 0.25rem;
  color: #64748b;
}

.conflicted-files {
  margin-bottom: 30px;
  padding: 20px;
  background: #fff3e0;
  border-radius: 8px;
  border-left: 4px solid #f57c00;
}

.conflicted-files h4 {
  color: #1e293b;
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

.inline-comparison {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #bfdbfe;
  border-radius: 0.65rem;
  background: white;
}

.inline-comparison > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid #dbeafe;
}

.inline-comparison > header h4 {
  margin: 0;
  overflow-wrap: anywhere;
}

.inline-comparison :deep(.review-list) {
  max-height: none;
  overflow: visible;
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
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
}

.decision-confirmation {
  flex: 1 0 100%;
  padding: 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.65rem;
  background: #f8fafc;
}

.decision-confirmation > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.decision-confirmation h4,
.decision-confirmation p {
  margin: 0 0 0.5rem;
}

.clear-decision {
  flex: none;
  padding: 0.35rem 0.55rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.4rem;
  color: #475569;
  background: white;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.decision-consequence {
  color: #475569;
}

.decision-confirmation .decision-impact {
  margin: 0.75rem 0;
  padding: 0.7rem 0.8rem;
  border-left: 3px solid #2563eb;
  background: white;
}

.completion-note {
  color: #475569;
  font-size: 0.9rem;
}

.completion-note a {
  color: #1d4ed8;
  font-weight: 700;
}

.decision-confirmation label {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e2e8f0;
  font-weight: 700;
}

.decision-confirmation input {
  flex: none;
  width: 1rem;
  height: 1rem;
  margin-top: 0.15rem;
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

@media (width <= 700px) {
  .conflict-file-item,
  .correction-path,
  .inline-comparison > header,
  .decision-confirmation > header {
    align-items: stretch;
    flex-direction: column;
  }

  .view-btn,
  .correction-button,
  .close-inline,
  .clear-decision,
  .resolution-actions > .action-btn {
    width: 100%;
  }
}
</style>
