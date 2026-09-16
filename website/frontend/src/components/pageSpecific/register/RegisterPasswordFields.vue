<template>
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
            error: errors.password,
            valid: form.password && !errors.password && strength !== 'weak',
          }"
          :placeholder="t('register.password_placeholder')"
          :aria-invalid="Boolean(errors.password)"
          aria-describedby="password-message"
          required
          autocomplete="new-password"
          @focus="requirementsVisible = true"
          @blur="
            requirementsVisible = false;
            emit('validate', 'password');
          "
          @input="emit('password-input')"
        />
        <button
          type="button"
          class="password-toggle"
          :title="
            showPassword
              ? t('register.hide_password')
              : t('register.show_password')
          "
          @click="showPassword = !showPassword"
        >
          {{ showPassword ? '👁️' : '👁️‍🗨️' }}
        </button>
      </div>

      <div v-if="form.password" class="password-strength">
        <div class="strength-bar">
          <div
            class="strength-fill"
            :class="`strength-${strength}`"
            :style="{ width: strengthWidth }"
          ></div>
        </div>
        <span class="strength-text" :class="`strength-${strength}`">
          {{ t(`register.password_strength_${strength}`) }}
        </span>
      </div>

      <div v-if="requirementsVisible" class="password-requirements">
        <div class="requirements-title">
          {{ t('register.password_requirements_title') }}
        </div>
        <div
          v-for="requirement in REQUIREMENTS"
          :key="requirement"
          class="requirement-item"
          :class="{ met: checks[requirement] }"
        >
          <span class="check-icon">{{ checks[requirement] ? '✓' : '✗' }}</span>
          {{ t(`register.password_requirement_${requirement}`) }}
        </div>
      </div>

      <div id="password-message" class="validation-messages">
        <div v-if="errors.password" class="error-message" role="alert">
          <i class="error-icon-small">⚠</i>{{ errors.password }}
        </div>
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
            error: errors.confirmPassword,
            valid: form.confirmPassword && !errors.confirmPassword && matches,
          }"
          :placeholder="t('register.confirm_password_placeholder')"
          :aria-invalid="Boolean(errors.confirmPassword)"
          aria-describedby="confirm-password-message"
          required
          autocomplete="new-password"
          @blur="emit('validate', 'confirmPassword')"
        />
        <button
          type="button"
          class="password-toggle"
          :title="
            showConfirmPassword
              ? t('register.hide_password')
              : t('register.show_password')
          "
          @click="showConfirmPassword = !showConfirmPassword"
        >
          {{ showConfirmPassword ? '👁️' : '👁️‍🗨️' }}
        </button>
      </div>
      <div id="confirm-password-message" class="validation-messages">
        <div v-if="errors.confirmPassword" class="error-message" role="alert">
          <i class="error-icon-small">⚠</i>{{ errors.confirmPassword }}
        </div>
        <div
          v-else-if="form.confirmPassword && matches"
          class="success-message"
        >
          <i class="success-icon-small">✓</i>{{ t('register.passwords_match') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  passwordChecksOf,
  passwordStrengthOf,
} from '@/utils/registrationValidation';

const REQUIREMENTS = ['length', 'lowercase', 'uppercase', 'number', 'special'];

const STRENGTH_WIDTH = { weak: '33%', medium: '66%', strong: '100%' };

const form = defineModel({ type: Object, required: true });

defineProps({
  errors: { type: Object, required: true },
});

const emit = defineEmits(['validate', 'password-input']);

const { t } = useI18n();

const showPassword = ref(false);
const showConfirmPassword = ref(false);
const requirementsVisible = ref(false);

const strength = computed(() => passwordStrengthOf(form.value.password));
const strengthWidth = computed(() => STRENGTH_WIDTH[strength.value]);
const checks = computed(() => passwordChecksOf(form.value.password));
const matches = computed(
  () => form.value.password === form.value.confirmPassword
);
</script>
