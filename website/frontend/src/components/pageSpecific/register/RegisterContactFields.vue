<template>
  <div class="register-contact">
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
            error: errors.email || available === false,
            valid: available === true && !errors.email,
            loading: checking,
          }"
          :placeholder="t('register.email_placeholder')"
          :aria-invalid="Boolean(errors.email) || available === false"
          aria-describedby="email-message"
          required
          :disabled="emailFixedByInvitation"
          @blur="emit('validate', 'email')"
          @input="emit('email-input')"
        />
        <div class="input-indicator">
          <div v-if="checking" class="loading-spinner"></div>
        </div>
      </div>
      <div id="email-message" class="validation-messages">
        <div v-if="errors.email" class="error-message" role="alert">
          <i class="error-icon-small">⚠</i>{{ errors.email }}
        </div>
        <div v-else-if="checking" class="info-message">
          <div class="loading-dot"></div>
          {{ t('register.checking_email') }}
        </div>
        <div v-else-if="available === true" class="success-message">
          <i class="success-icon-small">✓</i>{{ message }}
        </div>
        <div v-else-if="available === false" class="error-message" role="alert">
          <i class="error-icon-small">✗</i>{{ message }}
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
          error: errors.confirmEmail,
          valid: form.confirmEmail && !errors.confirmEmail && emailsMatch,
        }"
        :placeholder="t('register.confirm_email_placeholder')"
        :aria-invalid="Boolean(errors.confirmEmail)"
        aria-describedby="confirm-email-message"
        required
        :disabled="emailFixedByInvitation"
        @blur="emit('validate', 'confirmEmail')"
      />
      <div id="confirm-email-message" class="validation-messages">
        <div v-if="errors.confirmEmail" class="error-message" role="alert">
          <i class="error-icon-small">⚠</i>{{ errors.confirmEmail }}
        </div>
        <div
          v-else-if="form.confirmEmail && emailsMatch"
          class="success-message"
        >
          <i class="success-icon-small">✓</i>{{ t('register.emails_match') }}
        </div>
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
          error: errors.phoneNumber,
          valid: form.phoneNumber && !errors.phoneNumber,
        }"
        :placeholder="t('register.phone_placeholder')"
        :aria-invalid="Boolean(errors.phoneNumber)"
        aria-describedby="phone-message"
        @blur="emit('validate', 'phoneNumber')"
      />
      <div id="phone-message" class="validation-messages">
        <div v-if="errors.phoneNumber" class="error-message" role="alert">
          {{ errors.phoneNumber }}
        </div>
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
          error: errors.affiliation,
          valid: form.affiliation && !errors.affiliation,
        }"
        :placeholder="t('register.affiliation_placeholder')"
        :aria-invalid="Boolean(errors.affiliation)"
        aria-describedby="affiliation-message"
        required
        @blur="emit('validate', 'affiliation')"
      />
      <div id="affiliation-message" class="validation-messages">
        <div v-if="errors.affiliation" class="error-message" role="alert">
          {{ errors.affiliation }}
        </div>
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
          error: errors.department,
          valid: form.department && !errors.department,
        }"
        :placeholder="t('register.department_placeholder')"
        :aria-invalid="Boolean(errors.department)"
        aria-describedby="department-message"
        required
        @blur="emit('validate', 'department')"
      />
      <div id="department-message" class="validation-messages">
        <div v-if="errors.department" class="error-message" role="alert">
          {{ errors.department }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const form = defineModel({ type: Object, required: true });

defineProps({
  errors: { type: Object, required: true },
  available: { type: Boolean, default: null },
  checking: { type: Boolean, default: false },
  message: { type: String, default: '' },
  emailFixedByInvitation: { type: Boolean, default: false },
});

const emit = defineEmits(['validate', 'email-input']);

const { t } = useI18n();

const emailsMatch = computed(
  () => form.value.email === form.value.confirmEmail
);
</script>
