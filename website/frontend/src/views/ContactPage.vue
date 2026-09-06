<template>
  <div class="contact-container-wrapper">
    <div class="contact-container">
      <div class="contact-card">
        <div class="contact-header">
          <h1 class="contact-title">{{ t('contact.title') }}</h1>
          <p class="contact-subtitle">{{ t('contact.subtitle') }}</p>
        </div>

        <form class="contact-form" @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="email">{{ t('contact.email') }} *</label>
            <input
              id="email"
              v-model="contactForm.email"
              type="email"
              required
              :placeholder="t('contact.email_placeholder')"
              :disabled="isSubmitting || isAuthenticated"
              :readonly="isAuthenticated"
            />
          </div>

          <div class="form-group">
            <label for="request_type">{{ t('contact.request_type') }} *</label>
            <select
              id="request_type"
              v-model="contactForm.request_type"
              required
              :disabled="isSubmitting"
            >
              <option value="">{{ t('contact.select_request_type') }}</option>
              <option value="bug_report">{{ t('contact.bug_report') }}</option>
              <option value="feature_request">
                {{ t('contact.feature_request') }}
              </option>
              <option value="technical_support">
                {{ t('contact.technical_support') }}
              </option>
              <option value="account_issue">
                {{ t('contact.account_issue') }}
              </option>
              <option value="general_inquiry">
                {{ t('contact.general_inquiry') }}
              </option>
              <option value="other">{{ t('contact.other') }}</option>
            </select>
          </div>

          <div class="form-group">
            <label for="message">{{ t('contact.message') }} *</label>
            <textarea
              id="message"
              v-model="contactForm.message"
              required
              rows="6"
              :placeholder="t('contact.message_placeholder')"
              :disabled="isSubmitting"
            ></textarea>
            <div class="message-counter">
              <span
                :class="{
                  'text-error':
                    contactForm.message.length < 10 ||
                    contactForm.message.length > 5000,
                  'text-warning': contactForm.message.length > 4500,
                  'text-success':
                    contactForm.message.length >= 10 &&
                    contactForm.message.length <= 4500,
                }"
              >
                {{ contactForm.message.length }} / 5000 caractères
                <span v-if="contactForm.message.length < 10"
                  >(minimum: 10)</span
                >
              </span>
            </div>
          </div>

          <!-- Honeypot field (hidden from users, should remain empty) -->
          <div class="honeypot-field">
            <label for="website">{{ t('contact.website_label') }}</label>
            <input
              id="website"
              v-model="contactForm.website"
              type="text"
              tabindex="-1"
              autocomplete="off"
              :placeholder="t('contact.website_placeholder')"
            />
          </div>

          <!-- CAPTCHA -->
          <div class="form-group captcha-group">
            <label for="captcha">{{ t('contact.captcha_label') }} *</label>
            <div class="captcha-container">
              <span class="captcha-question">
                {{ captcha.num1 }} {{ captcha.operator }} {{ captcha.num2 }} = ?
              </span>
              <input
                id="captcha"
                v-model="contactForm.captcha_answer"
                type="number"
                required
                :placeholder="t('contact.captcha_placeholder')"
                :disabled="isSubmitting"
                class="captcha-input"
              />
              <button
                type="button"
                class="captcha-refresh"
                :disabled="isSubmitting"
                :title="t('contact.captcha_refresh')"
                aria-label="{{ t('contact.captcha_refresh') }}"
                @click="
                  generateCaptcha();
                  contactForm.captcha_answer = '';
                "
              >
                <!-- Small, sober reset icon (uses currentColor) -->
                <svg
                  class="captcha-refresh-icon"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  width="18"
                  height="18"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M21 12a9 9 0 1 1-3.1-6.4" />
                  <polyline points="21 3 21 9 15 9" />
                </svg>
                <span class="sr-only">{{ t('contact.captcha_refresh') }}</span>
              </button>
            </div>
          </div>

          <button
            type="submit"
            class="btn-primary contact-btn"
            :disabled="isSubmitting"
          >
            <span v-if="isSubmitting">{{ t('contact.sending') }}</span>
            <span v-else>{{ t('contact.send') }}</span>
          </button>
        </form>

        <div class="contact-info">
          <p class="contact-note">{{ t('contact.response_note') }}</p>
        </div>

        <div class="back-to-site">
          <router-link to="/" class="back-link">
            ← {{ t('contact.back_to_site') }}
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useEventMessageStore } from '@stores/eventMessage.js';
import { useUserStore } from '@stores/user.js';
import { contactService } from '@api/service/contactService.js';
import '@assets/css/contact-page.css';

const { t } = useI18n();
const eventMessageStore = useEventMessageStore();
const userStore = useUserStore();

const isSubmitting = ref(false);

const contactForm = reactive({
  email: '',
  request_type: '',
  message: '',
  captcha_answer: '',
  // Honeypot field - should remain empty
  website: '',
});

// CAPTCHA system
const captcha = ref({
  num1: 0,
  num2: 0,
  operator: '+',
  correctAnswer: 0,
});

// Generate a new CAPTCHA
const generateCaptcha = () => {
  const operators = ['+', '-', '*'];
  const operator = operators[Math.floor(Math.random() * operators.length)];

  let num1, num2, correctAnswer;

  switch (operator) {
    case '+':
      num1 = Math.floor(Math.random() * 20) + 1; // 1-20
      num2 = Math.floor(Math.random() * 20) + 1; // 1-20
      correctAnswer = num1 + num2;
      break;
    case '-':
      num1 = Math.floor(Math.random() * 30) + 10; // 10-39
      num2 = Math.floor(Math.random() * (num1 - 1)) + 1; // 1 to num1-1
      correctAnswer = num1 - num2;
      break;
    case '*':
      num1 = Math.floor(Math.random() * 10) + 1; // 1-10
      num2 = Math.floor(Math.random() * 10) + 1; // 1-10
      correctAnswer = num1 * num2;
      break;
  }

  captcha.value = { num1, num2, operator, correctAnswer };
};

// Computed property to check if user is authenticated
const isAuthenticated = computed(
  () => userStore.user && userStore.user.user_id
);

// Computed property to get user email
const userEmail = computed(() => userStore.user?.email || '');

// Initialize form with user email if authenticated
onMounted(async () => {
  // Generate initial CAPTCHA
  generateCaptcha();

  // Ensure authentication is verified first
  if (!userStore.authState.initialized) {
    await userStore.verifyAuthentication();
  }

  if (isAuthenticated.value && userEmail.value) {
    contactForm.email = userEmail.value;
  }
});

// Watch for authentication state changes
watch([isAuthenticated, userEmail], ([isAuth, email]) => {
  if (isAuth && email && !contactForm.email) {
    contactForm.email = email;
  }
});

// Handle error responses with specific error messages
const handleContactError = (error) => {
  console.error('Contact form submission error:', error);

  // Handle different types of errors with specific messages
  if (error.response?.status) {
    const status = error.response.status;

    switch (status) {
      case 400:
        handleValidationError(error);
        break;
      case 401:
      case 403:
        eventMessageStore.addMessage('contact.error_forbidden', 'error');
        break;
      case 404:
        eventMessageStore.addMessage('contact.error_not_found', 'error');
        break;
      case 409:
        eventMessageStore.addMessage('contact.error_conflict', 'error');
        break;
      case 413:
        eventMessageStore.addMessage(
          'contact.error_payload_too_large',
          'error'
        );
        break;
      case 429:
        // Rate limiting - too many requests
        eventMessageStore.addMessage('contact.error_rate_limit', 'error');
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        eventMessageStore.addMessage('contact.error_server', 'error');
        break;
      default:
        eventMessageStore.addMessage('contact.error_unknown', 'error');
    }
  } else if (error.code === 'NETWORK_ERROR' || error.code === 'ERR_NETWORK') {
    // Network connectivity issues
    eventMessageStore.addMessage('contact.error_network', 'error');
  } else if (error.code === 'TIMEOUT' || error.code === 'ECONNABORTED') {
    // Request timeout
    eventMessageStore.addMessage('contact.error_timeout', 'error');
  } else {
    // Generic error message for unknown errors
    eventMessageStore.addMessage('contact.error_unknown', 'error');
  }

  // Generate new CAPTCHA on error
  generateCaptcha();
  contactForm.captcha_answer = '';
};

// Handle backend validation errors (400 status)
const handleValidationError = (error) => {
  if (error.response?.data?.detail) {
    const errors = error.response.data.detail;

    // Check for specific validation errors
    const messageError = errors.find(
      (err) => err.loc && err.loc.includes('message')
    );
    const emailError = errors.find(
      (err) => err.loc && err.loc.includes('email')
    );
    const requestTypeError = errors.find(
      (err) => err.loc && err.loc.includes('request_type')
    );

    if (messageError) {
      if (messageError.type === 'string_too_short') {
        eventMessageStore.addMessage(
          'contact.error_message_too_short',
          'error'
        );
      } else if (messageError.type === 'string_too_long') {
        eventMessageStore.addMessage('contact.error_message_too_long', 'error');
      } else {
        eventMessageStore.addMessage('contact.error_message_invalid', 'error');
      }
    } else if (emailError) {
      eventMessageStore.addMessage('contact.error_email_invalid', 'error');
    } else if (requestTypeError) {
      eventMessageStore.addMessage(
        'contact.error_request_type_invalid',
        'error'
      );
    } else {
      eventMessageStore.addMessage('contact.error_validation', 'error');
    }
  } else {
    eventMessageStore.addMessage('contact.error_validation', 'error');
  }
};

const handleSubmit = async () => {
  if (isSubmitting.value) return;

  // Security checks
  // 1. Honeypot check - field should be empty
  if (contactForm.website.trim() !== '') {
    console.warn('Honeypot triggered - potential bot submission');
    return; // Silently reject without showing error
  }

  // 2. CAPTCHA validation
  const userAnswer = parseInt(contactForm.captcha_answer);
  if (isNaN(userAnswer) || userAnswer !== captcha.value.correctAnswer) {
    eventMessageStore.addMessage('contact.captcha_error', 'error');
    generateCaptcha(); // Generate new CAPTCHA
    contactForm.captcha_answer = '';
    return;
  }

  // 3. Frontend validation
  if (contactForm.message.trim().length < 10) {
    eventMessageStore.addMessage('contact.error_message_too_short', 'error');
    return;
  }

  if (contactForm.message.length > 5000) {
    eventMessageStore.addMessage('contact.error_message_too_long', 'error');
    return;
  }

  try {
    isSubmitting.value = true;

    // Send only the necessary fields (exclude security fields)
    const submissionData = {
      email: contactForm.email,
      request_type: contactForm.request_type,
      message: contactForm.message,
    };

    await contactService.sendContactMessage(submissionData);

    eventMessageStore.addMessage('contact.success_message', 'success');

    // Reset form, but keep email if user is authenticated
    if (!isAuthenticated.value) {
      contactForm.email = '';
    }
    contactForm.request_type = '';
    contactForm.message = '';
    contactForm.captcha_answer = '';
    contactForm.website = ''; // Reset honeypot

    // Generate new CAPTCHA for next submission
    generateCaptcha();
  } catch (error) {
    handleContactError(error);
  } finally {
    isSubmitting.value = false;
  }
};
</script>
