<template>
  <div>
    <div class="project-page-root">
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
        <div v-if="!projects.length" class="project-page-no-projects">
          {{ t('projectsPage.noProjects') }}
        </div>
        <template v-else>
          <div class="project-page-card-grid">
            <ProjectCard
              v-for="project in pageItems"
              :key="project.project_id"
              :project="project"
              :active="project.project_id === currentProject?.project_id"
              :can-edit="isAdmin"
              :can-delete="isAdmin"
              :can-share="canAdministerProject(project)"
              :can-configure="canConfigureProject(project)"
              @select="projectStore.setCurrentProject(project)"
              @edit="editingProject = project"
              @share="sharedProject = project"
              @configure="openConfiguration(project)"
              @delete="deleteProject(project)"
            />
          </div>
          <div v-if="pageCount > 1" class="project-page-pagination">
            <button
              :disabled="page === 1"
              class="pagination-arrow-btn"
              @click="previous"
            >
              <font-awesome-icon icon="fa-solid fa-angles-left" />
            </button>
            <input
              :value="page"
              type="number"
              min="1"
              :max="pageCount"
              class="project-page-pagination-input"
              :aria-label="t('projectsPage.pagination.pageNumberLabel')"
              @change="goTo($event.target.value)"
            />
            <span>/ {{ pageCount }}</span>
            <button
              class="pagination-arrow-btn"
              :disabled="page === pageCount"
              @click="next"
            >
              <font-awesome-icon icon="fa-solid fa-angles-right" />
            </button>
          </div>
        </template>
      </div>

      <template v-if="currentProject">
        <div v-if="projects.length" class="project-page-section-divider"></div>
        <div class="project-page-section project-page-section-card">
          <div class="project-page-files-tree-section">
            <SelectedProjectOverview
              :key="currentProject.project_id"
              :project="currentProject"
            />
            <div class="project-page-files-tree-title-row">
              <div class="project-page-files-tree-title">
                {{
                  t('projectsPage.filesInProject', {
                    projectName: currentProject.project_name,
                  })
                }}
              </div>
              <button
                v-if="isAdmin"
                class="project-page-create-btn"
                @click="syncDialogVisible = true"
              >
                <font-awesome-icon
                  icon="fa-solid fa-retweet"
                  class="project-page-sync-icon"
                />
                {{ t('projectsPage.synchronize') }}
              </button>
            </div>
            <div v-if="projectFiles.loading.value" class="project-page-loading">
              {{ t('projectsPage.loadingFiles') }}
            </div>
            <div v-else>
              <ProjectComplianceBanner
                v-if="isAdmin"
                :has-standard="projectFiles.hasEffectiveStandard.value"
                :non-compliant-count="
                  projectFiles.nonCompliantFiles.value.length
                "
                @configure="openConfiguration(currentProject)"
                @bulk-rename="bulkRenameOpen = true"
              />
              <FileTree
                v-if="projectFiles.files.value.length"
                :files="projectFiles.files.value"
                :show-compliance="projectFiles.checksCompliance.value"
                :project-id="currentProject.project_id"
                :project-name="currentProject.project_name"
                :media-standard="projectFiles.mediaStandard.value"
                :project-standard="projectFiles.projectStandard.value"
                @rename="onFileRenamed"
              />
              <div v-else class="project-page-loading">
                {{ t('projectsPage.noFilesFound') }}
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-if="isAdmin">
        <ProjectCreateDialog
          v-if="showCreateDialog"
          @close="showCreateDialog = false"
          @created="onProjectCreated"
        />
        <ProjectEditDialog
          v-if="editingProject"
          :project="editingProject"
          @close="editingProject = null"
          @edited="onProjectEdited"
        />
        <ProjectSyncDialog
          v-model:visible="syncDialogVisible"
          :project-name="currentProject?.project_name"
          :is-admin="isAdmin"
          @sync-completed="onSynchronized"
        />
        <BulkRenameDialog
          v-if="bulkRenameOpen && currentProject"
          :files="projectFiles.nonCompliantFiles.value"
          :all-files="projectFiles.files.value"
          :project-id="currentProject.project_id"
          :project-name="currentProject.project_name"
          :project-standard="projectFiles.projectStandard.value"
          :media-standard="projectFiles.mediaStandard.value"
          @close="bulkRenameOpen = false"
          @rename="onBulkRenamed"
        />
      </template>
      <ProjectShareModal
        v-if="sharedProject && canAdministerProject(sharedProject)"
        :show="true"
        :project-id="sharedProject.project_id"
        :project-name="sharedProject.project_name"
        @close="sharedProject = null"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useHead } from '@unhead/vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import gitService from '@/api/service/gitService';
import FileTree from '@/components/common/FileTree.vue';
import ProjectShareModal from '@/components/common/ProjectShareModal.vue';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import BulkRenameDialog from '@/components/pageSpecific/projectsPage/BulkRenameDialog.vue';
import ProjectCard from '@/components/pageSpecific/projectsPage/ProjectCard.vue';
import ProjectComplianceBanner from '@/components/pageSpecific/projectsPage/ProjectComplianceBanner.vue';
import ProjectCreateDialog from '@/components/pageSpecific/projectsPage/ProjectCreateDialog.vue';
import ProjectEditDialog from '@/components/pageSpecific/projectsPage/ProjectEditDialog.vue';
import ProjectSyncDialog from '@/components/pageSpecific/projectsPage/ProjectSyncDialog.vue';
import SelectedProjectOverview from '@/components/pageSpecific/projectsPage/SelectedProjectOverview.vue';
import { usePagination } from '@/composables/usePagination';
import { useProjectFiles } from '@/composables/useProjectFiles';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useAppInfoStore } from '@/stores/appInfo';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import { apiErrorMessage } from '@/utils/apiError';
import {
  hasProjectCapability,
  hasProjectPermission,
} from '@/utils/authorization';
import {
  bulkRenameMessage,
  successfulRenames,
} from '@/utils/bulkRenameOutcome';
import { reportClientError } from '@/utils/errorDiagnostics';

const PROJECTS_PER_PAGE = 6;

const { t } = useI18n();
const router = useRouter();
const projectStore = useProjectStore();
const userStore = useUserStore();
const appInfoStore = useAppInfoStore();
const messages = useEventMessageStore();
const confirmAction = useUserConfirm();

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
const projects = computed(() => projectStore.projects ?? []);
const currentProject = computed(() => projectStore.currentProject);
const isAdmin = computed(() => userStore.user?.role === 'admin');
const { page, pageCount, pageItems, goTo, next, previous } = usePagination(
  projects,
  PROJECTS_PER_PAGE
);
const projectFiles = useProjectFiles({ isAdmin });

const showCreateDialog = ref(false);
const editingProject = ref(null);
const sharedProject = ref(null);
const syncDialogVisible = ref(false);
const bulkRenameOpen = ref(false);

function canAdministerProject(project) {
  return hasProjectPermission(userStore.user, project, 'admin');
}

function canConfigureProject(project) {
  return (
    canAdministerProject(project) ||
    hasProjectCapability(userStore.user, project, 'manage_protocols')
  );
}

function openConfiguration(project) {
  if (!project || !canConfigureProject(project)) return;
  router.push({
    name: 'ProjectConfigurationPage',
    params: { projectId: project.project_id },
  });
}

async function refreshProjects() {
  const { projects: list } = await gitService.listUserProjects();
  projectStore.setProjects(list);
  if (!list.length) projectStore.clearCurrentProject();
}

async function deleteProject(project) {
  const confirmed = await confirmAction({
    title: t('projectsPage.deleteTitle'),
    message: t('projectsPage.deleteMessage', {
      projectName: project.project_name,
    }),
    confirmText: t('projectsPage.deleteConfirm'),
    cancelText: t('projectsPage.deleteCancel'),
    tone: 'danger',
  });
  if (!confirmed) return;
  try {
    await gitService.deleteProject(project.project_name);
    if (currentProject.value?.project_id === project.project_id) {
      projectStore.clearCurrentProject();
    }
    await refreshProjects();
  } catch (error) {
    reportClientError('Failed to delete project', error);
    messages.addMessage(
      apiErrorMessage(error, t, t('projectsPage.deleteFailed')),
      'error'
    );
  }
}

async function onProjectCreated() {
  showCreateDialog.value = false;
  await refreshProjects();
}

async function onProjectEdited() {
  editingProject.value = null;
  await refreshProjects();
}

async function onSynchronized() {
  await Promise.all([
    projectFiles.load(currentProject.value),
    refreshProjects(),
  ]);
}

function onFileRenamed({ file, newName }) {
  projectFiles.applyRenames([{ elan_id: file.elan_id, new_filename: newName }]);
  messages.addMessage('rename.success', 'success', 4000);
}

function onBulkRenamed({ renames = [], result } = {}) {
  const accepted = successfulRenames(renames, result, projectFiles.files.value);
  projectFiles.applyRenames(accepted);
  const message = result
    ? bulkRenameMessage({
        requested: renames.length,
        successful: accepted.length,
        conflicts: result.conflicts_count || 0,
      })
    : accepted.length &&
      bulkRenameMessage({
        requested: accepted.length,
        successful: accepted.length,
        conflicts: 0,
      });
  if (message) {
    messages.addMessage(
      message.key,
      message.type,
      message.duration,
      message.params
    );
  }
  bulkRenameOpen.value = false;
}

// The stored selection may arrive before the project list; load its files
// once the project is known to be one this user can open.
const openableProjectId = computed(() => {
  const id = currentProject.value?.project_id;
  return projects.value.some((project) => project.project_id === id)
    ? id
    : null;
});

watch(
  openableProjectId,
  (id) => {
    bulkRenameOpen.value = false;
    if (id) void projectFiles.load(currentProject.value);
    else projectFiles.clear();
  },
  { immediate: true }
);

onMounted(async () => {
  if (!projectStore.initialized) await projectStore.ensureProjects();
  projectStore.initBroadcastChannel();
  projectStore.loadCurrentProject();
});
</script>

<style src="@/assets/css/projects-page.css"></style>
