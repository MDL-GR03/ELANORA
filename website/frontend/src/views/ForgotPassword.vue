<template>
  <div class="forgot-password-wrapper">
    <div class="forgot-password-card">
      <h1 class="forgot-password-title">{{ t('forgotPassword.title') }}</h1>
      <form class="forgot-password-form" @submit.prevent="handleSubmit">
        <!-- Honeypot field (hidden) -->
        <input
          v-model="honeypot"
          type="text"
          name="website"
          class="honeypot"
          tabindex="-1"
          autocomplete="off"
        />
        <div class="form-group">
          <label for="email" class="form-label">{{
            t('forgotPassword.email_label')
          }}</label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            class="form-input"
            :placeholder="t('forgotPassword.email_placeholder')"
            autocomplete="email"
          />
        </div>

        <!-- CAPTCHA -->
        <div class="form-group captcha-container">
          <label for="captcha-answer" class="form-label">{{
            t('forgotPassword.captcha_label')
          }}</label>
          <div class="captcha-challenge">
            <span class="captcha-question">{{ captchaQuestion }}</span>
            <button
              type="button"
              class="captcha-refresh"
              :title="t('forgotPassword.captcha_refresh')"
              @click="generateCaptcha"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                <path d="M21 3v5h-5" />
                <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                <path d="M3 21v-5h5" />
              </svg>
            </button>
          </div>
          <input
            id="captcha-answer"
            v-model="captchaAnswer"
            type="number"
            required
            class="form-input captcha-input"
            :placeholder="t('forgotPassword.captcha_placeholder')"
            autocomplete="off"
          />
        </div>

        <button
          type="submit"
          class="btn-primary forgot-password-btn"
          :disabled="loading || !isCaptchaValid"
        >
          <span v-if="loading">{{ t('forgotPassword.sending') }}</span>
          <span v-else>{{ t('forgotPassword.send_code') }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { forgotPassword } from '@/api/service/authService';
import { useEventMessageStore } from '@stores/eventMessage';

const { t, locale } = useI18n();
const router = useRouter();
const eventMessageStore = useEventMessageStore();

const email = ref('');
const loading = ref(false);

// Security fields
const honeypot = ref('');
const captchaQuestion = ref('');
const captchaAnswer = ref('');
const captchaExpectedAnswer = ref(0);

// Generate a simple math CAPTCHA
const generateCaptcha = () => {
  const num1 = Math.floor(Math.random() * 10) + 1;
  const num2 = Math.floor(Math.random() * 10) + 1;
  const operations = ['+', '-', '×'];
  const operation = operations[Math.floor(Math.random() * operations.length)];

  captchaQuestion.value = `${num1} ${operation} ${num2} = ?`;

  switch (operation) {
    case '+':
      captchaExpectedAnswer.value = num1 + num2;
      break;
    case '-':
      captchaExpectedAnswer.value = num1 - num2;
      break;
    case '×':
      captchaExpectedAnswer.value = num1 * num2;
      break;
  }

  captchaAnswer.value = '';
};

// Check if CAPTCHA is valid
const isCaptchaValid = computed(() => {
  return parseInt(captchaAnswer.value) === captchaExpectedAnswer.value;
});

const handleSubmit = async () => {
  // Security checks
  if (honeypot.value) {
    // Bot detected, fail silently
    eventMessageStore.addMessage(t('forgotPassword.error'), 'error');
    return;
  }

  if (!isCaptchaValid.value) {
    eventMessageStore.addMessage(t('forgotPassword.captcha_error'), 'error');
    return;
  }

  loading.value = true;
  try {
    await forgotPassword(email.value, locale.value);
    eventMessageStore.addMessage(t('forgotPassword.code_sent'), 'success');
    router.push({ name: 'ResetPassword', query: { email: email.value } });
  } catch (error) {
    console.error(error);

    // Handle specific error types based on HTTP status codes
    if (error?.response?.status === 429) {
      // Rate limit exceeded - show specific message
      eventMessageStore.addMessage(
        t('forgotPassword.rate_limit_error'),
        'error'
      );
    } else if (error?.response?.status === 400) {
      // Handle validation errors
      const errorDetail = error.response?.data?.detail;
      if (Array.isArray(errorDetail)) {
        // Multiple validation errors
        const emailError = errorDetail.find(
          (err) => err.loc && err.loc.includes('email')
        );
        if (emailError) {
          eventMessageStore.addMessage(
            t('forgotPassword.validation_error'),
            'error'
          );
        } else {
          eventMessageStore.addMessage(t('forgotPassword.error'), 'error');
        }
      } else if (typeof errorDetail === 'string') {
        // Single error message from backend
        eventMessageStore.addMessage(errorDetail, 'error');
      } else {
        eventMessageStore.addMessage(
          t('forgotPassword.validation_error'),
          'error'
        );
      }
    } else if (error?.response?.status === 500) {
      // Server error
      eventMessageStore.addMessage(t('forgotPassword.server_error'), 'error');
    } else if (error?.response?.data?.detail) {
      // Use backend error message if available
      eventMessageStore.addMessage(error.response.data.detail, 'error');
    } else if (!error?.response) {
      // Network error
      eventMessageStore.addMessage(t('forgotPassword.network_error'), 'error');
    } else {
      // Fallback to generic error
      eventMessageStore.addMessage(t('forgotPassword.error'), 'error');
    }

    // Generate new CAPTCHA on error for security
    generateCaptcha();
  } finally {
    loading.value = false;
  }
};

// Generate initial CAPTCHA
onMounted(() => {
  generateCaptcha();
});
</script>

<style src="@/assets/css/forgot-password.css" scoped></style>
