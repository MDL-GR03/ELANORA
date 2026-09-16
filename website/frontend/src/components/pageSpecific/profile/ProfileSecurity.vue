<template>
  <div class="profile-security">
    <div class="security-section">
      <h3 class="security-title">
        {{ t('profile.security.change_password.title') }}
      </h3>
      <p class="security-description">
        {{ t('profile.security.change_password.description') }}
      </p>

      <form class="password-form" @submit.prevent="handlePasswordChange">
        <div class="form-group">
          <label for="current-password" class="form-label">
            {{ t('profile.security.change_password.current_password') }}
          </label>
          <input
            id="current-password"
            v-model="form.currentPassword"
            type="password"
            class="form-input"
            :placeholder="
              t('profile.security.change_password.current_password_placeholder')
            "
            required
            autocomplete="current-password"
          />
        </div>

        <div class="form-group">
          <label for="new-password" class="form-label">
            {{ t('profile.security.change_password.new_password') }}
          </label>
          <input
            id="new-password"
            v-model="form.newPassword"
            type="password"
            class="form-input"
            :placeholder="
              t('profile.security.change_password.new_password_placeholder')
            "
            required
            autocomplete="new-password"
            @input="validatePassword"
          />
          <div v-if="passwordValidation.show" class="password-requirements">
            <div class="requirements-title">
              {{ t('passwordPolicy.title') }}
            </div>
            <div
              v-for="requirement in passwordRequirements"
              :key="requirement.key"
              class="requirement-item"
              :class="{ valid: requirement.valid }"
            >
              <span class="requirement-icon">{{
                requirement.valid ? '✓' : '✗'
              }}</span>
              <span class="requirement-text">{{ requirement.text }}</span>
            </div>
            <p class="requirements-advice">{{ t('passwordPolicy.advice') }}</p>
          </div>
        </div>

        <div class="form-group">
          <label for="confirm-password" class="form-label">
            {{ t('profile.security.change_password.confirm_password') }}
          </label>
          <input
            id="confirm-password"
            v-model="form.confirmPassword"
            type="password"
            class="form-input"
            :placeholder="
              t('profile.security.change_password.confirm_password_placeholder')
            "
            required
            autocomplete="new-password"
          />
          <div
            v-if="form.confirmPassword && !passwordsMatch"
            class="error-message"
          >
            {{ t('profile.security.change_password.passwords_no_match') }}
          </div>
        </div>

        <div class="form-actions">
          <button
            type="submit"
            class="btn-primary"
            :disabled="!isFormValid || loading"
          >
            <span v-if="loading">{{
              t('profile.security.change_password.updating')
            }}</span>
            <span v-else>{{
              t('profile.security.change_password.update')
            }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { passwordRequirementList } from '@/utils/passwordPolicy';
import { changePassword } from '@/api/service/userService.js';
import { reportClientError } from '@/utils/errorDiagnostics';

const { t } = useI18n();
const emit = defineEmits(['show-message']);

// State
const form = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
});

const loading = ref(false);
const passwordValidation = ref({
  show: false,
});

// Password validation
const passwordRequirements = computed(() =>
  passwordRequirementList(form.value.newPassword, t)
);

const passwordsMatch = computed(() => {
  return form.value.newPassword === form.value.confirmPassword;
});

const isPasswordValid = computed(() => {
  return passwordRequirements.value.every((req) => req.valid);
});

const isFormValid = computed(() => {
  return (
    form.value.currentPassword &&
    form.value.newPassword &&
    form.value.confirmPassword &&
    isPasswordValid.value &&
    passwordsMatch.value
  );
});

// Methods
function validatePassword() {
  passwordValidation.value.show = form.value.newPassword.length > 0;
}

async function handlePasswordChange() {
  if (!isFormValid.value) {
    emit('show-message', {
      text: t('profile.security.change_password.form_invalid'),
      type: 'error',
    });
    return;
  }

  loading.value = true;
  try {
    await changePassword({
      current_password: form.value.currentPassword,
      new_password: form.value.newPassword,
    });

    emit('show-message', {
      text: t('profile.security.change_password.success'),
      type: 'success',
    });

    // Reset form
    form.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    };
    passwordValidation.value.show = false;
  } catch (error) {
    reportClientError('Password change error', error);
    emit('show-message', {
      text: apiErrorMessage(
        error,
        t,
        t('profile.security.change_password.error')
      ),
      type: 'error',
    });
  } finally {
    loading.value = false;
  }
}

// Watch for password field focus loss
watch(
  () => form.value.newPassword,
  (newVal) => {
    if (!newVal) {
      passwordValidation.value.show = false;
    }
  }
);
</script>

<style scoped>
@import url('../../../assets/css/profile-security.css');
</style>
