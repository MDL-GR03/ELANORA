<template>
  <div class="project-create-modal-overlay">
    <div class="project-create-modal-content">
      <h2 class="project-create-modal-title">
        {{ t('projectsPage.createProject') }}
      </h2>
      <form @submit.prevent="handleCreate">
        <!-- Project Name -->
        <input
          v-model="name"
          class="project-create-input"
          type="text"
          :placeholder="t('projectsPage.createDialog.projectNamePlaceholder')"
          maxlength="100"
          required
          @input="validateName"
        />
        <div class="project-create-error" style="min-height: 20px">
          <span v-if="nameError">{{ nameError }}</span>
        </div>

        <!-- Description -->
        <textarea
          v-model="description"
          class="project-create-textarea"
          :placeholder="
            t('projectsPage.createDialog.projectDescriptionPlaceholder')
          "
          maxlength="5000"
          rows="5"
          @input="validateDescription"
        ></textarea>
        <div class="project-create-desc-info">
          <span>{{ description.length }}/5000</span>
        </div>
        <div class="project-create-error" style="min-height: 20px">
          <span v-if="descError">{{ descError }}</span>
        </div>

        <!-- Upload Component -->
        <UploadFolder
          v-model="selectedFiles"
          :title="t('projectsPage.createDialog.dropFolder')"
          :subtitle="t('projectsPage.createDialog.onlyEafFiles')"
          compact
        />

        <div class="project-create-error" style="min-height: 20px">
          <span v-if="error">{{ error }}</span>
        </div>

        <div class="project-create-actions">
          <button
            type="submit"
            class="project-page-create-btn"
            :disabled="creating || !canCreate"
          >
            {{
              creating
                ? t('projectsPage.createDialog.creating')
                : t('projectsPage.createDialog.create')
            }}
          </button>
          <button
            type="button"
            class="project-page-create-btn"
            @click="emit('close')"
          >
            {{ t('common.cancel') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import UploadFolder from '@components/common/UploadFolder.vue';
import gitService from '@api/service/gitService';
import { useProjectStore } from '@stores/project';

const { t } = useI18n();
const emit = defineEmits(['close', 'created']);
const projectStore = useProjectStore();

const name = ref('');
const description = ref('');
const selectedFiles = ref([]);
const creating = ref(false);
const error = ref('');

const nameError = ref('');
const descError = ref('');

const allProjectNames = computed(() =>
  (projectStore.projects || []).map((p) => p.project_name.toLowerCase())
);

function validateName() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    nameError.value = t('projectsPage.createDialog.errors.nameRequired');
  } else if (trimmed.length > 100) {
    nameError.value = t('projectsPage.createDialog.errors.nameTooLong');
  } else if (allProjectNames.value.includes(trimmed.toLowerCase())) {
    nameError.value = t('projectsPage.createDialog.errors.nameExists');
  } else {
    nameError.value = '';
  }
}

function validateDescription() {
  if (description.value && !description.value.trim()) {
    description.value = '';
  }
  if (description.value.length > 5000) {
    descError.value = t('projectsPage.createDialog.errors.descTooLong');
  } else {
    descError.value = '';
  }
}

const canCreate = computed(() => {
  validateName();
  validateDescription();
  return !nameError.value && !descError.value && name.value.trim();
});

async function handleCreate() {
  validateName();
  validateDescription();
  if (!canCreate.value) {
    error.value = t('projectsPage.createDialog.errors.fixAbove');
    return;
  }

  creating.value = true;
  try {
    if (selectedFiles.value.length > 0) {
      await gitService.initProjectFromFolderUpload({
        project_name: name.value.trim(),
        description: description.value.trim() || undefined,
        files: selectedFiles.value,
      });
    } else {
      await gitService.createProject({
        project_name: name.value.trim(),
        description: description.value.trim() || undefined,
      });
    }

    // Reset form
    name.value = '';
    description.value = '';
    selectedFiles.value = [];
    error.value = '';

    emit('created');
  } catch (e) {
    error.value =
      e?.response?.data?.detail ||
      t('projectsPage.createDialog.errors.createFailed');
  } finally {
    creating.value = false;
  }
}

onMounted(() => {
  projectStore.initBroadcastChannel();
});
</script>

<style scoped>
.project-create-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgb(0 0 0 / 50%);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.project-create-modal-content {
  background: #fff;
  border-radius: 16px;
  padding: 32px 24px;
  min-width: 600px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 2px 16px rgb(0 0 0 / 8%);
}

/* Ensure the form doesn't add extra height */
.project-create-modal-content form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* Responsive adjustments for smaller screens */
@media (width <= 768px) {
  .project-create-modal-content {
    min-width: auto;
    max-width: 90vw;
    max-height: 95vh;
    padding: 24px 16px;
  }
}

.project-create-modal-title {
  margin-bottom: 18px;
  font-size: 1.3rem;
  font-weight: 600;
  text-align: center;
}

.project-create-input {
  width: 100%;
  margin-bottom: 10px;
  padding: 8px 12px;
  border: 1.5px solid #bdbdbd;
  border-radius: 6px;
  font-size: 1rem;
}

.project-create-textarea {
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

.project-create-desc-info {
  text-align: right;
  font-size: 0.95rem;
  color: #888;
  margin-bottom: 8px;
}

.project-create-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 18px;
}

.project-create-error {
  color: #d32f2f;
  margin-bottom: 8px;
  font-size: 0.98rem;
  text-align: left;
  margin-top: -2px;
  min-height: 20px;
}
</style>
