<template>
  <section class="settings-panel" aria-labelledby="database-config-heading">
    <div class="panel-header">
      <h2 id="database-config-heading">
        <font-awesome-icon icon="fa-solid fa-database" />
        {{ t('database.configuration') }}
      </h2>
      <p class="panel-description">{{ t('database.description') }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="settings-form">
      <!-- Storage & Limits Section -->
      <fieldset class="form-section">
        <legend class="section-title">{{ t('database.storage.title') }}</legend>
        
        <div class="form-grid">
          <div class="form-group">
            <label for="max-file-size">
              {{ t('database.storage.maxFileSize') }}
              <span class="hint">{{ t('database.storage.maxFileSizeHint') }}</span>
            </label>
            <div class="input-with-unit">
              <input
                id="max-file-size"
                v-model.number="formData.max_file_size_mb"
                type="number"
                min="1"
                max="10000"
                step="0.01"
                @change="trackChange('max_file_size_mb', formData.max_file_size_mb)"
                :disabled="isLoading"
              />
              <span class="unit">MB</span>
            </div>
            <span v-if="errors.max_file_size_mb" class="error-message">
              {{ errors.max_file_size_mb }}
            </span>
          </div>

          <div class="form-group">
            <label for="max-users">
              {{ t('database.storage.maxUsers') }}
              <span class="hint">{{ t('database.storage.maxUsersHint') }}</span>
            </label>
            <input
              id="max-users"
              v-model.number="formData.max_users"
              type="number"
              min="1"
              max="100000"
              @change="trackChange('max_users', formData.max_users)"
              :disabled="isLoading"
            />
            <span v-if="errors.max_users" class="error-message">
              {{ errors.max_users }}
            </span>
          </div>

          <div class="form-group full-width">
            <label for="timezone">{{ t('database.storage.timezone') }}</label>
            <select
              id="timezone"
              v-model="formData.timezone"
              @change="trackChange('timezone', formData.timezone)"
              :disabled="isLoading"
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

      <!-- System Settings Section -->
      <fieldset class="form-section">
        <legend class="section-title">{{ t('database.system.title') }}</legend>
        
        <div class="form-grid">
          <div class="form-group">
            <label for="default-language">{{ t('database.system.defaultLanguage') }}</label>
            <select
              id="default-language"
              v-model="formData.default_language"
              @change="trackChange('default_language', formData.default_language)"
              :disabled="isLoading"
            >
              <option value="en">English</option>
              <option value="fr">Francais</option>
              <option value="ja">日本語</option>
            </select>
          </div>

          <div class="form-group">
            <label for="is-active">
              {{ t('database.system.isActive') }}
              <span class="hint">{{ t('database.system.isActiveHint') }}</span>
            </label>
            <select
              id="is-active"
              v-model="formData.is_active"
              @change="trackChange('is_active', formData.is_active)"
              :disabled="isLoading"
            >
              <option :value="true">{{ t('common.yes') }}</option>
              <option :value="false">{{ t('common.no') }}</option>
            </select>
          </div>
        </div>
      </fieldset>

      <!-- Restart Warning -->
      <div
        v-if="warnings.length > 0"
        class="alert alert-warning"
        role="alert"
        aria-live="polite"
      >
        <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
        <div>
          <strong>{{ t('database.warning') }}</strong>
          <p>{{ warnings[0].message }}</p>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="form-actions">
        <button
          type="button"
          class="btn btn-text"
          @click="handleCancel"
          :disabled="isLoading"
        >
          {{ t('common.cancel') }}
        </button>
        
        <button
          type="button"
          class="btn btn-secondary"
          @click="handleReset"
          :disabled="isLoading"
        >
          <font-awesome-icon icon="fa-solid fa-undo" />
          {{ t('common.reset') }}
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
        <div>
          <strong>{{ successMessage }}</strong>
          <p v-if="restartRequired">{{ t('database.restartNote') }}</p>
        </div>
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
import { useDatabaseConfiguration } from '@/composables/useDatabaseConfiguration';
import { DEFAULT_DATABASE_CONFIG, RESTART_REQUIRED_SETTINGS } from '@/composables/useDatabaseConfiguration';

const { t } = useI18n();

const {
  databaseConfig,
  isLoading,
  error,
  changes,
  restartRequired,
  warnings,
  loadDatabaseConfiguration,
  updateDatabaseConfiguration,
  trackChange,
  clearChanges,
  validateConfigValue,
  validateAllChanges,
  requiresRestart,
} = useDatabaseConfiguration();

// Form data
const formData = ref({
  max_file_size_mb: DEFAULT_DATABASE_CONFIG.max_file_size_mb,
  max_users: DEFAULT_DATABASE_CONFIG.max_users,
  timezone: DEFAULT_DATABASE_CONFIG.timezone,
  default_language: DEFAULT_DATABASE_CONFIG.default_language,
  is_active: true,
});

// Messages
const successMessage = ref('');
const errorMessage = ref('');

// Errors
const errors = ref({
  max_file_size_mb: '',
  max_users: '',
});

// Computed
const hasChanges = computed(() => {
  return Object.keys(changes.value).length > 0;
});

const hasErrors = computed(() => {
  return Object.values(errors.value).some(Boolean);
});

const restartRequiredForSave = computed(() => {
  return changesRequiringRestart.value.length > 0;
});

const changesRequiringRestart = computed(() => {
  return Object.keys(changes.value).filter(key => RESTART_REQUIRED_SETTINGS.includes(key));
});

// Methods
const loadData = async () => {
  try {
    const config = await loadDatabaseConfiguration();
    
    if (config) {
      formData.value = {
        max_file_size_mb: config.max_file_size_mb || DEFAULT_DATABASE_CONFIG.max_file_size_mb,
        max_users: config.max_users || DEFAULT_DATABASE_CONFIG.max_users,
        timezone: config.timezone || DEFAULT_DATABASE_CONFIG.timezone,
        default_language: config.default_language || DEFAULT_DATABASE_CONFIG.default_language,
        is_active: config.is_active !== undefined ? config.is_active : true,
      };
      
      // Initialize changes tracking
      clearChanges();
    }
  } catch (err) {
    errorMessage.value = t('database.loadError');
    console.error('Failed to load database configuration:', err);
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

    const configData = {
      max_file_size_mb: formData.value.max_file_size_mb,
      max_users: formData.value.max_users,
      timezone: formData.value.timezone,
      default_language: formData.value.default_language,
      is_active: formData.value.is_active,
    };

    const result = await updateDatabaseConfiguration(configData);
    
    if (result.restartRequired) {
      successMessage.value = t('database.saveSuccessWithRestart');
    } else {
      successMessage.value = t('database.saveSuccess');
    }
    
    // Clear changes after successful save
    clearChanges();

    // Reload data to get fresh values
    await loadData();
  } catch (err) {
    errorMessage.value = t('database.saveError');
    console.error('Failed to save database configuration:', err);
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

const handleReset = () => {
  formData.value = {
    max_file_size_mb: DEFAULT_DATABASE_CONFIG.max_file_size_mb,
    max_users: DEFAULT_DATABASE_CONFIG.max_users,
    timezone: DEFAULT_DATABASE_CONFIG.timezone,
    default_language: DEFAULT_DATABASE_CONFIG.default_language,
    is_active: true,
  };
  
  // Track all as changes
  Object.keys(formData.value).forEach(key => {
    trackChange(key, formData.value[key]);
  });
};

// Validate form fields
watch(
  () => [
    formData.value.max_file_size_mb,
    formData.value.max_users,
  ],
  () => {
    errors.value.max_file_size_mb = validateConfigValue(
      'max_file_size_mb',
      formData.value.max_file_size_mb
    ) ? '' : t('database.storage.invalidMaxFileSize');
    errors.value.max_users = validateConfigValue(
      'max_users',
      formData.value.max_users
    ) ? '' : t('database.storage.invalidMaxUsers');
  },
  { deep: true, immediate: true }
);

// Track restart requirement
watch(
  () => changes.value,
  () => {
    if (restartRequiredForSave.value) {
      // Show warning
    }
  },
  { deep: true }
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
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 0.5rem);
  color: var(--color-text, #172033);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
}

.hint {
  color: var(--color-text-muted, #64748b);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 400;
}

.input-with-unit {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 0.5rem);
}

.input-with-unit .unit {
  color: var(--color-text-muted, #64748b);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  white-space: nowrap;
}

.form-group input,
.form-group select {
  padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 1rem);
  border: 1px solid var(--color-border, #dfe6ee);
  border-radius: var(--radius-md, 0.75rem);
  background: var(--color-surface, #fff);
  color: var(--color-text, #172033);
  font-size: var(--text-base, 1rem);
  transition: border-color var(--transition-fast, 0.15s) ease,
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
  align-items: flex-start;
  gap: var(--spacing-md, 1rem);
  padding: var(--spacing-md, 1rem);
  border-radius: var(--radius-md, 0.75rem);
  margin-top: var(--spacing-md, 1rem);
  font-size: var(--text-sm, 0.875rem);
}

.alert-warning {
  background: var(--color-warning-bg-subtle, #fffbeb);
  border: 1px solid var(--color-warning-bg, #fef3c7);
  color: var(--color-warning-dark, #7a4b00);
}

.alert-success {
  background: var(--color-success-bg-subtle, #f0fdf4);
  border: 1px solid var(--color-success-bg, #dcfce7);
  color: var(--color-success-dark, #14532d);
}

.alert-success p {
  margin: var(--spacing-xs, 0.25rem) 0 0;
  font-size: var(--text-xs, 0.75rem);
}

.alert-error {
  background: var(--color-error-bg-subtle, #fef2f2);
  border: 1px solid var(--color-error-bg, #fee2e2);
  color: var(--color-error-dark, #991b1b);
}

.alert-error p {
  margin: 0;
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

  .form-actions {
    flex-wrap: wrap;
    justify-content: stretch;
  }

  .form-actions .btn {
    flex: 1;
    min-width: 10rem;
  }

  .input-with-unit {
    flex-wrap: wrap;
  }

  .input-with-unit .unit {
    width: 100%;
    order: 3;
  }
}
</style>
