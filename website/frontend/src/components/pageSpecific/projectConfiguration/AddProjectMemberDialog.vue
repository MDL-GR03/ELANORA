<template>
  <div class="modal-overlay" role="presentation" @click.self="emit('close')">
    <div
      ref="dialogElement"
      class="modal-content"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-member-title"
      aria-describedby="add-member-description"
      tabindex="-1"
    >
      <div class="modal-header">
        <span class="modal-header-icon">
          <font-awesome-icon icon="fa-solid fa-circle-user" />
        </span>
        <div>
          <span class="modal-eyebrow">
            {{ t('projectSettings.members.add_modal.eyebrow') }}
          </span>
          <h4 id="add-member-title">
            {{ t('projectSettings.members.add_modal.title') }}
          </h4>
        </div>
        <button
          type="button"
          class="modal-close"
          :aria-label="t('common.cancel')"
          @click="emit('close')"
        >
          <font-awesome-icon icon="fa-solid fa-xmark" />
        </button>
      </div>

      <form class="add-member-form" @submit.prevent="submit">
        <p id="add-member-description" class="modal-description">
          {{ t('projectSettings.members.add_modal.description') }}
        </p>
        <div class="form-group">
          <label for="userId"
            >{{ t('project.share.select_user') }}
            <span class="share-required">*</span></label
          >
          <AppSelect
            id="userId"
            v-model="userId"
            :disabled="loadingCandidates"
            :required="true"
            :placeholder="
              loadingCandidates
                ? t('common.loading')
                : t('project.share.choose_user')
            "
            :options="candidateOptions"
            :aria-describedby="formError ? 'add-member-error' : undefined"
          />
        </div>

        <div class="form-group">
          <label for="permission">{{
            t('projectSettings.members.add_modal.permission')
          }}</label>
          <AppSelect
            id="permission"
            v-model="permission"
            :required="true"
            :options="permissionOptions"
          />
        </div>

        <p
          v-if="formError"
          id="add-member-error"
          class="add-member-error"
          role="alert"
        >
          {{ formError }}
        </p>

        <div class="form-actions">
          <button type="button" class="btn-cancel" @click="emit('close')">
            {{ t('common.cancel') }}
          </button>
          <button
            type="submit"
            class="btn-submit"
            :disabled="adding || !userId"
          >
            <span v-if="adding" class="loading-text"
              >{{ t('common.adding') }}...</span
            >
            <span v-else>{{ t('common.add') }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getAvailableProjectUsers } from '@/api/service/projectAssociationService';
import AppSelect from '@/components/common/AppSelect.vue';
import { useModalDialog } from '@/composables/useModalDialog';
import { apiErrorMessage } from '@/utils/apiError';
import { reportClientError } from '@/utils/errorDiagnostics';

/** Mounted only while open; `add` resolves once the member is added. */
const props = defineProps({
  projectId: { type: Number, required: true },
  memberIds: { type: Set, required: true },
  permissions: { type: Array, required: true },
  add: { type: Function, required: true },
});
const emit = defineEmits(['close']);

const { t } = useI18n();
const dialogElement = ref(null);
const candidates = ref([]);
const loadingCandidates = ref(false);
const userId = ref('');
const permission = ref('read');
const adding = ref(false);
const formError = ref('');

const candidateOptions = computed(() =>
  candidates.value
    .filter((user) => !props.memberIds.has(user.user_id))
    .map((user) => ({
      value: user.user_id,
      label: `${user.first_name} ${user.last_name} (${user.username}) - ${user.email}`,
    }))
);
const permissionOptions = computed(() =>
  props.permissions.map((value) => ({
    value,
    label: t(`projectSettings.permissions.${value}`),
  }))
);

async function loadCandidates() {
  loadingCandidates.value = true;
  try {
    const response = await getAvailableProjectUsers(props.projectId);
    candidates.value = response.data?.users ?? [];
  } catch (err) {
    reportClientError('Error loading available users', err);
    formError.value = apiErrorMessage(
      err,
      t,
      t('project.share.error_loading_users')
    );
  } finally {
    loadingCandidates.value = false;
  }
}

async function submit() {
  if (!userId.value) {
    formError.value = t('projectSettings.members.add_modal.user_required');
    return;
  }
  adding.value = true;
  formError.value = '';
  try {
    await props.add({ userId: userId.value, permission: permission.value });
    emit('close');
  } catch (err) {
    reportClientError('Error adding project member', err);
    formError.value = apiErrorMessage(
      err,
      t,
      t('projectSettings.members.add_error')
    );
  } finally {
    adding.value = false;
  }
}

useModalDialog(dialogElement, {
  onClose: () => emit('close'),
  initialFocus: dialogElement,
});
onMounted(loadCandidates);
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  padding: 24px;
  background: rgb(18 35 64 / 58%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(3px);
}

.modal-content {
  background: white;
  border: 1px solid var(--color-gray-blue-40);
  border-radius: 18px;
  padding: 0;
  width: min(520px, 100%);
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  box-shadow: 0 24px 70px rgb(15 35 70 / 28%);
}

.modal-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.85rem;
  align-items: center;
  margin: 0;
  padding: 1.4rem 1.5rem 1.15rem;
  background: linear-gradient(
    145deg,
    var(--color-surface),
    var(--color-blue-50-lightest)
  );
  border-bottom: 1px solid var(--color-gray-blue-30);
}

.modal-header h4 {
  margin: 0;
  color: var(--color-gray-900);
  font-size: 1.15rem;
  font-weight: 700;
}

.modal-header-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  color: var(--color-blue-500);
  background: var(--color-blue-400-bg);
  border-radius: 11px;
}

.modal-eyebrow {
  display: block;
  margin-bottom: 0.15rem;
  color: var(--color-blue-500);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--color-gray-600);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  transition: all 0.2s ease;
}

.modal-close:hover {
  color: var(--color-slate-700);
  background: var(--color-gray-500-alt);
}

.add-member-form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding: 1.4rem 1.5rem 1.5rem;
}

.modal-description {
  margin: 0;
  color: var(--color-gray-blue-500);
  font-size: 0.9rem;
  line-height: 1.55;
}

.add-member-error {
  margin: -0.25rem 0 0;
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--color-error-bg-light);
  border-radius: 8px;
  background: var(--color-error-bg);
  color: var(--color-error);
  font-size: 0.875rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: var(--color-slate-700);
  font-size: 0.875rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin: 0.4rem -1.5rem -1.5rem;
  padding: 1rem 1.5rem;
  background: var(--color-f7f9fc);
  border-top: 1px solid var(--color-gray-blue-30);
}

.btn-cancel,
.btn-submit {
  padding: 0.625rem 1.25rem;
  border: none;
  min-height: 42px;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

@media (width <= 560px) {
  .modal-overlay {
    align-items: end;
    padding: 12px;
  }

  .modal-content {
    border-radius: 16px;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .form-actions button {
    width: 100%;
  }
}

.btn-cancel {
  background: var(--color-gray-500-alt);
  color: var(--color-slate-700);
  border: 1px solid var(--color-gray-300);
}

.btn-cancel:hover:not(:disabled) {
  background: var(--color-border-subtle);
}

.btn-submit {
  background: var(--color-indigo-500);
  color: var(--color-text-inverse);
}

.btn-submit:hover:not(:disabled) {
  background: var(--color-indigo-600);
}

.btn-cancel:disabled,
.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loading-text::after {
  content: '';
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentcolor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}
</style>
