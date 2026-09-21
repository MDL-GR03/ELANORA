<template>
  <section
    class="settings-panel"
    aria-labelledby="installation-settings-heading"
  >
    <div class="panel-header">
      <h2 id="installation-settings-heading">
        <font-awesome-icon icon="fa-solid fa-gear" />
        {{ t('installation.settings') }}
      </h2>
      <p class="panel-description">{{ t('installation.description') }}</p>
    </div>

    <form class="settings-form" @submit.prevent="handleSubmit">
      <!-- Branding Section -->
      <fieldset class="form-section">
        <legend class="section-title">
          {{ t('installation.branding.title') }}
        </legend>

        <div class="form-grid">
          <div class="form-group">
            <label for="instance-name">{{
              t('installation.branding.instanceName')
            }}</label>
            <input
              id="instance-name"
              v-model="formData.instance_name"
              type="text"
              :placeholder="t('installation.branding.instanceNamePlaceholder')"
              :disabled="isLoading"
              aria-required="true"
              @change="trackChange('instance_name', formData.instance_name)"
            />
            <span v-if="errors.instance_name" class="error-message">
              {{ errors.instance_name }}
            </span>
          </div>

          <div class="form-group">
            <label for="institution-name">{{
              t('installation.branding.institutionName')
            }}</label>
            <input
              id="institution-name"
              v-model="formData.institution_name"
              type="text"
              :placeholder="
                t('installation.branding.institutionNamePlaceholder')
              "
              :disabled="isLoading"
              @change="
                trackChange('institution_name', formData.institution_name)
              "
            />
          </div>

          <div class="form-group full-width">
            <label for="contact-email">{{
              t('installation.branding.contactEmail')
            }}</label>
            <input
              id="contact-email"
              v-model="formData.contact_email"
              type="email"
              :placeholder="t('installation.branding.contactEmailPlaceholder')"
              :disabled="isLoading"
              @change="trackChange('contact_email', formData.contact_email)"
            />
          </div>
        </div>

        <!-- Color Theme -->
        <div class="color-theme">
          <h3>{{ t('installation.branding.colorTheme') }}</h3>
          <div class="color-pickers">
            <div class="color-picker">
              <label for="primary-color">{{
                t('installation.branding.primaryColor')
              }}</label>
              <div class="color-input">
                <input
                  id="primary-color"
                  v-model="formData.primary_color"
                  type="color"
                  :disabled="isLoading"
                  @change="trackChange('primary_color', formData.primary_color)"
                />
                <span class="color-value">{{ formData.primary_color }}</span>
              </div>
            </div>

            <div class="color-picker">
              <label for="secondary-color">{{
                t('installation.branding.secondaryColor')
              }}</label>
              <div class="color-input">
                <input
                  id="secondary-color"
                  v-model="formData.secondary_color"
                  type="color"
                  :disabled="isLoading"
                  @change="
                    trackChange('secondary_color', formData.secondary_color)
                  "
                />
                <span class="color-value">{{ formData.secondary_color }}</span>
              </div>
            </div>

            <div class="color-picker">
              <label for="accent-color">{{
                t('installation.branding.accentColor')
              }}</label>
              <div class="color-input">
                <input
                  id="accent-color"
                  v-model="formData.accent_color"
                  type="color"
                  :disabled="isLoading"
                  @change="trackChange('accent_color', formData.accent_color)"
                />
                <span class="color-value">{{ formData.accent_color }}</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            class="btn btn-secondary reset-colors"
            :disabled="isLoading"
            @click="resetColors"
          >
            <font-awesome-icon icon="fa-solid fa-undo" />
            {{ t('installation.branding.resetColors') }}
          </button>
        </div>
      </fieldset>

      <!-- General Settings Section -->
      <fieldset class="form-section">
        <legend class="section-title">
          {{ t('installation.general.title') }}
        </legend>

        <div class="form-grid">
          <div class="form-group">
            <label for="default-language">{{
              t('installation.general.defaultLanguage')
            }}</label>
            <select
              id="default-language"
              v-model="formData.default_language"
              :disabled="isLoading"
              @change="
                trackChange('default_language', formData.default_language)
              "
            >
              <option value="en">English</option>
              <option value="fr">Francais</option>
              <option value="ja">日本語</option>
            </select>
          </div>

          <div class="form-group">
            <label for="timezone">{{
              t('installation.general.timezone')
            }}</label>
            <select
              id="timezone"
              v-model="formData.timezone"
              :disabled="isLoading"
              @change="trackChange('timezone', formData.timezone)"
            >
              <option value="UTC">UTC</option>
              <option value="America/New_York">America/New_York</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="Europe/Paris">Europe/Paris</option>
              <option value="Asia/Tokyo">Asia/Tokyo</option>
            </select>
          </div>
        </div>
      </fieldset>

      <!-- Action Buttons -->
      <div class="form-actions">
        <button
          type="button"
          class="btn btn-text"
          :disabled="isLoading"
          @click="handleCancel"
        >
          {{ t('common.cancel') }}
        </button>

        <button
          type="submit"
          class="btn btn-primary"
          :disabled="isLoading || !hasChanges"
        >
          <font-awesome-icon v-if="isLoading" icon="fa-solid fa-spinner" spin />
          <span v-else>{{ t('common.save') }}</span>
        </button>
      </div>

      <!-- Success Message -->
      <div
        v-if="successMessage"
        class="alert alert-success"
        role="alert"
        aria-live="polite"
      >
        <font-awesome-icon icon="fa-solid fa-check-circle" />
        {{ successMessage }}
      </div>

      <!-- Error Message -->
      <div
        v-if="errorMessage"
        class="alert alert-error"
        role="alert"
        aria-live="assertive"
      >
        <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
        {{ errorMessage }}
      </div>
    </form>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useInstallationSettings } from '@/composables/useInstallationSettings';
import { DEFAULT_BRANDING } from '@/composables/useInstallationSettings';

const { t } = useI18n();

const {
  isLoading,
  changes,
  loadInstanceSettings,
  updateBranding,
  updateGeneralSettings,
  trackChange,
  clearChanges,
  isValidHexColor,
} = useInstallationSettings();

// Form data
const formData = ref({
  instance_name: '',
  institution_name: '',
  contact_email: '',
  primary_color: DEFAULT_BRANDING.primary_color,
  secondary_color: DEFAULT_BRANDING.secondary_color,
  accent_color: DEFAULT_BRANDING.accent_color,
  default_language: 'en',
  timezone: 'UTC',
});

// Messages
const successMessage = ref('');
const errorMessage = ref('');

// Errors
const errors = ref({
  instance_name: '',
  institution_name: '',
  contact_email: '',
  primary_color: '',
  secondary_color: '',
  accent_color: '',
});

// Computed
const hasChanges = computed(() => {
  return Object.keys(changes.value).length > 0;
});

const hasErrors = computed(() => {
  return Object.values(errors.value).some(Boolean);
});

// Methods
const loadData = async () => {
  try {
    const settings = await loadInstanceSettings();

    if (settings) {
      formData.value = {
        instance_name: settings.instance_name || '',
        institution_name: settings.institution_name || '',
        contact_email: settings.contact_email || '',
        primary_color: settings.primary_color || DEFAULT_BRANDING.primary_color,
        secondary_color:
          settings.secondary_color || DEFAULT_BRANDING.secondary_color,
        accent_color: settings.accent_color || DEFAULT_BRANDING.accent_color,
        default_language: settings.default_language || 'en',
        timezone: settings.timezone || 'UTC',
      };

      // Initialize changes tracking
      clearChanges();
    }
  } catch (err) {
    errorMessage.value = t('installation.loadError');
    console.error('Failed to load installation settings:', err);
  }
};

const handleSubmit = async () => {
  if (hasErrors.value) {
    return;
  }

  try {
    isLoading.value = true;
    errorMessage.value = '';
    successMessage.value = '';

    // Separate branding from general settings
    const brandingData = {
      instance_name: formData.value.instance_name,
      institution_name: formData.value.institution_name,
      contact_email: formData.value.contact_email,
      primary_color: formData.value.primary_color,
      secondary_color: formData.value.secondary_color,
      accent_color: formData.value.accent_color,
    };

    const generalData = {
      default_language: formData.value.default_language,
      timezone: formData.value.timezone,
    };

    // Update branding
    await updateBranding(brandingData);

    // Update general settings
    await updateGeneralSettings(generalData);

    successMessage.value = t('installation.saveSuccess');

    // Clear changes after successful save
    clearChanges();

    // Reload data to get fresh values
    await loadData();
  } catch (err) {
    errorMessage.value = t('installation.saveError');
    console.error('Failed to save installation settings:', err);
  } finally {
    isLoading.value = false;
  }
};

const handleCancel = () => {
  // Reset form data to original values
  loadData();
  clearChanges();
  errorMessage.value = '';
  successMessage.value = '';
};

const resetColors = () => {
  formData.value.primary_color = DEFAULT_BRANDING.primary_color;
  formData.value.secondary_color = DEFAULT_BRANDING.secondary_color;
  formData.value.accent_color = DEFAULT_BRANDING.accent_color;

  trackChange('primary_color', formData.value.primary_color);
  trackChange('secondary_color', formData.value.secondary_color);
  trackChange('accent_color', formData.value.accent_color);
};

// Validate form fields
watch(
  () => [
    formData.value.instance_name,
    formData.value.institution_name,
    formData.value.contact_email,
    formData.value.primary_color,
    formData.value.secondary_color,
    formData.value.accent_color,
  ],
  () => {
    errors.value.instance_name = formData.value.instance_name
      ? ''
      : t('installation.branding.instanceNameRequired');
    errors.value.institution_name = formData.value.institution_name
      ? ''
      : t('installation.branding.institutionNameRequired');
    errors.value.contact_email = formData.value.contact_email
      ? ''
      : t('installation.branding.contactEmailRequired');
    errors.value.primary_color = isValidHexColor(formData.value.primary_color)
      ? ''
      : t('installation.branding.invalidColor');
    errors.value.secondary_color = isValidHexColor(
      formData.value.secondary_color
    )
      ? ''
      : t('installation.branding.invalidColor');
    errors.value.accent_color = isValidHexColor(formData.value.accent_color)
      ? ''
      : t('installation.branding.invalidColor');
  },
  { deep: true, immediate: true }
);

// Load data on mount
onMounted(() => {
  loadData();
});
</script>

<style scoped>
/* Use CSS variables from _variables.css */
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 1.5rem);
  padding: var(--spacing-lg, 1.5rem);
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #dfe6ee);
  border-radius: var(--radius-lg, 1rem);
  box-shadow: 0 0.3rem 1rem rgb(15 23 42 / 5%);
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 0.5rem);
  margin-bottom: var(--spacing-md, 1rem);
  padding-bottom: var(--spacing-md, 1rem);
  border-bottom: 1px solid var(--color-border-subtle, #e5e7eb);
}

.panel-header h2 {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 1rem);
  margin: 0;
  color: var(--color-text, #172033);
  font-size: var(--text-xl, 1.25rem);
  font-weight: 700;
}

.panel-description {
  margin: 0;
  color: var(--color-text-muted, #64748b);
  font-size: var(--text-base, 1rem);
  line-height: 1.5;
}

/* Form Sections */
.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 1rem);
  margin: 0;
  padding: 0;
  border: none;
}

.section-title {
  color: var(--color-text, #172033);
  font-size: var(--text-lg, 1.125rem);
  font-weight: 700;
  padding: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
  gap: var(--spacing-lg, 1.5rem);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs, 0.375rem);
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  color: var(--color-text, #172033);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
}

.form-group input,
.form-group select {
  padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 1rem);
  border: 1px solid var(--color-border, #dfe6ee);
  border-radius: var(--radius-md, 0.75rem);
  background: var(--color-surface, #fff);
  color: var(--color-text, #172033);
  font-size: var(--text-base, 1rem);
  transition:
    border-color var(--transition-fast, 0.15s) ease,
    box-shadow var(--transition-fast, 0.15s) ease;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-primary, #2563eb);
  box-shadow: 0 0 0 3px var(--color-primary-bg, #edf4ff);
}

.form-group input:hover:not(:focus),
.form-group select:hover:not(:focus) {
  border-color: var(--color-border-strong, #cbd5e1);
}

.form-group input:disabled,
.form-group select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: var(--color-surface-subtle, #f8fafc);
}

/* Color Theme */
.color-theme {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 1rem);
  padding: var(--spacing-md, 1rem);
  background: var(--color-surface-subtle, #f8fafc);
  border-radius: var(--radius-md, 0.75rem);
}

.color-theme h3 {
  margin: 0;
  color: var(--color-text, #172033);
  font-size: var(--text-base, 1rem);
  font-weight: 600;
}

.color-pickers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: var(--spacing-md, 1rem);
}

.color-picker {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs, 0.375rem);
}

.color-picker label {
  color: var(--color-text, #172033);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
}

.color-input {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 1rem);
}

.color-input input[type='color'] {
  width: var(--size-10, 2.5rem);
  height: var(--size-10, 2.5rem);
  border: 2px solid var(--color-border, #dfe6ee);
  border-radius: var(--radius-md, 0.75rem);
  background: var(--color-surface, #fff);
  cursor: pointer;
  padding: 0;
  overflow: hidden;
}

.color-input input[type='color']:focus {
  outline: none;
  border-color: var(--color-primary, #2563eb);
  box-shadow: 0 0 0 3px var(--color-primary-bg, #edf4ff);
}

.color-value {
  color: var(--color-text-muted, #64748b);
  font-size: var(--text-sm, 0.875rem);
  font-family: monospace;
}

.reset-colors {
  align-self: flex-start;
  margin-top: var(--spacing-sm, 0.5rem);
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md, 1rem);
  margin-top: var(--spacing-lg, 1.5rem);
  padding-top: var(--spacing-lg, 1.5rem);
  border-top: 1px solid var(--color-border-subtle, #e5e7eb);
}

/* Alerts */
.alert {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 1rem);
  padding: var(--spacing-md, 1rem);
  border-radius: var(--radius-md, 0.75rem);
  margin-top: var(--spacing-md, 1rem);
  font-size: var(--text-sm, 0.875rem);
}

.alert-success {
  background: var(--color-success-bg-subtle, #f0fdf4);
  border: 1px solid var(--color-success-bg, #dcfce7);
  color: var(--color-success-dark, #14532d);
}

.alert-error {
  background: var(--color-error-bg-subtle, #fef2f2);
  border: 1px solid var(--color-error-bg, #fee2e2);
  color: var(--color-error-dark, #991b1b);
}

/* Error Messages */
.error-message {
  color: var(--color-error, #b91c1c);
  font-size: var(--text-xs, 0.75rem);
  margin-top: var(--spacing-xs, 0.25rem);
}

/* Responsive */
@media (width <= 48rem) {
  .settings-panel {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .color-pickers {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-wrap: wrap;
    justify-content: stretch;
  }

  .form-actions .btn {
    flex: 1;
    min-width: 10rem;
  }
}
</style>
