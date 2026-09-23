<template>
  <div class="upload-page-root">
    <WorkspaceHeader
      embedded
      :context="currentProjectName"
      :title="t('uploadPage.title')"
      :description="t('uploadPage.pageDescription')"
    />

    <UploadCorrectionContext
      v-if="correctionCase"
      :correction-case="correctionCase"
      :project-id="selectedProject"
    />

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
              :standard="standard"
              :media-standard="mediaStandard"
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

          <UploadContextStep
            v-if="selectedFiles.length"
            :context="context"
            :topics="researchTopics"
            :topics-loading="researchTopicsLoading"
            :busy="uploading"
          >
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
          </UploadContextStep>
          <div v-else class="upload-step-placeholder">
            <font-awesome-icon icon="fa-solid fa-arrow-up" />
            {{ t('uploadPage.context.addFilesFirst') }}
          </div>
        </div>
      </section>
    </div>

    <UploadResults
      v-if="uploadResults.length"
      :results="uploadResults"
      :project-id="selectedProject"
      :upload-id="completedUploadId"
      :correction-case-id="correctionCase?.case_id ?? null"
    />

    <div
      v-if="error"
      :class="
        errorIsInformational
          ? 'upload-compliance-banner upload-compliance-banner--warning'
          : 'error-message'
      "
      :role="errorIsInformational ? 'status' : 'alert'"
    >
      <template v-if="errorIsInformational">
        <font-awesome-icon icon="fa-solid fa-circle-info" />
        <span>{{ error }}</span>
      </template>
      <template v-else>
        {{ error }}
      </template>
    </div>
  </div>
</template>

<script setup>
import '@/assets/css/upload-page.css';
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import gitService from '@/api/service/gitService';
import reviewService from '@/api/service/reviewService';
import { fetchResearchTopics } from '@/api/service/tierService';
import AppSelect from '@/components/common/AppSelect.vue';
import UploadFolder from '@/components/common/UploadFolder.vue';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import UploadContextStep from '@/components/pageSpecific/upload/UploadContextStep.vue';
import UploadCorrectionContext from '@/components/pageSpecific/upload/UploadCorrectionContext.vue';
import UploadResults from '@/components/pageSpecific/upload/UploadResults.vue';
import { useContributionContext } from '@/composables/useContributionContext';
import { useUploadStandard } from '@/composables/useUploadStandard';
import { useEffectiveStandardStore } from '@/stores/effectiveStandard';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useNamingStandardStore } from '@/stores/namingStandard';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import { apiErrorCode, apiErrorMessage } from '@/utils/apiError';
import { findMissingCorrectionFiles } from '@/utils/correctionFiles';
import { formatEafUploadError } from '@/utils/eafValidationError';
import { getMediaStandardForProject } from '@/utils/filenameFromMediaFile';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const projectStore = useProjectStore();
const messages = useEventMessageStore();

const selectedProject = ref('');
const selectedFiles = ref([]);
const loading = ref(true);
const uploading = ref(false);
const uploadResults = ref([]);
const completedUploadId = ref(null);
const correctionCase = ref(null);
const error = ref('');
const errorIsInformational = ref(false);
const researchTopics = ref([]);
const researchTopicsLoading = ref(false);
const mediaStandard = ref(null);

const uploadStandard = useUploadStandard();
const {
  standard,
  loading: standardsLoading,
  failed: standardsLoadFailed,
  hasStandard: hasEffectiveStandard,
} = uploadStandard;
const context = useContributionContext({ topics: researchTopics });
const contributionContextReady = context.ready;

const projects = computed(() => projectStore.projects || []);
const projectOptions = computed(() =>
  projects.value.map((project) => ({
    value: project.project_id,
    label: project.project_name,
  }))
);
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
    isCompliant: uploadStandard.isCompliant(file.name),
  }))
);
const nonCompliantCount = computed(
  () => filesWithCompliance.value.filter((file) => !file.isCompliant).length
);
const missingCorrectionFiles = computed(() =>
  findMissingCorrectionFiles(correctionCase.value, selectedFiles.value)
);

async function loadStandard() {
  const loaded = await uploadStandard.load(selectedProject.value);
  if (!loaded) error.value = t('uploadPage.errors.standardsFailed');
}

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

async function loadMediaStandard() {
  if (!selectedProject.value) {
    mediaStandard.value = null;
    return;
  }
  const effectiveStandardStore = useEffectiveStandardStore();
  const namingStandardStore = useNamingStandardStore();
  const standard = await getMediaStandardForProject(
    selectedProject.value,
    effectiveStandardStore,
    namingStandardStore
  );
  mediaStandard.value = standard || null;
}

function loadProjectContext() {
  return Promise.all([
    loadStandard(),
    loadCorrectionContext(),
    loadResearchTopics(),
    loadMediaStandard(),
  ]);
}

function resetForProject() {
  selectedFiles.value = [];
  uploadResults.value = [];
  completedUploadId.value = null;
  correctionCase.value = null;
  error.value = '';
  errorIsInformational.value = false;
  mediaStandard.value = null;
  context.reset();
}

function uploadRefusal() {
  if (!selectedProject.value || !selectedFiles.value.length) {
    return t('uploadPage.errors.selectProjectAndFiles');
  }
  if (missingCorrectionFiles.value.length) {
    return t('uploadPage.errors.correctionFilesMissing', {
      files: missingCorrectionFiles.value.join(', '),
    });
  }
  if (standardsLoading.value || standardsLoadFailed.value) {
    return t('uploadPage.errors.standardsFailed');
  }
  return '';
}

async function linkCorrection(uploadId) {
  try {
    const linkedCase = await reviewService.resubmit(
      selectedProject.value,
      correctionCase.value.case_id,
      uploadId
    );
    completedUploadId.value = null;
    messages.addMessage('uploadPage.correctionLinked', 'success', 6000);
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

async function uploadFiles() {
  if (nonCompliantCount.value) {
    messages.addMessage('uploadPage.complianceWarning', 'warning');
    return;
  }
  const refusal = uploadRefusal();
  if (refusal) {
    error.value = refusal;
    return;
  }
  uploading.value = true;
  uploadResults.value = [];
  error.value = '';
  errorIsInformational.value = false;
  try {
    const response = await gitService.uploadElanFiles(
      selectedProject.value,
      selectedFiles.value,
      userStore.user?.username || '',
      correctionCase.value?.case_id || null,
      context.payload()
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
    context.reset();
    if (correctionCase.value && response.upload_id) {
      await linkCorrection(response.upload_id);
    }
  } catch (uploadError) {
    const code = apiErrorCode(uploadError);
    errorIsInformational.value =
      code === 'contribution_no_changes' ||
      code === 'contribution_duplicate_pending';
    error.value = formatEafUploadError(
      uploadError,
      t,
      t('uploadPage.errors.uploadFailed')
    );
  } finally {
    uploading.value = false;
  }
}

onMounted(async () => {
  projectStore.initializeFromStorage();
  await projectStore.ensureProjects();
  const requestedProjectId = Number(route.query.project);
  selectedProject.value = projects.value.some(
    (project) => project.project_id === requestedProjectId
  )
    ? requestedProjectId
    : projectStore.currentProject?.project_id || '';
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

watch(selectedProject, async (projectId) => {
  const project = projects.value.find(
    (candidate) => candidate.project_id === Number(projectId)
  );
  if (
    project &&
    project.project_id !== projectStore.currentProject?.project_id
  ) {
    projectStore.setCurrentProject(project);
  } else if (!projectId && projectStore.currentProject) {
    projectStore.clearCurrentProject();
  }
  resetForProject();
  if (projectId) await loadProjectContext();
  else {
    uploadStandard.clear();
    mediaStandard.value = null;
  }
});

watch(selectedFiles, (files) => context.detectFrom(files));
</script>
