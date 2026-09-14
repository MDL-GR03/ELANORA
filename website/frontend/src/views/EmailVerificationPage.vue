<template>
  <div class="email-verification-container">
    <div class="verification-wrapper">
      <!-- Header -->
      <div class="verification-header">
        <div class="icon-container">
          <svg
            class="verification-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        </div>
        <h1 class="verification-title">{{ $t('emailVerification.title') }}</h1>
        <p class="verification-subtitle">
          {{ $t('emailVerification.subtitle') }}
        </p>
        <div class="email-display">
          <span class="email-text">{{ userEmail }}</span>
        </div>
      </div>

      <!-- Verification Form Card -->
      <div class="verification-card">
        <form class="verification-form" @submit.prevent="handleVerification">
          <div class="form-group">
            <label for="verificationCode" class="form-label">
              {{ $t('emailVerification.codeLabel') }}
            </label>
            <div class="code-input-container">
              <input
                id="verificationCode"
                v-model="verificationCode"
                type="text"
                class="code-input"
                :class="{ error: validationMessage, loading: isLoading }"
                :placeholder="$t('emailVerification.codePlaceholder')"
                maxlength="6"
                autocomplete="off"
                @input="onCodeInput"
                @keypress="onKeyPress"
              />
              <div v-if="isLoading" class="input-loading-spinner">
                <div class="spinner"></div>
              </div>
            </div>

            <!-- Validation Messages -->
            <div v-if="validationMessage" class="validation-message error">
              <svg class="message-icon" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                  clip-rule="evenodd"
                />
              </svg>
              {{ validationMessage }}
            </div>

            <div v-if="successMessage" class="validation-message success">
              <svg class="message-icon" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clip-rule="evenodd"
                />
              </svg>
              {{ successMessage }}
            </div>
          </div>

          <!-- Verify Button -->
          <button
            type="submit"
            class="btn-primary verify-button"
            :disabled="
              !verificationCode || verificationCode.length !== 6 || isLoading
            "
          >
            <span v-if="!isLoading">{{
              $t('emailVerification.verifyButton')
            }}</span>
            <span v-else>{{ $t('emailVerification.verifying') }}</span>
          </button>
        </form>

        <!-- Resend Section -->
        <div class="resend-section">
          <p class="resend-text">
            {{ $t('emailVerification.noCodeReceived') }}
          </p>
          <button
            type="button"
            class="resend-button"
            :disabled="resendCooldown > 0 || isResending"
            @click="resendVerificationCode"
          >
            <span v-if="!isResending && resendCooldown === 0">
              {{ $t('emailVerification.resendButton') }}
            </span>
            <span v-else-if="isResending">
              {{ $t('emailVerification.resending') }}
            </span>
            <span v-else>
              {{
                $t('emailVerification.resendCooldown', {
                  seconds: resendCooldown,
                })
              }}
            </span>
          </button>
        </div>
      </div>

      <!-- Help Section -->
      <div class="help-card">
        <h3 class="help-title">{{ $t('emailVerification.helpTitle') }}</h3>
        <ul class="help-list">
          <li>{{ $t('emailVerification.helpCheck1') }}</li>
          <li>{{ $t('emailVerification.helpCheck2') }}</li>
          <li>{{ $t('emailVerification.helpCheck3') }}</li>
        </ul>
        <p class="help-contact">
          {{ $t('emailVerification.helpContact') }}
          <router-link to="/contact" class="contact-link">
            {{ $t('emailVerification.contactSupport') }}
          </router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { reportClientError } from '@/utils/errorDiagnostics';
import {
  sendVerificationEmail,
  verifyEmail,
} from '@api/service/authService.js';

export default {
  name: 'EmailVerificationPage',
  setup() {
    const router = useRouter();
    const route = useRoute();
    const { t } = useI18n();

    // Reactive data
    const verificationCode = ref('');
    const userEmail = ref('');
    const isLoading = ref(false);
    const isResending = ref(false);
    const validationMessage = ref('');
    const successMessage = ref('');
    const resendCooldown = ref(0);

    let cooldownInterval = null;

    // Get email from route query or localStorage
    onMounted(() => {
      userEmail.value =
        route.query.email ||
        localStorage.getItem('pendingVerificationEmail') ||
        '';

      if (!userEmail.value) {
        router.push({ name: 'LoginPage' });
      }

      // Start initial cooldown if this is a fresh verification request
      if (route.query.freshCode) {
        startResendCooldown();
      }
    });

    onUnmounted(() => {
      if (cooldownInterval) {
        clearInterval(cooldownInterval);
      }
    });

    // Handle code input
    const onCodeInput = () => {
      // Clear validation messages when user types
      validationMessage.value = '';
      successMessage.value = '';

      // Auto-format to digits only and limit to 6 characters
      verificationCode.value = verificationCode.value
        .replace(/\D/g, '')
        .slice(0, 6);
    };

    // Handle key press
    const onKeyPress = (event) => {
      // Only allow digits
      if (
        !/\d/.test(event.key) &&
        !['Backspace', 'Delete', 'Tab', 'Enter'].includes(event.key)
      ) {
        event.preventDefault();
      }
    };

    // Handle verification
    const handleVerification = async () => {
      if (!verificationCode.value || verificationCode.value.length !== 6) {
        validationMessage.value = t(
          'emailVerification.errors.invalidCodeLength'
        );
        return;
      }

      isLoading.value = true;
      validationMessage.value = '';
      successMessage.value = '';

      try {
        const response = await verifyEmail(
          userEmail.value,
          verificationCode.value
        );

        if (response.data.success) {
          successMessage.value = t('emailVerification.success');

          // Clear pending verification email
          localStorage.removeItem('pendingVerificationEmail');

          // Redirect to login after a short delay
          setTimeout(() => {
            router.push({ name: 'LoginPage', query: { verified: 'true' } });
          }, 2000);
        } else {
          validationMessage.value =
            response.data.message || t('emailVerification.errors.invalidCode');
        }
      } catch (error) {
        reportClientError('Email verification error', error);
        validationMessage.value =
          error.response?.data?.detail ||
          t('emailVerification.errors.verificationFailed');
      } finally {
        isLoading.value = false;
      }
    };

    // Resend verification code
    const resendVerificationCode = async () => {
      if (resendCooldown.value > 0 || isResending.value) {
        return;
      }

      isResending.value = true;
      validationMessage.value = '';
      successMessage.value = '';

      try {
        const response = await sendVerificationEmail(
          userEmail.value,
          localStorage.getItem('language') || 'en'
        );

        if (response.data.success) {
          successMessage.value = t('emailVerification.resendSuccess');
          startResendCooldown();
        } else {
          validationMessage.value =
            response.data.message || t('emailVerification.errors.resendFailed');
        }
      } catch (error) {
        reportClientError('Resend verification error', error);
        validationMessage.value =
          error.response?.data?.detail ||
          t('emailVerification.errors.resendFailed');
      } finally {
        isResending.value = false;
      }
    };

    // Start resend cooldown
    const startResendCooldown = () => {
      resendCooldown.value = 60; // 60 seconds cooldown

      cooldownInterval = setInterval(() => {
        resendCooldown.value--;
        if (resendCooldown.value <= 0) {
          clearInterval(cooldownInterval);
          cooldownInterval = null;
        }
      }, 1000);
    };

    return {
      verificationCode,
      userEmail,
      isLoading,
      isResending,
      validationMessage,
      successMessage,
      resendCooldown,
      handleVerification,
      resendVerificationCode,
      onCodeInput,
      onKeyPress,
    };
  },
};
</script>

<style scoped src="@/assets/css/email-verification.css"></style>
