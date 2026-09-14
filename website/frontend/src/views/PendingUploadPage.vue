<template>
  <div class="pending-uploads-page">
    <div class="pending-uploads-container">
      <WorkspaceHeader
        embedded
        :context="currentProjectName"
        :title="t('pendingUploads.title')"
        :description="t('pendingUploads.pageDescription')"
      />

      <ContributionWorkspaceTabs
        v-if="!workspaceMode"
        :active-view="activeView"
        :contribution-count="contributionThreads.length"
        :active-review-count="activeReviewCount"
        :can-administer="canAdminister"
        @select="setActiveView"
      />

      <section
        v-if="workspaceMode && selectedUpload"
        class="contribution-workspace"
        :aria-labelledby="`${workspaceMode}-workspace-title`"
      >
        <header class="contribution-workspace-header">
          <button
            type="button"
            class="workspace-back"
            :aria-label="t('contributionWorkspace.back')"
            :title="t('contributionWorkspace.back')"
            @click="closeWorkspace"
          >
            <font-awesome-icon icon="fa-solid fa-arrow-left" />
          </button>
          <div>
            <h2 :id="`${workspaceMode}-workspace-title`">
              {{
                workspaceMode === 'details'
                  ? t('contributionWorkspace.contribution', {
                      id: selectedUpload.upload_id,
                    })
                  : workspaceTitle
              }}
            </h2>
            <p>{{ workspaceDescription }}</p>
          </div>
        </header>

        <ReviewCasePanel
          v-if="workspaceMode === 'correction'"
          :project-id="currentProject.project_id"
          :project-name="currentProjectName"
          :upload-id="selectedUpload.upload_id"
          :filenames="selectedUploadFilenames"
          composer-only
          request-changes-on-create
          :allow-create="true"
          :can-manage="canAdminister"
          :can-comment="canContribute"
          :current-user-id="userStore.user?.user_id"
          @created="onCorrectionCreated"
          @cancel="closeWorkspace"
        />
        <UploadDetailsView
          v-else-if="workspaceMode === 'details'"
          :upload="selectedUpload"
          :project-name="currentProjectName"
        />
        <UploadResolutionView
          v-else-if="workspaceMode === 'resolution'"
          :project-id="currentProject.project_id"
          :project-name="currentProjectName"
          :upload="selectedUpload"
          @resolved="onUploadResolved"
          @cancelled="closeWorkspace"
        />
      </section>

      <!-- No Project Selected -->
      <div v-else-if="!currentProject" class="no-selection">
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
        v-else-if="activeView === 'queue' && contributionThreads.length === 0"
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
        <ContributionQueueControls
          v-model:filter="queueFilter"
          v-model:query="queueQuery"
          v-model:sort="queueSort"
          :total="totalPending"
          :ready="readyCount"
          :corrections="awaitingCorrectionsCount"
          :conflicts="conflictsCount"
          :result-count="filteredContributionThreads.length"
        />

        <!-- Upload List -->
        <div class="uploads-list">
          <div
            v-for="upload in filteredContributionThreads"
            :id="`contribution-${upload.upload_id}`"
            :key="upload.upload_id"
            class="upload-item"
            :class="getUploadStatusClass(upload)"
          >
            <ContributionCardHeader
              :upload="upload"
              :can-administer="canAdminister"
              :action-busy="actionBusy"
              :merging="merging === upload.upload_id"
              :testing="testing === upload.upload_id"
              @view="viewUploadDetails(upload, $event)"
              @discussion="openLinkedReview(upload.review_case)"
              @request-correction="requestCorrection(upload, $event)"
              @dismiss="dismissDuplicate(upload)"
              @merge="mergeUpload(upload)"
              @resolve="resolveUpload(upload, $event)"
              @test="testMerge(upload)"
              @decline="openDeclineModal(upload, $event)"
            />

            <ContributionCardBody
              :upload="upload"
              @show-contribution="scrollToContribution"
              @discussion="openLinkedReview(upload.review_case)"
              @view-version="viewUploadDetails"
            >
              <template #research-context>
                <ContributionResearchContext
                  v-model:topic-decision="topicDecisions[upload.upload_id]"
                  v-model:suggestion-name="
                    topicSuggestionNames[upload.upload_id]
                  "
                  :context="upload.research_context"
                  :topic-options="researchTopicOptions"
                  :can-administer="canAdminister"
                  :expanded="expandedTopicDecision === upload.upload_id"
                  :busy="topicDecisionBusy"
                  @toggle="toggleTopicDecision(upload.upload_id)"
                  @assign="assignResearchTopic(upload)"
                  @create="createResearchTopicFromContribution(upload)"
                />
              </template>
            </ContributionCardBody>
          </div>
          <div
            v-if="!filteredContributionThreads.length"
            class="queue-empty-filter"
          >
            No active contributions match this filter.
          </div>
        </div>
      </div>

      <ReviewCasePanel
        v-else-if="activeView === 'reviews'"
        id="contribution-reviews-panel"
        role="tabpanel"
        aria-labelledby="contribution-reviews-tab"
        :project-id="currentProject.project_id"
        :project-name="currentProjectName"
        :allow-create="false"
        :can-manage="canAdminister"
        :can-comment="canContribute"
        :current-user-id="userStore.user?.user_id"
        :highlighted-case-id="highlightedCaseId"
        :resubmission-upload-id="resubmissionUploadId"
        @count-change="onReviewCountChange"
      />

      <AcceptedProjectHistory
        v-else-if="activeView === 'history' && canAdminister"
        id="contribution-history-panel"
        role="tabpanel"
        aria-labelledby="contribution-history-tab"
        :project-name="currentProjectName"
        @restored="fetchPendingUploads"
      />

      <div
        v-if="showDeclineModal"
        class="modal-overlay"
        role="presentation"
        @click="closeDeclineModal"
      >
        <form
          ref="declineDialog"
          class="modal-content decline-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="decline-modal-title"
          tabindex="-1"
          @submit.prevent="declineUpload"
          @keydown.esc="closeDeclineModal"
          @click.stop
        >
          <div class="modal-header">
            <div>
              <span class="modal-eyebrow"
                >Contribution #{{ selectedUpload?.upload_id }}</span
              >
              <h2 id="decline-modal-title">Decline contribution</h2>
            </div>
            <button
              type="button"
              class="close-btn"
              :aria-label="t('common.close')"
              @click="closeDeclineModal"
            >
              <font-awesome-icon icon="fa-solid fa-xmark" />
            </button>
          </div>
          <div class="modal-body decline-modal-body">
            <p>
              This permanently closes the contribution and any linked correction
              discussion. Its audit history is preserved, but it cannot later be
              accepted.
            </p>
            <label for="decline-reason">Reason for the researcher</label>
            <textarea
              id="decline-reason"
              v-model="declineReason"
              rows="5"
              maxlength="1000"
              required
              minlength="3"
              placeholder="Explain why this contribution will not be accepted"
            ></textarea>
            <div class="decline-modal-actions">
              <button
                type="button"
                class="action-btn view-btn"
                @click="closeDeclineModal"
              >
                {{ t('common.cancel') }}
              </button>
              <button
                type="submit"
                class="action-btn decline-btn"
                :disabled="declineReason.trim().length < 3 || actionBusy"
              >
                {{
                  dismissing === selectedUpload?.upload_id
                    ? 'Declining…'
                    : 'Decline contribution'
                }}
              </button>
            </div>
          </div>
        </form>
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
import '@/assets/css/pending-uploads-page.css';
import UploadDetailsView from '@/components/common/UploadDetailsView.vue';
import UploadResolutionView from '@/components/common/UploadResolutionView.vue';
import ReviewCasePanel from '@/components/common/ReviewCasePanel.vue';
import AcceptedProjectHistory from '@/components/common/AcceptedProjectHistory.vue';
import ContributionCardBody from '@/components/pageSpecific/contributions/ContributionCardBody.vue';
import ContributionCardHeader from '@/components/pageSpecific/contributions/ContributionCardHeader.vue';
import ContributionQueueControls from '@/components/pageSpecific/contributions/ContributionQueueControls.vue';
import ContributionResearchContext from '@/components/pageSpecific/contributions/ContributionResearchContext.vue';
import ContributionWorkspaceTabs from '@/components/pageSpecific/contributions/ContributionWorkspaceTabs.vue';
import { useProjectStore } from '@/stores/project.js';
import { useUserStore } from '@/stores/user.js';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useContributionMutations } from '@/composables/useContributionMutations';
import { useContributionQueueData } from '@/composables/useContributionQueueData';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { hasProjectPermission } from '@/utils/authorization';
import {
  groupContributionThreads,
  sortContributionThreads,
} from '@/utils/contributionThreads';
import { useEventMessageStore } from '@/stores/eventMessage.js';

// State
const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const confirmAction = useUserConfirm();
const userStore = useUserStore();
const eventMessages = useEventMessageStore();
const topicDecisions = ref({});
const expandedTopicDecision = ref(null);

// Modal state
const showDeclineModal = ref(false);
const selectedUpload = ref(null);
const declineReason = ref('');
const declineDialog = ref(null);
let modalTrigger = null;

const queueFilter = ref('all');
const queueQuery = ref('');
const queueSort = ref('oldest');

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
const {
  pendingUploads,
  uploadsLoading,
  error,
  activeReviewCount,
  reviewCases,
  researchTopics,
  topicSuggestionNames,
  fetchPendingUploads,
  loadResearchTopics,
  fetchReviewCount,
  clear: clearQueueData,
} = useContributionQueueData({
  currentProject,
  currentProjectName,
  translate: t,
});
const {
  merging,
  testing,
  dismissing,
  topicDecisionBusy,
  actionBusy,
  assignResearchTopic: performTopicAssignment,
  createResearchTopic: performTopicCreation,
  testMerge,
  mergeUpload,
  dismissDuplicate,
  declineUpload: performDecline,
} = useContributionMutations({
  currentProjectName,
  pendingUploads,
  error,
  fetchPendingUploads,
  fetchReviewCount,
  loadResearchTopics,
  translate: t,
  confirmAction,
  eventMessages,
});
const researchTopicOptions = computed(() =>
  researchTopics.value.map((topic) => ({
    value: topic.topic_id,
    label: topic.name,
  }))
);
const activeView = computed(() => {
  if (route.query.view === 'reviews') return 'reviews';
  if (route.query.view === 'history' && canAdminister.value) return 'history';
  return 'queue';
});
const highlightedCaseId = computed(() => String(route.query.case || ''));
const resubmissionUploadId = computed(() =>
  route.query.resubmission ? Number(route.query.resubmission) : null
);
const workspaceMode = computed(() => {
  const mode = String(route.query.workspace || '');
  return ['details', 'correction', 'resolution'].includes(mode) ? mode : '';
});
const workspaceTitle = computed(
  () =>
    ({
      details: 'Contribution details',
      correction: 'Request corrections',
      resolution: 'Resolve contribution conflicts',
    })[workspaceMode.value] || 'Contribution workspace'
);
const workspaceDescription = computed(
  () =>
    ({
      details:
        'Inspect files, validation results, and ELAN annotation changes.',
      correction:
        'Select affected files and record each concrete requested edit.',
      resolution: 'Compare conflicting versions and record a safe resolution.',
    })[workspaceMode.value] || ''
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

// Upload computed properties
const contributionThreads = computed(() =>
  groupContributionThreads(pendingUploads.value, reviewCases.value)
);
const totalPending = computed(() => contributionThreads.value.length);
const readyCount = computed(
  () =>
    contributionThreads.value.filter((u) => u.merge_status === 'ready_to_merge')
      .length
);
const awaitingCorrectionsCount = computed(
  () =>
    contributionThreads.value.filter(
      (upload) => upload.merge_status === 'changes_requested'
    ).length
);
const filteredContributionThreads = computed(() => {
  const needle = queueQuery.value.toLocaleLowerCase();
  const matching = contributionThreads.value.filter((upload) => {
    const statusMatches =
      queueFilter.value === 'all' ||
      (queueFilter.value === 'ready' &&
        upload.merge_status === 'ready_to_merge') ||
      (queueFilter.value === 'corrections' &&
        ['under_review', 'changes_requested', 'review_required'].includes(
          upload.merge_status
        )) ||
      (queueFilter.value === 'resolution' &&
        upload.merge_status === 'needs_resolution');
    const searchable = [
      upload.upload_id,
      `#${upload.upload_id}`,
      `contribution ${upload.upload_id}`,
      upload.uploaded_by,
      upload.review_case?.title,
      ...Object.values(upload.files || {}).flat(),
      ...Object.entries(upload.semantic_summary || {}).flat(),
    ]
      .filter((value) => value != null)
      .join(' ')
      .toLocaleLowerCase();
    return statusMatches && (!needle || searchable.includes(needle));
  });
  return sortContributionThreads(matching, queueSort.value);
});
const conflictsCount = computed(
  () =>
    contributionThreads.value.filter(
      (u) => u.merge_status === 'needs_resolution'
    ).length
);

function toggleTopicDecision(uploadId) {
  expandedTopicDecision.value =
    expandedTopicDecision.value === uploadId ? null : uploadId;
}

function scrollToContribution(uploadId) {
  document
    .getElementById(`contribution-${uploadId}`)
    ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Auto-refresh interval
let refreshInterval = null;

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
    clearQueueData();
    if (newProjectId) {
      await Promise.all([
        fetchPendingUploads(),
        fetchReviewCount(),
        loadResearchTopics(),
      ]);
    }
  },
  { immediate: true }
);

watch(
  () => [route.query.workspace, route.query.upload, pendingUploads.value],
  ([mode, uploadId]) => {
    if (!mode || !uploadId) return;
    selectedUpload.value =
      pendingUploads.value.find(
        (upload) => upload.upload_id === Number(uploadId)
      ) || null;
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

async function assignResearchTopic(upload) {
  await performTopicAssignment(upload, topicDecisions.value[upload.upload_id]);
}

async function createResearchTopicFromContribution(upload) {
  await performTopicCreation(
    upload,
    topicSuggestionNames.value[upload.upload_id]
  );
}
async function onReviewCountChange(count) {
  activeReviewCount.value = count;
  await Promise.all([fetchReviewCount(), fetchPendingUploads(false)]);
}

function openLinkedReview(reviewCase) {
  void router.replace({
    query: {
      ...route.query,
      view: 'reviews',
      case: reviewCase.case_id,
      ...(reviewCase.resubmitted_upload_id
        ? { resubmission: reviewCase.resubmitted_upload_id }
        : {}),
    },
  });
}

function openDeclineModal(upload, event) {
  modalTrigger = event?.currentTarget || null;
  selectedUpload.value = upload;
  declineReason.value = '';
  showDeclineModal.value = true;
  void nextTick(() => declineDialog.value?.focus());
}

function closeDeclineModal() {
  if (dismissing.value !== null) return;
  showDeclineModal.value = false;
  declineReason.value = '';
  selectedUpload.value = null;
  void nextTick(() => modalTrigger?.focus());
}

async function declineUpload() {
  const upload = selectedUpload.value;
  const reason = declineReason.value.trim();
  if (await performDecline(upload, reason)) {
    showDeclineModal.value = false;
    selectedUpload.value = null;
    declineReason.value = '';
  }
}

function openWorkspace(mode, upload) {
  selectedUpload.value = upload;
  void router.replace({
    query: {
      ...route.query,
      view: 'queue',
      workspace: mode,
      upload: upload.upload_id,
    },
  });
}

function resolveUpload(upload) {
  openWorkspace('resolution', upload);
}

function viewUploadDetails(upload) {
  openWorkspace('details', upload);
}

function requestCorrection(upload) {
  openWorkspace('correction', upload);
}

function closeWorkspace() {
  selectedUpload.value = null;
  const query = { ...route.query };
  delete query.workspace;
  delete query.upload;
  void router.replace({ query });
}

async function onCorrectionCreated(created) {
  selectedUpload.value = null;
  eventMessages.addMessage('Correction request sent.', 'success');
  await fetchReviewCount();
  const query = {
    ...route.query,
    view: 'reviews',
    case: created.case_id,
  };
  delete query.workspace;
  delete query.upload;
  await router.replace({
    query,
  });
}

async function onUploadResolved() {
  closeWorkspace();
  eventMessages.addMessage('Contribution conflicts resolved.', 'success');
  // Refresh the list to show updated status
  await fetchPendingUploads();
}

// Utility functions
function getUploadStatusClass(upload) {
  return {
    'status-ready': upload.merge_status === 'ready_to_merge',
    'status-conflicts': upload.merge_status === 'needs_resolution',
    'status-error': upload.merge_status === 'error',
    'status-pending': [
      'pending_admin_approval',
      'under_review',
      'changes_requested',
      'review_required',
    ].includes(upload.merge_status),
    'status-duplicate': upload.merge_status === 'duplicate',
    'status-superseded': upload.merge_status === 'superseded',
  };
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
