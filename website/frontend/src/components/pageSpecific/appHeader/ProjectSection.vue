<template>
  <div ref="dropdownRoot" class="project-section-root">
    <button
      class="project-section-trigger"
      :aria-expanded="dropdownOpen"
      :aria-label="
        currentProject
          ? currentProjectName
          : t('appHeader.projectSection.selectProject')
      "
      @click="toggleDropdown"
    >
      <span class="project-section-current">
        <svg
          class="project-section-icon"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            fill="currentColor"
            d="M4 4h7v7H4V4Zm9 0h7v7h-7V4ZM4 13h7v7H4v-7Zm9 0h7v7h-7v-7Z"
          />
        </svg>
        <span
          class="project-section-current-name"
          :data-tooltip="currentProjectName"
          :title="
            currentProjectName || t('appHeader.projectSection.selectProject')
          "
        >
          {{
            currentProjectName || t('appHeader.projectSection.selectProject')
          }}
        </span>
      </span>
      <svg
        class="project-section-chevron"
        width="16"
        height="16"
        viewBox="0 0 20 20"
      >
        <path
          fill="currentColor"
          d="M5.23 7.21a1 1 0 0 1 1.41.02L10 10.67l3.36-3.44a1 1 0 1 1 1.42 1.4l-4.07 4.17a1 1 0 0 1-1.42 0L5.21 8.63a1 1 0 0 1 .02-1.42z"
        />
      </svg>
    </button>
    <transition name="project-section-fade">
      <ul v-if="dropdownOpen" class="project-section-menu" @click.stop>
        <li
          v-for="project in projects"
          :key="project.project_id || project"
          class="project-section-menuitem"
        >
          <button
            class="project-section-action"
            :disabled="isCurrentProject(project)"
            @click="selectProject(project)"
          >
            <span
              class="project-section-menuitem-name"
              :title="project.project_name || project"
            >
              {{ project.project_name || project }}
            </span>
            <span
              v-if="isCurrentProject(project)"
              class="project-section-current-indicator"
              >✓</span
            >
          </button>
        </li>
      </ul>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useProjectStore } from '@/stores/project';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

const projectStore = useProjectStore();
const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const projects = computed(() => projectStore.projects || []);
const currentProject = computed(() => projectStore.currentProject);
const currentProjectName = computed(() => {
  if (!currentProject.value) {
    return t('appHeader.projectSection.selectProject');
  }
  if (typeof currentProject.value === 'object') {
    return (
      currentProject.value.project_name ||
      t('appHeader.projectSection.selectProject')
    );
  }
  return currentProject.value || t('appHeader.projectSection.selectProject');
});

const dropdownOpen = ref(false);
const dropdownRoot = ref(null);

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value;
}
function closeDropdown() {
  dropdownOpen.value = false;
}
function selectProject(project) {
  projectStore.setCurrentProject(project);
  if (route.name === 'ProjectConfigurationPage' && project?.project_id) {
    void router.replace({
      name: 'ProjectConfigurationPage',
      params: { projectId: project.project_id },
    });
  }
  closeDropdown();
}
function isCurrentProject(project) {
  if (!currentProject.value) return false;
  if (typeof project === 'object' && typeof currentProject.value === 'object') {
    return project.project_id === currentProject.value.project_id;
  }
  return project === currentProject.value;
}
function handleClickOutside(event) {
  if (dropdownRoot.value && !dropdownRoot.value.contains(event.target)) {
    closeDropdown();
  }
}
onMounted(() => {
  projectStore.initializeFromStorage();
  projectStore.initBroadcastChannel();
  document.addEventListener('click', handleClickOutside);
});
onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.project-section-root {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
  max-width: 22vw;
}

.project-section-trigger {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  background: var(--color-purple-50);
  color: var(--color-purple-400);
  border: 1px solid var(--color-purple-800);
  border-radius: 0.65rem;
  padding: 0.48rem 0.75rem;
  font-size: 0.95rem;
  font-weight: 650;
  cursor: pointer;
  transition:
    background 0.18s,
    color 0.18s;
  box-shadow: 0 1px 2px rgb(76 29 149 / 5%);
  min-width: 0;
  max-width: 18vw;
  overflow: hidden;
}

.project-section-trigger:hover,
.project-section-trigger:focus-visible {
  background: var(--color-purple-100);
  color: var(--color-purple-600);
  border-color: var(--color-purple-200);
  outline: 0;
  box-shadow: 0 0 0 3px rgb(124 58 237 / 12%);
}

.project-section-current {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  flex: 1 1 auto;
}

.project-section-current-name {
  display: inline-block;
  max-width: 11vw;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.project-section-current-name::after {
  content: attr(data-tooltip);
  position: absolute;
  z-index: 120;
  top: calc(100% + 0.55rem);
  left: 50%;
  max-width: min(22rem, 80vw);
  padding: 0.42rem 0.65rem;
  border-radius: 0.45rem;
  background: var(--color-text);
  color: var(--color-surface);
  font-size: 0.78rem;
  font-weight: 500;
  line-height: 1.3;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transform: translate(-50%, -0.25rem);
  transition:
    opacity 120ms ease,
    transform 120ms ease;
}

.project-section-trigger:hover .project-section-current-name::after,
.project-section-trigger:focus-visible .project-section-current-name::after {
  opacity: 1;
  transform: translate(-50%, 0);
}

.project-section-icon {
  width: 1.1rem;
  height: 1.1rem;
  color: var(--color-purple-400);
  vertical-align: middle;
  flex-shrink: 0;
}

.project-section-chevron {
  margin-left: 0.2rem;
  transition: transform 0.2s;
  fill: var(--color-purple-300);
  flex-shrink: 0;
}

.project-section-trigger[aria-expanded='true'] .project-section-chevron {
  transform: rotate(180deg);
}

.project-section-fade-enter-active,
.project-section-fade-leave-active {
  transition: opacity 0.18s;
}

.project-section-fade-enter-from,
.project-section-fade-leave-to {
  opacity: 0;
}

.project-section-fade-enter-to,
.project-section-fade-leave-from {
  opacity: 1;
}

.project-section-menu {
  position: absolute;
  left: 0;
  top: calc(100% + 0.55rem);
  min-width: 15rem;
  max-width: min(22rem, 88vw);
  background: var(--color-surface);
  color: var(--color-slate-500);
  border-radius: 0.75rem;
  box-shadow: 0 16px 36px rgb(15 23 42 / 16%);
  padding: 0.4rem;
  z-index: 100;
  display: flex;
  flex-direction: column;
  animation: project-section-slide 0.18s;
  border: 1px solid var(--color-blue-100);
  overflow-x: hidden;
}

@keyframes project-section-slide {
  0% {
    transform: translateY(-10px);
    opacity: 0;
  }

  100% {
    transform: translateY(0);
    opacity: 1;
  }
}

.project-section-menuitem {
  width: 100%;
}

.project-section-action {
  width: 100%;
  background: none;
  border: none;
  color: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.65rem 0.75rem;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  transition:
    background 0.16s,
    color 0.16s;
  border-radius: 10px;
  text-decoration: none;
  min-height: 44px;
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.project-section-menuitem-name {
  display: inline-block;
  max-width: 18rem;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.project-section-action:hover,
.project-section-action:focus {
  background: var(--color-surface-subtle);
  color: var(--color-purple-400);
  outline: none;
}

.project-section-current-indicator {
  margin-left: auto;
  color: var(--color-purple-400);
  font-weight: bold;
}
</style>
