<template>
  <div
    class="project-edit-modal-overlay"
    role="presentation"
    @click.self="close"
  >
    <div
      ref="dialogElement"
      class="project-edit-modal-content"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      tabindex="-1"
    >
      <template v-if="props.project && props.project.project_name">
        <h2 :id="titleId" class="project-edit-modal-title">
          {{ t('projectsPage.editDialog.title') }}
        </h2>
        <form @submit.prevent="handleEdit">
          <label class="project-edit-label" :for="nameId">
            {{ t('projectsPage.editDialog.projectNameLabel') }}
          </label>
          <input
            :id="nameId"
            ref="nameInput"
            v-model="name"
            class="project-edit-input"
            type="text"
            :placeholder="t('projectsPage.editDialog.projectNamePlaceholder')"
            maxlength="100"
            required
            :aria-invalid="Boolean(nameError)"
            :aria-describedby="nameError ? nameErrorId : undefined"
            @input="validateName"
          />
          <div class="project-edit-error" style="min-height: 20px">
            <span v-if="nameError" :id="nameErrorId" role="alert">{{
              nameError
            }}</span>
          </div>
          <label class="project-edit-label" :for="descriptionId">
            {{ t('projectsPage.editDialog.projectDescriptionLabel') }}
          </label>
          <textarea
            :id="descriptionId"
            v-model="description"
            class="project-edit-textarea"
            :placeholder="
              t('projectsPage.editDialog.projectDescriptionPlaceholder')
            "
            maxlength="5000"
            rows="5"
            :aria-invalid="Boolean(descError)"
            :aria-describedby="
              descError ? descriptionErrorId : descriptionCountId
            "
            @input="validateDescription"
          ></textarea>
          <div :id="descriptionCountId" class="project-edit-desc-info">
            <span>{{ description.length }}/5000</span>
          </div>
          <div class="project-edit-error" style="min-height: 20px">
            <span v-if="descError" :id="descriptionErrorId" role="alert">{{
              descError
            }}</span>
          </div>
          <div class="project-edit-actions">
            <button
              type="submit"
              class="project-page-create-btn"
              :disabled="editing || !canEdit"
            >
              {{
                editing
                  ? t('projectsPage.editDialog.saving')
                  : t('projectsPage.editDialog.save')
              }}
            </button>
            <button
              type="button"
              class="project-page-create-btn"
              @click="close"
            >
              {{ t('common.cancel') }}
            </button>
          </div>
          <div class="project-edit-error" style="min-height: 20px">
            <span v-if="error" role="alert">{{ error }}</span>
          </div>
        </form>
      </template>
      <template v-else>
        <div role="status">{{ t('common.loading') }}</div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, useId, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import gitService from '@api/service/gitService';
import { useProjectStore } from '@stores/project';
import { useModalDialog } from '@/composables/useModalDialog';

const props = defineProps({
  project: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(['close', 'edited']);
const projectStore = useProjectStore();
const { t } = useI18n();

const name = ref('');
const description = ref('');
const editing = ref(false);
const error = ref('');
const nameError = ref('');
const descError = ref('');
const dialogElement = ref(null);
const nameInput = ref(null);
const titleId = `project-edit-title-${useId()}`;
const nameId = `project-edit-name-${useId()}`;
const nameErrorId = `project-edit-name-error-${useId()}`;
const descriptionId = `project-edit-description-${useId()}`;
const descriptionCountId = `project-edit-description-count-${useId()}`;
const descriptionErrorId = `project-edit-description-error-${useId()}`;

watch(
  () => props.project,
  (project) => {
    name.value = project?.project_name || '';
    description.value = project?.project_description || '';
  },
  { immediate: true }
);

const allProjectNames = computed(() =>
  (projectStore.projects || [])
    .filter((p) => p.project_id !== props.project?.project_id)
    .map((p) => p.project_name?.toLowerCase())
);

function validateName() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    nameError.value = t('projectsPage.editDialog.errors.nameRequired');
  } else if (trimmed.length > 100) {
    nameError.value = t('projectsPage.editDialog.errors.nameTooLong');
  } else if (allProjectNames.value.includes(trimmed.toLowerCase())) {
    nameError.value = t('projectsPage.editDialog.errors.nameExists');
  } else {
    nameError.value = '';
  }
}

function validateDescription() {
  if (description.value && !description.value.trim()) {
    description.value = '';
  }
  if (description.value.length > 5000) {
    descError.value = t('projectsPage.editDialog.errors.descTooLong');
  } else {
    descError.value = '';
  }
}

const canEdit = computed(() => {
  validateName();
  validateDescription();
  return !nameError.value && !descError.value && name.value.trim();
});

async function handleEdit() {
  validateName();
  validateDescription();
  if (!canEdit.value) {
    error.value = t('projectsPage.editDialog.errors.fixAbove');
    return;
  }
  editing.value = true;
  try {
    await gitService.editProject(
      props.project.project_name,
      name.value.trim(),
      description.value.trim()
    );
    error.value = '';
    emit('edited');
  } catch (e) {
    error.value =
      e?.response?.data?.detail ||
      t('projectsPage.editDialog.errors.editFailed');
  } finally {
    editing.value = false;
  }
}

function close() {
  emit('close');
}

useModalDialog(dialogElement, { onClose: close, initialFocus: nameInput });

onMounted(() => {
  projectStore.initBroadcastChannel();
});
</script>

<style scoped>
.project-edit-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgb(0 0 0 / 50%);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.project-edit-modal-content {
  background: #fff;
  border-radius: 16px;
  padding: 32px 24px;
  min-width: 340px;
  max-width: 95vw;
  box-shadow: 0 2px 16px rgb(0 0 0 / 8%);
}

.project-edit-modal-title {
  margin-bottom: 18px;
  font-size: 1.3rem;
  font-weight: 600;
  text-align: center;
}

.project-edit-label {
  display: block;
  margin-bottom: 6px;
  color: #26354d;
  font-size: 0.9rem;
  font-weight: 600;
}

.project-edit-input {
  width: 100%;
  margin-bottom: 10px;
  padding: 8px 12px;
  border: 1.5px solid #bdbdbd;
  border-radius: 6px;
  font-size: 1rem;
}

.project-edit-textarea {
  width: 100%;
  min-height: 90px;
  max-height: 180px;
  margin-bottom: 4px;
  padding: 10px 12px;
  border: 1.5px solid #bdbdbd;
  border-radius: 6px;
  font-size: 1rem;
  resize: vertical;
  overflow-y: auto;
  background: #f8f9fa;
  box-sizing: border-box;
}

.project-edit-desc-info {
  text-align: right;
  font-size: 0.95rem;
  color: #888;
  margin-bottom: 8px;
}

.project-edit-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 18px;
}

.project-edit-error {
  color: #d32f2f;
  margin-bottom: 8px;
  font-size: 0.98rem;
  text-align: left;
  margin-top: -2px;
  min-height: 20px;
}
</style>
