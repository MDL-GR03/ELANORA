<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-header">
        <img
          src="/images/logos/ELANora-logo.png"
          :alt="t('register.logo_alt')"
          class="register-logo"
        />
        <h1 class="register-title">{{ t('register.title') }}</h1>
        <p v-if="invitationValid" class="register-subtitle invitation-welcome">
          {{
            t('register.invitation_welcome', {
              senderName:
                invitationInfo?.sender_username ||
                t('register.invitation_sender_unknown'),
            })
          }}
        </p>
        <p v-else class="register-subtitle">
          {{ t('register.subtitle') }}
        </p>
      </div>

      <!-- Invitation Code Section -->
      <div v-if="!invitationValid" class="invitation-section">
        <div class="form-group">
          <label for="invitation-code" class="form-label">
            {{ t('register.invitation_code_label') }}
            <span class="required">*</span>
          </label>
          <input
            id="invitation-code"
            v-model="invitationCode"
            type="text"
            class="form-input"
            :class="{ error: invitationError }"
            :placeholder="t('register.invitation_code_placeholder')"
            @input="validateInvitationCode"
          />
          <div v-if="invitationError" class="error-message">
            {{ invitationError }}
          </div>
          <div v-if="invitationValidating" class="info-message">
            {{ t('register.validating_invitation') }}
          </div>
          <div v-if="invitationValid" class="success-message">
            {{ t('register.invitation_valid') }}
          </div>
        </div>
      </div>

      <!-- Registration Form -->
      <form
        v-if="invitationValid"
        class="register-form"
        @submit.prevent="handleRegister"
      >
        <RegisterIdentityFields
          v-model="form"
          :errors="validationErrors"
          :available="usernameAvailable"
          :checking="usernameCheckLoading"
          :message="usernameCheckMessage"
          @validate="validateField"
          @username-input="onUsernameInput"
        />

        <RegisterPasswordFields
          v-model="form"
          :errors="validationErrors"
          @validate="validateField"
          @password-input="onPasswordInput"
        />

        <RegisterContactFields
          v-model="form"
          :errors="validationErrors"
          :available="emailAvailable"
          :checking="emailCheckLoading"
          :message="emailCheckMessage"
          :email-fixed-by-invitation="Boolean(invitationInfo?.receiver_email)"
          @validate="validateField"
          @email-input="onEmailInput"
        />

        <RegisterAddressFields
          v-model="form.address"
          :verification="addressVerification"
          :country-options="countryOptions"
          :country-error="validationErrors.countryId || ''"
          @country-change="onCountryChange"
          @validate-country="validateField('countryId')"
        />

        <button
          type="submit"
          class="btn-primary register-btn"
          :disabled="loading || !invitationValid || !isFormValid"
        >
          <span v-if="loading">{{ t('register.registering') }}</span>
          <span v-else>{{ t('register.submit') }}</span>
        </button>
      </form>

      <div class="register-footer">
        <p>
          {{ t('register.already_have_account') }}
          <router-link to="/" class="link">{{
            t('register.login_here')
          }}</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useEventMessageStore } from '@stores/eventMessage';

import '@/assets/css/register-fields.css';
import RegisterIdentityFields from '@/components/pageSpecific/register/RegisterIdentityFields.vue';
import RegisterPasswordFields from '@/components/pageSpecific/register/RegisterPasswordFields.vue';
import RegisterContactFields from '@/components/pageSpecific/register/RegisterContactFields.vue';
import RegisterAddressFields from '@/components/pageSpecific/register/RegisterAddressFields.vue';
import * as invitationApi from '@/api/service/invitationService';
import * as authApi from '@/api/service/authService';
import { reportClientError } from '@/utils/errorDiagnostics';
import * as locationApi from '@/api/service/locationService';
import {
  checkUsernameAvailability,
  checkEmailAvailability,
} from '@/api/service/userService';
import {
  REQUIRED_ADDRESS_FIELDS,
  REQUIRED_REGISTRATION_FIELDS,
  validateRegistrationField,
  validateRegistrationForm,
} from '@/utils/registrationValidation';
import { useAddressVerification } from '@/composables/useAddressVerification';
import { useAvailabilityCheck } from '@/composables/useAvailabilityCheck';
import { useInvitationRegistration } from '@/composables/useInvitationRegistration';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const eventMessageStore = useEventMessageStore();

// Reactive data
const countries = ref([]);
const countryOptions = computed(() =>
  countries.value.map((country) => ({
    value: country.country_id,
    label: country.country_name,
  }))
);

const form = ref({
  firstName: '',
  lastName: '',
  username: '',
  email: '',
  confirmEmail: '',
  password: '',
  confirmPassword: '',
  phoneNumber: '',
  affiliation: '',
  department: '',
  address: {
    countryId: '',
    cityName: '',
    streetName: '',
    streetNumber: '',
    postalCode: '',
    addressLine2: '',
  },
});

// Is this username or email address still free?
const {
  available: usernameAvailable,
  checking: usernameCheckLoading,
  message: usernameCheckMessage,
  reset: resetUsernameAvailability,
  request: requestUsernameAvailability,
} = useAvailabilityCheck({
  check: checkUsernameAvailability,
  translate: t,
  errorKey: 'register.username_check_error',
  minimumLength: 3,
  reportError: reportClientError,
});

const {
  available: emailAvailable,
  checking: emailCheckLoading,
  message: emailCheckMessage,
  reset: resetEmailAvailability,
  request: requestEmailAvailability,
} = useAvailabilityCheck({
  check: checkEmailAvailability,
  translate: t,
  errorKey: 'register.email_check_error',
  reportError: reportClientError,
});

// Form validation
const validationErrors = ref({});

// Address checks against the location service
const addressVerification = useAddressVerification({
  address: computed(() => form.value.address),
  translate: t,
  locationApi,
  reportError: reportClientError,
});
const { addressAccepted, onCountryChange: resetAddressChecksForCountry } =
  addressVerification;

// Validating the invitation and creating the account it was issued for
const {
  invitationCode,
  invitationValid,
  invitationValidating,
  invitationError,
  invitationInfo,
  loading,
  validateInvitationCode,
  register: handleRegister,
} = useInvitationRegistration({
  form,
  countries,
  translate: t,
  invitationApi,
  authApi,
  eventMessages: eventMessageStore,
  router,
  validateAllFields: () => validateAllFields(),
  validationErrors,
  usernameAvailable,
  emailAvailable,
  reportError: reportClientError,
});

const isFormValid = computed(() => {
  const requiredFields = REQUIRED_REGISTRATION_FIELDS;
  const requiredAddressFields = REQUIRED_ADDRESS_FIELDS;

  // Check required fields
  for (const field of requiredFields) {
    if (!form.value[field] || validationErrors.value[field]) {
      return false;
    }
  }

  // Check required address fields
  for (const field of requiredAddressFields) {
    if (!form.value.address[field] || validationErrors.value[field]) {
      return false;
    }
  }

  // Check availability checks
  if (usernameAvailable.value === false || emailAvailable.value === false) {
    return false;
  }

  return addressAccepted.value;
});

// Input handlers
const onUsernameInput = () => {
  validationErrors.value.username = '';
  resetUsernameAvailability();
};

const onEmailInput = () => {
  validationErrors.value.email = '';
  resetEmailAvailability();
};

const onPasswordInput = () => {
  validationErrors.value.password = '';
  if (form.value.confirmPassword) {
    validateField('confirmPassword');
  }
};

// Validation functions
const validateField = (fieldName) => {
  validationErrors.value[fieldName] = validateRegistrationField(
    fieldName,
    form.value,
    t
  );
};

const validateAllFields = () => {
  validationErrors.value = validateRegistrationForm(form.value, t);
};

const onCountryChange = () => {
  validateField('countryId');
  resetAddressChecksForCountry();
};

// Check for invitation code in URL params
onMounted(async () => {
  const invitationParam = route.query.invitation;
  if (invitationParam) {
    invitationCode.value = invitationParam;
    validateInvitationCode();
  }

  // Load countries
  await loadCountries();
});

// Watch for changes in invitation code
watch(invitationCode, (newValue) => {
  if (newValue && newValue.length > 0) {
    invitationError.value = '';
  }
});

// Load countries from API
const loadCountries = async () => {
  try {
    const response = await locationApi.getCountries();
    if (response.success) {
      countries.value = response.data;
    } else {
      eventMessageStore.addMessage(
        t('register.error_loading_countries'),
        'error'
      );
    }
  } catch (error) {
    reportClientError('Error loading countries', error);
    eventMessageStore.addMessage(
      t('register.error_loading_countries'),
      'error'
    );
  }
};

watch(
  () => form.value.username,
  (username) => {
    validateField('username');
    requestUsernameAvailability(username, {
      skip: Boolean(validationErrors.value.username),
    });
  }
);

watch(
  () => form.value.email,
  (email) => {
    validateField('email');
    requestEmailAvailability(email, {
      skip: Boolean(validationErrors.value.email),
    });
  }
);
</script>

<style scoped src="@/assets/css/register.css"></style>
