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
import { validateInvitation } from '@/api/service/invitationService';
import { registerWithInvitation } from '@/api/service/authService';
import { reportClientError } from '@/utils/errorDiagnostics';
import {
  getCountries,
  validateCity,
  validatePostalCode,
  validatePostalCodeInCity,
  validateStreetInCity,
  validateStreetName,
} from '@/api/service/locationService';
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

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const eventMessageStore = useEventMessageStore();

// Reactive data
const invitationCode = ref('');
const invitationValid = ref(false);
const invitationValidating = ref(false);
const invitationError = ref('');
const invitationInfo = ref(null);
const loading = ref(false);
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

// Username availability check
const usernameAvailable = ref(null);
const usernameCheckLoading = ref(false);
const usernameCheckMessage = ref('');
let usernameCheckTimeout = null;

// Email availability check
const emailAvailable = ref(null);
const emailCheckLoading = ref(false);
const emailCheckMessage = ref('');
let emailCheckTimeout = null;

// Address validation timeouts
let cityValidationTimeout = null;
let streetValidationTimeout = null;
let postalCodeValidationTimeout = null;

// Form validation
const validationErrors = ref({});
const showPassword = ref(false);
const showConfirmPassword = ref(false);

// Address validation states
const addressValidation = ref({
  city: { isValid: null, message: '', loading: false },
  postalCode: { isValid: null, message: '', loading: false },
  streetName: { isValid: null, message: '' },
  streetInCity: { isValid: null, message: '', loading: false },
  postalCodeInCity: { isValid: null, message: '', loading: false },
  fullAddress: { isValid: null, message: '', loading: false, confidence: null },
});

// Focus management
const usernameInputFocused = ref(false);
const emailInputFocused = ref(false);
const passwordInputFocused = ref(false);

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

// Computed properties for address validation message display
const cityValidationMessage = computed(() => {
  if (addressValidation.value.city.loading) {
    return { type: 'info', text: t('register.validating_city') };
  }
  if (addressValidation.value.city.isValid === false) {
    return { type: 'error', text: addressValidation.value.city.message };
  }
  if (
    addressValidation.value.city.isValid === true &&
    addressValidation.value.city.message
  ) {
    return { type: 'success', text: addressValidation.value.city.message };
  }
  return null;
});

const streetValidationMessage = computed(() => {
  // Priority: loading > cross-validation > basic validation
  if (addressValidation.value.streetInCity.loading) {
    return { type: 'info', text: t('register.validating_street_in_city') };
  }
  if (addressValidation.value.streetInCity.isValid === false) {
    return {
      type: 'warning',
      text: addressValidation.value.streetInCity.message,
    };
  }
  if (addressValidation.value.streetInCity.isValid === true) {
    return {
      type: 'success',
      text: addressValidation.value.streetInCity.message,
    };
  }
  if (addressValidation.value.streetName.isValid === false) {
    return { type: 'error', text: addressValidation.value.streetName.message };
  }
  if (
    addressValidation.value.streetName.isValid === true &&
    addressValidation.value.streetName.message
  ) {
    return {
      type: 'success',
      text: addressValidation.value.streetName.message,
    };
  }
  return null;
});

const postalCodeValidationMessage = computed(() => {
  // Priority: loading > cross-validation > basic validation
  if (addressValidation.value.postalCode.loading) {
    return { type: 'info', text: t('register.validating_postal_code') };
  }
  if (addressValidation.value.postalCodeInCity.loading) {
    return { type: 'info', text: t('register.validating_postal_code_in_city') };
  }
  if (addressValidation.value.postalCodeInCity.isValid === false) {
    return {
      type: 'warning',
      text: addressValidation.value.postalCodeInCity.message,
    };
  }
  if (addressValidation.value.postalCodeInCity.isValid === true) {
    return {
      type: 'success',
      text: addressValidation.value.postalCodeInCity.message,
    };
  }
  if (addressValidation.value.postalCode.isValid === false) {
    return { type: 'error', text: addressValidation.value.postalCode.message };
  }
  if (
    addressValidation.value.postalCode.isValid === true &&
    addressValidation.value.postalCode.message
  ) {
    return {
      type: 'success',
      text: addressValidation.value.postalCode.message,
    };
  }
  return null;
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

  // Check address validations - basic validations must be valid
  if (
    addressValidation.value.city.isValid === false ||
    addressValidation.value.postalCode.isValid === false ||
    addressValidation.value.streetName.isValid === false
  ) {
    return false;
  }

  // Check cross-validations - they must be either valid or null (not checked yet)
  // If they are false, it means validation failed
  // For streets, if both street name and city are provided, street-in-city validation must be valid
  if (
    form.value.address.streetName &&
    form.value.address.cityName &&
    form.value.address.countryId
  ) {
    if (addressValidation.value.streetInCity.isValid === false) {
      return false;
    }
  }

  if (
    form.value.address.postalCode &&
    form.value.address.cityName &&
    form.value.address.countryId
  ) {
    if (addressValidation.value.postalCodeInCity.isValid === false) {
      return false;
    }
  }

  return true;
});

// Input handlers
const onUsernameInput = () => {
  validationErrors.value.username = '';
  usernameAvailable.value = null;
  usernameCheckMessage.value = '';
};

const onEmailInput = () => {
  validationErrors.value.email = '';
  emailAvailable.value = null;
  emailCheckMessage.value = '';
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

// Address validation functions
const validateCityField = async () => {
  if (!form.value.address.cityName || !form.value.address.countryId) {
    addressValidation.value.city = {
      isValid: false,
      message: form.value.address.cityName
        ? t('register.country_required')
        : t('register.city_required'),
      loading: false,
    };
    return;
  }

  addressValidation.value.city.loading = true;

  try {
    const result = await validateCity(
      form.value.address.cityName,
      form.value.address.countryId
    );
    if (result.success) {
      addressValidation.value.city = {
        isValid: result.data.isValid,
        message: result.data.isValid
          ? t('register.city_valid_in_country')
          : result.data.message || t('register.city_not_found_in_country'),
        loading: false,
      };

      // If city is valid, trigger cross-validation with postal code and street
      if (result.data.isValid) {
        // Re-validate street in city if street name is provided
        if (form.value.address.streetName) {
          await validateStreetInCityField();
        }

        // Re-validate postal code in city if postal code is provided
        if (form.value.address.postalCode) {
          await validatePostalCodeInCityField();
        }
      } else {
        // Reset cross-validations if city is invalid
        addressValidation.value.streetInCity = {
          isValid: null,
          message: '',
          loading: false,
        };
        addressValidation.value.postalCodeInCity = {
          isValid: null,
          message: '',
          loading: false,
        };
      }
    } else {
      addressValidation.value.city = {
        isValid: false,
        message: t('register.city_validation_error'),
        loading: false,
      };
    }
  } catch (error) {
    reportClientError('Error validating city', error);
    addressValidation.value.city = {
      isValid: false,
      message: t('register.city_validation_error'),
      loading: false,
    };
  }
};

const validatePostalCodeField = async () => {
  if (!form.value.address.postalCode || !form.value.address.countryId) {
    addressValidation.value.postalCode = {
      isValid: false,
      message: t('register.postal_code_required'),
      loading: false,
    };
    return;
  }

  addressValidation.value.postalCode.loading = true;

  try {
    const result = await validatePostalCode(
      form.value.address.postalCode,
      form.value.address.countryId
    );
    if (result.success) {
      // Set initial validation (format check)
      const isFormatValid = result.data.isValid;

      // Store format validation result
      addressValidation.value.postalCode = {
        isValid: isFormatValid,
        message: isFormatValid ? '' : result.data.message,
        loading: false,
      };

      // If format is valid and we have a valid city, do cross-validation
      if (
        isFormatValid &&
        form.value.address.cityName &&
        addressValidation.value.city.isValid === true
      ) {
        await validatePostalCodeInCityField();
      } else {
        // Reset cross-validation if format is invalid or no city
        addressValidation.value.postalCodeInCity = {
          isValid: null,
          message: '',
          loading: false,
        };
      }
    } else {
      addressValidation.value.postalCode = {
        isValid: false,
        message: t('register.postal_code_validation_error'),
        loading: false,
      };
    }
  } catch (error) {
    reportClientError('Error validating postal code', error);
    addressValidation.value.postalCode = {
      isValid: false,
      message: t('register.postal_code_validation_error'),
      loading: false,
    };
  }
};

const validateStreetNameField = async () => {
  const result = validateStreetName(form.value.address.streetName);

  if (!result.isValid) {
    // If basic validation fails, show the error
    addressValidation.value.streetName = {
      isValid: false,
      message: result.message,
    };
    // Reset cross-validation
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    return;
  }

  // Basic validation passed
  addressValidation.value.streetName = {
    isValid: true,
    message: '',
  };

  // Check if we can do cross-validation
  if (
    form.value.address.cityName &&
    form.value.address.countryId &&
    addressValidation.value.city.isValid === true
  ) {
    await validateStreetInCityField();
  } else {
    // Reset cross-validation if no city available
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
  }
};

// Advanced validation functions
const validateStreetInCityField = async () => {
  if (
    !form.value.address.streetName ||
    !form.value.address.cityName ||
    !form.value.address.countryId
  ) {
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    return;
  }

  addressValidation.value.streetInCity.loading = true;

  try {
    // Import the function dynamically to avoid unused import linting errors
    const result = await validateStreetInCity(
      form.value.address.streetName,
      form.value.address.cityName,
      form.value.address.countryId
    );

    if (result.success) {
      addressValidation.value.streetInCity = {
        isValid: result.data.isValid,
        message: result.data.message,
        loading: false,
        suggestions: result.data.suggestions || [],
      };
    } else {
      addressValidation.value.streetInCity = {
        isValid: false,
        message: t('register.street_validation_error'),
        loading: false,
      };
    }
  } catch (error) {
    reportClientError('Error validating street in city', error);
    addressValidation.value.streetInCity = {
      isValid: false,
      message: t('register.street_validation_error'),
      loading: false,
    };
  }
};

const validatePostalCodeInCityField = async () => {
  if (
    !form.value.address.postalCode ||
    !form.value.address.cityName ||
    !form.value.address.countryId
  ) {
    addressValidation.value.postalCodeInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    return;
  }

  addressValidation.value.postalCodeInCity.loading = true;

  try {
    // Import the function dynamically to avoid unused import linting errors
    const result = await validatePostalCodeInCity(
      form.value.address.postalCode,
      form.value.address.cityName,
      form.value.address.countryId
    );

    if (result.success) {
      addressValidation.value.postalCodeInCity = {
        isValid: result.data.isValid,
        message: result.data.message,
        loading: false,
        suggestions: result.data.suggestions || [],
      };
    } else {
      addressValidation.value.postalCodeInCity = {
        isValid: false,
        message: t('register.postal_code_city_validation_error'),
        loading: false,
      };
    }
  } catch (error) {
    reportClientError('Error validating postal code in city', error);
    addressValidation.value.postalCodeInCity = {
      isValid: false,
      message: t('register.postal_code_city_validation_error'),
      loading: false,
    };
  }
};

const onCountryChange = () => {
  validateField('countryId');

  // Reset all address validations when country changes
  addressValidation.value.city = { isValid: null, message: '', loading: false };
  addressValidation.value.postalCode = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.streetInCity = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.postalCodeInCity = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.fullAddress = {
    isValid: null,
    message: '',
    loading: false,
    confidence: null,
  };

  // Clear city and postal code values if they exist
  if (form.value.address.cityName) {
    form.value.address.cityName = '';
  }
  if (form.value.address.postalCode) {
    form.value.address.postalCode = '';
  }
};

// Trigger cross-validation when relevant fields change
const onCityChange = async () => {
  // Reset validations immediately on input
  addressValidation.value.city = { isValid: null, message: '', loading: false };
  addressValidation.value.streetInCity = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.postalCodeInCity = {
    isValid: null,
    message: '',
    loading: false,
  };

  // Debounce the validation to avoid too many API calls
  clearTimeout(cityValidationTimeout);
  cityValidationTimeout = setTimeout(async () => {
    if (form.value.address.cityName && form.value.address.countryId) {
      await validateCityField();
    }
  }, 500);
};

const onStreetNameChange = async () => {
  // Reset validations immediately on input
  addressValidation.value.streetName = { isValid: null, message: '' };
  addressValidation.value.streetInCity = {
    isValid: null,
    message: '',
    loading: false,
  };

  // Debounce the validation
  clearTimeout(streetValidationTimeout);
  streetValidationTimeout = setTimeout(async () => {
    if (form.value.address.streetName) {
      await validateStreetNameField();
    }
  }, 500);
};

const onPostalCodeChange = async () => {
  // Reset validations immediately on input
  addressValidation.value.postalCode = {
    isValid: null,
    message: '',
    loading: false,
  };
  addressValidation.value.postalCodeInCity = {
    isValid: null,
    message: '',
    loading: false,
  };

  // Debounce the validation
  clearTimeout(postalCodeValidationTimeout);
  postalCodeValidationTimeout = setTimeout(async () => {
    if (form.value.address.postalCode && form.value.address.countryId) {
      await validatePostalCodeField();
    }
  }, 500);
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

const validateInvitationCode = async () => {
  if (!invitationCode.value || invitationCode.value.length === 0) {
    invitationError.value = t('register.invitation_code_required');
    invitationValid.value = false;
    return;
  }

  invitationValidating.value = true;
  invitationError.value = '';

  try {
    const response = await validateInvitation(invitationCode.value);
    if (response.data.valid) {
      // Existing accounts review invitations after authentication. Validation
      // never grants project access by itself.
      if (response.data.user_exists) {
        eventMessageStore.addMessage(
          t('register.invitation_existing_user'),
          'info'
        );
        setTimeout(() => {
          router.push({ name: 'LoginPage' });
        }, 2000);
        return;
      }

      invitationValid.value = true;
      invitationInfo.value = response.data.invitation;

      // Pre-fill email if available and disable editing
      if (invitationInfo.value?.receiver_email) {
        form.value.email = invitationInfo.value.receiver_email;
        form.value.confirmEmail = invitationInfo.value.receiver_email;
      } else {
        form.value.email = '';
        form.value.confirmEmail = '';
      }

      eventMessageStore.addMessage(t('register.invitation_valid'), 'success');
    } else {
      invitationValid.value = false;
      invitationError.value =
        response.data.message || t('register.invitation_invalid');
    }
  } catch (error) {
    invitationValid.value = false;
    invitationError.value =
      error.response?.data?.detail || t('register.invitation_validation_error');
  } finally {
    invitationValidating.value = false;
  }
};

// Load countries from API
const loadCountries = async () => {
  try {
    const response = await getCountries();
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

const handleRegister = async () => {
  // Validate all fields first
  validateAllFields();

  // Check if form has any validation errors
  const hasErrors = Object.values(validationErrors.value).some(
    (error) => error
  );
  if (hasErrors) {
    eventMessageStore.addMessage(t('register.please_fix_errors'), 'error');
    return;
  }

  // Additional validations
  if (form.value.password !== form.value.confirmPassword) {
    eventMessageStore.addMessage(t('register.passwords_no_match'), 'error');
    return;
  }

  if (form.value.email !== form.value.confirmEmail) {
    eventMessageStore.addMessage(t('register.emails_no_match'), 'error');
    return;
  }

  if (form.value.password.length < 8) {
    eventMessageStore.addMessage(t('register.password_too_short'), 'error');
    return;
  }

  // Check username and email availability
  if (usernameAvailable.value === false) {
    eventMessageStore.addMessage(t('register.username_taken'), 'error');
    return;
  }

  if (emailAvailable.value === false) {
    eventMessageStore.addMessage(t('register.email_taken'), 'error');
    return;
  }

  loading.value = true;

  try {
    // Prepare address object if fields are filled
    let address = null;
    if (
      form.value.address.streetName &&
      form.value.address.cityName &&
      form.value.address.postalCode &&
      form.value.address.countryId
    ) {
      // Find the selected country to get its name
      const selectedCountry = countries.value.find(
        (country) => country.country_id === form.value.address.countryId
      );

      address = {
        street_name: form.value.address.streetName,
        street_number: form.value.address.streetNumber || null,
        city_name: form.value.address.cityName,
        country_code: form.value.address.countryId,
        country_name: selectedCountry?.country_name || '',
        postal_code: form.value.address.postalCode,
        address_line_2: form.value.address.addressLine2 || null,
      };
    }

    // API call for registration with invitation
    const payload = {
      invitation_code: invitationCode.value,
      first_name: form.value.firstName,
      last_name: form.value.lastName,
      username: form.value.username,
      email: form.value.email,
      password: form.value.password,
      phone_number: form.value.phoneNumber || null,
      affiliation: form.value.affiliation,
      department: form.value.department,
      address: address,
    };
    const response = await registerWithInvitation(payload);

    // Check if email verification is needed
    if (response.data && response.data.requires_activation) {
      eventMessageStore.addMessage(
        t('register.success_needs_verification'),
        'success'
      );

      // Redirect to email verification page
      router.push({
        name: 'EmailVerificationPage',
        query: {
          email: form.value.email,
          freshCode: 'true',
        },
      });
    } else {
      eventMessageStore.addMessage(t('register.success'), 'success');
      router.push({ name: 'LoginPage' });
    }
  } catch (error) {
    reportClientError('Registration error', error);
    eventMessageStore.addMessage(
      error?.response?.data?.detail || t('register.error'),
      'error'
    );
  } finally {
    loading.value = false;
  }
};

// Username availability check
watch(
  () => form.value.username,
  (newUsername) => {
    usernameAvailable.value = null;
    usernameCheckMessage.value = '';
    if (usernameCheckTimeout) clearTimeout(usernameCheckTimeout);
    validateField('username');
    if (
      !newUsername ||
      newUsername.length < 3 ||
      validationErrors.value.username
    )
      return;
    usernameCheckLoading.value = true;
    usernameCheckTimeout = setTimeout(async () => {
      try {
        const res = await checkUsernameAvailability(newUsername);
        usernameAvailable.value = res.available;
        usernameCheckMessage.value = res.message;
      } catch (e) {
        reportClientError('Username availability check error', e);
        usernameAvailable.value = null;
        usernameCheckMessage.value = t('register.username_check_error');
      } finally {
        usernameCheckLoading.value = false;
      }
    }, 500);
  }
);

// Email availability check
watch(
  () => form.value.email,
  (newEmail) => {
    emailAvailable.value = null;
    emailCheckMessage.value = '';
    if (emailCheckTimeout) clearTimeout(emailCheckTimeout);
    validateField('email');
    if (!newEmail || validationErrors.value.email) return;
    emailCheckLoading.value = true;
    emailCheckTimeout = setTimeout(async () => {
      try {
        const res = await checkEmailAvailability(newEmail);
        emailAvailable.value = res.available;
        emailCheckMessage.value = res.message;
      } catch (e) {
        reportClientError('Email availability check error', e);
        emailAvailable.value = null;
        emailCheckMessage.value = t('register.email_check_error');
      } finally {
        emailCheckLoading.value = false;
      }
    }, 500);
  }
);
</script>

<style scoped src="@/assets/css/register.css"></style>
