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
import gitService from '@/api/service/gitService';
import reviewService from '@/api/service/reviewService';
import { fetchResearchTopics } from '@/api/service/tierService';
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
const pendingUploads = ref([]);
const uploadsLoading = ref(false);
const error = ref('');
const activeReviewCount = ref(0);
const reviewCases = ref([]);
const researchTopics = ref([]);
const topicDecisions = ref({});
const topicSuggestionNames = ref({});
const topicDecisionBusy = ref(false);
const expandedTopicDecision = ref(null);

// Modal state
const showDeclineModal = ref(false);
const selectedUpload = ref(null);
const declineReason = ref('');
const declineDialog = ref(null);
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
const queueFilter = ref('all');
const queueQuery = ref('');
const queueSort = ref('oldest');
const researchTopicOptions = computed(() =>
  researchTopics.value.map((topic) => ({
    value: topic.topic_id,
    label: topic.name,
  }))
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
      topicSuggestionNames.value = Object.fromEntries(
        pendingUploads.value
          .filter((upload) => upload.research_context?.proposed_topic_name)
          .map((upload) => [
            upload.upload_id,
            upload.research_context.proposed_topic_name,
          ])
      );
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

async function loadResearchTopics() {
  if (!currentProject.value?.project_id) {
    researchTopics.value = [];
    return;
  }
  try {
    researchTopics.value = await fetchResearchTopics(
      currentProject.value.project_id
    );
  } catch {
    researchTopics.value = [];
  }
}

async function assignResearchTopic(upload) {
  const topicId = Number(topicDecisions.value[upload.upload_id]);
  if (!topicId) return;
  topicDecisionBusy.value = true;
  error.value = '';
  try {
    await gitService.setContributionResearchTopic(
      currentProjectName.value,
      upload.upload_id,
      { topic_id: topicId, new_topic_name: null }
    );
    await fetchPendingUploads(false);
    eventMessages.addMessage('Research topic assigned.', 'success');
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The research topic could not be assigned.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    topicDecisionBusy.value = false;
  }
}

async function createResearchTopicFromContribution(upload) {
  const topicName = (topicSuggestionNames.value[upload.upload_id] || '').trim();
  if (!topicName) return;
  topicDecisionBusy.value = true;
  error.value = '';
  try {
    const context = await gitService.setContributionResearchTopic(
      currentProjectName.value,
      upload.upload_id,
      { topic_id: null, new_topic_name: topicName }
    );
    await Promise.all([fetchPendingUploads(false), loadResearchTopics()]);
    eventMessages.addMessage(
      context.declared_topic_name === topicName
        ? 'Research topic created and assigned.'
        : `Matched and assigned the existing topic “${context.declared_topic_name}”.`,
      'success'
    );
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The research topic could not be created.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    topicDecisionBusy.value = false;
  }
}

async function fetchReviewCount() {
  if (!currentProject.value?.project_id) {
    activeReviewCount.value = 0;
    reviewCases.value = [];
    return;
  }
  try {
    const cases = await reviewService.list(currentProject.value.project_id);
    reviewCases.value = cases;
    activeReviewCount.value = cases.filter(
      (item) => !['resolved', 'closed'].includes(item.state)
    ).length;
  } catch {
    activeReviewCount.value = 0;
    reviewCases.value = [];
  }
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
    eventMessages.addMessage('Compatibility check completed.', 'success');
  } catch (e) {
    error.value =
      e?.response?.data?.detail || t('pendingUploads.errors.testMergeFailed');
    eventMessages.addMessage(error.value, 'error');
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
    eventMessages.addMessage(
      'Contribution merged into the project.',
      'success'
    );
  } catch (e) {
    error.value =
      e?.response?.data?.detail || t('pendingUploads.errors.mergeFailed');
    eventMessages.addMessage(error.value, 'error');
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
    eventMessages.addMessage('Duplicate contribution dismissed.', 'success');
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The duplicate contribution could not be dismissed.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    dismissing.value = null;
  }
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
  if (!upload || reason.length < 3) return;

  dismissing.value = upload.upload_id;
  error.value = '';
  try {
    await gitService.declinePendingUpload(
      currentProjectName.value,
      upload.upload_id,
      reason
    );
    pendingUploads.value = pendingUploads.value.filter(
      (item) => item.upload_id !== upload.upload_id
    );
    showDeclineModal.value = false;
    selectedUpload.value = null;
    declineReason.value = '';
    await Promise.all([fetchPendingUploads(false), fetchReviewCount()]);
    eventMessages.addMessage('Contribution declined and archived.', 'success');
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The contribution could not be declined.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    dismissing.value = null;
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
