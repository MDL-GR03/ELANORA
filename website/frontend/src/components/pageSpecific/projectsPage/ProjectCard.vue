<template>
  <div
    :class="['project-card', { 'project-card-active': active }]"
    role="button"
    tabindex="0"
    @click="emit('select')"
    @keydown.enter.prevent="emit('select')"
    @keydown.space.prevent="emit('select')"
  >
    <div class="project-card-row project-card-row-header">
      <div class="project-card-title-container">
        <span class="project-card-title" :title="project.project_name">
          <font-awesome-icon
            icon="fa-diagram-project"
            class="project-card-title-icon"
          />
          {{ project.project_name }}
        </span>
      </div>
      <div
        v-if="canEdit || canShare || canConfigure || canDelete"
        class="project-card-actions"
      >
        <button
          v-if="canEdit"
          class="project-card-action-btn edit"
          :title="t('projectsPage.project.buttons.rename')"
          @click.stop="emit('edit')"
        >
          <font-awesome-icon icon="fa-regular fa-pen-to-square" />
        </button>
        <button
          v-if="canShare"
          class="project-card-action-btn share"
          :title="t('projectsPage.project.buttons.share')"
          @click.stop="emit('share')"
        >
          <font-awesome-icon icon="fa-regular fa-share-from-square" />
        </button>
        <button
          v-if="canConfigure"
          class="project-card-action-btn config"
          :title="t('projectsPage.project.buttons.settings')"
          @click.stop="emit('configure')"
        >
          <font-awesome-icon icon="fa-solid fa-gears" />
        </button>
        <button
          v-if="canDelete"
          class="project-card-action-btn project-card-delete-btn"
          :title="t('projectsPage.project.buttons.delete')"
          @click.stop="emit('delete')"
        >
          <font-awesome-icon icon="trash" />
        </button>
      </div>
    </div>
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
            {{ project.project_description || t('projectsPage.noDescription') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

defineProps({
  project: { type: Object, required: true },
  active: { type: Boolean, default: false },
  canEdit: { type: Boolean, default: false },
  canShare: { type: Boolean, default: false },
  canConfigure: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: false },
});
const emit = defineEmits(['select', 'edit', 'share', 'configure', 'delete']);
const { t } = useI18n();
</script>
