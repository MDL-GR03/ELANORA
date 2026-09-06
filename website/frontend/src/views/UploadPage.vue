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
        <span>Corrected contribution</span>
        <strong>{{ correctionCase.title }}</strong>
        <p>
          Upload the corrected ELAN file(s). The completed contribution will be
          linked to this request automatically.
        </p>
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
        >View discussion</router-link
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
          <select
            id="projectSelect"
            v-model="selectedProject"
            class="project-select"
            :disabled="loading || uploading"
          >
            <option value="">
              {{ t('uploadPage.projectSelection.placeholder') }}
            </option>
            <option
              v-for="project in projects"
              :key="project.project_id"
              :value="project.project_id"
            >
              {{ project.project_name }}
            </option>
          </select>
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
              :title="t('uploadPage.uploadZone.title')"
              :subtitle="t('uploadPage.uploadZone.subtitle')"
              :files-with-compliance="filesWithCompliance"
              :disabled="uploading || standardsLoading || standardsLoadFailed"
              @error="error = $event"
            />

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

            <div v-if="selectedFiles.length" class="upload-submit-bar">
              <div>
                <strong>{{ t('uploadPage.submitTitle') }}</strong>
                <span>{{ t('uploadPage.submitDescription') }}</span>
              </div>
              <button
                type="button"
                class="upload-btn"
                :disabled="
                  uploading ||
                  standardsLoading ||
                  standardsLoadFailed ||
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
            {{ t('uploadPage.selectProjectFirst') }}
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
        Finish linking this contribution to the correction request
        <font-awesome-icon icon="fa-solid fa-arrow-right" />
      </router-link>
    </section>

    <div v-if="error" class="error-message" role="alert">{{ error }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import gitService from '@/api/service/gitService';
import reviewService from '@/api/service/reviewService';
import UploadFolder from '@/components/common/UploadFolder.vue';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useEffectiveStandardStore } from '@/stores/effectiveStandard';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useNamingStandardStore } from '@/stores/namingStandard';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import { formatEafUploadError } from '@/utils/eafValidationError';
import { isFilenameCompliant } from '@/utils/filenameCompliance';
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
let standardsRequest = 0;

const username = computed(() => userStore.user?.username || '');
const projects = computed(() => projectStore.projects || []);
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
    await Promise.all([fetchStandards(), loadCorrectionContext()]);
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
  if (newProjectId)
    await Promise.all([fetchStandards(), loadCorrectionContext()]);
  else {
    hasEffectiveStandard.value = false;
    standard.value = null;
    standardsLoadFailed.value = false;
  }
});

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
      error.value =
        'This correction request is no longer available for resubmission.';
    }
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The correction request could not be loaded.';
  }
}

async function uploadFiles() {
  if (!selectedProject.value || !selectedFiles.value.length) {
    error.value = t('uploadPage.errors.selectProjectAndFiles');
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
      username.value
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
        error.value =
          linkError?.response?.data?.detail ||
          'The contribution was created, but could not be linked automatically. Use the action below to finish linking it.';
      }
    }
  } catch (uploadError) {
    error.value = formatEafUploadError(
      uploadError?.response?.data?.detail,
      t('uploadPage.errors.uploadFailed')
    );
  } finally {
    uploading.value = false;
  }
}
</script>
