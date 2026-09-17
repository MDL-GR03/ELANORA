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
              @decline="openDeclineModal(upload)"
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
            {{ t('contributionWorkspace.queue.noMatches') }}
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

      <ContributionDeclineDialog
        :upload="declineTarget"
        :busy="declineTarget !== null && dismissing === declineTarget.upload_id"
        @decline="declineUpload"
        @close="closeDeclineModal"
      />

      <!-- Error Messages -->
      <div v-if="error" class="error-message" role="alert">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import '@/assets/css/pending-uploads-page.css';
import UploadDetailsView from '@/components/common/UploadDetailsView.vue';
import UploadResolutionView from '@/components/common/UploadResolutionView.vue';
import ReviewCasePanel from '@/components/common/ReviewCasePanel.vue';
import AcceptedProjectHistory from '@/components/common/AcceptedProjectHistory.vue';
import ContributionCardBody from '@/components/pageSpecific/contributions/ContributionCardBody.vue';
import ContributionCardHeader from '@/components/pageSpecific/contributions/ContributionCardHeader.vue';
import ContributionDeclineDialog from '@/components/pageSpecific/contributions/ContributionDeclineDialog.vue';
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
import { useContributionQueueRefresh } from '@/composables/useContributionQueueRefresh';
import { useContributionQueueView } from '@/composables/useContributionQueueView';
import { useContributionWorkspace } from '@/composables/useContributionWorkspace';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { hasProjectPermission } from '@/utils/authorization';
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

// Kept apart from selectedUpload, which follows the workspace in the URL.
const declineTarget = ref(null);

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
  uploadsLoaded,
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
const canAdminister = computed(() =>
  hasProjectPermission(userStore.user, currentProject.value, 'admin')
);
const canContribute = computed(() =>
  hasProjectPermission(userStore.user, currentProject.value, 'write')
);
const {
  activeView,
  highlightedCaseId,
  resubmissionUploadId,
  workspaceMode,
  selectedUpload,
  workspaceTitle,
  workspaceDescription,
  setActiveView,
  openWorkspace,
  closeWorkspace,
  openLinkedReview,
  showReviewCase,
} = useContributionWorkspace({
  route,
  router,
  pendingUploads,
  uploadsLoaded,
  canAdminister,
  translate: t,
  notify: (key, type, params) =>
    eventMessages.addMessage(key, type, undefined, params),
});
const selectedUploadFilenames = computed(() => {
  const files = selectedUpload.value?.files;
  if (!files) return [];
  return [
    ...(files.new || []),
    ...(files.modified || []),
    ...(files.deleted || []),
  ];
});

const {
  queueFilter,
  queueQuery,
  queueSort,
  contributionThreads,
  totalPending,
  readyCount,
  awaitingCorrectionsCount,
  conflictsCount,
  filteredContributionThreads,
} = useContributionQueueView({ pendingUploads, reviewCases });

function toggleTopicDecision(uploadId) {
  expandedTopicDecision.value =
    expandedTopicDecision.value === uploadId ? null : uploadId;
}

function scrollToContribution(uploadId) {
  document
    .getElementById(`contribution-${uploadId}`)
    ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

useContributionQueueRefresh({
  route,
  projectStore,
  currentProject,
  queue: {
    clear: clearQueueData,
    fetchPendingUploads,
    fetchReviewCount,
    loadResearchTopics,
  },
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

function openDeclineModal(upload) {
  declineTarget.value = upload;
}

function closeDeclineModal() {
  if (dismissing.value !== null) return;
  declineTarget.value = null;
}

async function declineUpload(reason) {
  if (await performDecline(declineTarget.value, reason)) {
    declineTarget.value = null;
  }
}

function resolveUpload(upload) {
  void openWorkspace('resolution', upload);
}

function viewUploadDetails(upload) {
  void openWorkspace('details', upload);
}

function requestCorrection(upload) {
  void openWorkspace('correction', upload);
}

async function onCorrectionCreated(created) {
  eventMessages.addMessage(
    'contributionWorkspace.messages.correctionSent',
    'success'
  );
  await fetchReviewCount();
  await showReviewCase(created.case_id);
}

async function onUploadResolved() {
  await closeWorkspace();
  eventMessages.addMessage(
    'contributionWorkspace.messages.conflictsResolved',
    'success'
  );
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
  color: var(--color-blue-700-alt, #1976d2);
  font-weight: 600;
}

.select-project-btn {
  display: inline-block;
  margin-top: 16px;
  padding: 12px 24px;
  background: var(--color-blue-700-alt, #1976d2);
  color: var(--color-text-inverse);
  text-decoration: none;
  border-radius: 8px;
  font-weight: 500;
  transition: background 0.3s;
}

.select-project-btn:hover {
  background: var(--color-blue-800-alt, #1565c0);
}
</style>
