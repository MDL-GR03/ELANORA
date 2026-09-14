<template>
  <div>
    <div class="project-page-root">
      <!-- Section 1: Project List as Card Grid -->
      <div class="project-page-section project-page-section-card">
        <WorkspaceHeader
          embedded
          :context="instanceName"
          :title="t('projectsPage.pageTitle')"
          :description="t('projectsPage.pageDescription')"
        >
          <template #actions>
            <button
              v-if="isAdmin"
              class="project-page-create-btn"
              @click="showCreateDialog = true"
            >
              <font-awesome-icon icon="fa-solid fa-plus" />
              {{ t('projectsPage.createProject') }}
            </button>
          </template>
        </WorkspaceHeader>
        <template v-if="(projectStore.projects?.length || 0) === 0">
          <div class="project-page-no-projects">
            {{ t('projectsPage.noProjects') }}
          </div>
        </template>
        <template v-else>
          <div class="project-page-card-grid">
            <div
              v-for="project in paginatedProjects"
              :key="project.project_id"
              :class="[
                'project-card',
                {
                  'project-card-active':
                    project.project_id === currentProjectId,
                },
              ]"
              @click="selectProject(project)"
            >
              <!-- Row 1: Name + Actions -->
              <div class="project-card-row project-card-row-header">
                <div class="project-card-title-container">
                  <span
                    class="project-card-title"
                    :title="project.project_name"
                  >
                    <font-awesome-icon
                      icon="fa-diagram-project"
                      class="project-card-title-icon"
                    />
                    {{ project.project_name }}
                  </span>
                </div>
                <div
                  v-if="isAdmin || canConfigureProject(project)"
                  class="project-card-actions"
                >
                  <button
                    v-if="isAdmin"
                    class="project-card-action-btn edit"
                    :title="t('projectsPage.project.buttons.rename')"
                    @click.stop="openEditDialog(project)"
                  >
                    <font-awesome-icon icon="fa-regular fa-pen-to-square" />
                  </button>
                  <button
                    v-if="canAdministerProject(project)"
                    class="project-card-action-btn share"
                    :title="t('projectsPage.project.buttons.share')"
                    @click.stop="openShareModal(project)"
                  >
                    <font-awesome-icon icon="fa-regular fa-share-from-square" />
                  </button>
                  <button
                    v-if="canConfigureProject(project)"
                    class="project-card-action-btn config"
                    :title="t('projectsPage.project.buttons.settings')"
                    @click.stop="goToStandardsPage(project)"
                  >
                    <font-awesome-icon icon="fa-solid fa-gears" />
                  </button>
                  <button
                    v-if="isAdmin"
                    class="project-card-action-btn project-card-delete-btn"
                    :title="t('projectsPage.project.buttons.delete')"
                    @click.stop="deleteProject(project.project_name)"
                  >
                    <font-awesome-icon icon="trash" />
                  </button>
                </div>
              </div>
              <!-- Row 2: Description -->
              <div class="project-card-row project-card-row-desc">
                <div class="project-card-desc-icon-section">
                  <font-awesome-icon
                    icon="fa-regular fa-comment-dots"
                    class="project-card-desc-icon-white"
                  />
                </div>
                <div
                  class="project-card-desc-container project-card-desc-container-contrast"
                >
                  <div class="project-card-desc-scroll">
                    <span class="project-card-desc-text">
                      {{
                        project.project_description ||
                        t('projectsPage.noDescription')
                      }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <!-- Pagination Controls -->
          <div v-if="totalPages > 1" class="project-page-pagination">
            <button
              :disabled="currentPage === 1"
              class="pagination-arrow-btn"
              @click="prevPage"
            >
              <font-awesome-icon icon="fa-solid fa-angles-left" />
            </button>
            <input
              v-model.number="currentPage"
              type="number"
              min="1"
              :max="totalPages"
              class="project-page-pagination-input"
              @change="goToPage(currentPage)"
            />
            <span>/ {{ totalPages }}</span>
            <button
              class="pagination-arrow-btn"
              :disabled="currentPage === totalPages"
              @click="nextPage"
            >
              <font-awesome-icon icon="fa-solid fa-angles-right" />
            </button>
          </div>
        </template>
      </div>

      <!-- Section Divider: only show if there are projects and a project is selected -->
      <div
        v-if="(projectStore.projects?.length || 0) > 0 && currentProjectName"
        class="project-page-section-divider"
      ></div>

      <!-- Section 2: Project Details (only if selected) -->
      <div
        v-if="currentProjectName"
        class="project-page-section project-page-section-card"
      >
        <div class="project-page-files-tree-section">
          <section
            class="project-selected-overview"
            :aria-labelledby="`selected-project-${currentProjectId}`"
          >
            <div class="project-selected-overview-icon" aria-hidden="true">
              <font-awesome-icon icon="fa-diagram-project" />
            </div>
            <div class="project-selected-overview-content">
              <span class="project-selected-overview-context">
                {{ t('projectsPage.selectedProject') }}
              </span>
              <h2 :id="`selected-project-${currentProjectId}`">
                {{ currentProjectName }}
              </h2>
              <p
                class="project-selected-description"
                :class="{
                  'project-selected-description--collapsed':
                    descriptionIsLong && !descriptionExpanded,
                }"
              >
                {{
                  selectedProjectDescription || t('projectsPage.noDescription')
                }}
              </p>
              <button
                v-if="descriptionIsLong"
                type="button"
                class="project-description-toggle"
                :aria-expanded="descriptionExpanded"
                @click="descriptionExpanded = !descriptionExpanded"
              >
                {{
                  descriptionExpanded
                    ? t('projectsPage.showLessDescription')
                    : t('projectsPage.readFullDescription')
                }}
              </button>
            </div>
          </section>
          <div class="project-page-files-tree-title-row">
            <div class="project-page-files-tree-title">
              {{
                t('projectsPage.filesInProject', {
                  projectName: currentProjectName,
                })
              }}
            </div>
            <button
              v-if="isAdmin"
              class="project-page-create-btn"
              :disabled="syncing"
              @click="openSyncDialog"
            >
              <font-awesome-icon
                icon="fa-solid fa-retweet"
                class="project-page-sync-icon"
              />
              {{
                syncing
                  ? t('projectsPage.synchronizing')
                  : t('projectsPage.synchronize')
              }}
            </button>
          </div>
          <div v-if="filesLoading" class="project-page-loading">
            {{ t('projectsPage.loadingFiles') }}
          </div>
          <div v-else>
            <!-- INFO BANNER containing the status row (only for admins) -->
            <div
              v-if="isAdmin"
              class="project-page-files-info-banner"
              :class="{
                'info-banner-compliant':
                  hasEffectiveStandard && nonCompliantCount === 0,
                'info-banner-noncompliant':
                  hasEffectiveStandard && nonCompliantCount > 0,
                'info-banner-no-standard': !hasEffectiveStandard,
              }"
            >
              <font-awesome-icon
                :icon="getBannerIcon"
                :class="['info-banner-icon', getBannerIconClass]"
              />
              <span class="info-banner-text">
                <template v-if="!hasEffectiveStandard">
                  {{ t('projectsPage.infoBanner.noEffectiveStandard1') }}
                  <button
                    class="info-banner-link"
                    @click="goToStandardsPage(projectStore.currentProject)"
                  >
                    {{ t('projectsPage.infoBanner.noEffectiveStandard2') }}
                  </button>
                  {{ t('projectsPage.infoBanner.noEffectiveStandard3') }}
                </template>
                <template v-else-if="nonCompliantCount > 0">
                  {{
                    t('projectsPage.infoBanner.nonCompliant', {
                      count: nonCompliantCount,
                    })
                  }}
                  <button
                    class="info-banner-bulk-rename-link"
                    tabindex="0"
                    @click="openBulkRenameDialog"
                    @keydown.enter="openBulkRenameDialog"
                  >
                    {{ t('projectsPage.infoBanner.bulkRename') }}
                  </button>
                </template>
                <template v-else>
                  {{ t('projectsPage.infoBanner.allCompliant') }}
                </template>
              </span>
            </div>
            <div
              v-if="
                projectFiles &&
                projectFiles.files &&
                projectFiles.files.length > 0
              "
            >
              <FileTree
                :files="projectFiles.files"
                :show-compliance="isAdmin && hasEffectiveStandard"
                :project-id="currentProjectId"
                :project-name="currentProjectName"
                :media-standard="mediaStandard"
                :project-standard="projectStandard"
                @rename="handleFileRename"
              />
            </div>
            <div v-else class="project-page-loading">
              {{ t('projectsPage.noFilesFound') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Project Create Modal (admin only) -->
      <ProjectCreateDialog
        v-if="showCreateDialog && isAdmin"
        @close="showCreateDialog = false"
        @created="onProjectCreated"
      />

      <!-- Edit Project Section (admin only) -->
      <ProjectEditDialog
        v-if="editDialogVisible && isAdmin"
        :project="editingProject"
        @close="closeEditDialog"
        @edited="onProjectEdited"
      />

      <!-- Project Share Modal (admin only) -->
      <ProjectShareModal
        v-if="
          showShareModal &&
          selectedShareProject &&
          canAdministerProject(selectedShareProject)
        "
        :show="showShareModal"
        :project-id="selectedShareProject.project_id"
        :project-name="shareProjectName"
        @close="closeShareModal"
      />

      <!-- Sync Dialog (admin only) -->
      <ProjectSyncDialog
        v-if="isAdmin"
        v-model:visible="syncDialogVisible"
        :project-name="currentProjectName"
        :is-admin="isAdmin"
        @sync-completed="handleSyncCompleted"
      />

      <!-- BulkRenameDialog (admin only) -->
      <BulkRenameDialog
        v-if="bulkRenameDialogVisible && isAdmin"
        :files="nonCompliantFiles"
        :all-files="projectFiles?.files || []"
        :project-id="currentProjectId"
        :project-name="currentProjectName"
        :project-standard="projectStandard"
        :media-standard="mediaStandard"
        @close="bulkRenameDialogVisible = false"
        @rename="handleBulkRename"
        @conflict="handleBulkRenameConflict"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useProjectStore } from '@stores/project';
import { useUserStore } from '@stores/user';
import { useAppInfoStore } from '@stores/appInfo';
import gitService from '@api/service/gitService';
import FileTree from '@components/common/FileTree.vue';
import ProjectCreateDialog from '@/components/pageSpecific/projectsPage/ProjectCreateDialog.vue';
import ProjectShareModal from '@components/common/ProjectShareModal.vue';
import ProjectSyncDialog from '@/components/pageSpecific/projectsPage/ProjectSyncDialog.vue';
import {
  hasProjectCapability,
  hasProjectPermission,
} from '@/utils/authorization';
import ProjectEditDialog from '@/components/pageSpecific/projectsPage/ProjectEditDialog.vue';
import BulkRenameDialog from '@/components/pageSpecific/projectsPage/BulkRenameDialog.vue';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useHead } from '@unhead/vue';
import { useEffectiveStandardStore } from '@/stores/effectiveStandard';
import { useNamingStandardStore } from '@/stores/namingStandard';
import { useEventMessageStore } from '@/stores/eventMessage';
import { isFilenameCompliant } from '@/utils/filenameCompliance';
import { getMediaStandardForProject } from '@/utils/filenameFromMediaFile';
import { reportClientError } from '@/utils/errorDiagnostics';

const projectStore = useProjectStore();
const userStore = useUserStore();
const appInfoStore = useAppInfoStore();
const eventMessageStore = useEventMessageStore();
const router = useRouter();
const projects = ref([]);
const loading = ref(true);
const { t } = useI18n();
const standardName = ref('');

useHead({
  title: computed(() => t('projectsPage.pageTitle')),
  meta: [
    {
      name: 'description',
      content: computed(() => t('projectsPage.pageDescription')),
    },
  ],
});

const instanceName = computed(
  () => appInfoStore.instance?.instance_name || 'ELANORA'
);

const showCreateDialog = ref(false);

const projectFiles = ref(null);
const filesLoading = ref(false);
let projectFilesRequest = 0;

const currentProjectId = computed(
  () => projectStore.currentProject?.project_id
);
const currentProjectName = computed(
  () => projectStore.currentProject?.project_name
);
const selectedProjectDescription = computed(
  () => projectStore.currentProject?.project_description?.trim() || ''
);
const descriptionExpanded = ref(false);
const descriptionIsLong = computed(
  () => selectedProjectDescription.value.length > 180
);

const syncing = ref(false);
const syncDialogVisible = ref(false);

// Share modal state
const showShareModal = ref(false);
const shareProjectName = ref('');

// Check if user is admin
const isAdmin = computed(() => userStore.user?.role === 'admin');
const selectedShareProject = computed(() =>
  projectStore.projects.find(
    (project) => project.project_name === shareProjectName.value
  )
);
const canAdministerProject = (project) =>
  hasProjectPermission(userStore.user, project, 'admin');
const canConfigureProject = (project) =>
  canAdministerProject(project) ||
  hasProjectCapability(userStore.user, project, 'manage_protocols');

// Standard state
const hasEffectiveStandard = ref(false);
const projectStandard = ref(null);
const mediaStandard = ref(null);

// Pagination state
const pageSize = 6;
const currentPage = ref(1);

const totalPages = computed(() =>
  Math.max(1, Math.ceil((projectStore.projects?.length || 0) / pageSize))
);

const paginatedProjects = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return projectStore.projects.slice(start, start + pageSize);
});

// Banner computed properties
const getBannerIcon = computed(() => {
  if (!hasEffectiveStandard.value) return 'fa-solid fa-circle-info';
  return nonCompliantCount.value > 0
    ? 'fa-solid fa-square-xmark'
    : 'fa-solid fa-square-check';
});

const getBannerIconClass = computed(() => {
  if (!hasEffectiveStandard.value) return 'icon-no-standard';
  return nonCompliantCount.value > 0 ? 'icon-noncompliant' : 'icon-compliant';
});

function goToPage(page) {
  let num = Number(page);
  if (isNaN(num) || num < 1) num = 1;
  if (num > totalPages.value) num = totalPages.value;
  currentPage.value = num;
}

function nextPage() {
  if (currentPage.value < totalPages.value) currentPage.value++;
}

function prevPage() {
  if (currentPage.value > 1) currentPage.value--;
}

// Reset to page 1 if projects change and current page is out of bounds
watch(
  () => projectStore.projects?.length,
  () => {
    if (currentPage.value > totalPages.value) currentPage.value = 1;
  }
);

watch(currentPage, (val) => {
  if (val < 1) currentPage.value = 1;
  if (val > totalPages.value) currentPage.value = totalPages.value;
});

watch(currentProjectId, () => {
  descriptionExpanded.value = false;
  projectFiles.value = null;
  hasEffectiveStandard.value = false;
  projectStandard.value = null;
  mediaStandard.value = null;
});

async function fetchProjects() {
  loading.value = true;
  try {
    const res = await gitService.listUserProjects();
    projects.value = res.projects;
    projectStore.setProjects(res.projects);
    if (res.projects.length === 0) {
      projectStore.clearCurrentProject();
      projectFiles.value = null;
    }
  } finally {
    loading.value = false;
  }
}

function selectProject(project) {
  projectStore.setCurrentProject(project);
}

async function fetchProjectFiles() {
  const request = ++projectFilesRequest;
  const projectId = currentProjectId.value;
  const projectName = currentProjectName.value;
  if (!projectName || !projectId) {
    projectFiles.value = null;
    hasEffectiveStandard.value = false;
    filesLoading.value = false;
    return;
  }

  filesLoading.value = true;
  try {
    const PROJECT_FILES_LOCATION_ID = 1;

    // Fetch standards for this project/location
    const effectiveStandardStore = useEffectiveStandardStore();
    const namingStandardStore = useNamingStandardStore();
    const [res] = await Promise.all([
      gitService.listProjectFiles(projectName, true),
      effectiveStandardStore.fetchEffectiveStandards(
        projectId,
        PROJECT_FILES_LOCATION_ID
      ),
      namingStandardStore.fetchStandardsAndComponentNames(projectId),
      effectiveStandardStore.fetchEffectiveStandards(projectId, 3),
    ]);

    if (request !== projectFilesRequest || projectId !== currentProjectId.value)
      return;

    // Get the first naming standard ID assigned for this location
    let standardId;
    const standardsObj =
      effectiveStandardStore.effectiveStandards[PROJECT_FILES_LOCATION_ID];
    if (standardsObj && typeof standardsObj === 'object') {
      // Get the first available naming_standard_id
      const ids = Object.values(standardsObj).filter((id) => !!id);
      standardId = ids.length > 0 ? ids[0] : undefined;
    } else if (
      typeof standardsObj === 'string' ||
      typeof standardsObj === 'number'
    ) {
      standardId = standardsObj;
    }

    // Check if there's an effective standard
    hasEffectiveStandard.value = !!standardId;

    // Check compliance for each file and add isCompliant property
    const standard = namingStandardStore.standards.find(
      (std) => std.id === standardId
    );
    standardName.value = standard ? standard.name : '';

    // Store the project standard for use in FileTree suggestions
    projectStandard.value = standard;

    // Get media standard for suggestions
    mediaStandard.value = await getMediaStandardForProject(
      projectId,
      effectiveStandardStore,
      namingStandardStore,
      false
    );

    if (request !== projectFilesRequest || projectId !== currentProjectId.value)
      return;

    // Only check compliance if there's a standard and user is admin
    res.files = res.files.map((file) => {
      const isCompliant =
        standard && isAdmin.value
          ? isFilenameCompliant(standard, file.name)
          : true;
      return {
        ...file,
        isCompliant,
      };
    });

    projectFiles.value = res;
  } finally {
    if (request === projectFilesRequest) filesLoading.value = false;
  }
}

async function openSyncDialog() {
  if (!currentProjectName.value || !isAdmin.value) return;
  syncing.value = true;
  syncDialogVisible.value = true;
  syncing.value = false;
}

function handleSyncCompleted() {
  fetchProjectFiles();
  fetchProjects();
}

const userConfirm = useUserConfirm();

async function deleteProject(projectName) {
  if (!isAdmin.value) return;

  const confirmed = await userConfirm({
    title: t('projectsPage.deleteTitle'),
    message: t('projectsPage.deleteMessage', { projectName }),
    confirmText: t('projectsPage.deleteConfirm'),
    cancelText: t('projectsPage.deleteCancel'),
  });
  if (!confirmed) return;

  try {
    await gitService.deleteProject(projectName);
    await fetchProjects();
    if (currentProjectName.value === projectName) {
      projectStore.clearCurrentProject();
      projectFiles.value = null;
    }
  } catch (error) {
    reportClientError('Failed to delete project', error);
  }
}

const editDialogVisible = ref(false);
const editingProject = ref(null);

function openEditDialog(project) {
  if (!isAdmin.value) return;
  editingProject.value = project;
  editDialogVisible.value = true;
}

function closeEditDialog() {
  editingProject.value = null;
  editDialogVisible.value = false;
}

async function onProjectEdited() {
  closeEditDialog();
  await fetchProjects();
}

function handleFileRename({ file, newName }) {
  // Update the file in the local files array to reflect the rename
  if (projectFiles.value && projectFiles.value.files) {
    const fileIndex = projectFiles.value.files.findIndex(
      (f) => f.elan_id === file.elan_id
    );
    if (fileIndex !== -1) {
      // Update the filename only - DO NOT update lastModified since content hasn't changed
      projectFiles.value.files[fileIndex].name = newName;

      // Update compliance status if standards are available
      if (projectStandard.value) {
        const isCompliant = isFilenameCompliant(projectStandard.value, newName);
        projectFiles.value.files[fileIndex].isCompliant = isCompliant;
      }

      // Show success message
      eventMessageStore.addMessage('rename.success', 'success', 4000);
    }
  }
}

function openShareModal(project) {
  if (!canAdministerProject(project)) return;
  shareProjectName.value = project.project_name;
  showShareModal.value = true;
}

function closeShareModal() {
  showShareModal.value = false;
  shareProjectName.value = '';
}

watch(
  [() => projectStore.projects, currentProjectName],
  ([projectsVal, currentProjectVal]) => {
    if (
      projectsVal.length > 0 &&
      currentProjectVal &&
      projectsVal.some((p) => p.project_name === currentProjectVal)
    ) {
      fetchProjectFiles();
    }
  },
  { immediate: true }
);

onMounted(async () => {
  if (!projectStore.initialized) {
    await projectStore.ensureProjects();
  }
  projectStore.initBroadcastChannel();
  projectStore.loadCurrentProject();
});

function goToStandardsPage(project) {
  if (!canConfigureProject(project)) return;
  router.push({
    name: 'ProjectConfigurationPage',
    params: { projectId: project.project_id },
  });
}

function onProjectCreated() {
  showCreateDialog.value = false;
  fetchProjects();
}

const nonCompliantFiles = computed(() =>
  isAdmin.value && hasEffectiveStandard.value
    ? projectFiles.value?.files?.filter((f) => f.isCompliant === false) || []
    : []
);
const nonCompliantCount = computed(() => nonCompliantFiles.value.length);

const bulkRenameDialogVisible = ref(false);
function openBulkRenameDialog() {
  if (!isAdmin.value) return;
  bulkRenameDialogVisible.value = true;
}

function handleBulkRename(eventData) {
  // Extract renames from the event data
  const renames = eventData.renames || eventData;
  const result = eventData.result;

  // Update files locally instead of refetching everything
  if (
    projectFiles.value &&
    projectFiles.value.files &&
    renames &&
    renames.length > 0
  ) {
    // Only update files that were successfully renamed (no conflicts)
    const successfulRenames =
      result && result.results
        ? renames.filter((rename) => {
            // Find the current filename for this elan_id to match with backend results
            const currentFile = projectFiles.value.files.find(
              (f) => f.elan_id === rename.elan_id
            );
            if (!currentFile) {
              return false;
            }

            // Match by current filename in the backend results
            const renameResult = result.results.find(
              (r) => r.old_filename === currentFile.name
            );
            const success =
              renameResult &&
              renameResult.success &&
              !renameResult.conflict_elan_id;
            return success;
          })
        : renames; // If no result data, assume all were successful

    successfulRenames.forEach((rename) => {
      const fileIndex = projectFiles.value.files.findIndex(
        (f) => f.elan_id === rename.elan_id
      );
      if (fileIndex !== -1) {
        // Update the filename only - DO NOT update lastModified since content hasn't changed
        projectFiles.value.files[fileIndex].name = rename.new_filename;

        // Update compliance status if standards are available
        if (projectStandard.value) {
          const isCompliant = isFilenameCompliant(
            projectStandard.value,
            rename.new_filename
          );
          projectFiles.value.files[fileIndex].isCompliant = isCompliant;
        }
      } else {
        reportClientError('Could not find renamed file in project files');
      }
    });

    // Show appropriate success message based on results
    if (result) {
      const totalRequested = renames.length;
      const successful = successfulRenames.length;
      const conflicts = result.conflicts_count || 0;
      const failed = totalRequested - successful;

      if (successful === totalRequested && conflicts === 0) {
        // All files renamed successfully
        eventMessageStore.addMessage('rename.bulkSuccess', 'success', 4000);
      } else if (successful > 0 && conflicts > 0) {
        // Mixed results: some success, some conflicts - choose message based on singular/plural
        if (successful === 1 && conflicts === 1) {
          eventMessageStore.addMessage(
            'rename.bulkMixedSingular',
            'warning',
            6000
          );
        } else if (successful === 1) {
          eventMessageStore.addMessage(
            'rename.bulkMixedOneSuccess',
            'warning',
            6000,
            { failed: conflicts }
          );
        } else if (conflicts === 1) {
          eventMessageStore.addMessage(
            'rename.bulkMixedOneConflict',
            'warning',
            6000,
            { successful: successful }
          );
        } else {
          eventMessageStore.addMessage('rename.bulkMixed', 'warning', 6000, {
            successful: successful,
            failed: conflicts,
          });
        }
      } else if (successful === 0 && conflicts > 0) {
        // All failed due to conflicts
        if (conflicts === 1) {
          eventMessageStore.addMessage(
            'rename.bulkAllConflictsSingular',
            'warning',
            6000
          );
        } else {
          eventMessageStore.addMessage(
            'rename.bulkAllConflicts',
            'warning',
            6000,
            {
              count: conflicts,
            }
          );
        }
      } else if (successful > 0) {
        // Some succeeded, some failed for other reasons
        if (successful === 1 && failed === 1) {
          eventMessageStore.addMessage(
            'rename.bulkPartialSingular',
            'warning',
            6000
          );
        } else if (successful === 1) {
          eventMessageStore.addMessage(
            'rename.bulkPartialOneSuccess',
            'warning',
            6000,
            { failed: failed }
          );
        } else if (failed === 1) {
          eventMessageStore.addMessage(
            'rename.bulkPartialOneFailed',
            'warning',
            6000,
            { successful: successful }
          );
        } else {
          eventMessageStore.addMessage('rename.bulkPartial', 'warning', 6000, {
            successful: successful,
            failed: failed,
          });
        }
      }
    } else if (successfulRenames.length > 0) {
      // Fallback: All files renamed successfully (no result data)
      eventMessageStore.addMessage('rename.bulkSuccess', 'success', 4000);
    }
  }

  // Close the dialog
  bulkRenameDialogVisible.value = false;
}

function handleBulkRenameConflict() {
  // TODO: When merge tool is implemented, you can collect these conflicts
  // and present them to the user for resolution
  // Note: Don't show message here - let handleBulkRename show a single comprehensive message
  // Note: Don't close the dialog here - let handleBulkRename handle that after updating files
}
</script>

<style src="@/assets/css/projects-page.css"></style>
