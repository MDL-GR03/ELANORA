<template>
  <div class="register-identity">
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
            error: errors.firstName,
            valid: form.firstName && !errors.firstName,
          }"
          :placeholder="t('register.first_name_placeholder')"
          :aria-invalid="Boolean(errors.firstName)"
          aria-describedby="first-name-message"
          required
          @blur="emit('validate', 'firstName')"
        />
        <div id="first-name-message" class="validation-messages">
          <div v-if="errors.firstName" class="error-message" role="alert">
            {{ errors.firstName }}
          </div>
          <div v-else-if="form.firstName" class="success-message">✓</div>
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
            error: errors.lastName,
            valid: form.lastName && !errors.lastName,
          }"
          :placeholder="t('register.last_name_placeholder')"
          :aria-invalid="Boolean(errors.lastName)"
          aria-describedby="last-name-message"
          required
          @blur="emit('validate', 'lastName')"
        />
        <div id="last-name-message" class="validation-messages">
          <div v-if="errors.lastName" class="error-message" role="alert">
            {{ errors.lastName }}
          </div>
          <div v-else-if="form.lastName" class="success-message">✓</div>
        </div>
      </div>
    </div>

    <div class="form-group">
      <label for="username" class="form-label">
        {{ t('register.username_label') }}
        <span class="required">*</span>
        <span class="field-requirements">{{
          t('register.username_requirements')
        }}</span>
      </label>
      <div class="input-with-indicator">
        <input
          id="username"
          v-model="form.username"
          type="text"
          class="form-input"
          :class="{
            error: errors.username || available === false,
            valid: available === true && !errors.username,
            loading: checking,
          }"
          :placeholder="t('register.username_placeholder')"
          :aria-invalid="Boolean(errors.username) || available === false"
          aria-describedby="username-message"
          required
          autocomplete="username"
          maxlength="20"
          @blur="emit('validate', 'username')"
          @input="emit('username-input')"
        />
        <div class="input-indicator">
          <div v-if="checking" class="loading-spinner"></div>
        </div>
      </div>
      <div id="username-message" class="validation-messages">
        <div v-if="errors.username" class="error-message" role="alert">
          <i class="error-icon-small">⚠</i>{{ errors.username }}
        </div>
        <div v-else-if="checking" class="info-message">
          <div class="loading-dot"></div>
          {{ t('register.checking_username') }}
        </div>
        <div v-else-if="available === true" class="success-message">
          <i class="success-icon-small">✓</i>{{ message }}
        </div>
        <div v-else-if="available === false" class="error-message" role="alert">
          <i class="error-icon-small">✗</i>{{ message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

const form = defineModel({ type: Object, required: true });

defineProps({
  errors: { type: Object, required: true },
  available: { type: Boolean, default: null },
  checking: { type: Boolean, default: false },
  message: { type: String, default: '' },
});

const emit = defineEmits(['validate', 'username-input']);

const { t } = useI18n();
</script>
