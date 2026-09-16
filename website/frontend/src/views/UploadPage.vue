<template>
  <div class="upload-page-root">
    <WorkspaceHeader
      embedded
      :context="currentProjectName"
      :title="t('uploadPage.title')"
      :description="t('uploadPage.pageDescription')"
    />

    <section v-if="correctionCase" class="correction-context" role="status">
      <div class="correction-context-icon">
        <font-awesome-icon icon="fa-solid fa-rotate" />
      </div>
      <div>
        <span>{{ t('uploadPage.correction.title') }}</span>
        <strong>{{ correctionCase.title }}</strong>
        <p>
          {{ t('uploadPage.correction.description') }}
        </p>
        <ul v-if="correctionTasks.length" class="correction-file-list">
          <li v-for="task in correctionTasks" :key="task.task_id">
            <font-awesome-icon icon="fa-solid fa-file-circle-exclamation" />
            <span>
              <strong>{{ task.filename }}</strong>
              <small>{{ task.instruction }}</small>
            </span>
          </li>
        </ul>
      </div>
      <router-link
        :to="{
          name: 'PendingUpload',
          query: {
            project: selectedProject,
            view: 'reviews',
            case: correctionCase.case_id,
          },
        }"
        >{{ t('uploadPage.correction.viewDiscussion') }}</router-link
      >
    </section>

    <div class="upload-workflow">
      <section class="upload-step" aria-labelledby="upload-project-heading">
        <div class="upload-step-marker">1</div>
        <div class="upload-step-content">
          <div class="upload-step-heading">
            <div>
              <h2 id="upload-project-heading">
                {{ t('uploadPage.projectStep.title') }}
              </h2>
              <p>{{ t('uploadPage.projectStep.description') }}</p>
            </div>
            <span v-if="selectedProject" class="upload-step-complete">
              <font-awesome-icon icon="fa-solid fa-check" />
              {{ t('uploadPage.ready') }}
            </span>
          </div>
          <label for="projectSelect" class="project-label">
            {{ t('uploadPage.projectSelection.label') }}
          </label>
          <AppSelect
            id="projectSelect"
            v-model="selectedProject"
            class="project-select-control"
            :disabled="loading || uploading"
            :placeholder="t('uploadPage.projectSelection.placeholder')"
            :options="projectOptions"
          />
        </div>
      </section>

      <section
        class="upload-step"
        :class="{ 'upload-step--disabled': !selectedProject }"
        aria-labelledby="upload-files-heading"
      >
        <div class="upload-step-marker">2</div>
        <div class="upload-step-content">
          <div class="upload-step-heading">
            <div>
              <h2 id="upload-files-heading">
                {{ t('uploadPage.filesStep.title') }}
              </h2>
              <p>{{ t('uploadPage.filesStep.description') }}</p>
            </div>
            <span v-if="selectedFiles.length" class="upload-file-total">
              {{
                t('uploadPage.selectedCount', { count: selectedFiles.length })
              }}
            </span>
          </div>

          <div v-if="selectedProject">
            <UploadFolder
              v-model="selectedFiles"
              :title="
                correctionCase
                  ? t('uploadPage.correction.addFiles')
                  : t('uploadPage.uploadZone.title')
              "
              :subtitle="
                correctionCase
                  ? t('uploadPage.correction.uploadHint')
                  : t('uploadPage.uploadZone.subtitle')
              "
              :files-with-compliance="filesWithCompliance"
              :disabled="uploading || standardsLoading || standardsLoadFailed"
              @error="error = $event"
            />

            <div
              v-if="correctionCase && missingCorrectionFiles.length"
              class="upload-compliance-banner upload-compliance-banner--warning"
              role="status"
            >
              <font-awesome-icon icon="fa-solid fa-file-circle-exclamation" />
              <span>
                {{ t('uploadPage.correction.stillRequired') }}:
                {{ missingCorrectionFiles.join(', ') }}
              </span>
            </div>

            <div
              v-if="selectedFiles.length && nonCompliantCount > 0"
              class="upload-compliance-banner upload-compliance-banner--warning"
              role="status"
            >
              <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
              <span>
                {{
                  t('uploadPage.nonCompliantSummary', {
                    count: nonCompliantCount,
                  })
                }}
              </span>
            </div>
            <div
              v-else-if="selectedFiles.length && hasEffectiveStandard"
              class="upload-compliance-banner upload-compliance-banner--success"
              role="status"
            >
              <font-awesome-icon icon="fa-solid fa-circle-check" />
              {{ t('uploadPage.compliantSummary') }}
            </div>
          </div>
          <div v-else class="upload-step-placeholder">
            <font-awesome-icon icon="fa-solid fa-arrow-up" />
            {{ t('uploadPage.selectProjectFirst') }}
          </div>
        </div>
      </section>

      <section
        class="upload-step"
        :class="{ 'upload-step--disabled': !selectedFiles.length }"
        aria-labelledby="upload-context-heading"
      >
        <div class="upload-step-marker">3</div>
        <div class="upload-step-content">
          <div class="upload-step-heading">
            <div>
              <h2 id="upload-context-heading">
                {{ t('uploadPage.context.title') }}
              </h2>
              <p>{{ t('uploadPage.context.description') }}</p>
            </div>
            <span v-if="contributionContextReady" class="upload-step-complete">
              <font-awesome-icon icon="fa-solid fa-check" />
              {{ t('uploadPage.ready') }}
            </span>
          </div>

          <div v-if="selectedFiles.length" class="contribution-context-fields">
            <div
              v-if="detectedResearchScope"
              class="detected-research-scope"
              role="status"
            >
              <font-awesome-icon icon="fa-solid fa-layer-group" />
              <div>
                <strong>{{ t('uploadPage.context.copyDetected') }}</strong>
                <span>
                  {{
                    detectedResearchScope.topicName ||
                    t('uploadPage.context.customScope')
                  }}
                  ·
                  {{
                    t('uploadPage.context.editableTiers', {
                      count: detectedResearchScope.tiers.length,
                    })
                  }}
                </span>
                <small>
                  {{ t('uploadPage.context.scopeCheckHint') }}
                </small>
              </div>
            </div>

            <label
              v-else
              class="contribution-context-field"
              for="upload-research-topic"
            >
              <span>{{ t('uploadPage.context.topic') }}</span>
              <AppSelect
                id="upload-research-topic"
                v-model="researchTopicChoice"
                :disabled="researchTopicsLoading || uploading"
                :placeholder="t('uploadPage.context.topicPlaceholder')"
                :options="researchTopicOptions"
              />
              <small>
                {{ t('uploadPage.context.topicHint') }}
              </small>
            </label>

            <label
              v-if="
                !detectedResearchScope && researchTopicChoice === '__propose__'
              "
              class="contribution-context-field"
            >
              <span>{{ t('uploadPage.context.suggestedName') }}</span>
              <input
                v-model.trim="proposedTopicName"
                maxlength="100"
                :placeholder="t('uploadPage.context.suggestedNamePlaceholder')"
              />
              <small>
                {{ t('uploadPage.context.suggestedNameHint') }}
              </small>
            </label>

            <div
              v-if="suggestedExistingTopic"
              class="research-topic-suggestion"
              role="status"
            >
              <div>
                <strong>{{ t('uploadPage.context.similarTopic') }}</strong>
                <span>
                  {{
                    t('uploadPage.context.similarTopicMessage', {
                      proposed: proposedTopicName,
                      existing: suggestedExistingTopic.name,
                    })
                  }}
                </span>
              </div>
              <button
                type="button"
                class="secondary-button"
                @click="acceptSuggestedTopic"
              >
                {{
                  t('uploadPage.context.useTopic', {
                    topic: suggestedExistingTopic.name,
                  })
                }}
              </button>
            </div>

            <label class="contribution-context-field">
              <span>{{ t('uploadPage.context.summary') }}</span>
              <strong class="required-field-label">{{
                t('uploadPage.context.required')
              }}</strong>
              <textarea
                v-model.trim="contributionSummary"
                rows="3"
                maxlength="1000"
                :placeholder="t('uploadPage.context.summaryPlaceholder')"
              ></textarea>
              <small>
                {{ t('uploadPage.context.summaryHint') }}
              </small>
            </label>

            <div class="upload-submit-bar">
              <div>
                <strong>{{ t('uploadPage.submitTitle') }}</strong>
                <span>
                  {{ t('uploadPage.context.reviewEvidence') }}
                </span>
              </div>
              <button
                type="button"
                class="upload-btn"
                :disabled="
                  uploading ||
                  standardsLoading ||
                  standardsLoadFailed ||
                  !contributionContextReady ||
                  missingCorrectionFiles.length > 0 ||
                  nonCompliantCount > 0
                "
                @click="uploadFiles"
              >
                <span
                  v-if="uploading"
                  class="spinner"
                  aria-hidden="true"
                ></span>
                <font-awesome-icon v-else icon="fa-solid fa-cloud-arrow-up" />
                {{
                  uploading
                    ? t('uploadPage.uploadingFiles', {
                        count: selectedFiles.length,
                      })
                    : t('uploadPage.uploadButton')
                }}
              </button>
            </div>
          </div>
          <div v-else class="upload-step-placeholder">
            <font-awesome-icon icon="fa-solid fa-arrow-up" />
            {{ t('uploadPage.context.addFilesFirst') }}
          </div>
        </div>
      </section>
    </div>

    <section
      v-if="uploadResults.length"
      class="upload-results"
      aria-labelledby="upload-results-heading"
      aria-live="polite"
    >
      <div class="upload-results-heading">
        <div>
          <span>{{ t('uploadPage.complete') }}</span>
          <h2 id="upload-results-heading">
            {{ t('uploadPage.uploadResults') }}
          </h2>
        </div>
        <strong>{{ successfulResultCount }}/{{ uploadResults.length }}</strong>
      </div>
      <ul class="results-list">
        <li
          v-for="result in uploadResults"
          :key="result.filename"
          class="result-item"
          :class="{ success: result.success, error: !result.success }"
        >
          <font-awesome-icon
            :icon="
              result.success
                ? 'fa-solid fa-circle-check'
                : 'fa-solid fa-circle-xmark'
            "
          />
          <span class="result-filename">{{ result.filename }}</span>
          <span class="result-status">
            {{
              result.success
                ? t('uploadPage.resultSuccess')
                : t('uploadPage.resultFailed')
            }}
          </span>
          <span v-if="result.error" class="result-error">{{
            result.error
          }}</span>
        </li>
      </ul>
      <router-link
        v-if="correctionCase && completedUploadId"
        class="finish-correction-link"
        :to="{
          name: 'PendingUpload',
          query: {
            project: selectedProject,
            view: 'reviews',
            case: correctionCase.case_id,
            resubmission: completedUploadId,
          },
        }"
      >
        {{ t('uploadPage.correction.finishLink') }}
        <font-awesome-icon icon="fa-solid fa-arrow-right" />
      </router-link>
      <router-link
        v-else-if="completedUploadId"
        class="finish-correction-link"
        :to="{
          name: 'PendingUpload',
          query: {
            project: selectedProject,
            view: 'queue',
            workspace: 'details',
            upload: completedUploadId,
          },
        }"
      >
        {{
          t('uploadPage.context.viewContribution', {
            id: completedUploadId,
          })
        }}
        <font-awesome-icon icon="fa-solid fa-arrow-right" />
      </router-link>
    </section>

    <div v-if="error" class="error-message" role="alert">{{ error }}</div>
  </div>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import gitService from '@/api/service/gitService';
import reviewService from '@/api/service/reviewService';
import { fetchResearchTopics } from '@/api/service/tierService';
import UploadFolder from '@/components/common/UploadFolder.vue';
import AppSelect from '@/components/common/AppSelect.vue';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useEffectiveStandardStore } from '@/stores/effectiveStandard';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useNamingStandardStore } from '@/stores/namingStandard';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import { formatEafUploadError } from '@/utils/eafValidationError';
import { isFilenameCompliant } from '@/utils/filenameCompliance';
import { findSimilarResearchTopic } from '@/utils/researchTopics';
import {
  activeCorrectionTasks,
  findMissingCorrectionFiles,
} from '@/utils/correctionFiles';
import '@/assets/css/upload-page.css';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const projectStore = useProjectStore();
const effectiveStandardStore = useEffectiveStandardStore();
const namingStandardStore = useNamingStandardStore();
const eventMessageStore = useEventMessageStore();

const selectedProject = ref('');
const selectedFiles = ref([]);
const uploading = ref(false);
const loading = ref(true);
const uploadResults = ref([]);
const completedUploadId = ref(null);
const correctionCase = ref(null);
const error = ref('');
const hasEffectiveStandard = ref(false);
const standard = ref(null);
const standardsLoading = ref(false);
const standardsLoadFailed = ref(false);
const researchTopics = ref([]);
const researchTopicsLoading = ref(false);
const researchTopicChoice = ref('');
const proposedTopicName = ref('');
const contributionSummary = ref('');
const detectedResearchScope = ref(null);
let standardsRequest = 0;

const username = computed(() => userStore.user?.username || '');
const projects = computed(() => projectStore.projects || []);
const projectOptions = computed(() =>
  projects.value.map((project) => ({
    value: project.project_id,
    label: project.project_name,
  }))
);
const researchTopicOptions = computed(() => [
  ...researchTopics.value.map((topic) => ({
    value: String(topic.topic_id),
    label: topic.name,
  })),
  { value: '__general__', label: t('uploadPage.topics.general') },
  { value: '__propose__', label: t('uploadPage.topics.propose') },
]);
const suggestedExistingTopic = computed(() => {
  if (
    detectedResearchScope.value ||
    researchTopicChoice.value !== '__propose__' ||
    proposedTopicName.value.trim().length < 2
  ) {
    return null;
  }
  return findSimilarResearchTopic(
    proposedTopicName.value,
    researchTopics.value
  );
});
const contributionContextReady = computed(
  () =>
    contributionSummary.value.trim().length >= 3 &&
    (detectedResearchScope.value ||
      (researchTopicChoice.value &&
        (researchTopicChoice.value !== '__propose__' ||
          (proposedTopicName.value.trim().length >= 2 &&
            !suggestedExistingTopic.value))))
);

function acceptSuggestedTopic() {
  if (!suggestedExistingTopic.value) return;
  researchTopicChoice.value = String(suggestedExistingTopic.value.topic_id);
  proposedTopicName.value = '';
}
const currentProjectName = computed(
  () =>
    projects.value.find(
      (project) => project.project_id === Number(selectedProject.value)
    )?.project_name ||
    projectStore.currentProject?.project_name ||
    ''
);

const filesWithCompliance = computed(() =>
  selectedFiles.value.map((file) => ({
    ...file,
    isCompliant:
      !hasEffectiveStandard.value || !standard.value
        ? true
        : isFilenameCompliant(standard.value, file.name),
  }))
);
const nonCompliantCount = computed(
  () => filesWithCompliance.value.filter((file) => !file.isCompliant).length
);
const successfulResultCount = computed(
  () => uploadResults.value.filter((result) => result.success).length
);
const correctionTasks = computed(() =>
  activeCorrectionTasks(correctionCase.value)
);
const missingCorrectionFiles = computed(() =>
  findMissingCorrectionFiles(correctionCase.value, selectedFiles.value)
);

onMounted(async () => {
  projectStore.initializeFromStorage();
  await projectStore.ensureProjects();
  const requestedProjectId = Number(route.query.project);
  selectedProject.value = projects.value.some(
    (project) => project.project_id === requestedProjectId
  )
    ? requestedProjectId
    : projectStore.currentProject?.project_id || '';
  if (selectedProject.value) {
    await Promise.all([
      fetchStandards(),
      loadCorrectionContext(),
      loadResearchTopics(),
    ]);
  }
  loading.value = false;
  projectStore.initBroadcastChannel();
});

watch(
  () => projectStore.currentProject?.project_id,
  (projectId) => {
    if (projectId !== selectedProject.value) {
      selectedProject.value = projectId || '';
    }
  }
);

watch(selectedProject, async (newProjectId, oldProjectId) => {
  if (newProjectId === oldProjectId) return;
  const project = projects.value.find(
    (candidate) => candidate.project_id === Number(newProjectId)
  );
  if (
    project &&
    project.project_id !== projectStore.currentProject?.project_id
  ) {
    projectStore.setCurrentProject(project);
  } else if (!newProjectId && projectStore.currentProject) {
    projectStore.clearCurrentProject();
  }
  selectedFiles.value = [];
  uploadResults.value = [];
  completedUploadId.value = null;
  correctionCase.value = null;
  error.value = '';
  researchTopicChoice.value = '';
  proposedTopicName.value = '';
  contributionSummary.value = '';
  detectedResearchScope.value = null;
  if (newProjectId)
    await Promise.all([
      fetchStandards(),
      loadCorrectionContext(),
      loadResearchTopics(),
    ]);
  else {
    hasEffectiveStandard.value = false;
    standard.value = null;
    standardsLoadFailed.value = false;
  }
});

watch(selectedFiles, async (files) => {
  detectedResearchScope.value = await detectResearchScope(files);
  const detectedTopicId = detectedResearchScope.value?.topicId;
  if (
    detectedTopicId &&
    researchTopics.value.some(
      (topic) => topic.topic_id === Number(detectedTopicId)
    )
  ) {
    researchTopicChoice.value = String(detectedTopicId);
  }
});

async function loadResearchTopics() {
  researchTopics.value = [];
  if (!selectedProject.value) return;
  researchTopicsLoading.value = true;
  try {
    researchTopics.value = await fetchResearchTopics(selectedProject.value);
  } catch {
    error.value = t('uploadPage.topics.loadFailed');
  } finally {
    researchTopicsLoading.value = false;
  }
}

async function detectResearchScope(files) {
  const scopes = [];
  for (const file of files) {
    try {
      const document = new DOMParser().parseFromString(
        await file.text(),
        'application/xml'
      );
      const property = Array.from(document.querySelectorAll('PROPERTY')).find(
        (item) => item.getAttribute('NAME') === 'ELANORA_RESEARCH_EXTRACT'
      );
      if (!property?.textContent) continue;
      const metadata = JSON.parse(property.textContent);
      if (metadata.purpose !== 'tier_scoped_edit') continue;
      scopes.push(metadata);
    } catch {
      // The server remains authoritative for malformed provenance and EAF data.
    }
  }
  if (!scopes.length) return null;
  const topicIds = [...new Set(scopes.map((item) => item.research_topic_id))];
  const topicNames = [...new Set(scopes.map((item) => item.research_topic))];
  return {
    topicId: topicIds.length === 1 ? topicIds[0] : null,
    topicName: topicNames.length === 1 ? topicNames[0] : null,
    tiers: [...new Set(scopes.flatMap((item) => item.selected_tiers || []))],
  };
}

async function fetchStandards() {
  const request = ++standardsRequest;
  const projectId = selectedProject.value;
  const uploadLocationId = 4;
  if (!projectId) return;
  standardsLoading.value = true;
  standardsLoadFailed.value = false;
  try {
    await Promise.all([
      effectiveStandardStore.fetchEffectiveStandards(
        projectId,
        uploadLocationId
      ),
      namingStandardStore.fetchStandardsAndComponentNames(projectId),
    ]);
    if (request !== standardsRequest || projectId !== selectedProject.value)
      return;
    const standardsAtLocation =
      effectiveStandardStore.effectiveStandards[uploadLocationId];
    const standardId =
      standardsAtLocation && typeof standardsAtLocation === 'object'
        ? Object.values(standardsAtLocation).find(Boolean)
        : standardsAtLocation;
    standard.value = namingStandardStore.standards.find(
      (candidate) => candidate.id === standardId
    );
    hasEffectiveStandard.value = Boolean(standardId);
  } catch {
    if (request === standardsRequest) {
      hasEffectiveStandard.value = false;
      standard.value = null;
      standardsLoadFailed.value = true;
      error.value = t('uploadPage.errors.standardsFailed');
    }
  } finally {
    if (request === standardsRequest) standardsLoading.value = false;
  }
}

async function loadCorrectionContext() {
  correctionCase.value = null;
  const caseId = String(route.query.correction || '');
  if (!caseId || !selectedProject.value) return;
  try {
    const cases = await reviewService.list(selectedProject.value);
    correctionCase.value =
      cases.find(
        (item) => item.case_id === caseId && item.state === 'changes_requested'
      ) || null;
    if (!correctionCase.value) {
      error.value = t('uploadPage.correction.unavailable');
    }
  } catch (requestError) {
    error.value = apiErrorMessage(
      requestError,
      t,
      t('uploadPage.correction.loadFailed')
    );
  }
}

async function uploadFiles() {
  if (!selectedProject.value || !selectedFiles.value.length) {
    error.value = t('uploadPage.errors.selectProjectAndFiles');
    return;
  }
  if (missingCorrectionFiles.value.length) {
    error.value = `Add every requested correction file before submitting: ${missingCorrectionFiles.value.join(', ')}`;
    return;
  }
  if (nonCompliantCount.value) {
    eventMessageStore.addMessage('uploadPage.complianceWarning', 'warning');
    return;
  }
  if (standardsLoading.value || standardsLoadFailed.value) {
    error.value = t('uploadPage.errors.standardsFailed');
    return;
  }
  uploading.value = true;
  uploadResults.value = [];
  error.value = '';
  try {
    const response = await gitService.uploadElanFiles(
      selectedProject.value,
      selectedFiles.value,
      username.value,
      correctionCase.value?.case_id || null,
      {
        topicId:
          !detectedResearchScope.value &&
          /^\d+$/.test(researchTopicChoice.value)
            ? Number(researchTopicChoice.value)
            : detectedResearchScope.value?.topicId || null,
        proposedTopicName:
          researchTopicChoice.value === '__propose__'
            ? proposedTopicName.value.trim()
            : '',
        summary: contributionSummary.value.trim(),
      }
    );
    completedUploadId.value = response.upload_id;
    uploadResults.value = [
      ...(response.uploaded_files || []).map((file) => ({
        ...file,
        success: true,
      })),
      ...(response.failed_files || []).map((file) => ({
        ...file,
        success: false,
      })),
    ];
    selectedFiles.value = [];
    researchTopicChoice.value = '';
    proposedTopicName.value = '';
    contributionSummary.value = '';
    detectedResearchScope.value = null;
    if (correctionCase.value && response.upload_id) {
      try {
        const linkedCase = await reviewService.resubmit(
          selectedProject.value,
          correctionCase.value.case_id,
          response.upload_id
        );
        completedUploadId.value = null;
        eventMessageStore.addMessage(
          'uploadPage.correctionLinked',
          'success',
          6000
        );
        await router.push({
          name: 'PendingUpload',
          query: {
            project: selectedProject.value,
            view: 'reviews',
            case: linkedCase.case_id,
          },
        });
      } catch (linkError) {
        error.value = apiErrorMessage(
          linkError,
          t,
          t('uploadPage.correction.linkFailed')
        );
      }
    }
  } catch (uploadError) {
    error.value = formatEafUploadError(
      uploadError,
      t,
      t('uploadPage.errors.uploadFailed')
    );
  } finally {
    uploading.value = false;
  }
}
</script>
