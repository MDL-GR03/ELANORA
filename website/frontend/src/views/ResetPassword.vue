<template>
  <div class="reset-password-wrapper">
    <div class="reset-password-card">
      <h1 class="reset-password-title">{{ t('resetPassword.title') }}</h1>
      <form class="reset-password-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="code" class="form-label">{{
            t('resetPassword.code_label')
          }}</label>
          <input
            id="code"
            v-model="form.code"
            type="text"
            class="form-input"
            :placeholder="t('resetPassword.code_placeholder')"
            required
            maxlength="6"
            inputmode="numeric"
            pattern="\d{6}"
            @input="form.code = form.code.replace(/[^\d]/g, '').slice(0, 6)"
          />
        </div>
        <div class="form-group">
          <label for="new-password" class="form-label">{{
            t('resetPassword.new_password_label')
          }}</label>
          <input
            id="new-password"
            v-model="form.newPassword"
            type="password"
            class="form-input"
            :placeholder="t('resetPassword.new_password_placeholder')"
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
          <label for="confirm-password" class="form-label">{{
            t('resetPassword.confirm_password_label')
          }}</label>
          <input
            id="confirm-password"
            v-model="form.confirmPassword"
            type="password"
            class="form-input"
            :placeholder="t('resetPassword.confirm_password_placeholder')"
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
        <button
          type="submit"
          class="btn-primary reset-password-btn"
          :disabled="!isFormValid || loading"
        >
          <span v-if="loading">{{ t('resetPassword.submitting') }}</span>
          <span v-else>{{ t('resetPassword.submit') }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
  passwordRequestError,
  passwordRequirementList,
} from '@/utils/passwordPolicy';
import { useEventMessageStore } from '@stores/eventMessage';
import { resetPassword } from '@/api/service/authService';
import '@/assets/css/resetpassword.css';
import { reportClientError } from '@/utils/errorDiagnostics';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const eventMessageStore = useEventMessageStore();

const form = ref({
  code: '',
  newPassword: '',
  confirmPassword: '',
});

const loading = ref(false);
const email = ref('');
const passwordValidation = ref({
  show: false,
});

// Password validation requirements
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
    form.value.code &&
    /^\d{6}$/.test(form.value.code) &&
    form.value.newPassword &&
    form.value.confirmPassword &&
    isPasswordValid.value &&
    passwordsMatch.value
  );
});

onMounted(() => {
  // Get email from query parameters
  email.value = route.query.email || '';
  if (!email.value) {
    eventMessageStore.addMessage(t('resetPassword.email_required'), 'error');
    router.push({ name: 'ForgotPassword' });
  }
});

// Methods
function validatePassword() {
  passwordValidation.value.show = form.value.newPassword.length > 0;
}

const handleSubmit = async () => {
  // Additional client-side validation before submit
  if (!isFormValid.value) {
    eventMessageStore.addMessage(
      t('profile.security.change_password.form_invalid'),
      'error'
    );
    return;
  }

  loading.value = true;
  try {
    await resetPassword(email.value, form.value.code, form.value.newPassword);
    eventMessageStore.addMessage(t('resetPassword.success'), 'success');
    router.push({ name: 'LoginPage' });
  } catch (error) {
    reportClientError('Reset password error', error);
    eventMessageStore.addMessage(
      passwordRequestError(error, t, t('resetPassword.error')),
      'error'
    );
  } finally {
    loading.value = false;
  }
};

// Watch for password field changes
watch(
  () => form.value.newPassword,
  (newVal) => {
    if (!newVal) {
      passwordValidation.value.show = false;
    }
  }
);
</script>
