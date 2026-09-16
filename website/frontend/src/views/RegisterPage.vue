<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-header">
        <img
          src="@logos/ELANora-logo.png"
          alt="ELANORA Logo"
          class="register-logo"
        />
        <h1 class="register-title">{{ t('register.title') }}</h1>
        <p v-if="invitationValid" class="register-subtitle invitation-welcome">
          {{
            t('register.invitation_welcome', {
              senderName:
                invitationInfo?.sender_username || 'Un administrateur',
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
        <div class="form-row">
          <div class="form-group">
            <label for="first-name" class="form-label">
              {{ t('register.first_name_label') }}
              <span class="required">*</span>
            </label>
            <input
              id="first-name"
              v-model="form.firstName"
              type="text"
              class="form-input"
              :class="{
                error: validationErrors.firstName,
                valid: form.firstName && !validationErrors.firstName,
              }"
              :placeholder="t('register.first_name_placeholder')"
              required
              @blur="validateField('firstName')"
            />
            <div v-if="validationErrors.firstName" class="error-message">
              {{ validationErrors.firstName }}
            </div>
            <div
              v-else-if="form.firstName && !validationErrors.firstName"
              class="success-message"
            >
              ✓
            </div>
          </div>
          <div class="form-group">
            <label for="last-name" class="form-label">
              {{ t('register.last_name_label') }}
              <span class="required">*</span>
            </label>
            <input
              id="last-name"
              v-model="form.lastName"
              type="text"
              class="form-input"
              :class="{
                error: validationErrors.lastName,
                valid: form.lastName && !validationErrors.lastName,
              }"
              :placeholder="t('register.last_name_placeholder')"
              required
              @blur="validateField('lastName')"
            />
            <div v-if="validationErrors.lastName" class="error-message">
              {{ validationErrors.lastName }}
            </div>
            <div
              v-else-if="form.lastName && !validationErrors.lastName"
              class="success-message"
            >
              ✓
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="username" class="form-label">
            {{ t('register.username_label') }}
            <span class="required">*</span>
            <span class="field-requirements"
              >• 3-20 characters • Letters, numbers, and underscores only</span
            >
          </label>
          <div class="input-with-indicator">
            <input
              id="username"
              v-model="form.username"
              type="text"
              class="form-input"
              :class="{
                error: validationErrors.username || usernameAvailable === false,
                valid: usernameAvailable === true && !validationErrors.username,
                loading: usernameCheckLoading,
              }"
              :placeholder="t('register.username_placeholder')"
              required
              autocomplete="username"
              maxlength="20"
              @focus="usernameInputFocused = true"
              @blur="
                usernameInputFocused = false;
                validateField('username');
              "
              @input="onUsernameInput"
            />
            <div class="input-indicator">
              <div v-if="usernameCheckLoading" class="loading-spinner"></div>
            </div>
          </div>
          <div class="validation-messages">
            <div v-if="validationErrors.username" class="error-message">
              <i class="error-icon-small">⚠</i>{{ validationErrors.username }}
            </div>
            <div v-else-if="usernameCheckLoading" class="info-message">
              <div class="loading-dot"></div>
              {{ t('register.checking_username') }}
            </div>
            <div v-else-if="usernameAvailable === true" class="success-message">
              <i class="success-icon-small">✓</i>{{ usernameCheckMessage }}
            </div>
            <div v-else-if="usernameAvailable === false" class="error-message">
              <i class="error-icon-small">✗</i>{{ usernameCheckMessage }}
            </div>
          </div>
        </div>

        <!-- Email field -->

        <div class="form-row">
          <div class="form-group">
            <label for="password" class="form-label">
              {{ t('register.password_label') }}
              <span class="required">*</span>
            </label>
            <div class="password-input-container">
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input"
                :class="{
                  error: validationErrors.password,
                  valid:
                    form.password &&
                    !validationErrors.password &&
                    passwordStrength !== 'weak',
                }"
                :placeholder="t('register.password_placeholder')"
                required
                autocomplete="new-password"
                @focus="passwordInputFocused = true"
                @blur="
                  passwordInputFocused = false;
                  validateField('password');
                "
                @input="onPasswordInput"
              />
              <button
                type="button"
                class="password-toggle"
                :title="showPassword ? 'Hide password' : 'Show password'"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
            <div v-if="form.password" class="password-strength">
              <div class="strength-bar">
                <div
                  class="strength-fill"
                  :class="`strength-${passwordStrength}`"
                  :style="{ width: passwordStrengthWidth }"
                ></div>
              </div>
              <span
                class="strength-text"
                :class="`strength-${passwordStrength}`"
              >
                {{ t(`register.password_strength_${passwordStrength}`) }}
              </span>
            </div>
            <div v-if="passwordInputFocused" class="password-requirements">
              <div class="requirements-title">Password Requirements:</div>
              <div
                class="requirement-item"
                :class="{ met: passwordChecks.length }"
              >
                <span class="check-icon">{{
                  passwordChecks.length ? '✓' : '✗'
                }}</span>
                At least 8 characters
              </div>
              <div
                class="requirement-item"
                :class="{ met: passwordChecks.lowercase }"
              >
                <span class="check-icon">{{
                  passwordChecks.lowercase ? '✓' : '✗'
                }}</span>
                One lowercase letter
              </div>
              <div
                class="requirement-item"
                :class="{ met: passwordChecks.uppercase }"
              >
                <span class="check-icon">{{
                  passwordChecks.uppercase ? '✓' : '✗'
                }}</span>
                One uppercase letter
              </div>
              <div
                class="requirement-item"
                :class="{ met: passwordChecks.number }"
              >
                <span class="check-icon">{{
                  passwordChecks.number ? '✓' : '✗'
                }}</span>
                One number
              </div>
              <div
                class="requirement-item"
                :class="{ met: passwordChecks.special }"
              >
                <span class="check-icon">{{
                  passwordChecks.special ? '✓' : '✗'
                }}</span>
                One special character
              </div>
            </div>
            <div v-if="validationErrors.password" class="error-message">
              <i class="error-icon-small">⚠</i>{{ validationErrors.password }}
            </div>
          </div>
          <div class="form-group">
            <label for="confirm-password" class="form-label">
              {{ t('register.confirm_password_label') }}
              <span class="required">*</span>
            </label>
            <div class="password-input-container">
              <input
                id="confirm-password"
                v-model="form.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                class="form-input"
                :class="{
                  error: validationErrors.confirmPassword,
                  valid:
                    form.confirmPassword &&
                    !validationErrors.confirmPassword &&
                    form.password === form.confirmPassword,
                }"
                :placeholder="t('register.confirm_password_placeholder')"
                required
                autocomplete="new-password"
                @blur="validateField('confirmPassword')"
              />
              <button
                type="button"
                class="password-toggle"
                :title="showConfirmPassword ? 'Hide password' : 'Show password'"
                @click="showConfirmPassword = !showConfirmPassword"
              >
                {{ showConfirmPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
            <div v-if="validationErrors.confirmPassword" class="error-message">
              <i class="error-icon-small">⚠</i
              >{{ validationErrors.confirmPassword }}
            </div>
            <div
              v-else-if="
                form.confirmPassword && form.password === form.confirmPassword
              "
              class="success-message"
            >
              <i class="success-icon-small">✓</i
              >{{ t('register.passwords_match') }}
            </div>
          </div>
        </div>
        <div class="form-group">
          <label for="email" class="form-label">
            {{ t('register.email_label') }}
            <span class="required">*</span>
          </label>
          <div class="input-with-indicator">
            <input
              id="email"
              v-model="form.email"
              type="email"
              class="form-input"
              :class="{
                error: validationErrors.email || emailAvailable === false,
                valid: emailAvailable === true && !validationErrors.email,
                loading: emailCheckLoading,
              }"
              :placeholder="t('register.email_placeholder')"
              required
              :disabled="!!invitationInfo?.receiver_email"
              @focus="emailInputFocused = true"
              @blur="
                emailInputFocused = false;
                validateField('email');
              "
              @input="onEmailInput"
            />
            <div class="input-indicator">
              <div v-if="emailCheckLoading" class="loading-spinner"></div>
            </div>
          </div>
          <div class="validation-messages">
            <div v-if="validationErrors.email" class="error-message">
              <i class="error-icon-small">⚠</i>{{ validationErrors.email }}
            </div>
            <div v-else-if="emailCheckLoading" class="info-message">
              <div class="loading-dot"></div>
              {{ t('register.checking_email') }}
            </div>
            <div v-else-if="emailAvailable === true" class="success-message">
              <i class="success-icon-small">✓</i>{{ emailCheckMessage }}
            </div>
            <div v-else-if="emailAvailable === false" class="error-message">
              <i class="error-icon-small">✗</i>{{ emailCheckMessage }}
            </div>
          </div>
        </div>
        <div class="form-group">
          <label for="confirm-email" class="form-label">
            {{ t('register.confirm_email_label') }}
            <span class="required">*</span>
          </label>
          <input
            id="confirm-email"
            v-model="form.confirmEmail"
            type="email"
            class="form-input"
            :class="{
              error: validationErrors.confirmEmail,
              valid:
                form.confirmEmail &&
                !validationErrors.confirmEmail &&
                form.email === form.confirmEmail,
            }"
            :placeholder="t('register.confirm_email_placeholder')"
            required
            :disabled="!!invitationInfo?.receiver_email"
            @blur="validateField('confirmEmail')"
          />
          <div v-if="validationErrors.confirmEmail" class="error-message">
            <i class="error-icon-small">⚠</i
            >{{ validationErrors.confirmEmail }}
          </div>
          <div
            v-else-if="form.confirmEmail && form.email === form.confirmEmail"
            class="success-message"
          >
            <i class="success-icon-small">✓</i>{{ t('register.emails_match') }}
          </div>
        </div>

        <div class="form-group">
          <label for="phone" class="form-label">
            {{ t('register.phone_label') }}
          </label>
          <input
            id="phone"
            v-model="form.phoneNumber"
            type="tel"
            class="form-input"
            :class="{
              error: validationErrors.phoneNumber,
              valid: form.phoneNumber && !validationErrors.phoneNumber,
            }"
            :placeholder="t('register.phone_placeholder')"
            @blur="validateField('phoneNumber')"
          />
          <div v-if="validationErrors.phoneNumber" class="error-message">
            {{ validationErrors.phoneNumber }}
          </div>
        </div>

        <div class="form-group">
          <label for="affiliation" class="form-label">
            {{ t('register.affiliation_label') }}
            <span class="required">*</span>
          </label>
          <input
            id="affiliation"
            v-model="form.affiliation"
            type="text"
            class="form-input"
            :class="{
              error: validationErrors.affiliation,
              valid: form.affiliation && !validationErrors.affiliation,
            }"
            :placeholder="t('register.affiliation_placeholder')"
            required
            @blur="validateField('affiliation')"
          />
          <div v-if="validationErrors.affiliation" class="error-message">
            {{ validationErrors.affiliation }}
          </div>
        </div>
        <div class="form-group">
          <label for="department" class="form-label">
            {{ t('register.department_label') }}
            <span class="required">*</span>
          </label>
          <input
            id="department"
            v-model="form.department"
            type="text"
            class="form-input"
            :class="{
              error: validationErrors.department,
              valid: form.department && !validationErrors.department,
            }"
            :placeholder="t('register.department_placeholder')"
            required
            @blur="validateField('department')"
          />
          <div v-if="validationErrors.department" class="error-message">
            {{ validationErrors.department }}
          </div>
        </div>

        <!-- Address Section -->
        <div class="address-section">
          <h3 class="section-title">{{ t('register.address_section') }}</h3>

          <div class="form-row">
            <div class="form-group">
              <label for="country" class="form-label">
                {{ t('register.country_label') }}
                <span class="required">*</span>
              </label>
              <AppSelect
                id="country"
                v-model="form.address.countryId"
                :invalid="Boolean(validationErrors.countryId)"
                :required="true"
                :placeholder="t('register.country_placeholder')"
                :options="countryOptions"
                @change="onCountryChange"
                @blur="validateField('countryId')"
              />
              <div v-if="validationErrors.countryId" class="error-message">
                {{ validationErrors.countryId }}
              </div>
            </div>

            <div class="form-group">
              <label for="city" class="form-label">
                {{ t('register.city_label') }}
                <span class="required">*</span>
              </label>
              <input
                id="city"
                v-model="form.address.cityName"
                type="text"
                class="form-input"
                :class="{
                  error: addressValidation.city.isValid === false,
                  valid:
                    addressValidation.city.isValid === true &&
                    cityValidationMessage &&
                    cityValidationMessage.type === 'success',
                  loading: addressValidation.city.loading,
                }"
                :placeholder="t('register.city_placeholder')"
                :disabled="!form.address.countryId"
                required
                @blur="validateCityField"
                @input="onCityChange"
              />
              <!-- City validation messages -->
              <div
                v-if="cityValidationMessage"
                :class="`${cityValidationMessage.type}-message`"
              >
                <i
                  v-if="cityValidationMessage.type === 'success'"
                  class="success-icon-small"
                  >✓</i
                >
                <i
                  v-else-if="cityValidationMessage.type === 'error'"
                  class="error-icon-small"
                  >⚠</i
                >
                {{ cityValidationMessage.text }}
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="streetName" class="form-label">
                {{ t('register.street_name_label') }}
                <span class="required">*</span>
              </label>
              <input
                id="streetName"
                v-model="form.address.streetName"
                type="text"
                class="form-input"
                :class="{
                  error: addressValidation.streetName.isValid === false,
                  valid:
                    addressValidation.streetName.isValid === true &&
                    streetValidationMessage &&
                    streetValidationMessage.type === 'success',
                }"
                :placeholder="t('register.street_name_placeholder')"
                required
                @blur="validateStreetNameField"
                @input="onStreetNameChange"
              />
              <!-- Street validation messages -->
              <div
                v-if="streetValidationMessage"
                :class="`${streetValidationMessage.type}-message`"
              >
                <i
                  v-if="streetValidationMessage.type === 'success'"
                  class="success-icon-small"
                  >✓</i
                >
                <i
                  v-else-if="streetValidationMessage.type === 'error'"
                  class="error-icon-small"
                  >⚠</i
                >
                {{ streetValidationMessage.text }}
              </div>
            </div>

            <div class="form-group">
              <label for="streetNumber" class="form-label">
                {{ t('register.street_number_label') }}
              </label>
              <input
                id="streetNumber"
                v-model="form.address.streetNumber"
                type="text"
                class="form-input"
                :placeholder="t('register.street_number_placeholder')"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="postalCode" class="form-label">
                {{ t('register.postal_code_label') }}
                <span class="required">*</span>
              </label>
              <input
                id="postalCode"
                v-model="form.address.postalCode"
                type="text"
                class="form-input"
                :class="{
                  error: addressValidation.postalCode.isValid === false,
                  valid:
                    addressValidation.postalCode.isValid === true &&
                    postalCodeValidationMessage &&
                    postalCodeValidationMessage.type === 'success',
                  loading: addressValidation.postalCode.loading,
                }"
                :placeholder="t('register.postal_code_placeholder')"
                :disabled="!form.address.countryId"
                required
                @blur="validatePostalCodeField"
                @input="onPostalCodeChange"
              />
              <!-- Postal code validation messages -->
              <div
                v-if="postalCodeValidationMessage"
                :class="`${postalCodeValidationMessage.type}-message`"
              >
                <i
                  v-if="postalCodeValidationMessage.type === 'success'"
                  class="success-icon-small"
                  >✓</i
                >
                <i
                  v-else-if="postalCodeValidationMessage.type === 'error'"
                  class="error-icon-small"
                  >⚠</i
                >
                {{ postalCodeValidationMessage.text }}
              </div>
            </div>

            <div class="form-group">
              <label for="addressLine2" class="form-label">
                {{ t('register.address_line2_label') }}
              </label>
              <input
                id="addressLine2"
                v-model="form.address.addressLine2"
                type="text"
                class="form-input"
                :class="{
                  valid:
                    form.address.addressLine2 &&
                    form.address.addressLine2.length > 0,
                }"
                :placeholder="t('register.address_line2_placeholder')"
              />
            </div>
          </div>
        </div>

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
import AppSelect from '@/components/common/AppSelect.vue';
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
  passwordChecksOf,
  passwordStrengthOf,
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
const showPassword = ref(false);
const showConfirmPassword = ref(false);

// Address checks against the location service
const {
  validation: addressValidation,
  cityMessage: cityValidationMessage,
  streetMessage: streetValidationMessage,
  postalCodeMessage: postalCodeValidationMessage,
  addressAccepted,
  validateCity: validateCityField,
  validatePostalCode: validatePostalCodeField,
  validateStreetName: validateStreetNameField,
  onCountryChange: resetAddressChecksForCountry,
  onCityChange,
  onStreetNameChange,
  onPostalCodeChange,
} = useAddressVerification({
  address: computed(() => form.value.address),
  translate: t,
  locationApi,
  reportError: reportClientError,
});

// Focus management
const usernameInputFocused = ref(false);
const emailInputFocused = ref(false);
const passwordInputFocused = ref(false);

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

// Password strength
const passwordStrength = computed(() =>
  passwordStrengthOf(form.value.password)
);

const passwordStrengthWidth = computed(() => {
  const strength = passwordStrength.value;
  if (strength === 'weak') return '33%';
  if (strength === 'medium') return '66%';
  return '100%';
});

// Password requirements check
const passwordChecks = computed(() => passwordChecksOf(form.value.password));

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
