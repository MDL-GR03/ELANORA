<template>
  <div class="pending-uploads-page">
    <div class="pending-uploads-container">
      <WorkspaceHeader
        embedded
        :context="currentProjectName"
        :title="t('pendingUploads.title')"
        :description="t('pendingUploads.pageDescription')"
      />

      <nav
        class="contribution-tabs"
        role="tablist"
        aria-label="Contribution views"
      >
        <button
          id="contribution-queue-tab"
          type="button"
          role="tab"
          :aria-selected="activeView === 'queue'"
          aria-controls="contribution-queue-panel"
          :class="{ active: activeView === 'queue' }"
          @click="setActiveView('queue')"
        >
          Incoming work
          <span v-if="pendingUploads.length">{{ pendingUploads.length }}</span>
        </button>
        <button
          id="contribution-reviews-tab"
          type="button"
          role="tab"
          :aria-selected="activeView === 'reviews'"
          aria-controls="contribution-reviews-panel"
          :class="{ active: activeView === 'reviews' }"
          @click="setActiveView('reviews')"
        >
          Questions and corrections
          <span v-if="activeReviewCount">{{ activeReviewCount }}</span>
        </button>
      </nav>

      <!-- No Project Selected -->
      <div v-if="!currentProject" class="no-selection">
        <div class="no-selection-icon">
          <font-awesome-icon icon="fa-solid fa-folder-open" />
        </div>
        <h3>{{ t('pendingUploads.noProjectSelected.title') }}</h3>
        <p>{{ t('pendingUploads.noProjectSelected.message') }}</p>
        <router-link to="/projects" class="select-project-btn">
          {{ t('pendingUploads.noProjectSelected.selectProject') }}
        </router-link>
      </div>

      <!-- Loading State -->
      <div v-else-if="activeView === 'queue' && uploadsLoading" class="loading">
        <div class="loading-spinner"></div>
        <p>{{ t('pendingUploads.loading') }}</p>
      </div>

      <!-- No Pending Uploads -->
      <div
        v-else-if="activeView === 'queue' && pendingUploads.length === 0"
        class="no-uploads"
      >
        <div class="no-uploads-icon">
          <font-awesome-icon icon="fa-solid fa-circle-check" />
        </div>
        <h3>{{ t('pendingUploads.noUploads.title') }}</h3>
        <p>{{ t('pendingUploads.noUploads.message') }}</p>
      </div>

      <!-- Pending Uploads List -->
      <div
        v-else-if="activeView === 'queue'"
        id="contribution-queue-panel"
        class="uploads-section"
        role="tabpanel"
        aria-labelledby="contribution-queue-tab"
      >
        <div class="contributions-toolbar">
          <div>
            <h2>{{ t('pendingUploads.queueTitle') }}</h2>
            <p>{{ t('pendingUploads.queueDescription') }}</p>
          </div>
          <div class="contribution-toolbar-actions">
            <label v-if="canAdminister" class="automatic-policy">
              <input
                type="checkbox"
                :checked="currentProject.auto_accept_new_files"
                :disabled="policySaving"
                @change="updateAutomaticPolicy($event.target.checked)"
              />
              Automatically accept submissions containing only valid new files
            </label>
            <button
              type="button"
              class="refresh-contributions-btn"
              :disabled="actionBusy"
              @click="fetchPendingUploads(false)"
            >
              <font-awesome-icon icon="fa-solid fa-arrows-rotate" />
              {{ t('pendingUploads.actions.refresh') }}
            </button>
          </div>
        </div>
        <!-- Summary Stats -->
        <div class="uploads-summary">
          <div class="summary-card">
            <font-awesome-icon icon="fa-solid fa-inbox" />
            <h3>{{ totalPending }}</h3>
            <p>{{ t('pendingUploads.summary.totalPending') }}</p>
          </div>
          <div class="summary-card ready">
            <font-awesome-icon icon="fa-solid fa-circle-check" />
            <h3>{{ readyCount }}</h3>
            <p>{{ t('pendingUploads.summary.readyToMerge') }}</p>
          </div>
          <div class="summary-card conflicts">
            <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
            <h3>{{ conflictsCount }}</h3>
            <p>{{ t('pendingUploads.summary.needResolution') }}</p>
          </div>
        </div>

        <!-- Upload List -->
        <div class="uploads-list">
          <div
            v-for="upload in pendingUploads"
            :key="upload.upload_id"
            class="upload-item"
            :class="getUploadStatusClass(upload)"
          >
            <div class="upload-header">
              <div class="upload-info">
                <h3 class="upload-branch">
                  Contribution #{{ upload.upload_id }}
                </h3>
                <div class="upload-meta">
                  <span class="upload-type">{{
                    formatUploadType(upload.upload_type)
                  }}</span>
                  <span class="upload-date">{{
                    formatDate(upload.uploaded_at)
                  }}</span>
                  <span class="upload-user">{{
                    t('pendingUploads.uploadedBy', {
                      user: upload.uploaded_by || t('pendingUploads.unknown'),
                    })
                  }}</span>
                </div>
              </div>

              <div class="upload-status-section">
                <div class="upload-status">
                  <span
                    class="status-badge"
                    :class="getStatusClass(upload.merge_status)"
                  >
                    {{ formatStatus(upload.merge_status) }}
                  </span>
                </div>

                <!-- Actions -->
                <div class="upload-actions">
                  <button
                    type="button"
                    class="action-btn view-btn"
                    :disabled="actionBusy"
                    @click="viewUploadDetails(upload, $event)"
                  >
                    <font-awesome-icon icon="fa-solid fa-eye" />
                    {{ t('pendingUploads.actions.viewDetails') }}
                  </button>

                  <button
                    v-if="canAdminister && upload.merge_status !== 'duplicate'"
                    type="button"
                    class="action-btn review-btn"
                    :disabled="actionBusy"
                    @click="requestCorrection(upload, $event)"
                  >
                    <font-awesome-icon icon="fa-solid fa-comment-dots" />
                    Request correction
                  </button>

                  <button
                    v-if="canAdminister && upload.merge_status === 'duplicate'"
                    type="button"
                    class="action-btn dismiss-btn"
                    :disabled="actionBusy"
                    @click="dismissDuplicate(upload)"
                  >
                    <font-awesome-icon icon="fa-solid fa-box-archive" />
                    Dismiss duplicate
                  </button>

                  <button
                    v-if="
                      canAdminister && upload.merge_status === 'ready_to_merge'
                    "
                    class="action-btn merge-btn"
                    type="button"
                    :disabled="actionBusy"
                    @click="mergeUpload(upload)"
                  >
                    <font-awesome-icon icon="fa-solid fa-code-merge" />
                    {{
                      merging === upload.upload_id
                        ? t('pendingUploads.actions.merging')
                        : t('pendingUploads.actions.mergeNow')
                    }}
                  </button>

                  <button
                    v-if="
                      canAdminister &&
                      upload.merge_status === 'needs_resolution'
                    "
                    class="action-btn resolve-btn"
                    type="button"
                    :disabled="actionBusy"
                    @click="resolveUpload(upload, $event)"
                  >
                    <font-awesome-icon icon="fa-solid fa-screwdriver-wrench" />
                    {{ t('pendingUploads.actions.resolveConflicts') }}
                  </button>

                  <button
                    v-if="canAdminister && upload.merge_status !== 'duplicate'"
                    type="button"
                    class="action-btn test-btn"
                    :disabled="actionBusy"
                    @click="testMerge(upload)"
                  >
                    <font-awesome-icon icon="fa-solid fa-flask" />
                    {{
                      testing === upload.upload_id
                        ? t('pendingUploads.actions.testing')
                        : t('pendingUploads.actions.testMerge')
                    }}
                  </button>
                </div>
              </div>
            </div>

            <!-- File Summary -->
            <div class="upload-summary">
              <div
                v-if="upload.duplicate_of_upload_id"
                class="duplicate-notice"
              >
                <font-awesome-icon icon="fa-solid fa-copy" />
                Same submitted content as contribution #{{
                  upload.duplicate_of_upload_id
                }}. Only the original can be accepted.
              </div>
              <div
                class="quality-checks"
                aria-label="Submission quality checks"
              >
                <span class="quality-check passed">
                  <font-awesome-icon icon="fa-solid fa-circle-check" />
                  Valid ELAN files
                </span>
                <span class="quality-check passed">
                  <font-awesome-icon icon="fa-solid fa-circle-check" />
                  Naming rules passed
                </span>
                <span class="quality-check" :class="protocolCheckClass(upload)">
                  <font-awesome-icon
                    :icon="
                      upload.quality_checks?.protocol === 'passed'
                        ? 'fa-solid fa-circle-check'
                        : upload.quality_checks?.protocol === 'recheck_required'
                          ? 'fa-solid fa-triangle-exclamation'
                          : 'fa-solid fa-circle-info'
                    "
                  />
                  {{ protocolCheckLabel(upload) }}
                </span>
              </div>
              <div class="file-counts">
                <span v-if="upload.file_counts?.new > 0" class="file-count new">
                  +{{ upload.file_counts.new }}
                  {{ t('pendingUploads.fileTypes.new') }}
                </span>
                <span
                  v-if="upload.file_counts?.modified > 0"
                  class="file-count modified"
                >
                  ~{{ upload.file_counts.modified }}
                  {{ t('pendingUploads.fileTypes.modified') }}
                </span>
                <span
                  v-if="upload.file_counts?.deleted > 0"
                  class="file-count deleted"
                >
                  -{{ upload.file_counts.deleted }}
                  {{ t('pendingUploads.fileTypes.deleted') }}
                </span>
              </div>

              <p class="upload-description">{{ upload.description }}</p>
            </div>

            <!-- Conflicts (if any) -->
            <div
              v-if="upload.conflicted_files?.length > 0"
              class="conflicts-section"
            >
              <h4>{{ t('pendingUploads.conflictedFiles') }}:</h4>
              <ul class="conflict-files">
                <li
                  v-for="file in upload.conflicted_files"
                  :key="file"
                  class="conflict-file"
                >
                  {{ file }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <ReviewCasePanel
        v-else
        id="contribution-reviews-panel"
        role="tabpanel"
        aria-labelledby="contribution-reviews-tab"
        :project-id="currentProject.project_id"
        :allow-create="false"
        :can-manage="canAdminister"
        :can-comment="canContribute"
        :highlighted-case-id="highlightedCaseId"
        :resubmission-upload-id="resubmissionUploadId"
        @count-change="activeReviewCount = $event"
      />

      <!-- Upload Details Modal -->
      <div
        v-if="showDetailsModal"
        class="modal-overlay"
        role="presentation"
        @click="closeDetailsModal"
      >
        <div
          ref="detailsDialog"
          class="modal-content"
          role="dialog"
          aria-modal="true"
          aria-labelledby="upload-details-title"
          tabindex="-1"
          @keydown.esc="closeDetailsModal"
          @click.stop
        >
          <div class="modal-header">
            <h2 id="upload-details-title">
              {{ t('pendingUploads.modal.uploadDetails') }}
            </h2>
            <button
              type="button"
              class="close-btn"
              :aria-label="t('common.close')"
              @click="closeDetailsModal"
            >
              <font-awesome-icon icon="fa-solid fa-xmark" />
            </button>
          </div>

          <div class="modal-body">
            <UploadDetailsView v-if="selectedUpload" :upload="selectedUpload" />
          </div>
        </div>
      </div>

      <!-- Focused correction request modal -->
      <div
        v-if="showCorrectionModal"
        class="modal-overlay"
        role="presentation"
        @click="closeCorrectionModal"
      >
        <div
          ref="correctionDialog"
          class="modal-content correction-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="correction-modal-title"
          tabindex="-1"
          @keydown.esc="closeCorrectionModal"
          @click.stop
        >
          <div class="modal-header">
            <div>
              <span class="modal-eyebrow"
                >Contribution #{{ selectedUpload?.upload_id }}</span
              >
              <h2 id="correction-modal-title">Request a correction</h2>
            </div>
            <button
              type="button"
              class="close-btn"
              :aria-label="t('common.close')"
              @click="closeCorrectionModal"
            >
              <font-awesome-icon icon="fa-solid fa-xmark" />
            </button>
          </div>
          <div class="modal-body">
            <ReviewCasePanel
              v-if="selectedUpload"
              :project-id="currentProject.project_id"
              :upload-id="selectedUpload.upload_id"
              :filenames="selectedUploadFilenames"
              composer-only
              request-changes-on-create
              :allow-create="true"
              :can-manage="canAdminister"
              :can-comment="canContribute"
              @created="onCorrectionCreated"
              @cancel="closeCorrectionModal"
            />
          </div>
        </div>
      </div>

      <!-- Conflict Resolution Modal -->
      <div
        v-if="showResolutionModal"
        class="modal-overlay large"
        role="presentation"
        @click="closeResolutionModal"
      >
        <div
          ref="resolutionDialog"
          class="modal-content large"
          role="dialog"
          aria-modal="true"
          aria-labelledby="resolution-modal-title"
          tabindex="-1"
          @keydown.esc="closeResolutionModal"
          @click.stop
        >
          <div class="modal-header">
            <h2 id="resolution-modal-title">
              {{ t('pendingUploads.modal.resolveConflicts') }}
            </h2>
            <button
              type="button"
              class="close-btn"
              :aria-label="t('common.close')"
              @click="closeResolutionModal"
            >
              <font-awesome-icon icon="fa-solid fa-xmark" />
            </button>
          </div>

          <div class="modal-body">
            <UploadResolutionView
              v-if="selectedUpload"
              :project-id="currentProject.project_id"
              :project-name="currentProjectName"
              :upload="selectedUpload"
              @resolved="onUploadResolved"
              @cancelled="closeResolutionModal"
            />
          </div>
        </div>
      </div>

      <!-- Error Messages -->
      <div v-if="error" class="error-message" role="alert">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted, watch, nextTick } from 'vue';
import gitService from '@/api/service/gitService';
import reviewService from '@/api/service/reviewService';
import '@/assets/css/pending-uploads-page.css';
import UploadDetailsView from '@/components/common/UploadDetailsView.vue';
import UploadResolutionView from '@/components/common/UploadResolutionView.vue';
import ReviewCasePanel from '@/components/common/ReviewCasePanel.vue';
import { useProjectStore } from '@/stores/project.js';
import { useUserStore } from '@/stores/user.js';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { hasProjectPermission } from '@/utils/authorization';

// State
const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const confirmAction = useUserConfirm();
const userStore = useUserStore();
const pendingUploads = ref([]);
const uploadsLoading = ref(false);
const error = ref('');
const policySaving = ref(false);
const activeReviewCount = ref(0);

// Modal state
const showDetailsModal = ref(false);
const showResolutionModal = ref(false);
const showCorrectionModal = ref(false);
const selectedUpload = ref(null);
const detailsDialog = ref(null);
const resolutionDialog = ref(null);
const correctionDialog = ref(null);
let modalTrigger = null;

// Action state
const merging = ref(null); // upload_id being merged
const testing = ref(null); // upload_id being tested
const dismissing = ref(null);
const actionBusy = computed(
  () =>
    merging.value !== null ||
    testing.value !== null ||
    dismissing.value !== null
);

// Project store
const projectStore = useProjectStore();

// Computed properties from project store
const currentProject = computed(() => projectStore.currentProject);
const currentProjectName = computed(() => {
  if (!currentProject.value) return '';

  return typeof currentProject.value === 'object'
    ? currentProject.value.project_name
    : currentProject.value;
});
const activeView = computed(() =>
  route.query.view === 'reviews' ? 'reviews' : 'queue'
);
const highlightedCaseId = computed(() => String(route.query.case || ''));
const resubmissionUploadId = computed(() =>
  route.query.resubmission ? Number(route.query.resubmission) : null
);
const canAdminister = computed(() =>
  hasProjectPermission(userStore.user, currentProject.value, 'admin')
);
const canContribute = computed(() =>
  hasProjectPermission(userStore.user, currentProject.value, 'write')
);
const selectedUploadFilenames = computed(() => {
  const files = selectedUpload.value?.files;
  if (!files) return [];
  return [
    ...(files.new || []),
    ...(files.modified || []),
    ...(files.deleted || []),
  ];
});

function setActiveView(view) {
  const query = { ...route.query, view };
  if (view !== 'reviews') {
    delete query.case;
    delete query.resubmission;
  }
  void router.replace({ query });
}

async function updateAutomaticPolicy(enabled) {
  policySaving.value = true;
  error.value = '';
  try {
    await gitService.updateContributionPolicy(
      currentProject.value.project_id,
      enabled
    );
    const updated = {
      ...currentProject.value,
      auto_accept_new_files: enabled,
    };
    projectStore.setCurrentProject(updated);
    projectStore.setProjects(
      projectStore.projects.map((project) =>
        project.project_id === updated.project_id ? updated : project
      )
    );
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The automatic acceptance policy could not be saved.';
  } finally {
    policySaving.value = false;
  }
}

// Upload computed properties
const totalPending = computed(() => pendingUploads.value.length);
const readyCount = computed(
  () =>
    pendingUploads.value.filter((u) => u.merge_status === 'ready_to_merge')
      .length
);
const conflictsCount = computed(
  () =>
    pendingUploads.value.filter((u) => u.merge_status === 'needs_resolution')
      .length
);

// Auto-refresh interval
let refreshInterval = null;
let fetchSequence = 0;
let fetchInFlight = false;

// Watch for project changes
watch(
  () => [route.query.project, projectStore.projects.length],
  ([projectId]) => {
    if (!projectId) return;
    const requested = projectStore.projects.find(
      (project) => project.project_id === Number(projectId)
    );
    if (requested) projectStore.setCurrentProject(requested);
  },
  { immediate: true }
);

watch(
  () => currentProject.value?.project_id,
  async (newProjectId, oldProjectId) => {
    if (newProjectId === oldProjectId) return;
    pendingUploads.value = [];
    error.value = '';
    if (newProjectId) await fetchPendingUploads();
    if (newProjectId) await fetchReviewCount();
  },
  { immediate: true }
);

onMounted(async () => {
  // Set up auto-refresh every 30 seconds
  refreshInterval = setInterval(() => {
    if (currentProject.value && document.visibilityState === 'visible') {
      fetchPendingUploads(false);
    }
  }, 30000);
  projectStore.initBroadcastChannel();
});

// Cleanup interval on unmount
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});

async function fetchPendingUploads(showLoading = true) {
  if (!currentProjectName.value) {
    pendingUploads.value = [];
    return;
  }

  if (fetchInFlight) return;
  const requestedProject = currentProjectName.value;
  const request = ++fetchSequence;
  fetchInFlight = true;
  try {
    if (showLoading) uploadsLoading.value = true;
    error.value = '';

    const response =
      await gitService.getPendingUploadsWithStatus(requestedProject);
    if (
      request === fetchSequence &&
      requestedProject === currentProjectName.value
    ) {
      pendingUploads.value = response.pending_uploads || [];
    }
  } catch {
    if (
      showLoading &&
      request === fetchSequence &&
      requestedProject === currentProjectName.value
    ) {
      error.value = t('pendingUploads.errors.loadFailed');
      pendingUploads.value = [];
    }
  } finally {
    fetchInFlight = false;
    if (showLoading && request === fetchSequence) uploadsLoading.value = false;
    if (
      requestedProject !== currentProjectName.value &&
      currentProjectName.value
    ) {
      void fetchPendingUploads(showLoading);
    }
  }
}

async function fetchReviewCount() {
  if (!currentProject.value?.project_id) {
    activeReviewCount.value = 0;
    return;
  }
  try {
    const cases = await reviewService.list(currentProject.value.project_id);
    activeReviewCount.value = cases.filter(
      (item) => !['resolved', 'closed'].includes(item.state)
    ).length;
  } catch {
    activeReviewCount.value = 0;
  }
}

async function testMerge(upload) {
  try {
    testing.value = upload.upload_id;
    error.value = '';

    const response = await gitService.adminTestMerge(
      currentProjectName.value,
      upload.branch_name
    );

    // Update the upload status in the list
    const index = pendingUploads.value.findIndex(
      (u) => u.upload_id === upload.upload_id
    );
    if (index !== -1) {
      pendingUploads.value[index] = {
        ...pendingUploads.value[index],
        merge_status: response.status,
        conflicted_files: response.conflicted_files || [],
        conflicts_count: response.conflicts_count || 0,
        can_auto_merge: response.can_auto_merge,
        tested_at: response.tested_at,
      };
    }
  } catch (e) {
    error.value =
      e?.response?.data?.detail || t('pendingUploads.errors.testMergeFailed');
  } finally {
    testing.value = null;
  }
}

async function mergeUpload(upload) {
  if (upload.merge_status !== 'ready_to_merge') {
    error.value = t('pendingUploads.errors.notReadyToMerge');
    return;
  }

  const confirmed = await confirmAction({
    title: t('pendingUploads.mergeConfirmation.title'),
    message: t('pendingUploads.mergeConfirmation.message', {
      branch: `contribution #${upload.upload_id}`,
    }),
    confirmText: t('pendingUploads.actions.mergeNow'),
    cancelText: t('common.cancel'),
  });
  if (!confirmed) return;

  try {
    merging.value = upload.upload_id;
    error.value = '';

    await gitService.adminCompleteMerge(
      currentProjectName.value,
      upload.branch_name,
      'auto' // Auto-merge since it's ready
    );

    // Remove the merged upload from the list
    const index = pendingUploads.value.findIndex(
      (u) => u.upload_id === upload.upload_id
    );
    if (index !== -1) {
      pendingUploads.value.splice(index, 1);
    }

    // Refresh all uploads to update status of remaining ones
    await fetchPendingUploads(false);
  } catch (e) {
    error.value =
      e?.response?.data?.detail || t('pendingUploads.errors.mergeFailed');
  } finally {
    merging.value = null;
  }
}

async function dismissDuplicate(upload) {
  const confirmed = await confirmAction({
    title: `Dismiss contribution #${upload.upload_id}?`,
    message: `It contains exactly the same project content as contribution #${upload.duplicate_of_upload_id}. Its redundant Git branch will be removed, while the dismissal remains in the audit history.`,
    confirmText: 'Dismiss duplicate',
    cancelText: t('common.cancel'),
  });
  if (!confirmed) return;

  dismissing.value = upload.upload_id;
  error.value = '';
  try {
    await gitService.dismissDuplicateUpload(
      currentProjectName.value,
      upload.upload_id
    );
    pendingUploads.value = pendingUploads.value.filter(
      (item) => item.upload_id !== upload.upload_id
    );
    await fetchPendingUploads(false);
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The duplicate contribution could not be dismissed.';
  } finally {
    dismissing.value = null;
  }
}

function resolveUpload(upload, event) {
  modalTrigger = event?.currentTarget || null;
  selectedUpload.value = upload;
  showResolutionModal.value = true;
  void nextTick(() => resolutionDialog.value?.focus());
}

function viewUploadDetails(upload, event) {
  modalTrigger = event?.currentTarget || null;
  selectedUpload.value = upload;
  showDetailsModal.value = true;
  void nextTick(() => detailsDialog.value?.focus());
}

function requestCorrection(upload, event) {
  modalTrigger = event?.currentTarget || null;
  selectedUpload.value = upload;
  showCorrectionModal.value = true;
  void nextTick(() => correctionDialog.value?.focus());
}

function closeCorrectionModal() {
  showCorrectionModal.value = false;
  selectedUpload.value = null;
  restoreModalFocus();
}

async function onCorrectionCreated(created) {
  showCorrectionModal.value = false;
  selectedUpload.value = null;
  await fetchReviewCount();
  await router.replace({
    query: {
      ...route.query,
      view: 'reviews',
      case: created.case_id,
    },
  });
}

function closeDetailsModal() {
  showDetailsModal.value = false;
  selectedUpload.value = null;
  restoreModalFocus();
}

function closeResolutionModal() {
  showResolutionModal.value = false;
  selectedUpload.value = null;
  restoreModalFocus();
}

function restoreModalFocus() {
  const trigger = modalTrigger;
  modalTrigger = null;
  void nextTick(() => trigger?.focus());
}

async function onUploadResolved() {
  closeResolutionModal();
  // Refresh the list to show updated status
  await fetchPendingUploads();
}

// Utility functions
function getUploadStatusClass(upload) {
  return {
    'status-ready': upload.merge_status === 'ready_to_merge',
    'status-conflicts': upload.merge_status === 'needs_resolution',
    'status-error': upload.merge_status === 'error',
    'status-pending': upload.merge_status === 'pending_admin_approval',
    'status-duplicate': upload.merge_status === 'duplicate',
  };
}

function getStatusClass(status) {
  const classes = {
    ready_to_merge: 'ready',
    needs_resolution: 'conflicts',
    error: 'error',
    pending_admin_approval: 'pending',
    duplicate: 'duplicate',
  };
  return classes[status] || 'pending';
}

function formatStatus(status) {
  const statuses = {
    ready_to_merge: t('pendingUploads.status.readyToMerge'),
    needs_resolution: t('pendingUploads.status.needsResolution'),
    error: t('pendingUploads.status.error'),
    pending_admin_approval: t('pendingUploads.status.pendingReview'),
    duplicate: 'Duplicate submission',
  };
  return statuses[status] || status;
}

function formatUploadType(type) {
  const types = {
    pending_upload: t('pendingUploads.uploadTypes.newFiles'),
    upload_with_modifications: t(
      'pendingUploads.uploadTypes.withModifications'
    ),
    upload_with_deletions: t('pendingUploads.uploadTypes.withDeletions'),
  };
  return types[type] || type;
}

function formatDate(dateString) {
  if (!dateString) return t('pendingUploads.unknown');
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString));
}

function protocolCheckClass(upload) {
  const outcome = upload.quality_checks?.protocol;
  if (outcome === 'passed') return 'passed';
  if (outcome === 'recheck_required') return 'recheck-required';
  return 'not-configured';
}

function protocolCheckLabel(upload) {
  const outcome = upload.quality_checks?.protocol;
  if (outcome === 'passed') return 'Project protocol passed';
  if (outcome === 'recheck_required')
    return 'Protocol changed — acceptance will recheck this contribution';
  if (outcome === 'not_configured') return 'No project protocol configured';
  return 'Protocol check not recorded for this older contribution';
}
</script>

<style scoped>
.project-name {
  color: #1976d2;
  font-weight: 600;
}

.select-project-btn {
  display: inline-block;
  margin-top: 16px;
  padding: 12px 24px;
  background: #1976d2;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 500;
  transition: background 0.3s;
}

.select-project-btn:hover {
  background: #1565c0;
}
</style>
